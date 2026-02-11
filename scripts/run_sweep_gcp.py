#!/usr/bin/env python3
"""
run_sweep_gcp.py (Threaded / Work-Stealing Version)

This script runs multiple inference configurations ("runs") in parallel using a thread pool.
It implements a dynamic work-stealing scheduler:
- Each prompt is a task.
- Workers write to thread-local temporary files for each run (avoids locking output file).
- At shutdown, temporary files are merged into the main output.
- Resume logic checks both main output and existing temporary files.
"""

import argparse
import datetime
import json
import os
import threading
import time
import sys
import shutil
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Set

from tqdm import tqdm

try:
    import run_inference_gcp
    # Ensure we have access to necessary classes/functions
    from run_inference_gcp import (
        RetryConfig, 
        build_client, 
        process_one_prompt, 
        read_jsonl, 
        should_keep, 
        load_done_ids
    )
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import run_inference_gcp
    from run_inference_gcp import (
        RetryConfig, 
        build_client, 
        process_one_prompt, 
        read_jsonl, 
        should_keep, 
        load_done_ids
    )


def load_config(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    if ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise RuntimeError("YAML config requested but PyYAML not installed.")
        return yaml.safe_load(txt)
    return json.loads(txt) # Handle JSONL or JSON


def project_root() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, os.pardir))


def abspath_from_root(p: str) -> str:
    if not p: return p
    if os.path.isabs(p): return p
    return os.path.abspath(os.path.join(project_root(), p))


def create_args_namespace(common_cfg: Dict, run_cfg: Dict, io_cfg: Dict, filters_cfg: Dict) -> SimpleNamespace:
    merged = {}
    
    defaults = {
        "temperature": 0.0,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 256,
        "seed": None,
        "json_mode": False,
        "sc_samples": 5,
        "sc_prefer_non_unknown": False,
        "stop_sequences": None,
        "api_version": "v1",
        "timeout_ms": None,
        "decoding": "greedy",
        "max_retries": 6,
        "retry_base_delay_s": 1.0,
        "retry_max_delay_s": 300.0,
        "retry_jitter": 0.3,
        "limit": 0,
        "resume": False,
        "prompts_path": None,
        "out_path": None,
        "filter_prompting_strategy": None,
        "filter_graph_variant": None,
        "filter_hop": None,
        
        # Auth / Vertex defaults
        "use_vertexai": False,
        "project": None,
        "location": None,
        "service_account_json": None,
        "service_account_scopes": None,
        "api_key": None
    }
    merged.update(defaults)
    merged.update(common_cfg)

    if "prompts_path" in io_cfg:
        merged["prompts_path"] = abspath_from_root(io_cfg["prompts_path"])
    
    if "resume" in io_cfg:
        merged["resume"] = bool(io_cfg["resume"])
    
    if "prompting_strategy" in filters_cfg:
        merged["filter_prompting_strategy"] = [str(x) for x in filters_cfg["prompting_strategy"]]
    if "graph_variant" in filters_cfg:
        merged["filter_graph_variant"] = [str(x) for x in filters_cfg["graph_variant"]]
    if "hop" in filters_cfg:
        merged["filter_hop"] = [int(x) for x in filters_cfg["hop"]]

    merged.update(run_cfg)
    
    if merged.get("service_account_json"):
        merged["service_account_json"] = abspath_from_root(merged["service_account_json"])
    
    if "out_dir" in io_cfg and "model" in merged:
        base = abspath_from_root(io_cfg["out_dir"])
        dec = merged.get("decoding", "greedy")
        path = os.path.join(base, merged["model"], dec, "responses.jsonl")
        merged["out_path"] = path

    return SimpleNamespace(**merged)


