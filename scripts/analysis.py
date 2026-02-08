#!/usr/bin/env python3
"""
analysis.py

Enhanced version with prettier plots, consistent config naming, and color scheme.
Generates plots and analysis report from evaluation results.
Reads evaluation_results.csv (produced by evaluate.py).

Outputs:
- Plots in `out_dir/plots`
- analysis_report.md
"""

import argparse
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
from matplotlib.ticker import MaxNLocator

# Model name mapping - centralized configuration
MODEL_NAMES = {
    "deepseek-ai/deepseek-v3.2-maas": "DeepSeek v3.2",
    "google/gemini-3-pro-preview": "Gemini 3 Pro",
    "openai/gpt-oss-120b-maas": "GPT-oss",
    "meta/llama-4-maverick-17b-128e-instruct-maas": "Llama 4",
}

# Decoding strategy abbreviations
DECODING_ABBREV = {
    "greedy": "G",
    "self_consistency": "SC",
}

# Config (Model + Decoding) color mapping - consistent across all plots
CONFIG_COLORS = {
    "DeepSeek v3.2 G": "#E74C3C",      # Red
    "DeepSeek v3.2 SC": "#C0392B",     # Dark Red
    "Gemini 3 Pro G": "#3498DB",       # Blue
    "Gemini 3 Pro SC": "#376E92",      # Dark Blue
    "GPT-oss G": "#2ECC71",            # Green
    "GPT-oss SC": "#27AE60",           # Dark Green
    "Llama 4 G": "#F39C12",            # Orange
    "Llama 4 SC": "#E67E22",           # Dark Orange
}


def get_model_display_name(model_path):
    """
    Convert model path to display name using MODEL_NAMES mapping.
    
    Args:
        model_path: Full model path (e.g., "deepseek-ai/deepseek-v3.2-maas")
    
    Returns:
        Display name (e.g., "DeepSeek v3.2")
    """
    # Look up in mapping, return as-is if not found
    return MODEL_NAMES.get(model_path, model_path)


def get_decoding_abbrev(decoding_strategy):
    """
    Get abbreviated decoding strategy name.
    
    Args:
        decoding_strategy: Full decoding name (e.g., "self_consistency")
    
    Returns:
        Abbreviated name (e.g., "SC")
    """
    return DECODING_ABBREV.get(decoding_strategy, decoding_strategy)


def get_config_name(model_display_name, decoding_strategy):
    """
    Create config name from model and decoding strategy.
    
    Args:
        model_display_name: Display name of model
        decoding_strategy: Decoding strategy name
    
    Returns:
        Config name (e.g., "DeepSeek v3.2 SC")
    """
    decoding_abbrev = get_decoding_abbrev(decoding_strategy)
    return f"{model_display_name} {decoding_abbrev}"


def get_config_color(config_name):
    """
    Get consistent color for a config.
    
    Args:
        config_name: Config name (e.g., "DeepSeek v3.2 SC")
    
    Returns:
        Color hex code
    """
    return CONFIG_COLORS.get(config_name, "#95a5a6")  # Gray as fallback


def get_color_palette(config_names):
    """
    Generate color palette for a list of config names.
    
    Args:
        config_names: List of config names
    
    Returns:
        List of colors in same order as config_names
    """
    return [get_config_color(name) for name in config_names]


def set_style():
    """Enhanced styling for publication-quality plots"""
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update({
        "figure.figsize": (12, 7),
        "font.size": 11,
        "axes.labelsize": 13,
        "axes.titlesize": 14,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 10,
        "figure.titlesize": 16,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    })


def prepare_config_column(df):
    """
    Add standardized Config column to dataframe with model display name + decoding abbrev.
    
    Args:
        df: DataFrame with 'model' and 'decoding' columns
    
    Returns:
        DataFrame with added 'Config' and 'ModelName' columns
    """
    df = df.copy()
    df["ModelName"] = df["model"].apply(get_model_display_name)
    df["DecodingAbbrev"] = df["decoding"].apply(get_decoding_abbrev)
    df["Config"] = df["ModelName"] + " " + df["DecodingAbbrev"]
    return df


