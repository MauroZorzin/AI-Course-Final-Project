#!/usr/bin/env python3
"""
run_inference_gcp.py

Run inference on a JSONL of prompts (render_prompts.py output) using Gemini on Vertex AI
via the Google Gen AI SDK (google-genai).

Key features:
- Reads prompts JSONL with {prompt_id, messages:[{role,content},...], ...}
- Decoding: greedy or self_consistency (majority vote over N samples)
- Writes JSONL responses with raw text, parsed JSON (best-effort), latency, token usage
- tqdm progress bar (assumed installed)

Auth:
- Recommended: pass a service account key file directly:
    --use_vertexai --project <PROJECT> --location <REGION> --service_account_json /path/key.json

This script will:
- Load credentials from the JSON key (google-auth) and pass them to genai.Client when supported.
- Also set GOOGLE_APPLICATION_CREDENTIALS internally for compatibility with SDK versions that do not
  accept a credentials kwarg.

If you still get 403 PERMISSION_DENIED with aiplatform.endpoints.predict, that's IAM on the target
project/model resource (not a code issue).
"""

import argparse
import datetime as _dt
import json
import os
import random
import time
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from tqdm import tqdm

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

try:
    from google.oauth2 import service_account
except Exception:
    service_account = None


JSONObj = Dict[str, Any]
DEFAULT_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)