class Scheduler:
    def __init__(self):
        self.lock = threading.Lock()
        self.queues = {}     # run_idx -> deque
        self.clients = {}    # run_idx -> client
        self.retry_cfgs = {} # run_idx -> retry_cfg
        self.auth_infos = {} # run_idx -> auth_info
        self.args_map = {}   # run_idx -> args
        self.out_paths = {}  # run_idx -> str (final output path)
        
        self.todo_counts = {} # run_idx -> int
        self.total_processed = 0
        self.total_errors = 0
        self.pbar = None
        
        # Resume sets (loaded from main + tmp files)
        self.done_sets = {} # run_idx -> set of prompt_ids

    def load_resume_state(self, run_idx, out_path):
        """
        Custom load_done_ids that checks out_path AND out_path + ".part*"
        """
        # load_done_ids from run_inference_gcp already scans partial files
        # in the directory (responses.jsonl.part*).
        # So we just call it directly.
        done = load_done_ids(out_path)
        self.done_sets[run_idx] = done

    def register_run(self, run_idx, args, client, auth_info, retry_cfg):
        self.clients[run_idx] = client
        self.auth_infos[run_idx] = auth_info
        self.retry_cfgs[run_idx] = retry_cfg
        self.args_map[run_idx] = args
        self.out_paths[run_idx] = args.out_path
        self.queues[run_idx] = deque()
        self.todo_counts[run_idx] = 0
        
        os.makedirs(os.path.dirname(args.out_path), exist_ok=True)
        
        # Load resume state
        if getattr(args, "resume", False):
            self.load_resume_state(run_idx, args.out_path)
        else:
            self.done_sets[run_idx] = set()

    def add_task(self, run_idx, prompt_obj):
        pid = str(prompt_obj.get("prompt_id") or "")
        # Resume check
        if pid and pid in self.done_sets[run_idx]:
            return # Skip
            
        self.queues[run_idx].append(prompt_obj)
        self.todo_counts[run_idx] += 1

    def get_task(self, preferred_run_idx) -> Tuple[Optional[int], Any]:
        with self.lock:
            # 1. Try preferred
            q = self.queues.get(preferred_run_idx)
            if q and len(q) > 0:
                self.todo_counts[preferred_run_idx] -= 1
                return preferred_run_idx, q.popleft()
            
            # 2. Help the most behind (largest queue)
            best_idx = -1
            max_len = 0
            for r_idx, dq in self.queues.items():
                if len(dq) > max_len:
                    max_len = len(dq)
                    best_idx = r_idx
            
            if best_idx != -1:
                self.todo_counts[best_idx] -= 1
                return best_idx, self.queues[best_idx].popleft()
            
            return None, None

    def update_stats(self, success: bool):
        with self.lock:
            self.total_processed += 1
            if not success:
                self.total_errors += 1
            if self.pbar:
                self.pbar.update(1)
                self.pbar.set_postfix_str(f"err={self.total_errors}")


class WorkerContext:
    def __init__(self, scheduler: Scheduler, worker_id: int):
        self.scheduler = scheduler
        self.worker_id = worker_id
        # Cache open file handles: { run_idx: file_handle }
        self.file_handles = {}

    def get_handle(self, run_idx: int):
        if run_idx in self.file_handles:
            return self.file_handles[run_idx]
        
        # Open new handle: out_path + ".part_workerID"
        base_path = self.scheduler.out_paths[run_idx]
        part_path = f"{base_path}.part_{self.worker_id}"
        
        f = open(part_path, "a", encoding="utf-8")
        self.file_handles[run_idx] = f
        return f

    def close(self):
        for f in self.file_handles.values():
            try:
                f.close()
            except:
                pass


def worker_main(scheduler: Scheduler, initial_run_idx: int, worker_id: int):
    ctx = WorkerContext(scheduler, worker_id)
    try:
        while True:
            run_idx, prompt_obj = scheduler.get_task(initial_run_idx)
            if run_idx is None:
                break
            
            try:
                client = scheduler.clients[run_idx]
                args = scheduler.args_map[run_idx]
                retry_cfg = scheduler.retry_cfgs[run_idx]
                auth_info = scheduler.auth_infos[run_idx]
                
                # Execute
                out = process_one_prompt(client, prompt_obj, args, retry_cfg, auth_info)
                
                # Write to temp file
                f = ctx.get_handle(run_idx)
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
                f.flush()
                
                scheduler.update_stats(success=not out.get("error"))
                
            except Exception as e:
                # Fallback logging if catastrophic failure in process_one_prompt
                # We still want to count it
                scheduler.update_stats(success=False)
                # Maybe print?
                # print(f"Error in W{worker_id} R{run_idx}: {e}")

    finally:
        ctx.close()


