#!/usr/bin/env python3
"""
evaluate.py

Computes metrics for SPARK experiments.
Reads responses.jsonl files from the output directory (produced by run_sweep_gcp.py)
and compares them against ground truth queries.

Metrics:
- EM (Exact Match)
- F1 (Token overlap)
- Override Rate (for Counterfactual)
- Efficiency (Tokens, Latency)

Usage:
    python scripts/evaluate.py --queries sources/queries/instances --responses out --out_dir eval
"""

import argparse
import collections
import glob
import json
import os
import re
import string
from typing import Any, Dict, List, Set, Tuple

import pandas as pd
from tqdm import tqdm

def normalize_answer(s: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(str(s)))))

def f1_score(prediction: str, ground_truth: str) -> float:
    prediction_tokens = normalize_answer(prediction).split()
    ground_truth_tokens = normalize_answer(ground_truth).split()
    common = collections.Counter(prediction_tokens) & collections.Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1

def exact_match_score(prediction: str, ground_truth: str) -> bool:
    return normalize_answer(prediction) == normalize_answer(ground_truth)

def metric_max_over_ground_truths(metric_fn, prediction, ground_truths):
    scores_for_ground_truths = []
    for ground_truth in ground_truths:
        score = metric_fn(prediction, ground_truth)
        scores_for_ground_truths.append(score)
    return max(scores_for_ground_truths)

