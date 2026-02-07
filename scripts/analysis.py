#!/usr/bin/env python3
"""
analysis_enhanced.py

Enhanced version with prettier plots and additional analysis.
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

def abbreviate(s):
    """
    Abbreviates a string by taking the first letter of each word.
    Example: "gpt-4" → "G4", "llama-2" → "L2", "beam-search" → "BS".
    """
    return "".join(w[0].upper() for w in s.replace("-", " ").split())

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

def annotate_bars(ax, fmt='.2f', fontsize=9):
    """Enhanced bar annotation with better positioning"""
    for container in ax.containers:
        labels = []
        for bar in container:
            height = bar.get_height()
            if height > 0:
                labels.append(f'{height:{fmt}}')
            else:
                labels.append('')
        ax.bar_label(container, labels=labels, fontsize=fontsize, padding=3, 
                    fmt='%s', label_type='edge')

def plot_accuracy_by_hop(df, out_dir):
    """
    Compact bar chart of EM score by Hop.
    - Abbreviated legend labels
    - Value labels on bars
    """
    df = df.copy()

    # --- ultra-compact legend labels ---
    def abbrev(s):
        return "".join(w[0].upper() for w in s.replace("-", " ").split())

    df["Config"] = (
        df["model"].str.split("/").str[-1].apply(abbrev)
        + "+"
        + df["decoding"].apply(abbrev)
    )

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True, sharey=True)
    fig.suptitle("Accuracy by Hop Count (EM)", fontsize=18, y=0.995)

    strategies = df["prompting_strategy"].unique()
    variants = df["graph_variant"].unique()
    palette = sns.color_palette("husl", n_colors=df["Config"].nunique())

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

            # --- annotate bars with values ---
            for container in ax.containers:
                ax.bar_label(container, fmt="%.1f", fontsize=8, padding=2)

            # --- single legend on right ---
            if j == 2:
                ax.legend(
                    title="Cfg",
                    bbox_to_anchor=(1.05, 0.5),
                    loc="center left",
                    frameon=True
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
    Comparison across Natural vs Abstract vs Counterfactual
    with compact legend labels and values on bars.
    """
    df = df.copy()

    # --- aggressive abbreviation for legend ---
    def abbrev(s):
        return "".join(w[0].upper() for w in s.replace("-", " ").split())

    df["Config"] = (
        df["model"].str.split("/").str[-1].apply(abbrev)
        + "+"
        + df["decoding"].apply(abbrev)
    )

    # Aggregate over hops
    agg_df = (
        df.groupby(["Config", "graph_variant", "prompting_strategy"])["em"]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(19, 7))
    fig.suptitle("Performance Across Graph Variants",
                 fontsize=18, fontweight="bold")

    strategies = agg_df["prompting_strategy"].unique()
    palette = sns.color_palette("rocket_r", n_colors=agg_df["Config"].nunique())

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

        # --- value labels on bars (capped at 0.90) ---
        for container in ax.containers:
            labels = [
                f"{min(v, 0.9):.1f}" if v is not None else ""
                for v in container.datavalues
            ]
            ax.bar_label(container, labels=labels,
                         fontsize=9, padding=2)

        # Remove per-axis legends
        if ax.get_legend():
            ax.get_legend().remove()

    # --- single global legend, fully outside ---
    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        title="Cfg",
        loc="center left",
        bbox_to_anchor=(0.9, 0.5),
        frameon=True
    )

    # Leave room on the right for legend
    plt.tight_layout(rect=[0, 0.03, 0.86, 0.95])

    out_path = os.path.join(out_dir, "graph_variant_comparison.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_override_rate(df, out_dir):
    """
    Enhanced override success rate visualization with a single global legend.
    """
    subset = df[df["graph_variant"] == "counterfactual"].copy()
    if subset.empty:
        return
    
    # Create the Config label
    subset["Config"] = subset["model"].str.split('/').str[-1] + "\n" + subset["decoding"]
    
    fig, axes = plt.subplots(1, 2, figsize=(18, 7)) # Increased width for global legend
    fig.suptitle("Counterfactual Override Success Rate", fontsize=18, fontweight='bold')
    
    strategies = sorted(subset["prompting_strategy"].unique())
    palette = sns.color_palette("viridis", n_colors=len(subset["Config"].unique()))
    
    for idx, strategy in enumerate(strategies):
        if idx >= len(axes): break # Safety check for subplot count
        
        ax = axes[idx]
        strat_subset = subset[subset["prompting_strategy"] == strategy]
        
        sns.barplot(data=strat_subset, x="hop", y="em", hue="Config",
                   ax=ax, palette=palette, alpha=0.9, errorbar=None)
        
        ax.set_title(f"{strategy.upper()} Strategy", fontweight='bold', fontsize=14)
        ax.set_xlabel("Hop Count", fontsize=12)
        ax.set_ylabel("Override Success Rate (EM)", fontsize=12)
        ax.set_ylim(0, 1.05)
        ax.grid(axis='y', alpha=0.3)
        
        # Add reference line WITHOUT a label here to prevent duplicates
        ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
        
        # REMOVED: ax.legend(...) from inside the loop
        # This prevents the legend from being drawn for every single subplot.
        ax.get_legend().remove() 

    # Create a SINGLE global legend for the entire figure
    handles, labels = axes[0].get_legend_handles_labels()
    
    # Add the Baseline manually to the legend handles to keep it clean
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], color='red', linestyle='--', linewidth=1.5))
    labels.append('Random Baseline')

    fig.legend(
        handles, 
        labels, 
        title="Configuration",
        loc='center right', 
        bbox_to_anchor=(0.98, 0.5),
        frameon=True,
        shadow=True
    )
    
    # Adjust layout to make room for the legend on the right
    plt.tight_layout(rect=[0, 0.03, 0.85, 0.95])
    plt.savefig(f"{out_dir}/override_rate_enhanced.png", dpi=300)
    plt.close()

