#!/usr/bin/env python3
"""
evaluate.py

Compute SPARK benchmark metrics from:
- Query instances JSONL (instantiate_queries.py output)
- Model responses JSONL (run_inference_gcp.py output) OR a directory containing many responses.jsonl files

Metrics (as per project-details.md):
- EM / F1
- Accuracy by hop
- Override rate (for counterfactual graphs)
- Path precision / recall
- Path EM
- Tokens / latency / costs (estimated, optional)

Outputs:
- per_record.csv
- summary.json (overall + grouped by experiment cell)
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


JSON = Dict[str, Any]


# -----------------------------
# Normalization + scoring
# -----------------------------

_ARTICLES = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    s = s or ""
    s = s.strip().lower()
    s = _PUNCT.sub(" ", s)
    s = _ARTICLES.sub(" ", s)
    s = _WS.sub(" ", s)
    return s.strip()


def tokenize(s: str) -> List[str]:
    s = normalize_text(s)
    return s.split() if s else []


def f1_score(pred: str, gold: str) -> float:
    pt = tokenize(pred)
    gt = tokenize(gold)
    if not pt and not gt:
        return 1.0
    if not pt or not gt:
        return 0.0
    common = Counter(pt) & Counter(gt)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pt)
    recall = num_same / len(gt)
    return 2 * precision * recall / (precision + recall)


def exact_match(pred: str, gold: str) -> int:
    return int(normalize_text(pred) == normalize_text(gold))


def coerce_answer(x: Any) -> List[str]:
    """Return a list of candidate answer strings."""
    if x is None:
        return []
    if isinstance(x, str):
        s = x.strip()
        return [s] if s else []
    if isinstance(x, (int, float, bool)):
        return [str(x)]
    if isinstance(x, list):
        out: List[str] = []
        for v in x:
            out.extend(coerce_answer(v))
        # de-dup while preserving order
        seen = set()
        dedup = []
        for s in out:
            ns = normalize_text(s)
            if ns and ns not in seen:
                seen.add(ns)
                dedup.append(s)
        return dedup
    if isinstance(x, dict):
        # common patterns: {"final_answer": "..."} or {"name": "..."}
        for k in ("final_answer", "answer", "name", "value", "text"):
            if k in x:
                return coerce_answer(x.get(k))
    return []


def best_em_f1(preds: List[str], golds: List[str]) -> Tuple[int, float]:
    """Compute best-match EM/F1 allowing multi-answer gold or pred."""
    if not golds:
        return (0, 0.0)
    if not preds:
        # if gold contains UNKNOWN, treat missing as UNKNOWN? No: missing is wrong.
        return (0, 0.0)
    best_em = 0
    best_f1 = 0.0
    for p in preds:
        for g in golds:
            best_em = max(best_em, exact_match(p, g))
            best_f1 = max(best_f1, f1_score(p, g))
    return best_em, best_f1


def is_unknown(ans: str) -> bool:
    return normalize_text(ans) in {"unknown", "unk", "n/a", "na", ""}


# -----------------------------
# Paths (optional)
# -----------------------------

def _norm_triple(t: Any) -> Optional[str]:
    """
    Normalize a triple representation to a canonical string.
    Accepts:
    - "S | r | O"
    - ["S","r","O"]
    - {"subject":..,"relation":..,"object":..}
    """
    if t is None:
        return None
    if isinstance(t, str):
        parts = [p.strip() for p in t.split("|")]
        if len(parts) == 3:
            return " | ".join(parts)
        # fallback: treat as single string
        s = t.strip()
        return s if s else None
    if isinstance(t, (list, tuple)) and len(t) == 3:
        s, r, o = (str(t[0]).strip(), str(t[1]).strip(), str(t[2]).strip())
        if s and r and o:
            return f"{s} | {r} | {o}"
    if isinstance(t, dict):
        s = t.get("subject") or t.get("subj") or t.get("s")
        r = t.get("relation") or t.get("rel") or t.get("p")
        o = t.get("object") or t.get("obj") or t.get("o")
        if s is not None and r is not None and o is not None:
            s, r, o = str(s).strip(), str(r).strip(), str(o).strip()
            if s and r and o:
                return f"{s} | {r} | {o}"
    return None


def coerce_path(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        out = []
        for v in x:
            nt = _norm_triple(v)
            if nt:
                out.append(nt)
        # de-dup preserve order
        seen = set()
        dedup = []
        for t in out:
            if t not in seen:
                seen.add(t)
                dedup.append(t)
        return dedup
    if isinstance(x, str):
        # try split lines
        lines = [ln.strip() for ln in x.splitlines() if ln.strip()]
        out = []
        for ln in lines:
            nt = _norm_triple(ln)
            if nt:
                out.append(nt)
        return out
    if isinstance(x, dict):
        for k in ("path", "predicted_path", "reasoning_path", "supporting_triples"):
            if k in x:
                return coerce_path(x.get(k))
    return []


def path_metrics(pred_path: List[str], gold_path: List[str]) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    """
    Set-based path precision/recall and path EM (set equality).
    Returns (precision, recall, em) or (None,None,None) if gold missing.
    """
    if not gold_path:
        return (None, None, None)
    gold_set = set(gold_path)
    pred_set = set(pred_path) if pred_path else set()
    if not pred_set:
        return (0.0, 0.0, 0)
    inter = len(gold_set & pred_set)
    prec = inter / len(pred_set) if pred_set else 0.0
    rec = inter / len(gold_set) if gold_set else 0.0
    em = int(pred_set == gold_set)
    return (prec, rec, em)


# -----------------------------
# IO helpers
# -----------------------------

def iter_jsonl(path: str) -> Iterable[JSON]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def collect_jsonl_files(path_or_dir: str) -> List[str]:
    if os.path.isfile(path_or_dir):
        return [path_or_dir]
    # directory or glob
    if any(ch in path_or_dir for ch in ["*", "?", "["]):
        return sorted(glob.glob(path_or_dir, recursive=True))
    if os.path.isdir(path_or_dir):
        return sorted(glob.glob(os.path.join(path_or_dir, "**", "*.jsonl"), recursive=True))
    raise FileNotFoundError(path_or_dir)


def safe_mean(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return (sum(xs) / len(xs)) if xs else None


def safe_stdev(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    if len(xs) < 2:
        return None
    return statistics.stdev(xs)


# -----------------------------
# Pricing
# -----------------------------

@dataclass
class Pricing:
    input_per_mtok: float
    output_per_mtok: float
    long_context_threshold: Optional[int] = None
    input_per_mtok_long: Optional[float] = None
    output_per_mtok_long: Optional[float] = None

    def estimate(self, prompt_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
        if prompt_tokens is None or output_tokens is None:
            return None
        in_rate = self.input_per_mtok
        out_rate = self.output_per_mtok
        if self.long_context_threshold is not None and prompt_tokens >= self.long_context_threshold:
            if self.input_per_mtok_long is not None:
                in_rate = self.input_per_mtok_long
            if self.output_per_mtok_long is not None:
                out_rate = self.output_per_mtok_long
        return (prompt_tokens * in_rate + output_tokens * out_rate) / 1_000_000.0


def load_pricing_from_config(config_path: Optional[str]) -> Dict[str, Pricing]:
    if not config_path:
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    out: Dict[str, Pricing] = {}
    pricing_cfg = cfg.get("pricing", {}) if isinstance(cfg, dict) else {}
    for model, p in pricing_cfg.items():
        try:
            out[model] = Pricing(
                input_per_mtok=float(p["input_per_mtok"]),
                output_per_mtok=float(p["output_per_mtok"]),
                long_context_threshold=int(p["long_context_threshold"]) if p.get("long_context_threshold") is not None else None,
                input_per_mtok_long=float(p["input_per_mtok_long"]) if p.get("input_per_mtok_long") is not None else None,
                output_per_mtok_long=float(p["output_per_mtok_long"]) if p.get("output_per_mtok_long") is not None else None,
            )
        except Exception:
            continue
    return out


def extract_usage(resp: JSON) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Returns (prompt_tokens, output_tokens, total_tokens) if available.
    Prefers usage_total_across_samples from run_inference_gcp.py.
    """
    usage = resp.get("usage_total_across_samples") or resp.get("usage_metadata")
    if not isinstance(usage, dict):
        usage = {}
    prompt_tokens = usage.get("prompt_token_count") or usage.get("promptTokenCount")
    output_tokens = usage.get("candidates_token_count") or usage.get("candidatesTokenCount")
    total_tokens = usage.get("total_token_count") or usage.get("totalTokenCount") or usage.get("total_tokens")
    try:
        prompt_tokens = int(prompt_tokens) if prompt_tokens is not None else None
    except Exception:
        prompt_tokens = None
    try:
        output_tokens = int(output_tokens) if output_tokens is not None else None
    except Exception:
        output_tokens = None
    try:
        total_tokens = int(total_tokens) if total_tokens is not None else None
    except Exception:
        total_tokens = None
    return prompt_tokens, output_tokens, total_tokens


