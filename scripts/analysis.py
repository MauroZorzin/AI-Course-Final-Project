#!/usr/bin/env python3
"""
analysis.py - SPARK Benchmark Analysis

Aggregates and visualizes evaluation results from evaluate.py.

Usage:
    python analysis.py --eval eval/natural --out_dir analysis/natural --make_plots
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# Utilities
# ============================================================================

def find_per_record_files(path_or_dir: str) -> List[str]:
    """Find per_record.csv files."""
    if os.path.isfile(path_or_dir) and path_or_dir.endswith(".csv"):
        return [path_or_dir]
    if os.path.isdir(path_or_dir):
        direct = os.path.join(path_or_dir, "per_record.csv")
        if os.path.isfile(direct):
            return [direct]
        # Search recursively
        return sorted(glob.glob(os.path.join(path_or_dir, "**", "per_record.csv"), recursive=True))
    # Glob
    if any(ch in path_or_dir for ch in ["*", "?", "["]):
        return sorted(glob.glob(path_or_dir, recursive=True))
    raise FileNotFoundError(f"No per_record.csv found: {path_or_dir}")


def safe_mean(xs: List[float]) -> Optional[float]:
    """Calculate mean, filtering invalid values."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return (sum(xs) / len(xs)) if xs else None


def safe_stderr(xs: List[float]) -> Optional[float]:
    """Calculate standard error."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    if len(xs) < 2:
        return None
    return statistics.stdev(xs) / (len(xs) ** 0.5)


def safe_median(xs: List[float]) -> Optional[float]:
    """Calculate median."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return statistics.median(xs) if xs else None


