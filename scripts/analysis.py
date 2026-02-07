#!/usr/bin/env python3
"""
analysis.py

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

def set_style():
    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.figsize"] = (10, 6)

def annotate_bars(g, fmt='.2f'):
    for ax in g.axes.flatten():
        for c in ax.containers:
            labels = [f'{v.get_height():{fmt}}' if v.get_height() > 0 else '' for v in c]
            ax.bar_label(c, labels=labels, label_type='edge', fontsize=8, padding=2)

def plot_accuracy_by_hop(df, out_dir):
    """
    Bar chart of EM score by Hop, grouped by Model/Strategy/Decoding.
    """
    plt.figure()
    
    # Create combined key for visualization
    df = df.copy()
    df["Config"] = df["model"] + "\n" + df["decoding"]

    g = sns.catplot(
        data=df, kind="bar",
        x="hop", y="em", hue="Config", row="prompting_strategy", col="graph_variant",
        errorbar=None, palette="viridis", alpha=.8, height=4, aspect=1.2,
        sharey=True
    )
    g.despine(left=True)
    g.set_axis_labels("Hop Count", "Exact Match Accuracy")
    g.fig.suptitle("Accuracy by Hop", y=1.02)
    annotate_bars(g)
    
    out_path = os.path.join(out_dir, "accuracy_by_hop.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_graph_variant_comparison(df, out_dir):
    """
    Compare Natural vs Abstract vs Counterfactual.
    """
    plt.figure()
    df = df.copy()
    df["Config"] = df["model"] + "\n" + df["decoding"]
    
    # Aggregate over hops for a general view
    g = sns.catplot(
        data=df, kind="bar",
        x="graph_variant", y="em", hue="Config", col="prompting_strategy",
        errorbar=None, palette="magma", alpha=.8, height=5, aspect=1.5
    )
    g.set_axis_labels("Graph Variant", "Exact Match Accuracy")
    g.fig.suptitle("Performance across Graph Variants", y=1.02)
    annotate_bars(g)
    
    out_path = os.path.join(out_dir, "graph_variant_comparison.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_override_rate(df, out_dir):
    """
    Plot override success rate (EM on Counterfactual graphs).
    """
    plt.figure()
    subset = df[df["graph_variant"] == "counterfactual"].copy()
    if subset.empty:
        return

    subset["Config"] = subset["model"] + "\n" + subset["decoding"]

    g = sns.catplot(
        data=subset, kind="bar",
        x="hop", y="em", hue="Config", col="prompting_strategy",
        errorbar=None, palette="rocket", alpha=.8, height=5, aspect=1.2
    )
    # y-label: Override Success Rate is simply EM on counterfactual data
    g.set_axis_labels("Hop Count", "Override Success Rate (EM)")
    g.fig.suptitle("Counterfactual Override Rate", y=1.02)
    
    # Add secondary metric annotation if possible, but keeping it simple for now
    annotate_bars(g)

    out_path = os.path.join(out_dir, "override_rate.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_failure_modes(df, out_dir):
    """
    Stacked bar chart of Outcome distributions (Correct, Wrong, Missed, Hallucination, Leakage, Parse Error).
    """
    plt.figure()
    df = df.copy()
    df["Config"] = df["model"] + "\n" + df["decoding"]
    
    # Calculate counts per group
    counts = df.groupby(["Config", "graph_variant", "outcome"]).size().reset_index(name='counts')
    
    # Normalize to get percentages
    totals = counts.groupby(["Config", "graph_variant"])['counts'].transform('sum')
    counts['percentage'] = counts['counts'] / totals
    
    # Plot
    # FacetGrid for cleaner separation if multiple models
    g = sns.catplot(
        data=counts, kind="bar",
        x="graph_variant", y="percentage", hue="outcome", col="Config",
        palette="RdYlGn_r", alpha=.9, height=5, aspect=1.2, sharey=True
    )
    g.set_axis_labels("Graph Variant", "Proportion of Queries")
    g.fig.suptitle("Failure Mode Distribution", y=1.02)
    
    annotate_bars(g, fmt='.2f')
    
    out_path = os.path.join(out_dir, "failure_modes_distribution.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_efficiency(df, out_dir):
    """
    Scatter plot: Latency vs EM.
    """
    plt.figure()
    agg = df.groupby(["model", "prompting_strategy"]).agg({
        "em": "mean",
        "latency_ms": "mean",
        "total_tokens": "mean"
    }).reset_index()
    
    if agg.empty:
        return

    sns.scatterplot(
        data=agg, x="latency_ms", y="em", hue="model", style="prompting_strategy",
        s=100
    )
    plt.title("Efficiency: Latency vs Accuracy")
    plt.xlabel("Average Latency (ms)")
    plt.ylabel("Average Exact Match")
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    
    out_path = os.path.join(out_dir, "efficiency_scatter.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_cost_analysis(df, out_dir):
    """
    Bar chart of Average Cost per Query by Model/Strategy.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        print("No cost data available to plot.")
        return

    plt.figure()
    df = df.copy()
    df["Config"] = df["model"] + "\n" + df["decoding"]
    
    g = sns.catplot(
        data=df, kind="bar",
        x="Config", y="cost", hue="prompting_strategy",
        errorbar=None, palette="coolwarm", alpha=.9, height=5, aspect=1.5
    )
    g.set_axis_labels("Model Configuration", "Avg Cost per Query ($)")
    g.fig.suptitle("Avg Cost Analysis", y=1.02)
    plt.xticks(rotation=45)
    annotate_bars(g, fmt='.4f')
    
    out_path = os.path.join(out_dir, "cost_analysis_avg.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def plot_total_cost(df, out_dir):
    """
    Bar chart of Total Cost by Model/Strategy.
    """
    if "cost" not in df.columns or df["cost"].sum() == 0:
        return

    plt.figure()
    df = df.copy()
    df["Config"] = df["model"] + "\n" + df["decoding"]
    
    # Sum costs
    total_costs = df.groupby(["Config", "prompting_strategy"])["cost"].sum().reset_index()

    g = sns.catplot(
        data=total_costs, kind="bar",
        x="Config", y="cost", hue="prompting_strategy",
        errorbar=None, palette="coolwarm", alpha=.9, height=5, aspect=1.5
    )
    g.set_axis_labels("Model Configuration", "Total Cost ($)")
    g.fig.suptitle("Total Experiment Cost", y=1.02)
    plt.xticks(rotation=45)
    annotate_bars(g, fmt='.2f')
    
    out_path = os.path.join(out_dir, "cost_analysis_total.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {out_path}")

def main():
    parser = argparse.ArgumentParser()
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
        
    df = pd.read_csv(csv_path)
    
    # Convert types if needed
    df["hop"] = df["hop"].astype(str)
    
    os.makedirs(os.path.join(args.out_dir, "plots"), exist_ok=True)
    plots_dir = os.path.join(args.out_dir, "plots")
    
    if args.make_plots:
        print("Generating plots...")
        set_style()
        plot_graph_variant_comparison(df, plots_dir)
        plot_accuracy_by_hop(df, plots_dir)
        plot_override_rate(df, plots_dir)
        plot_failure_modes(df, plots_dir)
        plot_efficiency(df, plots_dir)
        plot_cost_analysis(df, plots_dir)
        plot_total_cost(df, plots_dir)
    
    # Textual Analysis Report
    report_path = os.path.join(args.out_dir, "analysis_report.md")
    with open(report_path, "w") as f:
        f.write("# Experiment Analysis Report\n\n")
        
        # Overall Best
        best_model = df.groupby("model")["em"].mean().sort_values(ascending=False).head(1)
        f.write(f"## Best Performing Model\n{best_model.to_markdown()}\n\n")
        
        # Detailed Outcomes
        f.write("## Detailed Outcome Breakdown\n")
        # Pivot table of outcomes
        outcomes = df.pivot_table(
            index=["model", "graph_variant"], 
            columns="outcome", 
            aggfunc="size", 
            fill_value=0
        )
        # Add total count
        outcomes["Total"] = outcomes.sum(axis=1)
        # Calculate percentages
        outcomes_pct = outcomes.div(outcomes["Total"], axis=0).mul(100).round(2)
        f.write(outcomes_pct.to_markdown())
        f.write("\n\n")

        # Breakdown
        f.write("## Metric Summary\n")
        agg_cols = {
            "em": "mean",
            "f1": "mean",
            "latency_ms": "mean",
            "path_found": "mean"
        }
        if "cost" in df.columns:
            agg_cols["cost"] = "mean"
            
        summary = df.groupby(["model", "decoding", "graph_variant", "prompting_strategy"]).agg(agg_cols).reset_index()
        f.write(summary.to_markdown(index=False))
        
    print(f"Analysis report saved to {report_path}")

if __name__ == "__main__":
    main()