# -----------------------------
# Main evaluation logic
# -----------------------------

def get_gold_answer(query_obj: JSON) -> List[str]:
    for k in ("gold_answer", "answer", "answers", "label", "target", "final_answer"):
        if k in query_obj and query_obj.get(k) is not None:
            return coerce_answer(query_obj.get(k))
    return []


def get_gold_path(query_obj: JSON) -> List[str]:
    for k in ("gold_path", "path", "path_triples", "supporting_path", "reasoning_path"):
        if k in query_obj and query_obj.get(k) is not None:
            return coerce_path(query_obj.get(k))
    return []


def build_query_index(query_files: List[str]) -> Tuple[Dict[str, JSON], Dict[str, List[str]]]:
    """
    Returns:
      - query_by_id
      - natural_gold_by_intent (intent_key -> gold answer list)
    """
    query_by_id: Dict[str, JSON] = {}
    natural_gold_by_intent: Dict[str, List[str]] = {}
    for qf in query_files:
        for q in iter_jsonl(qf):
            qid = str(q.get("query_id") or q.get("id") or "")
            if not qid:
                continue
            query_by_id[qid] = q
            if str(q.get("graph_variant") or "").lower() == "natural":
                ik = str(q.get("intent_key") or "")
                if ik and ik not in natural_gold_by_intent:
                    natural_gold_by_intent[ik] = get_gold_answer(q)
    return query_by_id, natural_gold_by_intent


