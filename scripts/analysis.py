#!/usr/bin/env python3
"""
analysis.py

Aggregate evaluation outputs produced by evaluate.py.

Inputs:
- An evaluation directory produced by evaluate.py (contains per_record.csv), OR
- A directory containing multiple evaluation directories.

Outputs (written to --out_dir):
- aggregate_by_cell.csv
- leaderboard.csv
- accuracy_by_hop.csv
- optional plots (*.png) if matplotlib is installed

Experiment cell = model × hop × prompting_strategy × decoding × graph_variant
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import statistics
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple


def find_per_record_files(path_or_dir: str) -> List[str]:
    if os.path.isfile(path_or_dir) and path_or_dir.endswith(".csv"):
        return [path_or_dir]
    if os.path.isdir(path_or_dir):
        direct = os.path.join(path_or_dir, "per_record.csv")
        if os.path.isfile(direct):
            return [direct]
        # search recursively
        return sorted(glob.glob(os.path.join(path_or_dir, "**", "per_record.csv"), recursive=True))
    # glob
    if any(ch in path_or_dir for ch in ["*", "?", "["]):
        return sorted(glob.glob(path_or_dir, recursive=True))
    raise FileNotFoundError(path_or_dir)


def safe_mean(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return (sum(xs) / len(xs)) if xs else None


def safe_stderr(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    if len(xs) < 2:
        return None
    return statistics.stdev(xs) / (len(xs) ** 0.5)


def to_float(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except Exception:
        return None


def to_int(x: Any) -> Optional[int]:
    if x is None or x == "":
        return None
    try:
        return int(float(x))
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True, help="Path to per_record.csv, an eval dir, or a parent dir of many eval dirs.")
    ap.add_argument("--out_dir", required=True, help="Output directory.")
    ap.add_argument("--make_plots", action="store_true", help="If set, write PNG plots (requires matplotlib).")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    per_record_files = find_per_record_files(args.eval)
    if not per_record_files:
        raise SystemExit("No per_record.csv found.")

    # Aggregations
    # key: (model, decoding, prompting_strategy, graph_variant, hop)
    buckets: Dict[Tuple[str,str,str,str,int], Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    for pr in per_record_files:
        with open(pr, "r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                key = (
                    row.get("model",""),
                    row.get("decoding",""),
                    row.get("prompting_strategy",""),
                    row.get("graph_variant",""),
                    int(row.get("hop") or 0),
                )
                buckets[key]["em"].append(to_float(row.get("exact_match")) or 0.0)
                buckets[key]["f1"].append(to_float(row.get("f1")) or 0.0)

                ov = to_float(row.get("override"))
                if ov is not None:
                    buckets[key]["override"].append(ov)
                ad = to_float(row.get("adherence"))
                if ad is not None:
                    buckets[key]["adherence"].append(ad)

                pp = to_float(row.get("path_precision"))
                if pp is not None:
                    buckets[key]["path_precision"].append(pp)
                prc = to_float(row.get("path_recall"))
                if prc is not None:
                    buckets[key]["path_recall"].append(prc)
                pem = to_float(row.get("path_em"))
                if pem is not None:
                    buckets[key]["path_em"].append(pem)

                lat = to_float(row.get("latency_ms"))
                if lat is not None:
                    buckets[key]["latency_ms"].append(lat)
                tt = to_float(row.get("total_tokens"))
                if tt is not None:
                    buckets[key]["total_tokens"].append(tt)
                cost = to_float(row.get("estimated_cost_usd"))
                if cost is not None:
                    buckets[key]["estimated_cost_usd"].append(cost)
                
                pk_em = to_float(row.get("prior_knowledge_em"))
                if pk_em is not None:
                    buckets[key]["prior_knowledge_em"].append(pk_em)
                
                is_empty = to_float(row.get("is_empty_response"))
                if is_empty is not None:
                    buckets[key]["is_empty_response"].append(is_empty)
                
                parse_err = row.get("parse_error") or ""
                if parse_err:
                     buckets[key]["parse_error_rate"].append(1.0)
                else:
                     buckets[key]["parse_error_rate"].append(0.0)


    aggregate_csv = os.path.join(args.out_dir, "aggregate_by_cell.csv")
    leaderboard_csv = os.path.join(args.out_dir, "leaderboard.csv")
    accuracy_by_hop_csv = os.path.join(args.out_dir, "accuracy_by_hop.csv")

    # Write aggregate_by_cell.csv
    with open(aggregate_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "model","decoding","prompting_strategy","graph_variant","hop","n",
            "em_mean","em_stderr","f1_mean","f1_stderr",
            "override_rate","adherence_rate","prior_knowledge_em_mean",
            "path_precision_mean","path_recall_mean","path_em_mean",
            "latency_ms_mean","total_tokens_mean","estimated_cost_usd_mean",
            "parse_error_rate","empty_response_rate"
        ])
        for (model,decoding,prompting,graph,hop), m in sorted(buckets.items()):
            n = len(m["em"])
            w.writerow([
                model,decoding,prompting,graph,hop,n,
                safe_mean(m["em"]), safe_stderr(m["em"]),
                safe_mean(m["f1"]), safe_stderr(m["f1"]),
                safe_mean(m["override"]) if m.get("override") else None,
                safe_mean(m["adherence"]) if m.get("adherence") else None,
                safe_mean(m["prior_knowledge_em"]) if m.get("prior_knowledge_em") else None,
                safe_mean(m["path_precision"]) if m.get("path_precision") else None,
                safe_mean(m["path_recall"]) if m.get("path_recall") else None,
                safe_mean(m["path_em"]) if m.get("path_em") else None,
                safe_mean(m["latency_ms"]) if m.get("latency_ms") else None,
                safe_mean(m["total_tokens"]) if m.get("total_tokens") else None,
                safe_mean(m["estimated_cost_usd"]) if m.get("estimated_cost_usd") else None,
                safe_mean(m["parse_error_rate"]) if m.get("parse_error_rate") else None,
                safe_mean(m["is_empty_response"]) if m.get("is_empty_response") else None,
            ])

    # Leaderboard: aggregate over hop + prompting_strategy + graph_variant for each model/decoding
    leaderboard: Dict[Tuple[str,str], Dict[str,List[float]]] = defaultdict(lambda: defaultdict(list))
    for (model,decoding,_,_,_), m in buckets.items():
        leaderboard[(model,decoding)]["em"].extend(m["em"])
        leaderboard[(model,decoding)]["f1"].extend(m["f1"])
        leaderboard[(model,decoding)]["latency_ms"].extend(m.get("latency_ms", []))
        leaderboard[(model,decoding)]["total_tokens"].extend(m.get("total_tokens", []))
        leaderboard[(model,decoding)]["estimated_cost_usd"].extend(m.get("estimated_cost_usd", []))

    with open(leaderboard_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model","decoding","n","em_mean","f1_mean","latency_ms_mean","total_tokens_mean","estimated_cost_usd_mean"])
        rows = []
        for (model,decoding), m in leaderboard.items():
            rows.append((
                safe_mean(m["em"]) or 0.0,
                [model,decoding,len(m["em"]),safe_mean(m["em"]),safe_mean(m["f1"]),
                 safe_mean(m.get("latency_ms", [])), safe_mean(m.get("total_tokens", [])), safe_mean(m.get("estimated_cost_usd", []))]
            ))
        # sort by EM desc
        for _, row in sorted(rows, key=lambda x: x[0], reverse=True):
            w.writerow(row)

    # Accuracy by hop (collapsed over prompting strategy and graph variant)
    # key: (model, decoding, hop)
    by_hop: Dict[Tuple[str,str,int], List[float]] = defaultdict(list)
    for (model,decoding,_,_,hop), m in buckets.items():
        by_hop[(model,decoding,hop)].extend(m["em"])

    with open(accuracy_by_hop_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model","decoding","hop","n","em_mean","em_stderr"])
        for (model,decoding,hop), ems in sorted(by_hop.items()):
            w.writerow([model,decoding,hop,len(ems),safe_mean(ems),safe_stderr(ems)])

    # Plots (optional)
    if args.make_plots:
        try:
            import matplotlib.pyplot as plt  # type: ignore
        except Exception:
            print("matplotlib not available; skipping plots.")
            print(json.dumps({"aggregate_by_cell": aggregate_csv, "leaderboard": leaderboard_csv, "accuracy_by_hop": accuracy_by_hop_csv}, indent=2))
            return

        # Plot: EM by hop per model (separate plot per decoding)
        decodings = sorted(set(d for (_,d,_) in by_hop.keys()))
        for dec in decodings:
            plt.figure()
            # group by model
            models = sorted(set(m for (m,d,_) in by_hop.keys() if d == dec))
            for model in models:
                hops = sorted(set(h for (m,d,h) in by_hop.keys() if m==model and d==dec))
                ys = [safe_mean(by_hop[(model,dec,h)]) for h in hops]
                plt.plot(hops, ys, marker="o", label=model)
            plt.xlabel("Hop length")
            plt.ylabel("Exact Match (mean)")
            plt.title(f"Accuracy by hop ({dec})")
            plt.xticks([1,2,3])
            plt.legend()
            plt.grid(True, linestyle=":", linewidth=0.5)
            outp = os.path.join(args.out_dir, f"accuracy_by_hop_{dec}.png")
            plt.savefig(outp, dpi=180, bbox_inches="tight")
            plt.close()
        
        # Plot: Override Rate by Model (Counterfactual)
        # We aggregate over all hops/decoding/strategy for 'counterfactual' graph
        # key: model
        override_by_model = defaultdict(list)
        for (model,dec,_,graph,hop), m in buckets.items():
            if graph == "counterfactual" and "override" in m:
                override_by_model[model].extend(m["override"])
        
        if override_by_model:
            plt.figure()
            models = sorted(override_by_model.keys())
            means = [safe_mean(override_by_model[m]) or 0.0 for m in models]
            plt.bar(models, means)
            plt.xlabel("Model")
            plt.ylabel("Override Rate (mean)")
            plt.title("Override Rate on Counterfactual Graph")
            plt.ylim(0, 1)
            plt.grid(True, axis="y", linestyle=":", linewidth=0.5)
            outp = os.path.join(args.out_dir, "override_rate_by_model.png")
            plt.savefig(outp, dpi=180, bbox_inches="tight")
            plt.close()

        # Plot: Path EM by Model
        path_em_by_model = defaultdict(list)
        for (model,_,_,_,_), m in buckets.items():
            if "path_em" in m:
                 path_em_by_model[model].extend(m["path_em"])
        
        if path_em_by_model:
            plt.figure()
            models = sorted(path_em_by_model.keys())
            means = [safe_mean(path_em_by_model[m]) or 0.0 for m in models]
            plt.bar(models, means)
            plt.xlabel("Model")
            plt.ylabel("Path Exact Match (mean)")
            plt.title("Path Reconstruction Accuracy (Path EM)")
            plt.ylim(0, 1)
            plt.grid(True, axis="y", linestyle=":", linewidth=0.5)
            outp = os.path.join(args.out_dir, "path_em_by_model.png")
            plt.savefig(outp, dpi=180, bbox_inches="tight")
            plt.close()

        # Plot: efficiency trade-off (EM vs total tokens) for each experiment cell
        plt.figure()
        xs = []
        ys = []
        labels = []
        for (model,dec,prompting,graph,hop), m in buckets.items():
            em = safe_mean(m["em"])
            tt = safe_mean(m.get("total_tokens", []))
            if em is None or tt is None:
                continue
            xs.append(tt)
            ys.append(em)
            labels.append(f"{model}/{dec}/{prompting}/{graph}/H{hop}")
        plt.scatter(xs, ys)
        plt.xlabel("Total tokens (mean)")
        plt.ylabel("Exact Match (mean)")
        plt.title("Accuracy vs token usage (cells)")
        plt.grid(True, linestyle=":", linewidth=0.5)
        outp = os.path.join(args.out_dir, "accuracy_vs_tokens_cells.png")
        plt.savefig(outp, dpi=180, bbox_inches="tight")
        plt.close()

    print(json.dumps({
        "per_record_files": per_record_files,
        "aggregate_by_cell": aggregate_csv,
        "leaderboard": leaderboard_csv,
        "accuracy_by_hop": accuracy_by_hop_csv,
        "plots_written": bool(args.make_plots),
    }, indent=2))


if __name__ == "__main__":
    main()
