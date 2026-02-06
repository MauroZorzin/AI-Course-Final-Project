#!/usr/bin/env python3
"""
evaluate.py - Enhanced version

Compute SPARK benchmark metrics with improved:
- Error handling and validation
- Statistical confidence intervals
- Detailed failure analysis
- Token efficiency metrics
- Better logging and progress tracking
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
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

JSON = Dict[str, Any]


# ============================================================================
# Text Normalization & Scoring
# ============================================================================

_ARTICLES = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """Normalize text for comparison."""
    s = s or ""
    s = s.strip().lower()
    s = _PUNCT.sub(" ", s)
    s = _ARTICLES.sub(" ", s)
    s = _WS.sub(" ", s)
    return s.strip()


def tokenize(s: str) -> List[str]:
    """Tokenize normalized text."""
    s = normalize_text(s)
    return s.split() if s else []


def f1_score(pred: str, gold: str) -> float:
    """Calculate token-level F1 score."""
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
    """Check exact match after normalization."""
    return int(normalize_text(pred) == normalize_text(gold))


def coerce_answer(x: Any) -> List[str]:
    """Extract answer strings from various formats."""
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
        # Deduplicate while preserving order
        seen = set()
        dedup = []
        for s in out:
            ns = normalize_text(s)
            if ns and ns not in seen:
                seen.add(ns)
                dedup.append(s)
        return dedup
    if isinstance(x, dict):
        for k in ("final_answer", "answer", "name", "value", "text", "result"):
            if k in x:
                return coerce_answer(x.get(k))
    return []


def best_em_f1(preds: List[str], golds: List[str]) -> Tuple[int, float]:
    """Compute best-match EM/F1 across multiple predictions and gold answers."""
    if not golds:
        return (0, 0.0)
    if not preds:
        return (0, 0.0)
    best_em = 0
    best_f1 = 0.0
    for p in preds:
        for g in golds:
            best_em = max(best_em, exact_match(p, g))
            best_f1 = max(best_f1, f1_score(p, g))
    return best_em, best_f1


def is_unknown(ans: str) -> bool:
    """Check if answer indicates unknown."""
    return normalize_text(ans) in {"unknown", "unk", "n/a", "na", ""}


# ============================================================================
# Path Metrics
# ============================================================================

def _norm_triple(t: Any) -> Optional[str]:
    """Normalize triple to canonical string format."""
    if t is None:
        return None
    if isinstance(t, str):
        parts = [p.strip() for p in t.split("|")]
        if len(parts) == 3:
            return " | ".join(parts)
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
    """Extract path (list of triples) from various formats."""
    if x is None:
        return []
    if isinstance(x, list):
        out = []
        for v in x:
            nt = _norm_triple(v)
            if nt:
                out.append(nt)
        # Deduplicate preserving order
        seen = set()
        dedup = []
        for t in out:
            if t not in seen:
                seen.add(t)
                dedup.append(t)
        return dedup
    if isinstance(x, str):
        lines = [ln.strip() for ln in x.splitlines() if ln.strip()]
        out = []
        for ln in lines:
            nt = _norm_triple(ln)
            if nt:
                out.append(nt)
        return out
    if isinstance(x, dict):
        for k in ("path", "predicted_path", "reasoning_path", "supporting_triples", "reasoning"):
            if k in x:
                return coerce_path(x.get(k))
    return []


def path_metrics(pred_path: List[str], gold_path: List[str]) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    """Calculate path precision, recall, and EM."""
    if not gold_path:
        return None, None, None
    if not pred_path:
        return 0.0, 0.0, 0
    
    pred_set = set(pred_path)
    gold_set = set(gold_path)
    
    intersection = pred_set & gold_set
    precision = len(intersection) / len(pred_set) if pred_set else 0.0
    recall = len(intersection) / len(gold_set) if gold_set else 0.0
    
    # Path EM: ordered match
    path_em = int(pred_path == gold_path)
    
    return precision, recall, path_em


# ============================================================================
# Pricing
# ============================================================================

@dataclass
class PricingInfo:
    """Pricing information for a model."""
    input_per_mtok: float
    output_per_mtok: float
    long_context_threshold: Optional[int] = None
    input_per_mtok_long: Optional[float] = None
    output_per_mtok_long: Optional[float] = None
    
    def estimate(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
        """Estimate cost in USD."""
        if input_tokens is None or output_tokens is None:
            return None
        
        # Check if long context pricing applies
        if (self.long_context_threshold and 
            input_tokens > self.long_context_threshold and 
            self.input_per_mtok_long is not None and 
            self.output_per_mtok_long is not None):
            input_cost = (input_tokens / 1_000_000) * self.input_per_mtok_long
            output_cost = (output_tokens / 1_000_000) * self.output_per_mtok_long
        else:
            input_cost = (input_tokens / 1_000_000) * self.input_per_mtok
            output_cost = (output_tokens / 1_000_000) * self.output_per_mtok
        
        return input_cost + output_cost


def load_pricing(config_path: Optional[str] = None) -> Dict[str, PricingInfo]:
    """Load pricing configuration."""
    pricing = {}
    if not config_path or not os.path.isfile(config_path):
        return pricing
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            pricing_data = cfg.get("pricing", {})
            for model, info in pricing_data.items():
                pricing[model] = PricingInfo(**info)
    except Exception as e:
        print(f"Warning: Failed to load pricing from {config_path}: {e}", file=sys.stderr)
    
    return pricing


# ============================================================================
# Statistics
# ============================================================================

def safe_mean(xs: List[float]) -> Optional[float]:
    """Calculate mean, filtering out None and NaN."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return (sum(xs) / len(xs)) if xs else None