def safe_percentile(xs: List[float], p: float) -> Optional[float]:
    """Calculate percentile (0-100)."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    if not xs:
        return None
    xs_sorted = sorted(xs)
    k = (len(xs_sorted) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs_sorted[int(k)]
    return xs_sorted[int(f)] * (c - k) + xs_sorted[int(c)] * (k - f)


def confidence_interval_95(xs: List[float]) -> Optional[Tuple[float, float]]:
    """Calculate 95% confidence interval."""
    mean_val = safe_mean(xs)
    stderr_val = safe_stderr(xs)
    if mean_val is None or stderr_val is None:
        return None
    margin = 1.96 * stderr_val
    return (mean_val - margin, mean_val + margin)


def to_float(x: Any) -> Optional[float]:
    """Convert to float safely."""
    if x is None or x == "":
        return None
    try:
        return float(x)
    except:
        return None


def to_int(x: Any) -> Optional[int]:
    """Convert to int safely."""
    if x is None or x == "":
        return None
    try:
        return int(float(x))
    except:
        return None


# ============================================================================
# Data Aggregation
# ============================================================================

def load_per_record_data(per_record_files: List[str]) -> Dict:
    """Load and aggregate per-record data."""
    # Key: (model, decoding, prompting_strategy, graph_variant, hop)
    buckets = defaultdict(lambda: defaultdict(list))
    
    total_rows = 0
    for pr in per_record_files:
        with open(pr, "r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                key = (
                    row.get("model", ""),
                    row.get("decoding", ""),
                    row.get("prompting_strategy", ""),
                    row.get("graph_variant", ""),
                    int(row.get("hop") or 0),
                )
                
                # Core metrics
                buckets[key]["em"].append(to_float(row.get("exact_match")) or 0.0)
                buckets[key]["f1"].append(to_float(row.get("f1")) or 0.0)
                
                # Optional metrics
                for metric in ["override", "adherence", "prior_knowledge_em",
                               "path_precision", "path_recall", "path_em",
                               "latency_ms", "total_tokens", "estimated_cost_usd"]:
                    val = to_float(row.get(metric))
                    if val is not None:
                        buckets[key][metric].append(val)
                
                # Error tracking
                buckets[key]["is_empty_response"].append(to_float(row.get("is_empty_response")) or 0.0)
                
                parse_err = row.get("parse_error") or ""
                if parse_err:
                    buckets[key]["parse_error_rate"].append(1.0)
                else:
                    buckets[key]["parse_error_rate"].append(0.0)
                
                total_rows += 1
    
    return {"buckets": buckets, "total_rows": total_rows}


# ============================================================================
# Export Functions
# ============================================================================

def export_aggregate_by_cell(buckets: Dict, out_path: str):
    """Export aggregate_by_cell.csv with enhanced statistics."""
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "model", "decoding", "prompting_strategy", "graph_variant", "hop", "n",
            "em_mean", "em_stderr", "em_ci_95_low", "em_ci_95_high",
            "f1_mean", "f1_stderr", "f1_ci_95_low", "f1_ci_95_high",
            "override_rate", "adherence_rate", "prior_knowledge_em_mean",
            "path_precision_mean", "path_recall_mean", "path_em_mean",
            "latency_ms_mean", "latency_ms_median", "latency_ms_p95",
            "total_tokens_mean", "total_tokens_median",
            "estimated_cost_usd_mean", "estimated_cost_usd_total",
            "parse_error_rate", "empty_response_rate",
            "em_per_1k_tokens"
        ])
        
        for (model, decoding, prompting, graph, hop), m in sorted(buckets.items()):
            n = len(m["em"])
            
            em_ci = confidence_interval_95(m["em"])
            f1_ci = confidence_interval_95(m["f1"])
            
            # Token efficiency
            em_per_1k = None
            if m.get("total_tokens") and m.get("em"):
                total_correct = sum(m["em"])
                total_tokens_sum = sum(m["total_tokens"])
                if total_tokens_sum > 0:
                    em_per_1k = (total_correct / total_tokens_sum) * 1000
            
            w.writerow([
                model, decoding, prompting, graph, hop, n,
                safe_mean(m["em"]), safe_stderr(m["em"]),
                em_ci[0] if em_ci else None, em_ci[1] if em_ci else None,
                safe_mean(m["f1"]), safe_stderr(m["f1"]),
                f1_ci[0] if f1_ci else None, f1_ci[1] if f1_ci else None,
                safe_mean(m.get("override", [])) if m.get("override") else None,
                safe_mean(m.get("adherence", [])) if m.get("adherence") else None,
                safe_mean(m.get("prior_knowledge_em", [])) if m.get("prior_knowledge_em") else None,
                safe_mean(m.get("path_precision", [])) if m.get("path_precision") else None,
                safe_mean(m.get("path_recall", [])) if m.get("path_recall") else None,
                safe_mean(m.get("path_em", [])) if m.get("path_em") else None,
                safe_mean(m.get("latency_ms", [])) if m.get("latency_ms") else None,
                safe_median(m.get("latency_ms", [])) if m.get("latency_ms") else None,
                safe_percentile(m.get("latency_ms", []), 95) if m.get("latency_ms") else None,
                safe_mean(m.get("total_tokens", [])) if m.get("total_tokens") else None,
                safe_median(m.get("total_tokens", [])) if m.get("total_tokens") else None,
                safe_mean(m.get("estimated_cost_usd", [])) if m.get("estimated_cost_usd") else None,
                sum(m.get("estimated_cost_usd", [])) if m.get("estimated_cost_usd") else None,
                safe_mean(m.get("parse_error_rate", [])) if m.get("parse_error_rate") else None,
                safe_mean(m.get("is_empty_response", [])) if m.get("is_empty_response") else None,
                em_per_1k
            ])


def export_leaderboard(buckets: Dict, out_path: str):
    """Export leaderboard.csv with comprehensive model rankings."""
    # Aggregate over hop + prompting_strategy + graph_variant
    leaderboard = defaultdict(lambda: defaultdict(list))
    
    for (model, decoding, _, _, _), m in buckets.items():
        leaderboard[(model, decoding)]["em"].extend(m["em"])
        leaderboard[(model, decoding)]["f1"].extend(m["f1"])
        leaderboard[(model, decoding)]["latency_ms"].extend(m.get("latency_ms", []))
        leaderboard[(model, decoding)]["total_tokens"].extend(m.get("total_tokens", []))
        leaderboard[(model, decoding)]["estimated_cost_usd"].extend(m.get("estimated_cost_usd", []))
    
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "rank", "model", "decoding", "n",
            "em_mean", "em_stderr", "f1_mean", "f1_stderr",
            "latency_ms_median", "total_tokens_mean",
            "estimated_cost_usd_total", "em_per_1k_tokens"
        ])
        
        rows = []
        for (model, decoding), m in leaderboard.items():
            em_mean = safe_mean(m["em"]) or 0.0
            
            # Token efficiency
            em_per_1k = None
            if m.get("total_tokens") and m.get("em"):
                total_correct = sum(m["em"])
                total_tokens_sum = sum(m["total_tokens"])
                if total_tokens_sum > 0:
                    em_per_1k = (total_correct / total_tokens_sum) * 1000
            
            rows.append((
                em_mean,
                [
                    model, decoding, len(m["em"]),
                    em_mean, safe_stderr(m["em"]),
                    safe_mean(m["f1"]), safe_stderr(m["f1"]),
                    safe_median(m.get("latency_ms", [])),
                    safe_mean(m.get("total_tokens", [])),
                    sum(m.get("estimated_cost_usd", [])) if m.get("estimated_cost_usd") else None,
                    em_per_1k
                ]
            ))
        
        # Sort by EM descending
        for rank, (_, row) in enumerate(sorted(rows, key=lambda x: x[0], reverse=True), 1):
            w.writerow([rank] + row)


def export_accuracy_by_hop(buckets: Dict, out_path: str):
    """Export accuracy_by_hop.csv."""
    # Key: (model, decoding, hop)
    by_hop = defaultdict(lambda: defaultdict(list))
    
    for (model, decoding, _, _, hop), m in buckets.items():
        by_hop[(model, decoding, hop)]["em"].extend(m["em"])
        by_hop[(model, decoding, hop)]["f1"].extend(m["f1"])
    
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "model", "decoding", "hop", "n",
            "em_mean", "em_stderr", "em_ci_95_low", "em_ci_95_high",
            "f1_mean", "f1_stderr"
        ])
        
        for (model, decoding, hop), m in sorted(by_hop.items()):
            em_ci = confidence_interval_95(m["em"])
            w.writerow([
                model, decoding, hop, len(m["em"]),
                safe_mean(m["em"]), safe_stderr(m["em"]),
                em_ci[0] if em_ci else None, em_ci[1] if em_ci else None,
                safe_mean(m["f1"]), safe_stderr(m["f1"])
            ])


def export_by_graph_variant(buckets: Dict, out_path: str):
    """Export accuracy by graph variant."""
    # Key: (model, decoding, graph_variant)
    by_graph = defaultdict(lambda: defaultdict(list))
    
    for (model, decoding, _, graph, _), m in buckets.items():
        by_graph[(model, decoding, graph)]["em"].extend(m["em"])
        by_graph[(model, decoding, graph)]["f1"].extend(m["f1"])
        by_graph[(model, decoding, graph)]["override"].extend(m.get("override", []))
        by_graph[(model, decoding, graph)]["adherence"].extend(m.get("adherence", []))
    
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "model", "decoding", "graph_variant", "n",
            "em_mean", "em_stderr", "f1_mean",
            "override_rate", "adherence_rate"
        ])
        
        for (model, decoding, graph), m in sorted(by_graph.items()):
            w.writerow([
                model, decoding, graph, len(m["em"]),
                safe_mean(m["em"]), safe_stderr(m["em"]),
                safe_mean(m["f1"]),
                safe_mean(m.get("override", [])) if m.get("override") else None,
                safe_mean(m.get("adherence", [])) if m.get("adherence") else None
            ])


def export_by_prompting_strategy(buckets: Dict, out_path: str):
    """Export accuracy by prompting strategy."""
    # Key: (model, decoding, prompting_strategy)
    by_prompting = defaultdict(lambda: defaultdict(list))
    
    for (model, decoding, prompting, _, _), m in buckets.items():
        by_prompting[(model, decoding, prompting)]["em"].extend(m["em"])
        by_prompting[(model, decoding, prompting)]["f1"].extend(m["f1"])
    
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "model", "decoding", "prompting_strategy", "n",
            "em_mean", "em_stderr", "f1_mean", "f1_stderr"
        ])
        
        for (model, decoding, prompting), m in sorted(by_prompting.items()):
            w.writerow([
                model, decoding, prompting, len(m["em"]),
                safe_mean(m["em"]), safe_stderr(m["em"]),
                safe_mean(m["f1"]), safe_stderr(m["f1"])
            ])


# ============================================================================
# Visualization
# ============================================================================

def create_plots(buckets: Dict, out_dir: str):
    """Create all plots."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.dpi'] = 300
        plt.rcParams['savefig.dpi'] = 300
        plt.rcParams['font.size'] = 10
        
    except ImportError:
        print("Warning: matplotlib/seaborn not available; skipping plots.", file=sys.stderr)
        return
    
    # 1. EM by hop per model
    plot_em_by_hop(buckets, out_dir, plt, sns)
    
    # 2. Override rate (counterfactual)
    plot_override_rate(buckets, out_dir, plt, sns)
    
    # 3. Path EM
    plot_path_em(buckets, out_dir, plt, sns)
    
    # 4. Efficiency: EM vs tokens
    plot_efficiency(buckets, out_dir, plt, sns)
    
    # 5. Heatmap: model × hop
    plot_heatmap(buckets, out_dir, plt, sns)
    
    # 6. Graph variant comparison
    plot_graph_variant_comparison(buckets, out_dir, plt, sns)
    
    # 7. Prompting strategy comparison
    plot_prompting_comparison(buckets, out_dir, plt, sns)
    
    print(f"Generated plots in {out_dir}", file=sys.stderr)