def plot_accuracy_by_hop(df, out_dir):
    """
    Compact bar chart of EM score by Hop with consistent colors.
    """
    df = prepare_config_column(df)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True, sharey=True)
    fig.suptitle("Accuracy by Hop Count (EM)", fontsize=18, y=0.995)

    strategies = sorted(df["prompting_strategy"].unique())
    variants = sorted(df["graph_variant"].unique())
    
    # Get unique configs and their colors
    unique_configs = sorted(df["Config"].unique())
    palette = get_color_palette(unique_configs)

    for i, strategy in enumerate(strategies):
        for j, variant in enumerate(variants):
            ax = axes[i, j]
            subset = df[
                (df["prompting_strategy"] == strategy) &
                (df["graph_variant"] == variant)
            ]

            if subset.empty:
                ax.axis("off")
                continue

            sns.barplot(
                data=subset,
                x="hop",
                y="em",
                hue="Config",
                hue_order=unique_configs,
                ax=ax,
                palette=palette,
                alpha=0.9,
                errorbar=None
            )

            ax.set_title(f"{strategy.upper()} – {variant.capitalize()}",
                         fontsize=12, fontweight="bold")
            ax.set_xlabel("Hop" if i == 1 else "")
            ax.set_ylabel("EM" if j == 0 else "")
            ax.set_ylim(0, 1.05)
            ax.grid(axis="y", alpha=0.3)

            # Annotate bars with values
            for container in ax.containers:
                ax.bar_label(container, fmt="%.2f", fontsize=8, padding=2)

            # Single legend on right
            if j == 2:
                ax.legend(
                    title="Config",
                    bbox_to_anchor=(1.05, 0.5),
                    loc="center left",
                    frameon=True,
                    fontsize=9
                )
            else:
                ax.legend().set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "accuracy_by_hop.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_graph_variant_comparison(df, out_dir):
    """
    Comparison across Natural vs Abstract vs Counterfactual with consistent colors.
    """
    df = prepare_config_column(df)

    # Aggregate over hops
    agg_df = (
        df.groupby(["Config", "graph_variant", "prompting_strategy"])["em"]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(19, 7))
    fig.suptitle("Performance Across Graph Variants",
                 fontsize=18, fontweight="bold")

    strategies = sorted(agg_df["prompting_strategy"].unique())
    
    # Get colors based on config names
    unique_configs = sorted(agg_df["Config"].unique())
    palette = get_color_palette(unique_configs)

    for idx, strategy in enumerate(strategies):
        if idx >= len(axes):
            break

        ax = axes[idx]
        subset = agg_df[agg_df["prompting_strategy"] == strategy]

        sns.barplot(
            data=subset,
            x="graph_variant",
            y="em",
            hue="Config",
            hue_order=unique_configs,
            ax=ax,
            palette=palette,
            alpha=0.9,
            errorbar=None
        )

        ax.set_title(f"{strategy.upper()} Strategy",
                     fontsize=14, fontweight="bold")
        ax.set_xlabel("Graph Variant", fontsize=12)
        ax.set_ylabel("Mean EM", fontsize=12)
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)

        # Value labels on bars
        for container in ax.containers:
            labels = [
                f"{v:.2f}" if v is not None else ""
                for v in container.datavalues
            ]
            ax.bar_label(container, labels=labels, fontsize=9, padding=2)

        # Remove per-axis legends
        if ax.get_legend():
            ax.get_legend().remove()

    # Single global legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Config",
        loc="center left",
        bbox_to_anchor=(0.9, 0.5),
        frameon=True
    )

    plt.tight_layout(rect=[0, 0.03, 0.86, 0.95])
    out_path = os.path.join(out_dir, "graph_variant_comparison.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_override_rate(df, out_dir):
    """
    Enhanced override success rate visualization with consistent colors.
    """
    subset = df[df["graph_variant"] == "counterfactual"].copy()
    if subset.empty:
        return

    subset = prepare_config_column(subset)

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle("Counterfactual Override Success Rate",
                 fontsize=18, fontweight="bold")

    strategies = sorted(subset["prompting_strategy"].unique())

    # Get consistent colors
    unique_configs = sorted(subset["Config"].unique())
    palette = get_color_palette(unique_configs)

    for idx, strategy in enumerate(strategies):
        if idx >= len(axes):
            break

        ax = axes[idx]
        strat_subset = subset[subset["prompting_strategy"] == strategy]

        sns.barplot(
            data=strat_subset,
            x="hop",
            y="em",
            hue="Config",
            hue_order=unique_configs,
            ax=ax,
            palette=palette,
            alpha=0.9,
            errorbar=None,
        )

        ax.set_title(f"{strategy.upper()} Strategy",
                     fontweight="bold", fontsize=14)
        ax.set_xlabel("Hop Count", fontsize=12)
        ax.set_ylabel("Override Success Rate (EM)", fontsize=12)
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)

        # Annotate bars
        for container in ax.containers:
            ax.bar_label(container, fmt="%.2f", fontsize=8, padding=2)

        ax.get_legend().remove()

    # Single global legend
    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        title="Configuration",
        loc="center right",
        bbox_to_anchor=(0.98, 0.5),
        frameon=True,
        shadow=True,
    )

    plt.tight_layout(rect=[0, 0.03, 0.85, 0.95])
    out_path = os.path.join(out_dir, "override_rate.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved {out_path}")