def safe_stderr(xs: List[float]) -> Optional[float]:
    """Calculate standard error."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    if len(xs) < 2:
        return None
    return statistics.stdev(xs) / (len(xs) ** 0.5)


def confidence_interval_95(xs: List[float]) -> Optional[Tuple[float, float]]:
    """Calculate 95% confidence interval."""
    mean_val = safe_mean(xs)
    stderr_val = safe_stderr(xs)
    if mean_val is None or stderr_val is None:
        return None
    # Approximation using 1.96 * SE for 95% CI
    margin = 1.96 * stderr_val
    return (mean_val - margin, mean_val + margin)


# ============================================================================
# Data Loading
# ============================================================================

def iter_jsonl(path: str):
    """Iterate over JSONL file."""
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON at {path}:{line_no}: {e}", file=sys.stderr)


def find_files(path_or_glob: str, filename: str) -> List[str]:
    """Find files matching pattern."""
    if os.path.isfile(path_or_glob):
        return [path_or_glob]
    
    if os.path.isdir(path_or_glob):
        direct = os.path.join(path_or_glob, filename)
        if os.path.isfile(direct):
            return [direct]
        # Search recursively
        return sorted(glob.glob(os.path.join(path_or_glob, "**", filename), recursive=True))
    
    # Glob pattern
    if any(ch in path_or_glob for ch in ["*", "?", "["]):
        return sorted(glob.glob(path_or_glob, recursive=True))
    
    return []


def get_gold_answer(query: JSON) -> List[str]:
    """Extract gold answer from query."""
    for key in ("gold_answer", "answer", "expected_answer", "final_answer"):
        if key in query:
            return coerce_answer(query[key])
    return []


def get_gold_path(query: JSON) -> List[str]:
    """Extract gold reasoning path from query."""
    for key in ("gold_path", "reasoning_path", "supporting_triples", "path"):
        if key in query:
            return coerce_path(query[key])
    return []


def extract_usage(resp: JSON) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract token usage from response."""
    usage = resp.get("usage", {})
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        
        # Calculate total if not provided
        if total_tokens is None and prompt_tokens is not None and output_tokens is not None:
            total_tokens = prompt_tokens + output_tokens
        
        return prompt_tokens, output_tokens, total_tokens
    
    # Fallback to top-level keys
    prompt_tokens = resp.get("prompt_tokens")
    output_tokens = resp.get("output_tokens") or resp.get("completion_tokens")
    total_tokens = resp.get("total_tokens")
    
    if total_tokens is None and prompt_tokens is not None and output_tokens is not None:
        total_tokens = prompt_tokens + output_tokens
    
    return prompt_tokens, output_tokens, total_tokens