def load_queries(instances_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads all query instances from JSONL files in the directory.
    Returns a dict mapping query_id -> query_obj
    """
    queries = {}
    print(f"Loading queries from {instances_dir}...")
    files = glob.glob(os.path.join(instances_dir, "*.jsonl"))
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                queries[obj["id"]] = obj
    print(f"Loaded {len(queries)} queries.")
    return queries

def load_responses(response_dir: str) -> List[Dict[str, Any]]:
    """
    Recursively finds responses.jsonl files.
    Returns a list of response objects, augmented with run metadata inferred from path if missing.
    """
    print(f"Scanning for responses in {response_dir}...")
    responses = []
    # Pattern: out_dir/model/decoding/responses.jsonl
    files = glob.glob(os.path.join(response_dir, "**", "responses.jsonl"), recursive=True)
    
    for fpath in files:
        # Try to infer model/decoding from path if needed
        # path parts: .../out/model_name/decoding_strategy/responses.jsonl
        path_parts = os.path.normpath(fpath).split(os.sep)
        
        # Heuristic: assume standard structure
        inferred_model = path_parts[-3] if len(path_parts) >= 3 else "unknown_model"
        inferred_decoding = path_parts[-2] if len(path_parts) >= 3 else "unknown_decoding"
        
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    # Backfill generic fields if missing
                    if "model" not in obj:
                        obj["model"] = inferred_model
                    if "decoding" not in obj:
                        obj["decoding"] = inferred_decoding
                    responses.append(obj)
                except json.JSONDecodeError:
                    continue
                    
    print(f"Loaded {len(responses)} total response records.")
    return responses

def calculate_cost(model: str, usage: Dict[str, int], pricing: Dict[str, Any]) -> float:
    """
    Calculates cost for a single request based on usage and pricing config.
    Pricing keys: input_per_mtok, output_per_mtok, input_per_mtok_long, output_per_mtok_long, long_context_threshold
    Usage keys: prompt_token_count, candidates_token_count (or completion_tokens/prompt_tokens variants)
    """
    if not pricing or model not in pricing:
        return 0.0

    model_price = pricing[model]
    
    # Normalize usage keys
    prompt_tokens = usage.get("prompt_token_count") or usage.get("prompt_tokens") or 0
    output_tokens = usage.get("candidates_token_count") or usage.get("completion_tokens") or 0
    
    # Long context logic
    threshold = model_price.get("long_context_threshold", float("inf"))
    is_long = prompt_tokens > threshold
    
    in_price = model_price.get("input_per_mtok_long" if is_long else "input_per_mtok", 0.0)
    out_price = model_price.get("output_per_mtok_long" if is_long else "output_per_mtok", 0.0)
    
    input_cost = (prompt_tokens / 1_000_000) * in_price
    output_cost = (output_tokens / 1_000_000) * out_price
    
    return input_cost + output_cost

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True, help="Directory containing query instance JSONL files (ground truth).")
    parser.add_argument("--responses", required=True, help="Root directory containing response JSONL files.")
    parser.add_argument("--out_dir", required=True, help="Directory to save evaluation results.")
    parser.add_argument("--natural_queries", default=None, help="Path to natural queries JSONL (optional, required for rigorous override rate calculation if IDs match).")
    parser.add_argument("--config", default="config/config.json", help="Path to config file (optional, for reference).")
    
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)

    # 0. Load Config & Pricing
    pricing = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                pricing = cfg.get("pricing", {})
            print(f"Loaded pricing for models: {list(pricing.keys())}")
        except Exception as e:
            print(f"Warning: Failed to load config/pricing: {e}")
    
    # 1. Load Ground Truth
    queries = load_queries(args.queries)
    
    # Optional: Load natural queries map for Counterfactual Override checking
    natural_answers = {}
    if args.natural_queries and os.path.exists(args.natural_queries):
        print(f"Loading natural queries from {args.natural_queries} for override checks...")
        with open(args.natural_queries, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                # Map by ID. Assuming CF queries have same ID or we map by intent/question.
                # Usually CF queries share the same ID or can be mapped. 
                # If they have different IDs, we might need a mapping key.
                # In this project, let's assume `id` or `intent_key` helps. 
                # For now, we store by `intent_key` and `hop` as a composite key if IDs vary.
                key = obj.get("id") 
                natural_answers[key] = obj.get("gold_answer")
                
    # 2. Load Responses
    responses = load_responses(args.responses)
    
    results = []
    
    print("Evaluating...")
    for resp in tqdm(responses):
        qid = resp.get("query_id")
        if qid not in queries:
            # warn or skip
            continue
            
        q = queries[qid]
        
        # Extract prediction
        pred_text = getattr(resp, "final_answer", None)
        
        # If final_answer is missing in top-level, check parsed_json
        if not pred_text and resp.get("parsed_json"):
            pred_text = resp["parsed_json"].get("final_answer")
            
        # Fallback to response_text if nothing else (usually raw text)
        if not pred_text:
            pred_text = resp.get("response_text", "")
            
        # 3. Compute Metrics
        
        # Gold answers can be a list or single string
        golds = q.get("gold_answers", [])
        if not golds and "gold_answer" in q:
            golds = [q["gold_answer"]]
        
        # Normalize unknowns for easier classification
        unknown_tokens = {"unknown", "i dont know", "none", "not defined"}
        normalized_pred = normalize_answer(str(pred_text))
        is_pred_unknown = normalized_pred in unknown_tokens
        
        # Determine if gold is effectively unknown (empty list or "unknown")
        is_gold_unknown = (not golds) or (any(normalize_answer(x) in unknown_tokens for x in golds))

        # Check correctness
        is_correct = metric_max_over_ground_truths(exact_match_score, str(pred_text), golds)
        f1 = metric_max_over_ground_truths(f1_score, str(pred_text), golds)
        
        # Parse Errors
        parse_error = 1 if resp.get("parse_error") else 0
        
        # Detailed Failure Categorization
        outcome = "correct"
        if not is_correct:
            if parse_error:
                outcome = "parse_error"
            elif is_gold_unknown and not is_pred_unknown:
                outcome = "hallucinated_answer" # Should have been unknown, but gave an answer
            elif not is_gold_unknown and is_pred_unknown:
                outcome = "missed_answer" # Should have been an answer, but gave unknown
            else:
                outcome = "wrong_answer" # Gave an answer, but it was the wrong one

        # Override Rate / Parametric Leakage (Counterfactual only)
        # Check if it matches the *natural* answer despite being a CF query
        is_parametric_leakage = False
        natural_gold = None
        if resp.get("graph_variant") == "counterfactual":
            # Try to find natural answer
            natural_gold = natural_answers.get(qid)
            if natural_gold:
                 # Only count as leakage if it matches natural AND is incorrect for current graph
                 # (Though usually if it matches natural in CF, it IS incorrect, unless the fact wasn't changed)
                 if metric_max_over_ground_truths(exact_match_score, str(pred_text), [natural_gold]) and not is_correct:
                    is_parametric_leakage = True
                    outcome = "parametric_leakage" # Specific subtype of wrong_answer

        # Efficiency
        usage = resp.get("usage_total_across_samples", {})
        total_tokens = usage.get("total_token_count", 0)
        latency = resp.get("latency_ms", 0)
        cost = calculate_cost(resp.get("model"), usage, pricing)
        
        # Append result
        res_record = {
            "query_id": qid,
            "model": resp.get("model"),
            "decoding": resp.get("decoding"),
            "prompting_strategy": resp.get("prompting_strategy"),
            "graph_variant": resp.get("graph_variant"),
            "hop": str(resp.get("hop")),
            "template_id": resp.get("template_id"),
            "prediction": str(pred_text),
            "gold": golds[0] if golds else "",
            "natural_gold": natural_gold if natural_gold else "",
            "em": 1 if is_correct else 0,
            "f1": f1,
            "outcome": outcome,
            "parse_error": parse_error,
            "parametric_leakage": 1 if is_parametric_leakage else 0,
            "total_tokens": total_tokens,
            "latency_ms": latency,
            "cost": cost
        }
        results.append(res_record)
        
    # 4. Save results
    df = pd.DataFrame(results)
    out_csv = os.path.join(args.out_dir, "evaluation_results.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved evaluation results to {out_csv}")
    
    # 5. Print Summary
    if not df.empty:
        summary = df.groupby(["model", "graph_variant", "prompting_strategy"]).agg({
            "em": "mean",
            "f1": "mean",
            "parametric_leakage": "mean",
            "parse_error": "mean",
            "total_tokens": "mean",
            "latency_ms": "mean",
            "cost": "mean"
        }).reset_index()
        
        # Detailed failure counts
        failure_counts = df.pivot_table(index=["model", "graph_variant"], columns="outcome", aggfunc="size", fill_value=0)
        
        print("\nSummary:")
        print(summary.to_string())
        
        print("\nFailure Categories Count:")
        print(failure_counts.to_string())
        
        summary_csv = os.path.join(args.out_dir, "evaluation_summary.csv")
        summary.to_csv(summary_csv, index=False)
        print(f"Saved summary to {summary_csv}")

if __name__ == "__main__":
    main()
