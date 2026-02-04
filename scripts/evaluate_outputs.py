#!/usr/bin/env python3
"""
Evaluate LLM outputs against ground-truth MetaQA-style queries.

Inputs:
- queries.jsonl        (contains gold_answers, gold_path, metadata)
- model_outputs.jsonl  (contains model generations)

Output:
- evaluation.jsonl     (per-query metrics)
- optional aggregate metrics printed to stdout
"""

import json
import argparse
from collections import defaultdict
from typing import Dict, List


# -------------------------
# Utilities
# -------------------------

def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def normalize_answer(ans: str) -> str:
    return ans.strip().lower()


def exact_match(pred: str, gold: List[str]) -> int:
    pred_n = normalize_answer(pred)
    gold_n = {normalize_answer(g) for g in gold}
    return int(pred_n in gold_n)


def f1_score(pred: str, gold: List[str]) -> float:
    """
    Token-level F1 (simple, robust, standard)
    """
    pred_tokens = normalize_answer(pred).split()
    if not pred_tokens:
        return 0.0

    scores = []
    for g in gold:
        gold_tokens = normalize_answer(g).split()
        common = set(pred_tokens) & set(gold_tokens)
        if not common:
            scores.append(0.0)
            continue

        precision = len(common) / len(pred_tokens)
        recall = len(common) / len(gold_tokens)
        scores.append(2 * precision * recall / (precision + recall))

    return max(scores)


def parse_final_answer(text: str) -> str:
    """
    Extract final_answer from model output text.
    Expected formats:
      {"final_answer": "..."}
      {"reasoning": [...], "final_answer": "..."}
    """
    try:
        obj = json.loads(text)
        return obj.get("final_answer", "").strip()
    except Exception:
        return ""


# -------------------------
# Main evaluation
# -------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries_path", required=True)
    parser.add_argument("--outputs_path", required=True)
    parser.add_argument("--out_path", required=True)
    args = parser.parse_args()

    # Load ground truth
    queries: Dict[str, dict] = {}
    for q in load_jsonl(args.queries_path):
        queries[q["id"]] = q

    # Accumulators
    results = []
    totals = defaultdict(float)
    count = 0

    # Evaluate outputs
    for out in load_jsonl(args.outputs_path):
        qid = out["query_id"]
        if qid not in queries:
            continue

        query = queries[qid]
        gold_answers = query.get("gold_answers", [])

        responses = out.get("responses", [])
        if not responses:
            pred = ""
        else:
            pred = parse_final_answer(responses[0]["text"])

        em = exact_match(pred, gold_answers)
        f1 = f1_score(pred, gold_answers)

        record = {
            "query_id": qid,
            "prediction": pred,
            "gold_answers": gold_answers,
            "exact_match": em,
            "f1": f1,
            # metadata for slicing
            "model": out.get("model"),
            "prompting_strategy": out.get("prompting_strategy"),
            "graph_variant": query.get("graph_variant"),
            "hop": query.get("hop"),
            "template_id": query.get("template_id"),
        }

        results.append(record)

        totals["exact_match"] += em
        totals["f1"] += f1
        count += 1

    # Write per-instance results
    with open(args.out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Print aggregate metrics
    if count > 0:
        print("==== Evaluation summary ====")
        print(f"Queries evaluated: {count}")
        print(f"Exact Match: {totals['exact_match'] / count:.4f}")
        print(f"F1:          {totals['f1'] / count:.4f}")
    else:
        print("No evaluable queries found.")


if __name__ == "__main__":
    main()