# ============================================================================
# Aggregation
# ============================================================================

@dataclass
class Bucket:
    """Aggregation bucket for metrics."""
    n: int = 0
    em: List[int] = field(default_factory=list)
    f1: List[float] = field(default_factory=list)
    override: List[int] = field(default_factory=list)
    adherence: List[int] = field(default_factory=list)
    prior_knowledge_em: List[int] = field(default_factory=list)
    path_precision: List[float] = field(default_factory=list)
    path_recall: List[float] = field(default_factory=list)
    path_em: List[int] = field(default_factory=list)
    latency_ms: List[float] = field(default_factory=list)
    prompt_tokens: List[int] = field(default_factory=list)
    output_tokens: List[int] = field(default_factory=list)
    total_tokens: List[int] = field(default_factory=list)
    estimated_cost_usd: List[float] = field(default_factory=list)
    parse_error_rate: int = 0
    error_rate: int = 0
    empty_response_rate: int = 0
    finish_reasons: Counter = field(default_factory=Counter)
    
    def finalize(self) -> Dict[str, Any]:
        """Finalize bucket into summary statistics."""
        n = self.n
        result = {
            "n": n,
            "em_mean": safe_mean(self.em),
            "em_stderr": safe_stderr(self.em),
            "em_ci_95": confidence_interval_95(self.em),
            "f1_mean": safe_mean(self.f1),
            "f1_stderr": safe_stderr(self.f1),
            "f1_ci_95": confidence_interval_95(self.f1),
        }
        
        # Optional metrics
        if self.override:
            result["override_rate"] = safe_mean(self.override)
        if self.adherence:
            result["adherence_rate"] = safe_mean(self.adherence)
        if self.prior_knowledge_em:
            result["prior_knowledge_em_mean"] = safe_mean(self.prior_knowledge_em)
        if self.path_precision:
            result["path_precision_mean"] = safe_mean(self.path_precision)
        if self.path_recall:
            result["path_recall_mean"] = safe_mean(self.path_recall)
        if self.path_em:
            result["path_em_mean"] = safe_mean(self.path_em)
        
        # Efficiency metrics
        if self.latency_ms:
            result["latency_ms_mean"] = safe_mean(self.latency_ms)
            result["latency_ms_p50"] = statistics.median(self.latency_ms) if self.latency_ms else None
            result["latency_ms_p95"] = statistics.quantiles(self.latency_ms, n=20)[18] if len(self.latency_ms) >= 20 else None
        
        if self.total_tokens:
            result["total_tokens_mean"] = safe_mean(self.total_tokens)
            result["total_tokens_median"] = statistics.median(self.total_tokens)
        
        if self.prompt_tokens:
            result["prompt_tokens_mean"] = safe_mean(self.prompt_tokens)
        
        if self.output_tokens:
            result["output_tokens_mean"] = safe_mean(self.output_tokens)
        
        if self.estimated_cost_usd:
            result["estimated_cost_usd_mean"] = safe_mean(self.estimated_cost_usd)
            result["estimated_cost_usd_total"] = sum(self.estimated_cost_usd)
        
        # Token efficiency: EM per 1000 tokens
        if self.em and self.total_tokens:
            total_correct = sum(self.em)
            total_tokens_sum = sum(self.total_tokens)
            if total_tokens_sum > 0:
                result["em_per_1k_tokens"] = (total_correct / total_tokens_sum) * 1000
        
        # Error rates
        result["parse_error_rate"] = (self.parse_error_rate / n) if n else 0.0
        result["error_rate"] = (self.error_rate / n) if n else 0.0
        result["empty_response_rate"] = (self.empty_response_rate / n) if n else 0.0
        
        if self.finish_reasons:
            result["finish_reasons"] = dict(self.finish_reasons.most_common(5))
        
        return result


def group_key(resp: JSON) -> Tuple[str, str, str, str, int]:
    """Generate group key from response."""
    return (
        str(resp.get("model", "")),
        str(resp.get("decoding", "")),
        str(resp.get("prompting_strategy", "")),
        str(resp.get("graph_variant", "")),
        int(resp.get("hop") or 0),
    )