def plot_failure_modes(df, out_dir):
    """
    Enhanced stacked bar chart of outcome distributions.
    """
    df = df.copy()
    df["Config"] = df["model"].str.split('/').str[-1] + "\n" + df["decoding"]
    
    # Calculate percentages
    counts = df.groupby(["Config", "graph_variant", "prompting_strategy", "outcome"]).size().reset_index(name='counts')
    totals = counts.groupby(["Config", "graph_variant", "prompting_strategy"])['counts'].transform('sum')
    counts['percentage'] = counts['counts'] / totals * 100
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle("Failure Mode Distribution", fontsize=18, fontweight='bold')
    
    # Define color mapping for outcomes
    outcome_colors = {
        'correct': '#2ecc71',      # green
        'wrong': '#e74c3c',        # red
        'missed': '#f39c12',       # orange
        'hallucination': '#9b59b6', # purple
        'leakage': '#e67e22',      # dark orange
        'parse_error': '#34495e'    # dark gray
    }
    
    strategies = counts["prompting_strategy"].unique()
    variants = counts["graph_variant"].unique()
    
    for i, strategy in enumerate(strategies):
        for j, variant in enumerate(variants):
            ax = axes[i, j]
            subset = counts[(counts["prompting_strategy"] == strategy) & 
                           (counts["graph_variant"] == variant)]
            
            if not subset.empty:
                # Pivot for stacked bar
                pivot = subset.pivot_table(index='Config', columns='outcome', 
                                          values='percentage', fill_value=0)
                
                # Ensure all outcomes are present
                for outcome in outcome_colors.keys():
                    if outcome not in pivot.columns:
                        pivot[outcome] = 0
                
                # Sort outcomes for consistent ordering
                outcome_order = ['correct']
                pivot = pivot[[col for col in outcome_order if col in pivot.columns]]
                
                pivot.plot(kind='bar', stacked=True, ax=ax, 
                          color=[outcome_colors.get(col, '#95a5a6') for col in pivot.columns],
                          alpha=0.9, width=0.7)
                
                ax.set_title(f"{strategy.upper()} - {variant.capitalize()}", 
                           fontweight='bold', fontsize=12)
                ax.set_xlabel("Configuration" if i == 1 else "", fontsize=11)
                ax.set_ylabel("Percentage (%)" if j == 0 else "", fontsize=11)
                ax.set_ylim(0, 105)
                ax.legend(title="Outcome", bbox_to_anchor=(1.05, 1), loc='upper left',
                         frameon=True, shadow=True, fontsize=9)
                ax.grid(axis='y', alpha=0.3)
                ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "failure_modes_enhanced.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")
    