def group_key(resp: JSON) -> Tuple[str, str, str, str, int]:
    return (
        str(resp.get("model") or ""),
        str(resp.get("decoding") or ""),
        str(resp.get("prompting_strategy") or ""),
        str(resp.get("graph_variant") or ""),
        int(resp.get("hop") or 0),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True,
                    help="Query instances: a JSONL file, a directory, or a glob. "
                         "If a directory/glob, all *.jsonl files will be read.")
    ap.add_argument("--responses", required=True,
                    help="Responses: a JSONL file, a directory, or a glob. "
                         "If a directory/glob, all *.jsonl files will be read.")
    ap.add_argument("--natural_queries", default=None,
                    help="Optional path to natural queries JSONL (for evaluating prior knowledge leakage). "
                         "Can be a file or directory.")
    ap.add_argument("--out_dir", required=True, help="Output directory.")
    ap.add_argument("--config", default=None, help="Optional config.json with a 'pricing' section.")
    ap.add_argument("--write_unknown_as", default="UNKNOWN", help="String used for unknown answers (for reporting).")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    query_files = collect_jsonl_files(args.queries)
    resp_files = collect_jsonl_files(args.responses)

    query_by_id, _ = build_query_index(query_files)  # Current queries
    
    # Load natural queries if provided
    natural_gold_by_intent: Dict[str, List[str]] = {}
    if args.natural_queries:
        nat_files = collect_jsonl_files(args.natural_queries)
        _, natural_gold_by_intent = build_query_index(nat_files)

    pricing = load_pricing_from_config(args.config)

    per_record_path = os.path.join(args.out_dir, "per_record.csv")
    summary_path = os.path.join(args.out_dir, "summary.json")

    fieldnames = [
        "prompt_id","query_id","intent_key","model","decoding","prompting_strategy","graph_variant","hop","template_id",
        "gold_answer","pred_answer","exact_match","f1",
        "override","adherence",
        "path_precision","path_recall","path_em",
        "prior_knowledge_answer","prior_knowledge_em",
        "finish_reason","is_empty_response",
        "latency_ms","prompt_tokens","output_tokens","total_tokens","estimated_cost_usd",
        "parse_error","error_type"
    ]

    # Aggregations by group key
    agg = defaultdict(lambda: {
        "n": 0,
        "em": [],
        "f1": [],
        "override": [],
        "adherence": [],
        "path_precision": [],
        "path_recall": [],
        "path_em": [],
        "prior_knowledge_em": [],
        "finish_reasons": Counter(),
        "empty_response_rate": 0,
        "latency_ms": [],
        "prompt_tokens": [],
        "output_tokens": [],
        "total_tokens": [],
        "estimated_cost_usd": [],
        "parse_error_rate": 0,
        "error_rate": 0,
    })
    overall = agg[("__OVERALL__","","","","",0)]  # type: ignore

    def _add_num(lst, v):
        if v is None:
            return
        lst.append(v)

    with open(per_record_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=fieldnames)
        w.writeheader()

        for rf in resp_files:
            for resp in iter_jsonl(rf):
                qid = str(resp.get("query_id") or "")
                q = query_by_id.get(qid, {})
                golds = get_gold_answer(q)
                pred = coerce_answer(resp.get("final_answer"))
                # fallback: if final_answer missing, try parsed_json
                if not pred:
                    pred = coerce_answer(resp.get("parsed_json"))
                em, f1 = best_em_f1(pred, golds)

                # override/adherence (counterfactual only)
                graph_variant = str(resp.get("graph_variant") or "").lower()
                intent_key = str(resp.get("intent_key") or q.get("intent_key") or "")
                
                # Check natural gold if available
                natural_gold = natural_gold_by_intent.get(intent_key, [])
                
                # Override: Used for Counterfactual. If pred matches NATURAL answer but NOT Counterfactual Gold.
                # However, logic in README says "Override rate" for CF.
                # We calculate override if graph_variant == counterfactual
                
                override = None
                adherence = None
                prior_knowledge_em = None
                
                # If we have natural gold, we can check "Prior Knowledge Leakage" for ANY variant that is not natural
                # If graph_variant is abstract, checking against natural implies we know the mapping.
                # Since we use intent_key, we might have it.
                if natural_gold and graph_variant != "natural":
                     # Check if prediction matches natural gold
                     pk_match, _ = best_em_f1(pred, natural_gold)
                     prior_knowledge_em = pk_match
                
                if graph_variant == "counterfactual" and golds and natural_gold:
                    # only meaningful if natural != counterfactual
                    if normalize_text(" ".join(natural_gold)) != normalize_text(" ".join(golds)):
                        # override: predicted equals natural answer
                        override = int(best_em_f1(pred, natural_gold)[0] == 1)
                        adherence = int(em == 1)

                # path metrics (optional)
                gold_path = get_gold_path(q)
                # predicted path: look for path-like keys in parsed_json OR top-level
                pred_path = []
                if isinstance(resp.get("parsed_json"), dict):
                    pred_path = coerce_path(resp["parsed_json"])
                if not pred_path:
                    pred_path = coerce_path(resp)
                p_prec, p_rec, p_em = path_metrics(pred_path, gold_path)

                latency_ms = resp.get("latency_ms")
                try:
                    latency_ms = int(latency_ms) if latency_ms is not None else None
                except Exception:
                    latency_ms = None

                prompt_tokens, output_tokens, total_tokens = extract_usage(resp)

                model = str(resp.get("model") or "")
                est_cost = None
                if model in pricing:
                    est_cost = pricing[model].estimate(prompt_tokens, output_tokens)

                parse_error = resp.get("parse_error")
                error_obj = resp.get("error")
                error_type = ""
                if isinstance(error_obj, dict):
                    error_type = str(error_obj.get("type") or "")
                
                # failure taxonomy
                samples = resp.get("samples") or []
                finish_reason = None
                if samples and isinstance(samples, list) and len(samples) > 0:
                     finish_reason = samples[0].get("finish_reason")
                
                is_empty = 0
                if not pred:
                    is_empty = 1
                elif all(not s.strip() for s in pred):
                    is_empty = 1

                row = {
                    "prompt_id": resp.get("prompt_id"),
                    "query_id": qid,
                    "intent_key": intent_key,
                    "model": model,
                    "decoding": resp.get("decoding"),
                    "prompting_strategy": resp.get("prompting_strategy"),
                    "graph_variant": resp.get("graph_variant"),
                    "hop": resp.get("hop"),
                    "template_id": resp.get("template_id") or q.get("template_id"),
                    "gold_answer": golds[0] if len(golds)==1 else json.dumps(golds, ensure_ascii=False),
                    "pred_answer": pred[0] if len(pred)==1 else json.dumps(pred, ensure_ascii=False),
                    "exact_match": em,
                    "f1": f1,
                    "override": override,
                    "adherence": adherence,
                    "path_precision": p_prec,
                    "path_recall": p_rec,
                    "path_em": p_em,
                    "prior_knowledge_answer": natural_gold[0] if natural_gold and len(natural_gold)==1 else json.dumps(natural_gold, ensure_ascii=False) if natural_gold else None,
                    "prior_knowledge_em": prior_knowledge_em,
                    "finish_reason": finish_reason,
                    "is_empty_response": is_empty,
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost_usd": est_cost,
                    "parse_error": parse_error,
                    "error_type": error_type,
                }
                w.writerow(row)

                gk = group_key(resp)
                for bucket in (overall, agg[gk]):
                    bucket["n"] += 1
                    bucket["em"].append(em)
                    bucket["f1"].append(f1)
                    if override is not None:
                        bucket["override"].append(override)
                    if adherence is not None:
                        bucket["adherence"].append(adherence)
                    if p_prec is not None:
                        bucket["path_precision"].append(float(p_prec))
                    if p_rec is not None:
                        bucket["path_recall"].append(float(p_rec))
                    if p_em is not None:
                        bucket["path_em"].append(int(p_em))
                    if prior_knowledge_em is not None:
                        bucket["prior_knowledge_em"].append(prior_knowledge_em)
                    if finish_reason:
                        bucket["finish_reasons"][finish_reason] += 1
                    bucket["empty_response_rate"] += is_empty

                    if latency_ms is not None:
                        bucket["latency_ms"].append(latency_ms)
                    if prompt_tokens is not None:
                        bucket["prompt_tokens"].append(prompt_tokens)
                    if output_tokens is not None:
                        bucket["output_tokens"].append(output_tokens)
                    if total_tokens is not None:
                        bucket["total_tokens"].append(total_tokens)
                    if est_cost is not None:
                        bucket["estimated_cost_usd"].append(est_cost)

                    if parse_error:
                        bucket["parse_error_rate"] += 1
                    if error_type:
                        bucket["error_rate"] += 1

    # finalize summary
    def finalize(bucket: Dict[str, Any]) -> Dict[str, Any]:
        n = bucket["n"]
        return {
            "n": n,
            "em_mean": safe_mean(bucket["em"]),
            "f1_mean": safe_mean(bucket["f1"]),
            "override_rate": safe_mean(bucket["override"]) if bucket["override"] else None,
            "adherence_rate": safe_mean(bucket["adherence"]) if bucket["adherence"] else None,
            "prior_knowledge_em_mean": safe_mean(bucket["prior_knowledge_em"]) if bucket["prior_knowledge_em"] else None,
            "path_precision_mean": safe_mean(bucket["path_precision"]) if bucket["path_precision"] else None,
            "path_recall_mean": safe_mean(bucket["path_recall"]) if bucket["path_recall"] else None,
            "path_em_mean": safe_mean(bucket["path_em"]) if bucket["path_em"] else None,
            "latency_ms_mean": safe_mean(bucket["latency_ms"]) if bucket["latency_ms"] else None,
            "prompt_tokens_mean": safe_mean(bucket["prompt_tokens"]) if bucket["prompt_tokens"] else None,
            "output_tokens_mean": safe_mean(bucket["output_tokens"]) if bucket["output_tokens"] else None,
            "total_tokens_mean": safe_mean(bucket["total_tokens"]) if bucket["total_tokens"] else None,
            "estimated_cost_usd_mean": safe_mean(bucket["estimated_cost_usd"]) if bucket["estimated_cost_usd"] else None,
            "parse_error_rate": (bucket["parse_error_rate"] / n) if n else None,
            "error_rate": (bucket["error_rate"] / n) if n else None,
            "empty_response_rate": (bucket["empty_response_rate"] / n) if n else None,
            "top_finish_reasons": bucket["finish_reasons"].most_common(3) if bucket["finish_reasons"] else None,
        }

    summary = {
        "overall": finalize(overall),
        "groups": {}
    }
    for k, bucket in agg.items():
        if k[0] == "__OVERALL__":
            continue
        model, decoding, prompting, graph, hop = k
        summary["groups"][f"{model}::{decoding}::{prompting}::{graph}::H{hop}"] = finalize(bucket)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps({
        "query_files": query_files,
        "response_files": resp_files,
        "per_record_csv": per_record_path,
        "summary_json": summary_path,
        "pricing_loaded_models": sorted(pricing.keys()),
    }, indent=2))


if __name__ == "__main__":
    main()
