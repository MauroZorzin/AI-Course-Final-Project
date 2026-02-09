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
    Updated: Y-axis as Percentage, no duplicate legends.
    """
    df = prepare_config_column(df)
    
    # Convert EM to Percentage
    df["em_pct"] = df["em"] * 100

    # Increased figure width to 20 to allow slightly wider bars without overlap
    fig, axes = plt.subplots(2, 3, figsize=(20, 10), sharex=True, sharey=True)
    fig.suptitle("Accuracy by Hop Count (EM)", fontsize=18, y=0.995)

    strategies = sorted(df["prompting_strategy"].unique())
    variants = sorted(df["graph_variant"].unique())
    
    unique_configs = sorted(df["Config"].unique())
    palette = get_color_palette(unique_configs)
    
    # Create global legend handles
    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=palette[i], label=unique_configs[i]) for i in range(len(unique_configs))]

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

            # Plot using Percentage
            sns.barplot(
                data=subset,
                x="hop",
                y="em_pct",
                hue="Config",
                hue_order=unique_configs,
                ax=ax,
                palette=palette,
                alpha=0.9,
                errorbar=None,
                width=0.8, # Gap between hops
            )

            ax.set_title(f"{strategy.upper()} – {variant.capitalize()}",
                         fontsize=12, fontweight="bold")
            ax.set_xlabel("Hop" if i == 1 else "")
            
            # Label Y-axis with unit
            if j == 0:
                ax.set_ylabel("Accuracy (%)")
            else:
                ax.set_ylabel("")

            # Set limits 0-105 to fit labels
            ax.set_ylim(0, 115)
            ax.grid(axis="y", alpha=0.3)
            
            # Remove individual legends
            if ax.get_legend():
                ax.get_legend().remove()

            # Annotate bars
            for container in ax.containers:
                # Use fewer decimal places for percentage to prevent overlap
                ax.bar_label(container, fmt="%.0f", fontsize=8, padding=2) # Slightly smaller font

    # Use a single global legend
    fig.legend(
        handles=legend_handles,
        title="Config",
        bbox_to_anchor=(0.99, 0.5), # Outside right, closer
        loc="center left",
        frameon=True,
        fontsize=10
    )

    plt.tight_layout(rect=[0, 0, 0.94, 1]) # Use more width for plots
    out_path = os.path.join(out_dir, "accuracy_by_hop.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_outcome_distribution(df, out_dir):
    """
    Unified plot replacing failure_modes, graph_variant_comparison, and outcome_distribution.
    Shows the distribution of outcomes (Correct, Wrong, Missed) per configuration.
    "Correct" is model-colored. Others are fixed colors.
    """
    set_style()
    df = prepare_config_column(df)
    
    # Calculate distributions
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
    
    # Fixed colors for errors
    fixed_outcomes = {
        "missed_answer": "#95a5a6",    # Gray
        "wrong_answer": "#ff0000",     # Bright Red
        "parse_error": "#8e44ad",      # Purple (distinct from yellow)
        "parametric_leakage": "#d35400", 
        "hallucinated_answer": "#c0392b"
    }
    
    all_outcome_types = sorted(counts["outcome"].unique())
    # Ensure Correct is first (bottom of stack)
    stack_order = ["correct"] + [o for o in all_outcome_types if o != "correct"]
    
    strategies = sorted(counts["prompting_strategy"].unique())
    variants = sorted(counts["graph_variant"].unique())
    
    fig, axes = plt.subplots(len(strategies), len(variants), 
                             figsize=(6 * len(variants), 5 * len(strategies)), 
                             sharey=True)
    
    # Handle subplot dimensionality
    if len(strategies) == 1 and len(variants) == 1:
        axes = np.array([[axes]])
    elif len(strategies) == 1:
        axes = np.array([axes])
    elif len(variants) == 1:
        axes = np.array([[ax] for ax in axes])
    elif not isinstance(axes, np.ndarray):
         axes = np.array([[axes]])
        
    fig.suptitle("Outcome Distribution by Configuration", fontsize=20, y=0.995)

    for i, strategy in enumerate(strategies):
        for j, variant in enumerate(variants):
            ax = axes[i, j]
            subset = counts[
                (counts["prompting_strategy"] == strategy) & 
                (counts["graph_variant"] == variant)
            ]
            
            if subset.empty:
                ax.axis("off")
                continue
                
            unique_configs = sorted(subset["Config"].unique())
            bottoms = np.zeros(len(unique_configs))
            
            # Stack bars manually
            for outcome in stack_order:
                values = []
                colors = []
                
                for cfg in unique_configs:
                    row = subset[(subset["Config"] == cfg) & (subset["outcome"] == outcome)]
                    val = row["percentage"].values[0] if not row.empty else 0
                    values.append(val)
                    
                    if outcome == "correct":
                        colors.append(get_config_color(cfg))
                    else:
                        colors.append(fixed_outcomes.get(outcome, "#333333"))
                
                values = np.array(values)
                bars = ax.bar(
                    np.arange(len(unique_configs)),
                    values,
                    bottom=bottoms,
                    color=colors,
                    width=0.8
                )
                
                # Add percentage text if segment is substantial
                for rect in bars:
                    height = rect.get_height()
                    if height > 5: 
                         ax.text(rect.get_x() + rect.get_width() / 2, 
                                 rect.get_y() + height / 2, 
                                 f"{int(height)}", 
                                 ha="center", va="center", color="white", fontsize=9, fontweight="bold")
                
                bottoms += values
            
            ax.set_title(f"{strategy.upper()} – {variant.capitalize()}", fontsize=14, fontweight="bold")
            if j == 0:
                ax.set_ylabel("Percentage (%)")
            
            ax.set_ylim(0, 100)
            ax.set_xticks(np.arange(len(unique_configs)))
            ax.set_xticklabels([]) # Remove model names as requested
            ax.grid(axis="y", alpha=0.3)

    # Legend
    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor="black", label="Correct (Model Color)")]
    for o in stack_order:
        if o != "correct" and o in all_outcome_types:
            legend_handles.append(Patch(facecolor=fixed_outcomes.get(o, "#333333"), label=o.replace("_", " ").title()))
            
    fig.legend(handles=legend_handles, title="Outcome", loc="lower center", ncol=len(legend_handles), bbox_to_anchor=(0.5, 0.0), fontsize=12)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    out_path = os.path.join(out_dir, "outcome_distribution_unified.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_override_rate(df, out_dir):
    """
    Override success rate visualization by Hop.
    """
    subset = df[df["graph_variant"] == "counterfactual"].copy()
    if subset.empty:
        return

    subset = prepare_config_column(subset)
    # Convert to Percentage
    subset["em_pct"] = subset["em"] * 100

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle("Counterfactual Override Success Rate (by Hop)",
                 fontsize=18, fontweight="bold")

    strategies = sorted(subset["prompting_strategy"].unique())
    unique_configs = sorted(subset["Config"].unique())
    palette = get_color_palette(unique_configs)

    for idx, strategy in enumerate(strategies):
        if idx >= len(axes): break
        ax = axes[idx]
        strat_subset = subset[subset["prompting_strategy"] == strategy]
        
        sns.barplot(
            data=strat_subset,
            x="hop",
            y="em_pct",
            hue="Config",
            hue_order=unique_configs,
            ax=ax,
            palette=palette,
            alpha=0.9,
            errorbar=None,
            width=0.9
        )

        ax.set_title(f"{strategy.upper()} Strategy", fontweight="bold", fontsize=14)
        ax.set_xlabel("Hop Count", fontsize=12)
        ax.set_ylabel("Override Success Rate (%)", fontsize=12)
        ax.set_ylim(0, 110)
        ax.grid(axis="y", alpha=0.3)
        if ax.get_legend(): ax.get_legend().remove()
        
        for container in ax.containers:
            ax.bar_label(container, fmt="%.0f", fontsize=9, padding=2)

    handles = [plt.Rectangle((0,0),1,1, color=palette[i]) for i in range(len(palette))]
    fig.legend(handles, unique_configs, title="Configuration", loc="center right", bbox_to_anchor=(0.98, 0.5))
    plt.tight_layout(rect=[0, 0.03, 0.85, 0.95])
    
    out_path = os.path.join(out_dir, "override_rate_by_hop.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved {out_path}")



def plot_token_usage_by_variant(df, out_dir):
    """
    Histogram of average token usage per query by Graph Variant.
    Renamed from plot_token_usage_histogram.
    """
    df = prepare_config_column(df)

    avg_tokens = (
        df.groupby(["Config", "prompting_strategy", "graph_variant"])["total_tokens"]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle("Average Token Usage per Query (By Variant)", fontsize=18, fontweight="bold")

    strategies = sorted(avg_tokens["prompting_strategy"].unique())
    unique_configs = sorted(avg_tokens["Config"].unique())
    palette = get_color_palette(unique_configs)
    
    # Shared Y limit
    y_max = avg_tokens["total_tokens"].max() * 1.1

    for idx, strategy in enumerate(strategies):
        if idx >= len(axes):
            break

        ax = axes[idx]
        subset = avg_tokens[avg_tokens["prompting_strategy"] == strategy]

        barplot = sns.barplot(
            data=subset,
            x="graph_variant",
            y="total_tokens",
            hue="Config",
            hue_order=unique_configs,
            ax=ax,
            palette=palette,
            alpha=0.9,
            errorbar=None,
            width=0.9
        )

        ax.set_title(f"{strategy.upper()} Strategy",
                     fontweight="bold", fontsize=14)
        ax.set_xlabel("Graph Variant", fontsize=12)
        ax.set_ylabel("Avg Token Usage", fontsize=12)
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
                    f"{int(height)}",
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
    out_path = os.path.join(out_dir, "token_usage_by_variant.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")

def plot_token_usage_by_hop(df, out_dir):
    """
    Histogram of average token usage per query by Hop.
    """
    df = prepare_config_column(df)

    avg_tokens = (
        df.groupby(["Config", "prompting_strategy", "hop"])["total_tokens"]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle("Average Token Usage per Query (By Hop)", fontsize=18, fontweight="bold")

    strategies = sorted(avg_tokens["prompting_strategy"].unique())
    unique_configs = sorted(avg_tokens["Config"].unique())
    palette = get_color_palette(unique_configs)
    
    y_max = avg_tokens["total_tokens"].max() * 1.1

    for idx, strategy in enumerate(strategies):
        if idx >= len(axes): break
        ax = axes[idx]
        subset = avg_tokens[avg_tokens["prompting_strategy"] == strategy]

        barplot = sns.barplot(
            data=subset,
            x="hop",
            y="total_tokens",
            hue="Config",
            hue_order=unique_configs,
            ax=ax,
            palette=palette,
            alpha=0.9,
            errorbar=None,
            width=0.9
        )

        ax.set_title(f"{strategy.upper()} Strategy", fontweight="bold", fontsize=14)
        ax.set_xlabel("Hop Count", fontsize=12)
        ax.set_ylabel("Avg Token Usage", fontsize=12)
        ax.set_ylim(0, y_max)
        ax.grid(axis="y", alpha=0.3)
        if ax.get_legend(): ax.get_legend().remove()
        
        for p in barplot.patches:
            height = p.get_height()
            if height > 0:
                ax.annotate(f"{int(height)}", 
                            (p.get_x() + p.get_width() / 2., height), 
                            ha="center", va="bottom", fontsize=8, xytext=(0, 4), textcoords="offset points")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, title="Configuration", loc="center right", bbox_to_anchor=(0.98, 0.5))
    plt.tight_layout(rect=[0, 0.03, 0.85, 0.95])
    
    out_path = os.path.join(out_dir, "token_usage_by_hop.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
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
            width=0.9, # Widen bars
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
                    rotation=90 # Rotate labels to prevent overlap
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


def plot_metrics_histograms(df, out_dir):
    """
    Bar charts comparing metric values across configurations
    for the direct prompting strategy.
    Uses percentage for metrics (EM, F1, Path Found) and ms for Latency.
    """
    set_style()
    df = prepare_config_column(df)

    # Filter for direct prompting strategy
    df_direct = df[df["prompting_strategy"] == "scot"]
    
    # Pre-calculate Percentages
    df_direct["em_pct"] = df_direct["em"] * 100
    df_direct["f1_pct"] = df_direct["f1"] * 100
    df_direct["path_found_pct"] = df_direct["path_found"] * 100

    # Aggregate metrics for direct prompting strategy
    metrics = df_direct.groupby("Config").agg({
        "em_pct": "mean",
        "f1_pct": "mean",
        "path_found_pct": "mean",
        "latency_ms": "mean"
    }).reset_index()
    
    # Define metrics and their corresponding column names
    categories = ['EM (%)', 'F1 (%)', 'Path Found (%)', 'Latency (ms)']
    column_mapping = {
        'EM (%)': "em_pct",
        'F1 (%)': "f1_pct",
        'Path Found (%)': "path_found_pct",
        'Latency (ms)': "latency_ms"
    }
    
    # Get unique configurations and generate color palette
    unique_configs = sorted(metrics["Config"].unique())
    palette = {cfg: get_config_color(cfg) for cfg in unique_configs}
    
    # Plot bar charts for each metric
    fig, axes = plt.subplots(2, 2, figsize=(18, 10))
    fig.suptitle("Metric Values Across Configurations (Direct Prompting Strategy)", fontsize=18, y=0.995)
    axes = axes.flatten()  # Flatten the axes array for easy iteration
    for idx, category in enumerate(categories):
        ax = axes[idx]
        column_name = column_mapping[category]
        subset = metrics[["Config", column_name]]
        sns.barplot(
            data=subset,
            x="Config",
            y=column_name,
            hue="Config",
            hue_order=unique_configs,
            palette=palette,
            ax=ax,
            errorbar=None,
            alpha=0.9,
            legend=False
        )
        ax.set_title(category, fontsize=12, fontweight="bold", pad=15)
        ax.set_xlabel("")
        ax.set_ylabel("Score (%)" if "ms" not in category else "Time (ms)")
        
        if "ms" not in category:
             ax.set_ylim(0, 115) # Allow headroom for labels
             
        ax.grid(axis="y", alpha=0.3)
        ax.set_xticklabels([])  # Hide x-axis labels since we have legend
        # Annotate bars with values
        for container in ax.containers:
            # No decimal for percentages, 0 decimal for ms (as per usual preference for clean numbers)
            fmt = "%.0f" 
            ax.bar_label(container, fmt=fmt, fontsize=9, padding=3)
    
    # Manually create legend from palette
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor=palette[cfg], label=cfg)
        for cfg in unique_configs
    ]
    axes[1].legend(
        handles=legend_handles,
        title="Config",
        bbox_to_anchor=(1.05, 0.5),
        loc="center left",
        frameon=True,
        fontsize=9
    )
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "metrics_histograms.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")



def plot_hop_degradation(df, out_dir):
    """
    Line plot showing performance degradation with increasing hops.
    Uses consistent colors for configs.
    Changes:
    - Y-axis limited to 0.5 to 1.
    - Single legend outside the plot grid.
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
    
    # Collect legend handles and labels
    handles, labels = [], []
    
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
                line = ax.plot(
                    config_data["hop"],
                    config_data["em"],
                    marker="o",
                    linewidth=2.5,
                    markersize=8,
                    label=config,
                    color=color,
                    alpha=0.8,
                )
                # Collect handles and labels for the legend
                if config not in labels:
                    handles.append(line[0])
                    labels.append(config)
            ax.set_title(f"{strategy.upper()} - {variant.capitalize()}",
                         fontweight="bold", fontsize=12)
            ax.set_xlabel("Hop Count" if i == 1 else "", fontsize=11)
            ax.set_ylabel("Exact Match" if j == 0 else "", fontsize=11)
            ax.set_ylim(0.6, 1.05)  # Set y-axis to start at 0.5
            ax.grid(True, alpha=0.3)
            # Force integer x-axis ticks
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    
    # Add a single legend outside the plot grid
    fig.legend(handles, labels,
               bbox_to_anchor=(1.02, 0.5),
               loc="center left",
               frameon=True,
               shadow=True,
               fontsize=9,
               title="Configuration")
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "hop_degradation.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")