def plot_efficiency(df, out_dir):
    """
    Enhanced scatter plot: Latency vs EM with size representing token usage.
    Annotations removed for better readability.
    """
    agg = df.groupby(["model", "prompting_strategy", "decoding", "graph_variant"]).agg({
        "em": "mean",
        "latency_ms": "mean",
        "total_tokens": "mean"
    }).reset_index()
    
    agg["Model"] = agg["model"].str.split('/').str[-1]
    
    if agg.empty:
        return
        
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Create scatter plot:
    # Size represents total_tokens for a 3rd dimension of data
    scatter = sns.scatterplot(
        data=agg, x="latency_ms", y="em", 
        hue="prompting_strategy", 
        style="graph_variant",
        size="total_tokens", 
        sizes=(150, 1200), # Increased size range for better visibility
        alpha=0.8, 
        palette="Set2", 
        ax=ax,
        edgecolor="w",
        linewidth=1
    )
    
    # REMOVED: The annotation loop that was placing model names on dots.
    
    ax.set_title("Efficiency Analysis: Latency vs Accuracy vs Token Usage", 
                fontweight='bold', fontsize=18, pad=20)
    ax.set_xlabel("Average Latency (ms)", fontsize=13)
    ax.set_ylabel("Average Exact Match (Accuracy)", fontsize=13)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Add quadrant lines based on medians
    median_latency = agg["latency_ms"].median()
    median_em = agg["em"].median()
    ax.axvline(x=median_latency, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.axhline(y=median_em, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    
    # Helpful Quadrant Labels
    ax.text(0.02, 0.96, "High Accuracy / Fast", transform=ax.transAxes,
           fontsize=11, fontweight='bold', verticalalignment='top', color='green',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='green', alpha=0.05))
           
    ax.text(0.98, 0.04, "Low Accuracy / Slow", transform=ax.transAxes,
           fontsize=11, fontweight='bold', verticalalignment='bottom', 
           horizontalalignment='right', color='red',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.05))
    
    # Legend management
    ax.legend(
        title="Analysis Dimensions",
        bbox_to_anchor=(1.02, 1), 
        loc='upper left', 
        frameon=True, 
        shadow=True,
        fontsize=10
    )
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "efficiency_scatter_enhanced.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_cost_analysis(df, out_dir):
    """
    Enhanced cost per query visualization with values on bars, abbreviated model names, and a single global legend.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        print("No cost data available to plot.")
        return
    
    df = df.copy()
    
    # Abbreviate model and decoding names
    df["Config"] = (
        df["model"].str.split('/').str[-1].apply(abbreviate)
        + "+"
        + df["decoding"].apply(abbreviate)
    )
    
    # Calculate average cost per configuration
    avg_cost = df.groupby(["Config", "prompting_strategy", "graph_variant"])["cost"].mean().reset_index()
    
    # Increase width to accommodate the legend on the right
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle("Cost Analysis per Query", fontsize=18, fontweight='bold')
    
    strategies = sorted(avg_cost["prompting_strategy"].unique())
    palette = sns.color_palette("coolwarm", n_colors=len(avg_cost["Config"].unique()))
    
    for idx, strategy in enumerate(strategies):
        if idx >= len(axes):
            break
        ax = axes[idx]
        subset = avg_cost[avg_cost["prompting_strategy"] == strategy]
        
        # Create bar plot
        barplot = sns.barplot(data=subset, x="graph_variant", y="cost", hue="Config",
                              ax=ax, palette=palette, alpha=0.9, errorbar=None)
        
        ax.set_title(f"{strategy.upper()} Strategy", fontweight='bold', fontsize=14)
        ax.set_xlabel("Graph Variant", fontsize=12)
        ax.set_ylabel("Avg Cost per Query (USD)", fontsize=12)
        ax.grid(axis='y', alpha=0.3)
        ax.tick_params(axis='x', rotation=15)
        
        # Remove the individual legend for this subplot
        if ax.get_legend():
            ax.get_legend().remove()
        
        # Annotate bars with their values
        for p in barplot.patches:
            ax.annotate(format(p.get_height(), '.2f'), 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        xytext=(0, 5), 
                        textcoords='offset points', 
                        fontsize=8)
    
    # Extract handles and labels for the global legend
    handles, labels = axes[0].get_legend_handles_labels()
    
    # Create ONE shared legend
    fig.legend(
        handles, 
        labels, 
        title="Configuration",
        loc='center right', 
        bbox_to_anchor=(0.98, 0.5),
        frameon=True,
        shadow=True
    )
    
    # Adjust layout to prevent overlap with the global legend
    plt.tight_layout(rect=[0, 0.03, 0.85, 0.95])
    
    out_path = os.path.join(out_dir, "cost_analysis_enhanced.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")



def plot_total_cost(df, out_dir):
    """
    Enhanced total cost visualization with values displayed on the bars and abbreviated model names.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        return
    
    df = df.copy()
    
    # Abbreviate model and decoding names
    df["Config"] = (
        df["model"].str.split("/").str[-1].apply(abbreviate)
        + "+"
        + df["decoding"].apply(abbreviate)
    )
    
    # Sum costs
    total_costs = df.groupby(["Config", "prompting_strategy", "graph_variant"])["cost"].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Create grouped bar chart
    barplot = sns.barplot(data=total_costs, x="graph_variant", y="cost", 
                          hue="Config", palette="Spectral", alpha=0.9, ax=ax, errorbar=None)
    
    ax.set_title("Total Experiment Cost by Configuration", fontweight='bold', fontsize=16)
    ax.set_xlabel("Graph Variant", fontsize=13)
    ax.set_ylabel("Total Cost ($)", fontsize=13)
    ax.legend(title="Configuration", frameon=True, shadow=True, 
              bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    # Annotate bars with their values
    for p in barplot.patches:
        barplot.annotate(format(p.get_height(), '.2f'), 
                         (p.get_x() + p.get_width() / 2., p.get_height()), 
                         ha='center', va='center', 
                         xytext=(0, 5), 
                         textcoords='offset points', 
                         fontsize=9)
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "cost_total_enhanced.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

# NEW PLOTS BELOW

def plot_heatmap_performance(df, out_dir):
    """
    Heatmap showing performance across all dimensions
    with maximally abbreviated configuration names.
    """
    df = df.copy()

    # --- ultra-minimal abbreviations ---
    def abbrev_model(name):
        name = name.lower()
        letters = "".join(c for c in name if c.isalpha())
        digits = "".join(c for c in name if c.isdigit())
        return (letters[0].upper() + digits) if digits else letters[0].upper()

    def abbrev_decoding(name):
        return name[0].upper()

    df["Config"] = (
        df["model"].str.split("/").str[-1].apply(abbrev_model)
        + "+"
        + df["decoding"].apply(abbrev_decoding)
    )

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
    ax.set_ylabel("Cfg & Strategy", fontsize=13)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "heatmap_performance.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def plot_radar_chart(df, out_dir):
    """
    Radar chart comparing different metrics for each configuration.
    """
    from math import pi
    
    df = df.copy()
    df["Config"] = df["model"].str.split('/').str[-1] + " " + df["decoding"]
    
    # Aggregate metrics
    metrics = df.groupby(["Config", "prompting_strategy"]).agg({
        "em": "mean",
        "f1": "mean",
        "path_found": "mean",
    }).reset_index()
    
    # Add inverse normalized latency (so higher is better)
    latency_agg = df.groupby(["Config", "prompting_strategy"])["latency_ms"].mean()
    max_latency = latency_agg.max()
    metrics["speed"] = metrics.apply(
        lambda row: 1 - (df[(df["Config"] == row["Config"]) & 
                           (df["prompting_strategy"] == row["prompting_strategy"])]["latency_ms"].mean() / max_latency),
        axis=1
    )
    
    categories = ['EM', 'F1', 'Path Found', 'Speed']
    N = len(categories)
    
    # Create subplots for each strategy
    strategies = metrics["prompting_strategy"].unique()
    fig, axes = plt.subplots(1, len(strategies), figsize=(16, 7), subplot_kw=dict(projection='polar'))
    
    if len(strategies) == 1:
        axes = [axes]
    
    fig.suptitle("Multi-Metric Radar Comparison", fontsize=18, fontweight='bold')
    
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    colors = sns.color_palette("husl", n_colors=len(metrics["Config"].unique()))
    
    for idx, strategy in enumerate(strategies):
        ax = axes[idx]
        subset = metrics[metrics["prompting_strategy"] == strategy]
        
        for i, (_, row) in enumerate(subset.iterrows()):
            values = [row["em"], row["f1"], row["path_found"], row["speed"]]
            values += values[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, label=row["Config"], 
                   color=colors[i], alpha=0.7)
            ax.fill(angles, values, alpha=0.15, color=colors[i])
        
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
    Line plot showing how performance degrades with increasing hops.
    """
    df = df.copy()
    df["Config"] = df["model"].str.split('/').str[-1] + " " + df["decoding"]
    df["hop"] = df["hop"].astype(int)
    
    # Aggregate by hop
    hop_perf = df.groupby(["Config", "prompting_strategy", "graph_variant", "hop"])["em"].mean().reset_index()
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True, sharey=True)
    fig.suptitle("Performance Degradation by Hop Count", fontsize=18, fontweight='bold')
    
    strategies = hop_perf["prompting_strategy"].unique()
    variants = hop_perf["graph_variant"].unique()
    
    palette = sns.color_palette("Set2", n_colors=len(hop_perf["Config"].unique()))
    
    for i, strategy in enumerate(strategies):
        for j, variant in enumerate(variants):
            ax = axes[i, j]
            subset = hop_perf[(hop_perf["prompting_strategy"] == strategy) & 
                             (hop_perf["graph_variant"] == variant)]
            
            if not subset.empty:
                for k, config in enumerate(subset["Config"].unique()):
                    config_data = subset[subset["Config"] == config].sort_values("hop")
                    ax.plot(config_data["hop"], config_data["em"], 
                           marker='o', linewidth=2.5, markersize=8,
                           label=config, color=palette[k], alpha=0.8)
                
                ax.set_title(f"{strategy.upper()} - {variant.capitalize()}", 
                           fontweight='bold', fontsize=12)
                ax.set_xlabel("Hop Count" if i == 1 else "", fontsize=11)
                ax.set_ylabel("Exact Match" if j == 0 else "", fontsize=11)
                ax.set_ylim(0, 1.05)
                ax.grid(True, alpha=0.3)
                
                if j == 2:
                    ax.legend(bbox_to_anchor=(1.05, 0.5), loc='center left', 
                            frameon=True, shadow=True, fontsize=9)
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "hop_degradation.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")


def plot_cost_vs_accuracy(df, out_dir):
    """
    Scatter plot showing cost-accuracy tradeoff without overlapping text labels.
    Uses markers and colors to differentiate configurations.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        return
    
    df = df.copy()
    # Using a cleaner Config name for the legend
    df["Config"] = df["model"].str.split('/').str[-1] + " (" + df["decoding"] + ")"
    
    # Aggregate data
    agg = df.groupby(["Config", "prompting_strategy", "graph_variant"]).agg({
        "em": "mean",
        "cost": "mean"
    }).reset_index()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # We use 'hue' for Strategy and 'style' for Config or Variant 
    # to keep the plot visually distinguishable without text clutter.
    scatter = sns.scatterplot(
        data=agg, x="cost", y="em",
        hue="prompting_strategy", 
        style="graph_variant",
        s=250, 
        alpha=0.8, 
        palette="tab10", 
        ax=ax,
        edgecolor="w",
        linewidth=1.5
    )
    
    # REMOVED: The annotation loop that was creating illegible text overlaps.
    
    ax.set_title("Cost vs Accuracy Tradeoff", fontweight='bold', fontsize=18, pad=20)
    ax.set_xlabel("Average Cost per Query (USD)", fontsize=13)
    ax.set_ylabel("Average Exact Match (Accuracy)", fontsize=13)
    ax.grid(True, linestyle='--', alpha=0.4)
    
    # Calculate Pareto frontier
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
               linewidth=2.5, alpha=0.6, label='Pareto Frontier (Optimal)')
    
    # Move legend outside to keep the plot area clean
    ax.legend(
        title="Analysis Dimensions",
        bbox_to_anchor=(1.02, 1), 
        loc='upper left', 
        frameon=True, 
        shadow=True,
        fontsize=10
    )
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "cost_vs_accuracy_enhanced.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_outcome_sunburst(df, out_dir):
    """
    Create a hierarchical view of outcomes using a treemap-style visualization.
    """
    df = df.copy()
    df["Config"] = df["model"].str.split('/').str[-1]
    
    # Count outcomes
    outcome_counts = df.groupby(["prompting_strategy", "graph_variant", "outcome"]).size().reset_index(name='count')
    
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle("Outcome Distribution Overview", fontsize=18, fontweight='bold')
    
    outcome_colors = {
        'correct': '#2ecc71',
        'wrong': '#e74c3c',
        'missed': '#f39c12',
        'hallucination': '#9b59b6',
        'leakage': '#e67e22',
        'parse_error': '#34495e'
    }
    
    strategies = outcome_counts["prompting_strategy"].unique()
    
    for idx, strategy in enumerate(strategies):
        ax = axes[idx]
        subset = outcome_counts[outcome_counts["prompting_strategy"] == strategy]
        
        # Create stacked bar by variant
        pivot = subset.pivot_table(index='graph_variant', columns='outcome', 
                                   values='count', fill_value=0)
        
        # Normalize to percentages
        pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
        
        pivot_pct.plot(kind='barh', stacked=True, ax=ax,
                      color=[outcome_colors.get(col, '#95a5a6') for col in pivot_pct.columns],
                      alpha=0.9, width=0.7)
        
        ax.set_title(f"{strategy.upper()} Strategy", fontweight='bold', fontsize=14)
        ax.set_xlabel("Percentage (%)", fontsize=12)
        ax.set_ylabel("Graph Variant", fontsize=12)
        ax.set_xlim(0, 100)
        ax.legend(title="Outcome", bbox_to_anchor=(1.05, 1), loc='upper left',
                 frameon=True, shadow=True)
        ax.grid(axis='x', alpha=0.3)
        
        # Add percentage labels
        for c in ax.containers:
            labels = [f'{v.get_width():.1f}%' if v.get_width() > 3 else '' for v in c]
            ax.bar_label(c, labels=labels, label_type='center', fontsize=8)
    
    plt.tight_layout()
    out_path = os.path.join(out_dir, "outcome_distribution.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Enhanced analysis with prettier plots")
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
        print("\nGenerating enhanced plots...")
        set_style()
        
        # Original plots (enhanced)
        plot_graph_variant_comparison(df, plots_dir)
        plot_accuracy_by_hop(df, plots_dir)
        plot_override_rate(df, plots_dir)
        plot_failure_modes(df, plots_dir)
        plot_efficiency(df, plots_dir)
        plot_cost_analysis(df, plots_dir)
        plot_total_cost(df, plots_dir)
        
        # New plots
        print("\nGenerating additional insights...")
        plot_heatmap_performance(df, plots_dir)
        plot_radar_chart(df, plots_dir)
        plot_hop_degradation(df, plots_dir)
        plot_cost_vs_accuracy(df, plots_dir)
        plot_outcome_sunburst(df, plots_dir)
        
        print(f"\nAll plots saved to {plots_dir}")
    
    # Enhanced Textual Analysis Report
    print("\nGenerating analysis report...")
    report_path = os.path.join(args.out_dir, "analysis_report.md")
    with open(report_path, "w") as f:
        f.write("# Experiment Analysis Report\n\n")
        f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Queries Evaluated:** {len(df)}\n\n")
        f.write("---\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        best_config = df.groupby(["model", "decoding", "prompting_strategy"])["em"].mean().sort_values(ascending=False).head(1)
        f.write(f"**Best Performing Configuration:**\n")
        f.write(f"- Model: `{best_config.index[0][0]}`\n")
        f.write(f"- Decoding: `{best_config.index[0][1]}`\n")
        f.write(f"- Strategy: `{best_config.index[0][2]}`\n")
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
        
        # Detailed Outcomes
        f.write("## Detailed Outcome Breakdown\n\n")
        
        # Pivot table of outcomes
        outcomes = df.pivot_table(
            index=["model", "graph_variant"], 
            columns="outcome", 
            aggfunc="size", 
            fill_value=0
        )
        outcomes["Total"] = outcomes.sum(axis=1)
        outcomes_pct = outcomes.div(outcomes["Total"], axis=0).mul(100).round(2)
        f.write("### Outcome Percentages by Model and Graph Variant\n\n")
        f.write(outcomes_pct.to_markdown())
        f.write("\n\n---\n\n")
        
        # Performance by Strategy
        f.write("## Performance by Strategy\n\n")
        strategy_perf = df.groupby(["prompting_strategy", "graph_variant"]).agg({
            "em": ["mean", "std"],
            "f1": "mean",
            "latency_ms": "mean"
        }).round(4)
        strategy_perf.columns = ['_'.join(col).strip() for col in strategy_perf.columns.values]
        f.write(strategy_perf.to_markdown())
        f.write("\n\n---\n\n")
        
        # Hop analysis
        f.write("## Performance by Hop Count\n\n")
        hop_perf = df.groupby(["hop", "graph_variant"])["em"].mean().reset_index()
        hop_pivot = hop_perf.pivot(index="hop", columns="graph_variant", values="em").round(4)
        f.write(hop_pivot.to_markdown())
        f.write("\n\n---\n\n")
        
        # Metric Summary
        f.write("## Comprehensive Metric Summary\n\n")
        agg_cols = {
            "em": "mean",
            "f1": "mean",
            "latency_ms": "mean",
            "total_tokens": "mean",
            "path_found": "mean"
        }
        if "cost" in df.columns and df["cost"].sum() > 0:
            agg_cols["cost"] = ["mean", "sum"]
            
        summary = df.groupby(["model", "decoding", "graph_variant", "prompting_strategy"]).agg(agg_cols).round(4)
        summary.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in summary.columns.values]
        f.write(summary.to_markdown())
        f.write("\n\n---\n\n")
        
        # Key Insights
        f.write("## Key Insights\n\n")
        
        # Best per variant
        f.write("### Best Configuration per Graph Variant\n\n")
        for variant in df["graph_variant"].unique():
            variant_df = df[df["graph_variant"] == variant]
            best = variant_df.groupby(["model", "prompting_strategy"])["em"].mean().sort_values(ascending=False).head(1)
            f.write(f"**{variant.capitalize()}:** {best.index[0][0]} with {best.index[0][1]} strategy (EM: {best.values[0]:.4f})\n\n")
        
        # Strategy comparison
        f.write("### Strategy Effectiveness\n\n")
        strategy_avg = df.groupby("prompting_strategy")["em"].mean().sort_values(ascending=False)
        for strat, score in strategy_avg.items():
            f.write(f"- **{strat.upper()}**: {score:.4f} average EM\n")
        f.write("\n")
        
        # Failure analysis
        f.write("### Most Common Failure Modes\n\n")
        failure_counts = df[df["outcome"] != "correct"]["outcome"].value_counts()
        for outcome, count in failure_counts.items():
            pct = (count / len(df)) * 100
            f.write(f"- **{outcome.capitalize()}**: {count} occurrences ({pct:.2f}%)\n")
        f.write("\n---\n\n")
        
        # Efficiency insights
        if "cost" in df.columns and df["cost"].sum() > 0:
            f.write("## Cost Efficiency Analysis\n\n")
            cost_eff = df.groupby(["model", "prompting_strategy"]).agg({
                "em": "mean",
                "cost": "mean"
            }).reset_index()
            cost_eff["cost_per_em_point"] = (cost_eff["cost"] / cost_eff["em"]).round(6)
            cost_eff = cost_eff.sort_values("cost_per_em_point")
            f.write("### Cost per EM Point (Lower is Better)\n\n")
            f.write(cost_eff.to_markdown(index=False))
            f.write("\n\n")
        
        f.write("---\n\n")
        f.write("*End of Report*\n")
        
    print(f"Analysis report saved to {report_path}")

if __name__ == "__main__":
    main()