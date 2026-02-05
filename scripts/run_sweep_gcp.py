#!/usr/bin/env python3
"""
run_sweep_gcp_v2.py

Drop-in replacement for run_sweep_gcp.py that supports per-run overrides for:
- location
- project
- service_account_json
- api_version

It keeps the original config format but reads run-level fields if present.

Example run entry:
{ "model":"llama-4-maverick-17b-128e-instruct-maas", "decoding":"greedy", "location":"us-east5" }
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import queue
from typing import Any, Dict, List, Optional

from tqdm import tqdm

JSONObj = Dict[str, Any]


def load_config(path: str) -> JSONObj:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise RuntimeError("YAML config requested but PyYAML not installed.") from e
        return yaml.safe_load(txt)
    return json.loads(txt)


def project_root() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, os.pardir))


def abspath_from_root(p: str) -> str:
    if p is None:
        return p
    if os.path.isabs(p):
        return p
    return os.path.abspath(os.path.join(project_root(), p))


def to_cli_args(cfg: JSONObj, run: JSONObj, runner: str) -> List[str]:
    vertex = cfg.get("vertex", {}) or {}
    io = cfg.get("io", {}) or {}
    common = cfg.get("common", {}) or {}
    filt = cfg.get("filters", {}) or {}

    # Allow per-run overrides
    project = run.get("project") or vertex.get("project")
    location = run.get("location") or vertex.get("location")
    sa_json = run.get("service_account_json") or vertex.get("service_account_json")
    api_version = run.get("api_version") or vertex.get("api_version")

    args: List[str] = [
        sys.executable, runner,
        "--prompts_path", abspath_from_root(io["prompts_path"]),
        "--out_path", abspath_from_root(os.path.join(io["out_dir"], run.get("model","model"), run.get("decoding","decoding"), "responses.jsonl")),
        "--model", str(run["model"]),
        "--decoding", str(run.get("decoding", "greedy")),
    ]

    if io.get("resume", False):
        args.append("--resume")

    # Filters
    if "prompting_strategy" in filt:
        args += ["--filter_prompting_strategy"] + [str(x) for x in filt["prompting_strategy"]]
    if "graph_variant" in filt:
        args += ["--filter_graph_variant"] + [str(x) for x in filt["graph_variant"]]
    if "hop" in filt:
        args += ["--filter_hop"] + [str(int(x)) for x in filt["hop"]]

    # Common + run-level overrides
    merged = dict(common)
    merged.update({k: v for k, v in run.items() if k not in ("model","decoding")})

    for k in ("temperature","top_p","top_k","max_output_tokens","max_retries","seed"):
        if k in merged and merged[k] is not None:
            args += [f"--{k}", str(merged[k])]
    if merged.get("json_mode", False):
        args.append("--json_mode")
    if merged.get("stop_sequences"):
        args += ["--stop_sequences"] + [str(x) for x in merged["stop_sequences"]]

    # Self-consistency options
    if run.get("decoding") == "self_consistency":
        if run.get("sc_samples") is not None:
            args += ["--sc_samples", str(int(run["sc_samples"]))]
        if run.get("sc_prefer_non_unknown") is not None:
            args += ["--sc_prefer_non_unknown", str(bool(run["sc_prefer_non_unknown"]))]

    # Vertex/auth
    if vertex.get("use_vertexai", False):
        args.append("--use_vertexai")
    if project:
        args += ["--project", str(project)]
    if location:
        args += ["--location", str(location)]
    if sa_json:
        args += ["--service_account_json", abspath_from_root(str(sa_json))]
    if api_version:
        args += ["--api_version", str(api_version)]

    return args


def run_single_job(
    cfg: JSONObj, 
    run: JSONObj, 
    runner: str, 
    dry_run: bool, 
    parallel: bool = False,
    bar_pos: int = 0
) -> Optional[str]:
    cmd = to_cli_args(cfg, run, runner)
    # If parallel, we enable machine_readable_progress
    if parallel:
        cmd.append("--machine_readable_progress")

    if dry_run:
        return " ".join(cmd)
    
    run_name = f"{run.get('model', 'model')}/{run.get('decoding', 'greedy')}"
    
    if parallel:
        # Create a progress bar at the assigned position.
        # Use position=bar_pos + 1 to leave room for the main bar at 0.
        # leave=False so it disappears when done (optional, prevents clutter if many lines)
        pbar = tqdm(total=100, position=bar_pos + 1, desc=f"{run_name}", leave=False, 
                    bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}")
        
        try:
             process = subprocess.Popen(
                 cmd, 
                 stdout=subprocess.PIPE, 
                 stderr=subprocess.PIPE, 
                 text=True, 
                 encoding='utf-8',
                 bufsize=1 # Line buffered
             )
             
             # Read stdout for progress updates
             while True:
                 line = process.stdout.readline()
                 if not line and process.poll() is not None:
                     break
                 
                 if line:
                     line = line.strip()
                     # Look for PROGRESS_UPDATE:{current}:{total}:{errors}
                     if line.startswith("PROGRESS_UPDATE:"):
                         try:
                             parts = line.split(":")
                             curr = int(parts[1])
                             total = int(parts[2])
                             # errs = int(parts[3])
                             
                             if pbar.total != total:
                                 pbar.reset(total=total)
                             
                             pbar.n = curr
                             pbar.last_print_n = curr
                             pbar.update(0) # trigger refresh
                         except Exception:
                             pass
             
             pbar.close()
             if process.returncode != 0:
                 stderr_out = process.stderr.read()
                 raise RuntimeError(f"Job {run_name} failed. Exit code {process.returncode}\nSTDERR: {stderr_out}")
                 
             return f"Job {run_name} completed."
             
        except Exception as e:
            pbar.close()
            raise e
    else:
        # Serial: let it stream
        # (We did not add --machine_readable_progress, so run_inference uses normal tqdm)
        subprocess.run(cmd, check=True)
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Config JSON/YAML.")
    ap.add_argument("--runner", default=os.path.join(project_root(), "scripts", "run_inference_gcp.py"),
                    help="Path to run_inference script.")
    ap.add_argument("--dry_run", action="store_true")
    ap.add_argument("--parallel", type=int, nargs="?", const=-1, default=0,
                    help="Number of parallel workers. 0 (default) for serial. "
                         "If flag is used without value, uses cpu_count - 2.")
    args = ap.parse_args()

    cfg = load_config(args.config)
    runs = cfg.get("runs", [])
    if not isinstance(runs, list) or not runs:
        raise SystemExit("No runs[] found in config.")

    runner = args.runner
    if not os.path.isabs(runner):
        runner = abspath_from_root(runner)

    # Determine parallelism
    workers = args.parallel
    
    if workers == -1:
        # Flag present without value: default to cpu_count - 2
        cpus = os.cpu_count() or 4
        workers = max(1, cpus - 2)
    
    # Cap workers based on user constraints if we are in parallel mode
    if workers > 0:
        cpus = os.cpu_count() or 1
        limit = min(cpus, len(runs))
        if workers > limit:
            workers = limit
        workers = max(1, workers) # Ensure at least 1

    if workers > 0:
        print(f"Running sweep with {workers} workers.")
        
        # We need to assign each worker a "slot" (0 to workers-1) for UI positioning
        slot_queue = queue.Queue()
        for i in range(workers):
            slot_queue.put(i)

        # Wrapper to grab slot
        def _worker_wrapper(r):
            slot = slot_queue.get()
            try:
                return run_single_job(cfg, r, runner, args.dry_run, parallel=True, bar_pos=slot)
            finally:
                slot_queue.put(slot)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for run in runs:
                futures.append(executor.submit(_worker_wrapper, run))
            
            # Using position 0 for the main bar
            for f in tqdm(concurrent.futures.as_completed(futures), total=len(runs), desc="Sweep runs", position=0):
                try:
                    res = f.result()
                    if res and res.strip():
                        # We don't print "Job Completed" to avoid messing up the bars, 
                        # or we print it above/below?
                        # tqdm.write automatically prints above bars if possible.
                        pass 
                except Exception as e:
                    tqdm.write(f"Job failed: {e}")
    else:
        # Serial execution
        print("Running sweep in serial mode.")
        for run in tqdm(runs, desc="Sweep runs"):
            try:
                run_single_job(cfg, run, runner, args.dry_run, False)
            except subprocess.CalledProcessError:
                print("Job failed.") 
                # Don't exit entire sweep on one failure? Or do? 
                # Original behavior was check=True -> exit.
                # Let's keep check=True behavior which raises exception and stops script.
                raise


if __name__ == "__main__":
    main()