# ============================================================================
# Main Evaluation
# ============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Evaluate SPARK benchmark results with comprehensive metrics"
    )
    ap.add_argument("--queries", required=True, help="Path to queries JSONL or directory")
    ap.add_argument("--responses", required=True, help="Path to responses JSONL or directory")
    ap.add_argument("--out_dir", required=True, help="Output directory")
    ap.add_argument("--config", help="Config JSON with pricing info")
    ap.add_argument("--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()
    
    # Setup
    os.makedirs(args.out_dir, exist_ok=True)
    per_record_path = os.path.join(args.out_dir, "per_record.csv")
    summary_path = os.path.join(args.out_dir, "summary.json")
    
    # Load pricing
    pricing = load_pricing(args.config)
    if args.verbose and pricing:
        print(f"Loaded pricing for: {', '.join(sorted(pricing.keys()))}")
    
    # Find files
    query_files = find_files(args.queries, "queries.jsonl")
    if not query_files:
        query_files = find_files(args.queries, "*.jsonl")
    
    resp_files = find_files(args.responses, "responses.jsonl")
    if not resp_files:
        resp_files = find_files(args.responses, "*.jsonl")
    
    if not query_files:
        raise SystemExit(f"No query files found in: {args.queries}")
    if not resp_files:
        raise SystemExit(f"No response files found in: {args.responses}")
    
    if args.verbose:
        print(f"Found {len(query_files)} query file(s)")
        print(f"Found {len(resp_files)} response file(s)")
    
    # Load queries
    query_by_id = {}
    natural_gold_by_intent = {}
    
    for qf in query_files:
        for query in iter_jsonl(qf):
            qid = str(query.get("query_id", ""))
            if qid:
                query_by_id[qid] = query
                
                # Track natural answers by intent
                if query.get("graph_variant") == "natural":
                    intent_key = str(query.get("intent_key", ""))
                    if intent_key:
                        gold = get_gold_answer(query)
                        if gold:
                            natural_gold_by_intent[intent_key] = gold
    
    if args.verbose:
        print(f"Loaded {len(query_by_id)} queries")
        print(f"Found {len(natural_gold_by_intent)} natural intents")
    
    # Aggregation
    overall = Bucket()
    agg: Dict[Tuple, Bucket] = defaultdict(Bucket)
    
    # CSV header
    csv_columns = [
        "prompt_id", "query_id", "intent_key", "model", "decoding",
        "prompting_strategy", "graph_variant", "hop", "template_id",
        "gold_answer", "pred_answer", "exact_match", "f1",
        "override", "adherence", "path_precision", "path_recall", "path_em",
        "prior_knowledge_answer", "prior_knowledge_em",
        "finish_reason", "is_empty_response",
        "latency_ms", "prompt_tokens", "output_tokens", "total_tokens",
        "estimated_cost_usd", "parse_error", "error_type"
    ]
    
    # Process responses
    processed = 0
    with open(per_record_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_columns)
        w.writeheader()
        
        for rf in resp_files:
            for resp in iter_jsonl(rf):
                qid = str(resp.get("query_id") or "")
                q = query_by_id.get(qid, {})
                golds = get_gold_answer(q)
                pred = coerce_answer(resp.get("final_answer"))
                
                # Fallback
                if not pred:
                    pred = coerce_answer(resp.get("parsed_json"))
                
                em, f1 = best_em_f1(pred, golds)
                
                # Counterfactual metrics
                graph_variant = str(resp.get("graph_variant") or "").lower()
                intent_key = str(resp.get("intent_key") or q.get("intent_key") or "")
                natural_gold = natural_gold_by_intent.get(intent_key, [])
                
                override = None
                adherence = None
                prior_knowledge_em = None
                
                # Prior knowledge leakage
                if natural_gold and graph_variant != "natural":
                    pk_match, _ = best_em_f1(pred, natural_gold)
                    prior_knowledge_em = pk_match
                
                # Override & adherence for counterfactual
                if graph_variant == "counterfactual" and golds and natural_gold:
                    if normalize_text(" ".join(natural_gold)) != normalize_text(" ".join(golds)):
                        override = int(best_em_f1(pred, natural_gold)[0] == 1)
                        adherence = int(em == 1)
                
                # Path metrics
                gold_path = get_gold_path(q)
                pred_path = []
                if isinstance(resp.get("parsed_json"), dict):
                    pred_path = coerce_path(resp["parsed_json"])
                if not pred_path:
                    pred_path = coerce_path(resp)
                p_prec, p_rec, p_em = path_metrics(pred_path, gold_path)
                
                # Latency
                latency_ms = resp.get("latency_ms")
                try:
                    latency_ms = float(latency_ms) if latency_ms is not None else None
                except:
                    latency_ms = None
                
                # Tokens & cost
                prompt_tokens, output_tokens, total_tokens = extract_usage(resp)
                model = str(resp.get("model") or "")
                est_cost = None
                if model in pricing:
                    est_cost = pricing[model].estimate(prompt_tokens, output_tokens)
                
                # Errors
                parse_error = resp.get("parse_error")
                error_obj = resp.get("error")
                error_type = ""
                if isinstance(error_obj, dict):
                    error_type = str(error_obj.get("type") or "")
                
                # Finish reason
                samples = resp.get("samples") or []
                finish_reason = None
                if samples and isinstance(samples, list) and len(samples) > 0:
                    finish_reason = samples[0].get("finish_reason")
                
                # Empty response
                is_empty = 0
                if not pred or all(not s.strip() for s in pred):
                    is_empty = 1
                
                # Write row
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
                    "gold_answer": golds[0] if len(golds) == 1 else json.dumps(golds, ensure_ascii=False),
                    "pred_answer": pred[0] if len(pred) == 1 else json.dumps(pred, ensure_ascii=False),
                    "exact_match": em,
                    "f1": f1,
                    "override": override,
                    "adherence": adherence,
                    "path_precision": p_prec,
                    "path_recall": p_rec,
                    "path_em": p_em,
                    "prior_knowledge_answer": natural_gold[0] if natural_gold and len(natural_gold) == 1 else json.dumps(natural_gold, ensure_ascii=False) if natural_gold else None,
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
                
                # Aggregate
                gk = group_key(resp)
                for bucket in (overall, agg[gk]):
                    bucket.n += 1
                    bucket.em.append(em)
                    bucket.f1.append(f1)
                    
                    if override is not None:
                        bucket.override.append(override)
                    if adherence is not None:
                        bucket.adherence.append(adherence)
                    if p_prec is not None:
                        bucket.path_precision.append(float(p_prec))
                    if p_rec is not None:
                        bucket.path_recall.append(float(p_rec))
                    if p_em is not None:
                        bucket.path_em.append(int(p_em))
                    if prior_knowledge_em is not None:
                        bucket.prior_knowledge_em.append(prior_knowledge_em)
                    if finish_reason:
                        bucket.finish_reasons[finish_reason] += 1
                    bucket.empty_response_rate += is_empty
                    
                    if latency_ms is not None:
                        bucket.latency_ms.append(latency_ms)
                    if prompt_tokens is not None:
                        bucket.prompt_tokens.append(prompt_tokens)
                    if output_tokens is not None:
                        bucket.output_tokens.append(output_tokens)
                    if total_tokens is not None:
                        bucket.total_tokens.append(total_tokens)
                    if est_cost is not None:
                        bucket.estimated_cost_usd.append(est_cost)
                    
                    if parse_error:
                        bucket.parse_error_rate += 1
                    if error_type:
                        bucket.error_rate += 1
                
                processed += 1
                if args.verbose and processed % 100 == 0:
                    print(f"Processed {processed} responses...", file=sys.stderr)
    
    if args.verbose:
        print(f"Processed {processed} total responses")
    
    # Finalize summary
    summary = {
        "overall": overall.finalize(),
        "groups": {}
    }
    
    for k, bucket in agg.items():
        model, decoding, prompting, graph, hop = k
        group_name = f"{model}::{decoding}::{prompting}::{graph}::H{hop}"
        summary["groups"][group_name] = bucket.finalize()
    
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Output
    result = {
        "query_files": query_files,
        "response_files": resp_files,
        "total_processed": processed,
        "per_record_csv": per_record_path,
        "summary_json": summary_path,
        "pricing_loaded_models": sorted(pricing.keys()),
        "num_groups": len(summary["groups"]),
    }
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()