def plot_em_by_hop(buckets: Dict, out_dir: str, plt, sns):
    """Plot EM by hop for each decoding strategy."""
    by_hop = defaultdict(list)
    for (model, decoding, _, _, hop), m in buckets.items():
        by_hop[(model, decoding, hop)].extend(m["em"])
    
    decodings = sorted(set(d for (_, d, _) in by_hop.keys()))
    
    for dec in decodings:
        fig, ax = plt.subplots(figsize=(10, 6))
        models = sorted(set(m for (m, d, _) in by_hop.keys() if d == dec))
        
        for model in models:
            hops = sorted(set(h for (m, d, h) in by_hop.keys() if m == model and d == dec))
            means = [safe_mean(by_hop[(model, dec, h)]) for h in hops]
            stderrs = [safe_stderr(by_hop[(model, dec, h)]) for h in hops]
            
            # Filter None values
            valid_data = [(h, m, s) for h, m, s in zip(hops, means, stderrs) if m is not None]
            if not valid_data:
                continue
            
            hops_valid, means_valid, stderrs_valid = zip(*valid_data)
            ax.errorbar(hops_valid, means_valid, yerr=stderrs_valid, marker='o', label=model, capsize=5, linewidth=2)
        
        ax.set_xlabel("Hop Length", fontsize=12)
        ax.set_ylabel("Exact Match (Mean)", fontsize=12)
        ax.set_title(f"Accuracy by Hop Length ({dec})", fontsize=14, fontweight='bold')
        ax.set_xticks([1, 2, 3])
        ax.set_ylim(0, 1.05)
        ax.legend(loc='best', frameon=True)
        ax.grid(True, linestyle=':', alpha=0.6)
        
        out_path = os.path.join(out_dir, f"accuracy_by_hop_{dec}.png")
        plt.savefig(out_path, bbox_inches='tight')
        plt.close()