def merge_results(scheduler: Scheduler):
    """
    Merge all .part_* files into the main output file for each run.
    """
    print("Merging temporary files...")
    for run_idx, out_path in scheduler.out_paths.items():
        base_dir = os.path.dirname(out_path)
        basename = os.path.basename(out_path)
        
        # Gather all part files
        part_files = []
        if os.path.exists(base_dir):
            for fname in os.listdir(base_dir):
                if fname.startswith(basename + ".part_"):
                    part_files.append(os.path.join(base_dir, fname))
        
        if not part_files:
            continue
            
        print(f"Merging {len(part_files)} logs for run {run_idx} into {out_path}")
        # Merge
        with open(out_path, "a", encoding="utf-8") as fout:
            for pfile in part_files:
                try:
                    with open(pfile, "r", encoding="utf-8") as fin:
                        shutil.copyfileobj(fin, fout)
                    # Delete after successful merge
                    try:
                        os.remove(pfile)
                    except:
                        pass
                except Exception as e:
                    print(f"Error merging {pfile} to {out_path}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Config JSON/YAML.")
    ap.add_argument("--parallel", type=int, default=8, help="Number of parallel threads (default 8).")
    args = ap.parse_args()

    cfg = load_config(args.config)
    runs_cfg = cfg.get("runs", [])
    if not runs_cfg:
        print("No runs found in config.")
        return

    common_cfg = cfg.get("common", {})
    io_cfg = cfg.get("io", {})
    filters_cfg = cfg.get("filters", {})
    vertex_global = cfg.get("vertex", {})
    common_cfg.update(vertex_global)

    scheduler = Scheduler()
    
    print(f"Initializing {len(runs_cfg)} runs...")

    for i, run_c in enumerate(runs_cfg):
        run_args = create_args_namespace(common_cfg, run_c, io_cfg, filters_cfg)
        
        try:
            client, auth_info = build_client(run_args)
        except Exception as e:
            print(f"Failed to initialize client for run {i} ({run_args.model}): {e}")
            continue
            
        retry_cfg = RetryConfig(
            max_retries=run_args.max_retries,
            base_delay_s=run_args.retry_base_delay_s,
            max_delay_s=run_args.retry_max_delay_s,
            jitter=run_args.retry_jitter
        )
        
        scheduler.register_run(i, run_args, client, auth_info, retry_cfg)
        
        if not run_args.prompts_path or not os.path.exists(run_args.prompts_path):
            print(f"Warning: prompts_path not found: {run_args.prompts_path}")
            continue
        
        c = 0
        limit = run_args.limit
        for prompt_obj in read_jsonl(run_args.prompts_path):
            if not should_keep(prompt_obj, run_args):
                continue
                
            scheduler.add_task(i, prompt_obj)
            c += 1
            if limit > 0 and c >= limit:
                break
        
        print(f"  Run {i}: {run_args.model} | {run_args.decoding} -> {scheduler.todo_counts[i]} tasks (after resume filter)")

    total_tasks = sum(scheduler.todo_counts.values())
    if total_tasks == 0:
        print("No tasks to run.")
        return

    scheduler.pbar = tqdm(total=total_tasks, desc="Sweep Progress", unit="task")

    workers = args.parallel if args.parallel > 0 else 8
    num_runs = len(runs_cfg)
    
    print(f"Starting {workers} workers processing {total_tasks} tasks...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for w_id in range(workers):
            initial_run_idx = w_id % num_runs
            futures.append(executor.submit(worker_main, scheduler, initial_run_idx, w_id))
        
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"Worker exception: {e}")

    scheduler.pbar.close()
    
    # Merge results
    merge_results(scheduler)
    print("Sweep completed.")

if __name__ == "__main__":
    main()