def plot_failure_modes(df, out_dir):
    """
    Bar chart of 'correct' outcome percentages per model configuration.
    Uses consistent config colors with a single legend on the right.
    """
    set_style()
    df = prepare_config_column(df)

    counts = (
        df.groupby(["Config", "graph_variant", "prompting_strategy", "outcome"])
          .size()
          .reset_index(name="counts")
    )
    counts["total"] = (
        counts.groupby(["Config", "graph_variant", "prompting_strategy"])["counts"]
              .transform("sum")
    )
    counts["percentage"] = counts["counts"] / counts["total"] * 100

    correct_data = counts[counts["outcome"] == "correct"].copy()
    unique_configs = sorted(correct_data["Config"].unique())

    # Config → color mapping
    palette = {cfg: get_config_color(cfg) for cfg in unique_configs}

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharey=True)
    fig.suptitle("Correct Outcome Distribution", fontsize=18, y=0.995)

    strategies = sorted(correct_data["prompting_strategy"].unique())
    variants = sorted(correct_data["graph_variant"].unique())

    for i, strategy in enumerate(strategies):
        for j, variant in enumerate(variants):
            ax = axes[i, j]
            subset = correct_data[
                (correct_data["prompting_strategy"] == strategy) &
                (correct_data["graph_variant"] == variant)
            ]

            if subset.empty:
                ax.axis("off")
                continue

            sns.barplot(
                data=subset,
                x="Config",
                y="percentage",
                hue="Config",
                hue_order=unique_configs,
                palette=palette,
                ax=ax,
                errorbar=None,
                alpha=0.9,
                legend=False
            )

            ax.set_title(f"{strategy.upper()} – {variant.capitalize()}",
                         fontsize=12, fontweight="bold")
            ax.set_xlabel("")
            ax.set_ylabel("Percentage (%)" if j == 0 else "")
            ax.set_ylim(0, 105)
            ax.grid(axis="y", alpha=0.3)
            ax.set_xticklabels([])

            for container in ax.containers:
                ax.bar_label(container, fmt="%.1f%%", fontsize=9, padding=3)

    # Manually create legend from palette
    from matplotlib.patches import Patch

    legend_handles = [
        Patch(facecolor=palette[cfg], label=cfg)
        for cfg in unique_configs
    ]

    axes[0, 2].legend(
        handles=legend_handles,
        title="Config",
        bbox_to_anchor=(1.05, 0.5),
        loc="center left",
        frameon=True,
        fontsize=9
    )

    plt.tight_layout()
    out_path = os.path.join(out_dir, "failure_modes.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_efficiency(df, out_dir):
    """
    Scatter plot: Latency vs EM using consistent config colors.
    """
    df = prepare_config_column(df)

    agg = df.groupby(["Config", "prompting_strategy"]).agg({
        "em": "mean",
        "latency_ms": "mean",
        "total_tokens": "mean"
    }).reset_index()

    if agg.empty:
        print("No data to plot.")
        return

    unique_configs = agg["Config"].unique()
    palette = {cfg: get_config_color(cfg) for cfg in unique_configs}

    fig, ax = plt.subplots(figsize=(14, 8))

    sns.scatterplot(
        data=agg,
        x="latency_ms",
        y="em",
        hue="Config",
        palette=palette,
        style="prompting_strategy",
        s=200,
        alpha=0.8,
        edgecolor="w",
        linewidth=1.5,
        ax=ax
    )

    ax.set_title("Efficiency: Latency vs Accuracy", fontweight='bold', fontsize=16)
    ax.set_xlabel("Average Latency (ms)", fontsize=13)
    ax.set_ylabel("Average Exact Match", fontsize=13)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', frameon=True, shadow=True)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "efficiency_scatter.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")


def plot_cost_analysis(df, out_dir):
    """
    Enhanced cost per query visualization with consistent colors
    and shared Y-axis scale across subplots.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        print("No cost data available to plot.")
        return

    df = prepare_config_column(df)

    avg_cost = (
        df.groupby(["Config", "prompting_strategy", "graph_variant"])["cost"]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle("Cost Analysis per Query", fontsize=18, fontweight="bold")

    strategies = sorted(avg_cost["prompting_strategy"].unique())

    # Get consistent colors
    unique_configs = sorted(avg_cost["Config"].unique())
    palette = get_color_palette(unique_configs)

    # Global Y max (shared scale)
    y_max = avg_cost["cost"].max() * 1.1

    for idx, strategy in enumerate(strategies):
        if idx >= len(axes):
            break

        ax = axes[idx]
        subset = avg_cost[avg_cost["prompting_strategy"] == strategy]

        barplot = sns.barplot(
            data=subset,
            x="graph_variant",
            y="cost",
            hue="Config",
            hue_order=unique_configs,
            ax=ax,
            palette=palette,
            alpha=0.9,
            errorbar=None,
        )

        ax.set_title(f"{strategy.upper()} Strategy",
                     fontweight="bold", fontsize=14)
        ax.set_xlabel("Graph Variant", fontsize=12)
        ax.set_ylabel("Avg Cost per Query (USD)", fontsize=12)
        ax.set_ylim(0, y_max)
        ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", rotation=15)

        if ax.get_legend():
            ax.get_legend().remove()

        # Annotate bars
        for p in barplot.patches:
            height = p.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:.4f}",
                    (p.get_x() + p.get_width() / 2.0, height),
                    ha="center",
                    va="bottom",
                    xytext=(0, 4),
                    textcoords="offset points",
                    fontsize=8,
                )

    # Global legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Configuration",
        loc="center right",
        bbox_to_anchor=(0.98, 0.5),
        frameon=True,
        shadow=True,
    )

    plt.tight_layout(rect=[0, 0.03, 0.85, 0.95])
    out_path = os.path.join(out_dir, "cost_analysis.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_total_cost(df, out_dir):
    """
    Enhanced total cost visualization with consistent colors.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        return
    
    df = prepare_config_column(df)
    
    total_costs = df.groupby(["Config", "prompting_strategy", "graph_variant"])["cost"].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Get consistent colors
    unique_configs = sorted(total_costs["Config"].unique())
    palette = get_color_palette(unique_configs)
    
    barplot = sns.barplot(
        data=total_costs, 
        x="graph_variant", 
        y="cost", 
        hue="Config",
        hue_order=unique_configs,
        palette=palette, 
        alpha=0.9, 
        ax=ax, 
        errorbar=None
    )
    
    ax.set_title("Total Experiment Cost by Configuration", fontweight='bold', fontsize=16)
    ax.set_xlabel("Graph Variant", fontsize=13)
    ax.set_ylabel("Total Cost ($)", fontsize=13)
    ax.legend(title="Configuration", frameon=True, shadow=True, 
              bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    # Annotate bars
    for p in barplot.patches:
        height = p.get_height()
        if height > 0:
            ax.annotate(format(height, '.2f'), 
                         (p.get_x() + p.get_width() / 2., height), 
                         ha='center', va='center', 
                         xytext=(0, 5), 
                         textcoords='offset points', 
                         fontsize=9)
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "cost_total.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")


def plot_heatmap_performance(df, out_dir):
    """
    Heatmap showing performance across all dimensions with clean config names.
    """
    df = prepare_config_column(df)

    # Pivot table
    pivot = df.pivot_table(
        values="em",
        index=["Config", "prompting_strategy"],
        columns=["graph_variant", "hop"],
        aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(16, 8))

    sns.heatmap(
        pivot,
        annot=True,
        fmt=".3f",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        cbar_kws={"label": "Exact Match"},
        linewidths=0.5,
        linecolor="gray",
        ax=ax
    )

    ax.set_title(
        "Performance Heatmap: EM Across All Configurations",
        fontsize=16,
        fontweight="bold"
    )
    ax.set_xlabel("Graph Variant & Hop Count", fontsize=13)
    ax.set_ylabel("Config & Strategy", fontsize=13)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "heatmap_performance.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_radar_chart(df, out_dir):
    """
    Radar chart comparing different metrics with consistent colors.
    """
    from math import pi
    
    df = prepare_config_column(df)
    
    # Aggregate metrics
    metrics = df.groupby(["Config", "prompting_strategy"]).agg({
        "em": "mean",
        "f1": "mean",
        "path_found": "mean",
    }).reset_index()
    
    # Add inverse normalized latency
    latency_agg = df.groupby(["Config", "prompting_strategy"])["latency_ms"].mean()
    max_latency = latency_agg.max()
    metrics["speed"] = metrics.apply(
        lambda row: 1 - (df[(df["Config"] == row["Config"]) & 
                           (df["prompting_strategy"] == row["prompting_strategy"])]["latency_ms"].mean() / max_latency),
        axis=1
    )
    
    categories = ['EM', 'F1', 'Path Found', 'Speed']
    N = len(categories)
    
    strategies = sorted(metrics["prompting_strategy"].unique())
    fig, axes = plt.subplots(1, len(strategies), figsize=(16, 7), subplot_kw=dict(projection='polar'))
    
    if len(strategies) == 1:
        axes = [axes]
    
    fig.suptitle("Multi-Metric Radar Comparison", fontsize=18, fontweight='bold')
    
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    for idx, strategy in enumerate(strategies):
        ax = axes[idx]
        subset = metrics[metrics["prompting_strategy"] == strategy]
        
        for i, (_, row) in enumerate(subset.iterrows()):
            config_name = row["Config"]
            color = get_config_color(config_name)
            
            values = [row["em"], row["f1"], row["path_found"], row["speed"]]
            values += values[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, label=config_name, 
                   color=color, alpha=0.7)
            ax.fill(angles, values, alpha=0.15, color=color)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11)
        ax.set_ylim(0, 1)
        ax.set_title(f"{strategy.upper()}", fontweight='bold', fontsize=13, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "radar_comparison.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")