def plot_override_rate(buckets: Dict, out_dir: str, plt, sns):
    """Plot override rate by model (counterfactual)."""
    override_by_model = defaultdict(list)
    
    for (model, dec, _, graph, _), m in buckets.items():
        if graph == "counterfactual" and "override" in m:
            override_by_model[model].extend(m["override"])
    
    if not override_by_model:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    models = sorted(override_by_model.keys())
    means = [safe_mean(override_by_model[m]) or 0.0 for m in models]
    stderrs = [safe_stderr(override_by_model[m]) or 0.0 for m in models]
    
    bars = ax.bar(range(len(models)), means, yerr=stderrs, capsize=5, alpha=0.8, color=sns.color_palette("Set2"))
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, rotation=45, ha='right')
    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Override Rate (Mean)", fontsize=12)
    ax.set_title("Override Rate on Counterfactual Graph", fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis='y', linestyle=':', alpha=0.6)
    
    # Add value labels
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, f'{mean:.3f}', 
                ha='center', va='bottom', fontsize=9)
    
    out_path = os.path.join(out_dir, "override_rate_by_model.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()


def plot_path_em(buckets: Dict, out_dir: str, plt, sns):
    """Plot path EM by model."""
    path_em_by_model = defaultdict(list)
    
    for (model, _, _, _, _), m in buckets.items():
        if "path_em" in m:
            path_em_by_model[model].extend(m["path_em"])
    
    if not path_em_by_model:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    models = sorted(path_em_by_model.keys())
    means = [safe_mean(path_em_by_model[m]) or 0.0 for m in models]
    
    bars = ax.bar(range(len(models)), means, alpha=0.8, color=sns.color_palette("Set3"))
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, rotation=45, ha='right')
    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Path Exact Match (Mean)", fontsize=12)
    ax.set_title("Path Reconstruction Accuracy", fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis='y', linestyle=':', alpha=0.6)
    
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, f'{mean:.3f}', 
                ha='center', va='bottom', fontsize=9)
    
    out_path = os.path.join(out_dir, "path_em_by_model.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()


def plot_efficiency(buckets: Dict, out_dir: str, plt, sns):
    """Plot efficiency: EM vs total tokens."""
    data = []
    labels = []
    
    for (model, dec, prompting, graph, hop), m in buckets.items():
        em = safe_mean(m["em"])
        tt = safe_mean(m.get("total_tokens", []))
        if em is not None and tt is not None:
            data.append((tt, em))
            labels.append(f"{model}/{dec}/{prompting}/{graph}/H{hop}")
    
    if not data:
        return
    
    fig, ax = plt.subplots(figsize=(12, 8))
    xs, ys = zip(*data)
    scatter = ax.scatter(xs, ys, alpha=0.6, s=100, c=range(len(data)), cmap='viridis')
    
    ax.set_xlabel("Total Tokens (Mean)", fontsize=12)
    ax.set_ylabel("Exact Match (Mean)", fontsize=12)
    ax.set_title("Accuracy vs Token Usage (All Configurations)", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    out_path = os.path.join(out_dir, "accuracy_vs_tokens.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()


def plot_heatmap(buckets: Dict, out_dir: str, plt, sns):
    """Plot heatmap of model × hop."""
    # Aggregate: (model, hop) -> EM
    heatmap_data = defaultdict(list)
    
    for (model, _, _, _, hop), m in buckets.items():
        heatmap_data[(model, hop)].extend(m["em"])
    
    models = sorted(set(m for (m, _) in heatmap_data.keys()))
    hops = sorted(set(h for (_, h) in heatmap_data.keys()))
    
    if not models or not hops:
        return
    
    # Build matrix
    matrix = []
    for model in models:
        row = []
        for hop in hops:
            mean_em = safe_mean(heatmap_data.get((model, hop), []))
            row.append(mean_em if mean_em is not None else 0.0)
        matrix.append(row)
    
    fig, ax = plt.subplots(figsize=(8, len(models) * 0.5 + 2))
    sns.heatmap(matrix, annot=True, fmt='.3f', cmap='RdYlGn', vmin=0, vmax=1,
                xticklabels=[f"H{h}" for h in hops], yticklabels=models,
                cbar_kws={'label': 'Exact Match'}, ax=ax)
    ax.set_title("Model Performance Heatmap (EM by Hop)", fontsize=14, fontweight='bold')
    ax.set_xlabel("Hop Length", fontsize=12)
    ax.set_ylabel("Model", fontsize=12)
    
    out_path = os.path.join(out_dir, "heatmap_model_hop.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()


def plot_graph_variant_comparison(buckets: Dict, out_dir: str, plt, sns):
    """Compare performance across graph variants."""
    by_graph = defaultdict(lambda: defaultdict(list))
    
    for (model, dec, _, graph, _), m in buckets.items():
        by_graph[(model, dec)][graph].extend(m["em"])
    
    if not by_graph:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x_pos = 0
    width = 0.25
    colors = sns.color_palette("Set2", 3)
    graph_variants = ["natural", "abstract", "counterfactual"]
    
    for (model, dec), graphs in sorted(by_graph.items()):
        positions = [x_pos + i * width for i in range(len(graph_variants))]
        means = [safe_mean(graphs.get(g, [])) or 0.0 for g in graph_variants]
        
        for i, (pos, mean, color, variant) in enumerate(zip(positions, means, colors, graph_variants)):
            ax.bar(pos, mean, width, label=variant if x_pos == 0 else "", color=color, alpha=0.8)
        
        ax.text(x_pos + width, -0.1, f"{model}\n{dec}", ha='center', va='top', fontsize=9)
        x_pos += 1.0
    
    ax.set_ylabel("Exact Match (Mean)", fontsize=12)
    ax.set_title("Performance Across Graph Variants", fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.set_xticks([])
    ax.legend(loc='upper right')
    ax.grid(True, axis='y', linestyle=':', alpha=0.6)
    
    out_path = os.path.join(out_dir, "graph_variant_comparison.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()


def plot_prompting_comparison(buckets: Dict, out_dir: str, plt, sns):
    """Compare prompting strategies."""
    by_prompting = defaultdict(lambda: defaultdict(list))
    
    for (model, dec, prompting, _, _), m in buckets.items():
        by_prompting[(model, dec)][prompting].extend(m["em"])
    
    if not by_prompting:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x_pos = 0
    width = 0.25
    colors = sns.color_palette("Pastel1", 2)
    strategies = ["direct", "scot"]
    
    for (model, dec), proms in sorted(by_prompting.items()):
        positions = [x_pos + i * width for i in range(len(strategies))]
        means = [safe_mean(proms.get(s, [])) or 0.0 for s in strategies]
        
        for i, (pos, mean, color, strat) in enumerate(zip(positions, means, colors, strategies)):
            ax.bar(pos, mean, width, label=strat if x_pos == 0 else "", color=color, alpha=0.8)
        
        ax.text(x_pos + width/2, -0.1, f"{model}\n{dec}", ha='center', va='top', fontsize=9)
        x_pos += 0.8
    
    ax.set_ylabel("Exact Match (Mean)", fontsize=12)
    ax.set_title("Prompting Strategy Comparison", fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.set_xticks([])
    ax.legend(loc='upper right')
    ax.grid(True, axis='y', linestyle=':', alpha=0.6)
    
    out_path = os.path.join(out_dir, "prompting_comparison.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analyze SPARK evaluation results"
    )
    ap.add_argument("--eval", required=True, help="Path to per_record.csv, eval dir, or parent dir")
    ap.add_argument("--out_dir", required=True, help="Output directory")
    ap.add_argument("--make_plots", action="store_true", help="Generate PNG plots")
    ap.add_argument("--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    # Find files
    per_record_files = find_per_record_files(args.eval)
    if not per_record_files:
        raise SystemExit(f"No per_record.csv found in: {args.eval}")
    
    if args.verbose:
        print(f"Found {len(per_record_files)} per_record.csv file(s)", file=sys.stderr)
    
    # Load data
    data = load_per_record_data(per_record_files)
    buckets = data["buckets"]
    
    if args.verbose:
        print(f"Loaded {data['total_rows']} rows", file=sys.stderr)
        print(f"Found {len(buckets)} unique experiment cells", file=sys.stderr)
    
    # Export CSVs
    aggregate_csv = os.path.join(args.out_dir, "aggregate_by_cell.csv")
    leaderboard_csv = os.path.join(args.out_dir, "leaderboard.csv")
    accuracy_by_hop_csv = os.path.join(args.out_dir, "accuracy_by_hop.csv")
    by_graph_csv = os.path.join(args.out_dir, "accuracy_by_graph_variant.csv")
    by_prompting_csv = os.path.join(args.out_dir, "accuracy_by_prompting_strategy.csv")
    
    export_aggregate_by_cell(buckets, aggregate_csv)
    export_leaderboard(buckets, leaderboard_csv)
    export_accuracy_by_hop(buckets, accuracy_by_hop_csv)
    export_by_graph_variant(buckets, by_graph_csv)
    export_by_prompting_strategy(buckets, by_prompting_csv)
    
    if args.verbose:
        print("Exported CSV files", file=sys.stderr)
    
    # Create plots
    if args.make_plots:
        create_plots(buckets, args.out_dir)
    
    # Summary
    result = {
        "per_record_files": per_record_files,
        "total_rows": data["total_rows"],
        "num_cells": len(buckets),
        "aggregate_by_cell": aggregate_csv,
        "leaderboard": leaderboard_csv,
        "accuracy_by_hop": accuracy_by_hop_csv,
        "accuracy_by_graph_variant": by_graph_csv,
        "accuracy_by_prompting_strategy": by_prompting_csv,
        "plots_generated": args.make_plots,
    }
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()