def plot_cost_vs_accuracy(df, out_dir):
    """
    Scatter plot showing cost-accuracy tradeoff with consistent colors and further aggregation.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        return
    
    # Prepare data
    df = prepare_config_column(df)
    
    # Aggregate data: Average cost and accuracy per configuration (ignoring prompting strategy and graph variant)
    agg = df.groupby(["Config"]).agg({
        "em": "mean",  # Or use "median" for robustness
        "cost": "mean"  # Or use "median" for robustness
    }).reset_index()
    
    # Plot with consistent colors
    fig, ax = plt.subplots(figsize=(14, 8))
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
    
    # Add labels and grid
    ax.set_title("Cost vs Accuracy Tradeoff", fontweight='bold', fontsize=18, pad=20)
    ax.set_xlabel("Average Cost per Query (USD)", fontsize=13)
    ax.set_ylabel("Average Exact Match (Accuracy)", fontsize=13)
    ax.grid(True, linestyle='--', alpha=0.4)
    
    # Add legend
    ax.legend(
        title="Configuration",
        bbox_to_anchor=(1.02, 1), 
        loc='upper left', 
        frameon=True, 
        shadow=True,
        fontsize=10
    )
    
    # Save plot
    plt.tight_layout()
    out_path = os.path.join(out_dir, "cost_vs_accuracy.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")


def plot_outcome_sunburst(df, out_dir):
    """
    Horizontal stacked bar charts split by graph_variant (side label).
    Columns = prompting strategy.
    Correct outcome uses model/config color.
    """
    set_style()
    df = prepare_config_column(df)

    strategies = sorted(df["prompting_strategy"].unique())
    variants = sorted(df["graph_variant"].unique())
    configs = sorted(df["Config"].unique())

    fig, axes = plt.subplots(
        len(variants),
        len(strategies),
        figsize=(5 * len(strategies), 2.8 * len(variants)),
        sharex=True
    )

    if len(variants) == 1:
        axes = [axes]
    if len(strategies) == 1:
        axes = [[ax] for ax in axes]

    fig.suptitle("Outcome Distribution", fontsize=18, fontweight="bold")

    base_outcome_colors = {
        "missed_answer": "#bdc3c7",
        "wrong_answer": "#ff0000",
    }

    config_colors = {cfg: get_config_color(cfg) for cfg in configs}

    for r, variant in enumerate(variants):
        for c, strategy in enumerate(strategies):
            ax = axes[r][c]

            subset = df[
                (df["graph_variant"] == variant) &
                (df["prompting_strategy"] == strategy)
            ]

            if subset.empty:
                ax.axis("off")
                continue

            counts = (
                subset.groupby(["Config", "outcome"])
                      .size()
                      .reset_index(name="counts")
            )

            counts["total"] = counts.groupby("Config")["counts"].transform("sum")
            counts["percentage"] = counts["counts"] / counts["total"] * 100

            pivot = counts.pivot_table(
                index="Config",
                columns="outcome",
                values="percentage",
                fill_value=0
            )

            for col in ["correct", "missed_answer", "wrong_answer"]:
                if col not in pivot.columns:
                    pivot[col] = 0

            pivot = pivot.loc[configs]
            y_pos = np.arange(len(pivot))
            left = np.zeros(len(pivot))

            # Correct (model-colored)
            for i, cfg in enumerate(pivot.index):
                v = pivot.loc[cfg, "correct"]
                if v > 0:
                    ax.barh(
                        i,
                        v,
                        left=left[i],
                        color=config_colors[cfg],
                        height=0.65,
                        alpha=0.9
                    )
                    left[i] += v

            # Other outcomes
            for outcome in ["missed_answer", "wrong_answer"]:
                vals = pivot[outcome].values
                ax.barh(
                    y_pos,
                    vals,
                    left=left,
                    color=base_outcome_colors[outcome],
                    height=0.65,
                    alpha=0.9
                )
                left += vals

            ax.set_xlim(0, 100)
            ax.grid(axis="x", alpha=0.3)

            if r == len(variants) - 1:
                ax.set_xlabel("Percentage (%)")

            if c == 0:
                ax.set_yticks(y_pos)
                ax.set_yticklabels(pivot.index, fontsize=9)
                ax.set_ylabel(variant, fontsize=11, fontweight="bold")
            else:
                ax.set_yticks([])

            if r == 0:
                ax.set_title(strategy.upper(), fontsize=12, fontweight="bold")

    from matplotlib.patches import Patch

    outcome_legend = [
        Patch(facecolor="#000000", label="Correct (model color)"),
        Patch(facecolor=base_outcome_colors["missed_answer"], label="Missed"),
        Patch(facecolor=base_outcome_colors["wrong_answer"], label="Wrong"),
    ]

    config_legend = [
        Patch(facecolor=config_colors[cfg], label=cfg)
        for cfg in configs
    ]

    fig.legend(
        handles=outcome_legend,
        title="Outcome",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        frameon=True
    )

    plt.tight_layout(rect=[0, 0.05, 0.9, 0.95])
    out_path = os.path.join(out_dir, "outcome_distribution.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_efficiency_scatter(df, out_dir):
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
        plot_accuracy_by_hop(df, plots_dir)
        plot_override_rate(df, plots_dir)
        # plot_override_rate_by_variant removed as redundant
        plot_outcome_distribution(df, plots_dir)
        plot_token_usage_by_variant(df, plots_dir)
        plot_token_usage_by_hop(df, plots_dir)
        plot_cost_analysis(df, plots_dir)
        plot_total_cost(df, plots_dir)
        
        print("\nGenerating additional insights...")
        plot_heatmap_performance(df, plots_dir)
        plot_efficiency_scatter(df, plots_dir)
        plot_metrics_histograms(df, plots_dir)
        plot_hop_degradation(df, plots_dir)
        plot_cost_vs_accuracy(df, plots_dir)
        
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