def utc_now_iso() -> str:
    # timezone-aware UTC (fixes datetime.utcnow deprecation)
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: str) -> Iterable[JSONObj]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def safe_model_dump(obj: Any) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    for attr in ("model_dump", "dict", "to_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    try:
        d = dict(obj.__dict__)
        for k in list(d.keys()):
            if k.startswith("_"):
                d.pop(k, None)
        return d
    except Exception:
        return None


def extract_first_json_object(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if text is None:
        return None, "empty_text"
    s = str(text).strip()
    if not s:
        return None, "empty_text"

    # If output is a JSON string that contains JSON, unquote and retry
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        try:
            inner = json.loads(s)
            if isinstance(inner, str):
                s = inner.strip()
        except Exception:
            pass

    # Fast path
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj, None
    except Exception:
        pass

    start = s.find("{")
    if start == -1:
        return None, "no_json_object_found"

    depth = 0
    end = None
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        return None, "unbalanced_braces"

    candidate = s[start:end]
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj, None
        return None, "json_not_object"
    except Exception as e:
        return None, f"json_parse_error: {e}"


def get_final_answer(parsed: Optional[Dict[str, Any]]) -> Optional[str]:
    if not parsed:
        return None
    if "final_answer" in parsed and parsed["final_answer"] is not None:
        return str(parsed["final_answer"])
    return None


def normalize_answer(ans: Optional[str]) -> Optional[str]:
    if ans is None:
        return None
    a = str(ans).strip()
    return a if a else None


def aggregate_self_consistency(answers: List[Optional[str]], prefer_non_unknown: bool = True) -> Dict[str, Any]:
    norm = [normalize_answer(a) for a in answers]
    if prefer_non_unknown:
        non_unknown = [a for a in norm if a and a.upper() != "UNKNOWN"]
        if non_unknown:
            norm = non_unknown

    counts: Dict[str, int] = {}
    for a in norm:
        if not a:
            continue
        counts[a] = counts.get(a, 0) + 1

    if not counts:
        return {"final_answer": "UNKNOWN", "vote_counts": {}, "selected": "UNKNOWN"}

    max_n = max(counts.values())
    winners = sorted([a for a, c in counts.items() if c == max_n])
    selected = winners[0]
    return {"final_answer": selected, "vote_counts": counts, "selected": selected}


def extract_messages(prompt_obj: JSONObj) -> Tuple[str, List[Any]]:
    """
    Convert prompt record -> (system_instruction, contents list for generate_content).
    role=system -> config.system_instruction
    role=user/assistant/model/tool -> contents[]
    """
    if types is None:
        raise RuntimeError("google-genai is not installed. Run: pip install --upgrade google-genai")

    messages = prompt_obj.get("messages") or []
    if not isinstance(messages, list):
        raise ValueError("prompt.messages must be a list")

    sys_parts: List[str] = []
    contents: List[Any] = []

    for m in messages:
        role = str(m.get("role", "")).lower()
        content = m.get("content", "")
        content = "" if content is None else str(content)

        if role == "system":
            if content.strip():
                sys_parts.append(content.strip())
            continue

        mapped_role = "model" if role in ("assistant", "model") else ("user" if role not in ("user", "tool") else role)
        contents.append(
            types.Content(
                role=mapped_role,
                parts=[types.Part.from_text(text=content)],
            )
        )

    return "\n".join(sys_parts).strip(), contents


@dataclass
class RetryConfig:
    max_retries: int = 6
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    jitter: float = 0.3


def call_with_retries(fn, retry_cfg: RetryConfig):
    attempt = 0
    while True:
        try:
            return fn(), attempt
        except Exception:
            attempt += 1
            if attempt > retry_cfg.max_retries:
                raise
            delay = min(retry_cfg.max_delay_s, retry_cfg.base_delay_s * (2 ** (attempt - 1)))
            delay *= (1.0 + (random.random() * 2 - 1.0) * retry_cfg.jitter)
            time.sleep(max(0.0, delay))


def load_service_account_credentials(sa_path: str, scopes: Sequence[str]):
    if service_account is None:
        raise RuntimeError("google-auth is not installed. Run: pip install --upgrade google-auth")
    return service_account.Credentials.from_service_account_file(sa_path, scopes=list(scopes))


def infer_sa_identity(sa_path: str) -> Dict[str, Optional[str]]:
    try:
        with open(sa_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return {
            "client_email": obj.get("client_email"),
            "project_id_in_key": obj.get("project_id"),
        }
    except Exception:
        return {"client_email": None, "project_id_in_key": None}


def build_client(args) -> Tuple[Any, Dict[str, Optional[str]]]:
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed. Run: pip install --upgrade google-genai")

    auth_info = {"client_email": None, "project_id_in_key": None}

    http_opts = types.HttpOptions(
        api_version=args.api_version,
        timeout=args.timeout_ms if args.timeout_ms else None,
    )

    if args.use_vertexai:
        if not args.project:
            raise ValueError("--project is required for Vertex AI")
        if not args.location:
            raise ValueError("--location is required for Vertex AI (e.g., europe-west8, us-central1, global)")

        creds = None
        if args.service_account_json:
            sa_path = os.path.abspath(args.service_account_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path  # compatibility path
            auth_info = infer_sa_identity(sa_path)
            scopes = args.service_account_scopes or DEFAULT_SCOPES
            creds = load_service_account_credentials(sa_path, scopes=scopes)

        # Some google-genai versions accept credentials=..., others don't.
        if creds is not None:
            try:
                c = genai.Client(
                    vertexai=True,
                    project=args.project,
                    location=args.location,
                    credentials=creds,
                    http_options=http_opts,
                )
                return c, auth_info
            except TypeError:
                # Fallback: rely on GOOGLE_APPLICATION_CREDENTIALS set above
                pass

        c = genai.Client(
            vertexai=True,
            project=args.project,
            location=args.location,
            http_options=http_opts,
        )
        return c, auth_info

    # Gemini Developer API
    if not args.api_key:
        raise ValueError("--api_key is required when not using --use_vertexai")
    return genai.Client(api_key=args.api_key, http_options=http_opts), auth_info


def build_gen_config(args, system_instruction: str, temperature: float, seed: Optional[int]):
    cfg_kwargs = dict(
        temperature=temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        candidate_count=1,
        max_output_tokens=args.max_output_tokens,
    )
    if seed is not None:
        cfg_kwargs["seed"] = seed
    if system_instruction:
        cfg_kwargs["system_instruction"] = system_instruction
    if args.json_mode:
        cfg_kwargs["response_mime_type"] = "application/json"
    if args.stop_sequences:
        cfg_kwargs["stop_sequences"] = args.stop_sequences
    return types.GenerateContentConfig(**cfg_kwargs)


def should_keep(prompt_obj: JSONObj, args) -> bool:
    if args.filter_prompting_strategy and str(prompt_obj.get("prompting_strategy")) not in args.filter_prompting_strategy:
        return False
    if args.filter_graph_variant and str(prompt_obj.get("graph_variant")) not in args.filter_graph_variant:
        return False
    if args.filter_hop and int(prompt_obj.get("hop", -1)) not in args.filter_hop:
        return False
    return True


def load_done_ids(out_path: str) -> set:
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                pid = obj.get("prompt_id")
                if pid:
                    done.add(pid)
            except Exception:
                continue
    return done


def count_remaining(prompts_path: str, args, done_ids: set) -> Tuple[int, int]:
    """Return (remaining_to_process, skipped_total) under current filters/resume."""
    remaining = 0
    skipped = 0
    with open(prompts_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if not should_keep(obj, args):
                skipped += 1
                continue
            pid = str(obj.get("prompt_id") or "")
            if args.resume and pid and pid in done_ids:
                skipped += 1
                continue
            remaining += 1
    return remaining, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts_path", required=True, help="Input JSONL prompts.")
    ap.add_argument("--out_path", required=True, help="Output JSONL responses.")
    ap.add_argument("--resume", action="store_true", help="Skip prompt_ids already present in out_path.")

    # Vertex AI / auth
    ap.add_argument("--use_vertexai", action="store_true", help="Use Vertex AI.")
    ap.add_argument("--project", default=None, help="GCP project (Vertex AI).")
    ap.add_argument("--location", default=None, help="GCP location/region (Vertex AI).")
    ap.add_argument("--service_account_json", default=None, help="Path to service account JSON key (Vertex AI).")
    ap.add_argument("--service_account_scopes", nargs="*", default=None, help="OAuth scopes for SA creds.")
    ap.add_argument("--api_key", default=None, help="API key (Gemini Developer API only).")

    # Model / decoding
    ap.add_argument("--model", required=True, help="Model name, e.g. gemini-2.5-flash.")
    ap.add_argument("--decoding", choices=["greedy", "self_consistency"], default="greedy")
    ap.add_argument("--temperature", type=float, default=0.0, help="Base temperature (SC uses 0.7 if <=0).")
    ap.add_argument("--top_p", type=float, default=0.95)
    ap.add_argument("--top_k", type=int, default=40)
    ap.add_argument("--max_output_tokens", type=int, default=256)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--json_mode", action="store_true", help="Set response_mime_type='application/json'.")

    # Self-consistency
    ap.add_argument("--sc_samples", type=int, default=5)
    ap.add_argument("--sc_prefer_non_unknown", action="store_true")

    # Request options
    ap.add_argument("--stop_sequences", nargs="*", default=None)
    ap.add_argument("--timeout_ms", type=int, default=None)
    ap.add_argument("--api_version", default="v1")

    # Filtering / slicing
    ap.add_argument("--filter_prompting_strategy", nargs="*", default=None)
    ap.add_argument("--filter_graph_variant", nargs="*", default=None)
    ap.add_argument("--filter_hop", nargs="*", type=int, default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--shuffle", action="store_true")

    # Retries
    ap.add_argument("--max_retries", type=int, default=6)
    ap.add_argument("--retry_base_delay_s", type=float, default=1.0)
    ap.add_argument("--retry_max_delay_s", type=float, default=300.0)
    ap.add_argument("--retry_jitter", type=float, default=0.3)
    ap.add_argument("--machine_readable_progress", action="store_true", help="Print progress as simple text for parsing.")

    args = ap.parse_args()

    client, auth_info = build_client(args)
    retry_cfg = RetryConfig(
        max_retries=args.max_retries,
        base_delay_s=args.retry_base_delay_s,
        max_delay_s=args.retry_max_delay_s,
        jitter=args.retry_jitter,
    )

    done_ids = load_done_ids(args.out_path) if args.resume else set()
    total_to_process, skipped_total = count_remaining(args.prompts_path, args, done_ids)

    os.makedirs(os.path.dirname(args.out_path) or ".", exist_ok=True)

    processed = 0
    errors = 0

    bar = None
    if not args.machine_readable_progress:
        bar = tqdm(total=total_to_process, desc=f"{args.model} | {args.decoding}", unit="prompt")
    
    with open(args.out_path, "a", encoding="utf-8") as fout:
        for prompt_obj in read_jsonl(args.prompts_path):
            if not should_keep(prompt_obj, args):
                continue

            prompt_id = str(prompt_obj.get("prompt_id") or "")
            if args.resume and prompt_id and prompt_id in done_ids:
                continue

            if args.limit and processed >= args.limit:
                break

            system_instruction, contents = extract_messages(prompt_obj)

            # Temperature schedule
            if args.decoding == "greedy":
                temps = [0.0]
            else:
                base_t = float(args.temperature)
                if base_t <= 0.0:
                    base_t = 0.7
                temps = [base_t] * int(args.sc_samples)

            samples_out: List[Dict[str, Any]] = []
            started_at = utc_now_iso()
            t0 = time.time()

            error_obj = None
            usage_accum = {
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0,
                "thoughts_token_count": 0,
                "tool_use_prompt_token_count": 0,
            }

            try:
                for si, temp in enumerate(temps):
                    seed = (int(args.seed) + si) if args.seed is not None else None
                    gen_cfg = build_gen_config(args, system_instruction, temperature=temp, seed=seed)

                    def _do_call():
                        return client.models.generate_content(
                            model=args.model,
                            contents=contents,
                            config=gen_cfg,
                        )

                    resp, retries_used = call_with_retries(_do_call, retry_cfg)

                    resp_text = getattr(resp, "text", None)
                    finish_reason = None
                    if resp_text is None:
                        try:
                            cand0 = resp.candidates[0]
                            finish_reason = getattr(cand0, "finish_reason", None)
                            parts = cand0.content.parts if getattr(cand0, "content", None) else []
                            resp_text = "".join([getattr(p, "text", "") for p in parts if getattr(p, "text", None)])
                        except Exception:
                            resp_text = None
                    else:
                        try:
                             cand0 = resp.candidates[0]
                             finish_reason = getattr(cand0, "finish_reason", None)
                        except Exception:
                             pass

                    parsed, perr = extract_first_json_object(resp_text or "")
                    final_answer = get_final_answer(parsed)

                    # Usage metadata (best-effort)
                    usage = {}
                    um = getattr(resp, "usage_metadata", None)
                    if um is not None:
                        usage = safe_model_dump(um) or {}
                    else:
                        md = safe_model_dump(resp) or {}
                        usage = md.get("usage_metadata") or md.get("usageMetadata") or {}

                    def _acc(key: str, *aliases: str):
                        v = None
                        if isinstance(usage, dict):
                            for k in (key,) + aliases:
                                if k in usage:
                                    v = usage.get(k)
                                    break
                        if isinstance(v, (int, float)):
                            usage_accum[key] = usage_accum.get(key, 0) + int(v)

                    _acc("prompt_token_count", "promptTokenCount")
                    _acc("candidates_token_count", "candidatesTokenCount")
                    _acc("total_token_count", "totalTokenCount")
                    _acc("thoughts_token_count", "thoughtsTokenCount")
                    _acc("tool_use_prompt_token_count", "toolUsePromptTokenCount")

                    samples_out.append({
                        "sample_index": si,
                        "temperature": temp,
                        "seed": seed,
                        "retries_used": retries_used,
                        "response_text": resp_text,
                        "finish_reason": str(finish_reason) if finish_reason is not None else None,
                        "parsed_json": parsed,
                        "parse_error": perr,
                        "final_answer": final_answer,
                        "usage_metadata": usage if usage else None,
                    })

                latency_ms = int((time.time() - t0) * 1000)

            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                error_obj = {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
                errors += 1

            # Aggregate
            if args.decoding == "greedy":
                chosen = samples_out[0] if samples_out else {}
                final_out = normalize_answer(chosen.get("final_answer")) if chosen else None
                agg = {
                    "final_answer": final_out,
                    "parsed_json": chosen.get("parsed_json") if chosen else None,
                    "parse_error": chosen.get("parse_error") if chosen else None,
                    "response_text": chosen.get("response_text") if chosen else None,
                }
                sc_meta = None
            else:
                answers = [s.get("final_answer") for s in samples_out]
                sc = aggregate_self_consistency(answers, prefer_non_unknown=bool(args.sc_prefer_non_unknown))
                agg = {
                    "final_answer": sc["final_answer"],
                    "vote_counts": sc["vote_counts"],
                }
                sc_meta = {
                    "sc_samples": int(args.sc_samples),
                    "sc_prefer_non_unknown": bool(args.sc_prefer_non_unknown),
                }

            out = {
                "prompt_id": prompt_obj.get("prompt_id"),
                "query_id": prompt_obj.get("query_id"),
                "intent_key": prompt_obj.get("intent_key"),
                "prompting_strategy": prompt_obj.get("prompting_strategy"),
                "graph_variant": prompt_obj.get("graph_variant"),
                "hop": prompt_obj.get("hop"),
                "template_id": prompt_obj.get("template_id"),

                "model": args.model,
                "decoding": args.decoding,
                "request": {
                    "temperature": float(args.temperature),
                    "top_p": float(args.top_p),
                    "top_k": int(args.top_k),
                    "max_output_tokens": int(args.max_output_tokens),
                    "seed": args.seed,
                    "json_mode": bool(args.json_mode),
                    "stop_sequences": args.stop_sequences,
                    "api_version": args.api_version,
                    "project": args.project,
                    "location": args.location,
                    "service_account_json": os.path.abspath(args.service_account_json) if args.service_account_json else None,
                    "service_account_client_email": auth_info.get("client_email"),
                    "service_account_project_id_in_key": auth_info.get("project_id_in_key"),
                },

                "started_at": started_at,
                "latency_ms": latency_ms,

                "final_answer": agg.get("final_answer"),
                "vote_counts": agg.get("vote_counts"),
                "parsed_json": agg.get("parsed_json"),
                "parse_error": agg.get("parse_error"),
                "response_text": agg.get("response_text"),

                "samples": samples_out,
                "self_consistency": sc_meta,
                "usage_total_across_samples": usage_accum,
                "error": error_obj,
            }

            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            fout.flush()

            processed += 1
            if bar:
                bar.update(1)
                bar.set_postfix_str(f"processed={processed} errors={errors}")
            elif args.machine_readable_progress:
                # Format: PROGRESS_UPDATE:{current}:{total}:{errors}
                # Using sys.stdout and flushing to ensure parent process sees it immediately
                print(f"PROGRESS_UPDATE:{processed}:{total_to_process}:{errors}", flush=True)

    if bar:
        bar.close()
    
    summary = {
        "prompts_path": args.prompts_path,
        "out_path": args.out_path,
        "model": args.model,
        "decoding": args.decoding,
        "total_to_process": total_to_process,
        "skipped_total": skipped_total,
        "processed": processed,
        "errors": errors,
        "resume": bool(args.resume),
        "auth_client_email": auth_info.get("client_email"),
        "auth_project_id_in_key": auth_info.get("project_id_in_key"),
    }
    
    # Write summary to a separate log file next to responses.jsonl
    # E.g. responses.log.json
    log_path = args.out_path + ".log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