def plot_hop_degradation(df, out_dir):
    """
    Line plot showing performance degradation with increasing hops.
    Uses consistent colors for configs.
    """
    df = prepare_config_column(df)
    df["hop"] = df["hop"].astype(int)

    hop_perf = (
        df.groupby(["Config", "prompting_strategy", "graph_variant", "hop"])["em"]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True, sharey=True)
    fig.suptitle("Performance Degradation by Hop Count",
                 fontsize=18, fontweight="bold")

    strategies = sorted(hop_perf["prompting_strategy"].unique())
    variants = sorted(hop_perf["graph_variant"].unique())

    for i, strategy in enumerate(strategies):
        for j, variant in enumerate(variants):
            ax = axes[i, j]
            subset = hop_perf[
                (hop_perf["prompting_strategy"] == strategy) &
                (hop_perf["graph_variant"] == variant)
            ]

            if subset.empty:
                ax.axis("off")
                continue

            for config in sorted(subset["Config"].unique()):
                config_data = subset[subset["Config"] == config].sort_values("hop")
                color = get_config_color(config)

                ax.plot(
                    config_data["hop"],
                    config_data["em"],
                    marker="o",
                    linewidth=2.5,
                    markersize=8,
                    label=config,
                    color=color,
                    alpha=0.8,
                )

            ax.set_title(f"{strategy.upper()} - {variant.capitalize()}",
                         fontweight="bold", fontsize=12)
            ax.set_xlabel("Hop Count" if i == 1 else "", fontsize=11)
            ax.set_ylabel("Exact Match" if j == 0 else "", fontsize=11)
            ax.set_ylim(0, 1.05)
            ax.grid(True, alpha=0.3)

            # Force integer x-axis ticks
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

            if j == 2:
                ax.legend(
                    bbox_to_anchor=(1.05, 0.5),
                    loc="center left",
                    frameon=True,
                    shadow=True,
                    fontsize=9,
                )

    plt.tight_layout()
    out_path = os.path.join(out_dir, "hop_degradation.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_cost_vs_accuracy(df, out_dir):
    """
    Scatter plot showing cost-accuracy tradeoff with consistent colors.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        return
    
    df = prepare_config_column(df)
    
    agg = df.groupby(["Config", "prompting_strategy", "graph_variant"]).agg({
        "em": "mean",
        "cost": "mean"
    }).reset_index()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Plot with consistent colors
    for config in sorted(agg["Config"].unique()):
        config_data = agg[agg["Config"] == config]
        color = get_config_color(config)
        
        ax.scatter(
            config_data["cost"],
            config_data["em"],
            s=250,
            alpha=0.7,
            color=color,
            edgecolor="w",
            linewidth=1.5,
            label=config
        )
    
    ax.set_title("Cost vs Accuracy Tradeoff", fontweight='bold', fontsize=18, pad=20)
    ax.set_xlabel("Average Cost per Query (USD)", fontsize=13)
    ax.set_ylabel("Average Exact Match (Accuracy)", fontsize=13)
    ax.grid(True, linestyle='--', alpha=0.4)
    
    # Pareto frontier
    pareto_points = []
    for _, row in agg.iterrows():
        is_pareto = True
        for _, other in agg.iterrows():
            if (other["cost"] <= row["cost"] and other["em"] >= row["em"]) and \
               (other["cost"] < row["cost"] or other["em"] > row["em"]):
                is_pareto = False
                break
        if is_pareto:
            pareto_points.append(row)
            
    if pareto_points:
        pareto_df = pd.DataFrame(pareto_points).sort_values("cost")
        ax.plot(pareto_df["cost"], pareto_df["em"], color='red', linestyle='--', 
               linewidth=2.5, alpha=0.6, label='Pareto Frontier')
    
    ax.legend(
        title="Configuration",
        bbox_to_anchor=(1.02, 1), 
        loc='upper left', 
        frameon=True, 
        shadow=True,
        fontsize=10
    )
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "cost_vs_accuracy.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")


def plot_outcome_sunburst(df, out_dir):
    """
    Single-bar plot showing percentage of correct answers
    per (prompting strategy × graph variant) typology.
    """
    set_style()
    df = prepare_config_column(df)

    # Aggregate counts
    counts = (
        df.groupby(["prompting_strategy", "graph_variant", "outcome"])
          .size()
          .reset_index(name="counts")
    )

    counts["total"] = (
        counts.groupby(["prompting_strategy", "graph_variant"])["counts"]
              .transform("sum")
    )

    counts["percentage"] = counts["counts"] / counts["total"] * 100

    # Keep only correct outcomes
    correct = counts[counts["outcome"] == "correct"].copy()

    # Build typology label
    correct["typology"] = (
        correct["prompting_strategy"].str.upper()
        + " – "
        + correct["graph_variant"].str.capitalize()
    )

    correct = correct.sort_values("typology")

    # Palette (one color per typology)
    palette = sns.color_palette("tab10", n_colors=len(correct))

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle("Correct Answer Rate by Typology",
                 fontsize=18, fontweight="bold")

    bars = ax.bar(
        correct["typology"],
        correct["percentage"],
        color=palette,
        alpha=0.9
    )

    ax.set_ylabel("Percentage (%)", fontsize=12)
    ax.set_xlabel("")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xticklabels(correct["typology"], rotation=30, ha="right")

    # Value labels
    ax.bar_label(bars, fmt="%.1f%%", fontsize=10, padding=3)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "outcome_distribution.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Enhanced analysis with consistent naming and colors")
    parser.add_argument("--eval", required=True, help="Directory containing evaluation_results.csv or path to csv.")
    parser.add_argument("--out_dir", required=True, help="Directory to save plots.")
    parser.add_argument("--make_plots", action="store_true", help="Generate plots.")
    
    args = parser.parse_args()
    
    # Determine input file path
    if os.path.isdir(args.eval):
        csv_path = os.path.join(args.eval, "evaluation_results.csv")
    else:
        csv_path = args.eval
        
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records")
    
    os.makedirs(os.path.join(args.out_dir, "plots"), exist_ok=True)
    plots_dir = os.path.join(args.out_dir, "plots")
    
    if args.make_plots:
        print("\nGenerating enhanced plots with consistent colors...")
        set_style()
        
        # All plots
        plot_graph_variant_comparison(df, plots_dir)
        plot_accuracy_by_hop(df, plots_dir)
        plot_override_rate(df, plots_dir)
        plot_failure_modes(df, plots_dir)
        plot_efficiency(df, plots_dir)
        plot_cost_analysis(df, plots_dir)
        plot_total_cost(df, plots_dir)
        
        print("\nGenerating additional insights...")
        plot_heatmap_performance(df, plots_dir)
        plot_radar_chart(df, plots_dir)
        plot_hop_degradation(df, plots_dir)
        plot_cost_vs_accuracy(df, plots_dir)
        plot_outcome_sunburst(df, plots_dir)
        
        print(f"\nAll plots saved to {plots_dir}")
    
    # Analysis Report
    print("\nGenerating analysis report...")
    df_display = prepare_config_column(df)
    
    report_path = os.path.join(args.out_dir, "analysis_report.md")
    with open(report_path, "w") as f:
        f.write("# Experiment Analysis Report\n\n")
        f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Queries Evaluated:** {len(df)}\n\n")
        f.write("---\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        best_config = df_display.groupby(["Config", "prompting_strategy"])["em"].mean().sort_values(ascending=False).head(1)
        f.write(f"**Best Performing Configuration:**\n")
        f.write(f"- Config: `{best_config.index[0][0]}`\n")
        f.write(f"- Strategy: `{best_config.index[0][1]}`\n")
        f.write(f"- EM Score: `{best_config.values[0]:.4f}`\n\n")
        
        # Overall statistics
        f.write("### Overall Statistics\n\n")
        f.write(f"- Mean EM: `{df['em'].mean():.4f}`\n")
        f.write(f"- Mean F1: `{df['f1'].mean():.4f}`\n")
        f.write(f"- Path Found Rate: `{df['path_found'].mean():.4f}`\n")
        f.write(f"- Mean Latency: `{df['latency_ms'].mean():.2f}` ms\n")
        if "cost" in df.columns and df["cost"].sum() > 0:
            f.write(f"- Total Cost: `${df['cost'].sum():.4f}`\n")
            f.write(f"- Avg Cost per Query: `${df['cost'].mean():.6f}`\n")
        f.write("\n---\n\n")
        
        # Config comparison
        f.write("## Configuration Performance Comparison\n\n")
        config_perf = df_display.groupby("Config").agg({
            "em": ["mean", "std"],
            "f1": "mean",
            "latency_ms": "mean"
        }).round(4)
        config_perf.columns = ['_'.join(col).strip() for col in config_perf.columns.values]
        f.write(config_perf.to_markdown())
        f.write("\n\n---\n\n")
        
        # Performance by Strategy
        f.write("## Performance by Strategy\n\n")
        strategy_perf = df_display.groupby(["prompting_strategy", "graph_variant"]).agg({
            "em": ["mean", "std"],
            "f1": "mean",
            "latency_ms": "mean"
        }).round(4)
        strategy_perf.columns = ['_'.join(col).strip() for col in strategy_perf.columns.values]
        f.write(strategy_perf.to_markdown())
        f.write("\n\n---\n\n")
        
        # Hop analysis
        f.write("## Performance by Hop Count\n\n")
        hop_perf = df_display.groupby(["hop", "graph_variant"])["em"].mean().reset_index()
        hop_pivot = hop_perf.pivot(index="hop", columns="graph_variant", values="em").round(4)
        f.write(hop_pivot.to_markdown())
        f.write("\n\n---\n\n")
        
        f.write("---\n\n")
        f.write("*End of Report*\n")
        
    print(f"Analysis report saved to {report_path}")


if __name__ == "__main__":
    main()