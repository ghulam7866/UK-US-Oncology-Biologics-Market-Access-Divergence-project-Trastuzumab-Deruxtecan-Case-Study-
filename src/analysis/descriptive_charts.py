"""
descriptive_charts.py

Descriptive (non-model) visualizations derived directly from the coded
dataset - no regression fitting involved. Kept deliberately separate from
analysis.py, which owns the modeling pipeline and its own diagnostic
outputs (diagnostics.png: LOO, EPV, confusion matrix). These charts only
need the crosstabs of coded_dataset_numeric.csv, so bundling them into
analysis.py would couple simple reporting output to the modeling pipeline
for no reason.

This is the intended home for future descriptive/exploratory charts as
the project grows (i.e. anything that summarizes the dataset itself
rather than a fitted model).

Charts produced:
  1. eag_separation_chart  - outcome_3cat by eag_disagreement_ord (stacked
     bar), with n per EAG level labelled on the x-axis. Visualizes the
     eag_disagreement_ord finding: EAG=0 excludes not_recommended/CDF,
     EAG=2 excludes recommended, EAG=1 excludes not_recommended.
  2. icer_completeness_chart - count of rows by icer_base_gbp_type
     (horizontal bar). Visualizes that only single_value/approx/
     averaged_range rows (5/13) carry a usable single-point ICER; the
     rest are confidential, not_disclosed, lower_bound_only, or
     multi_value by nature of the source documents, not a data gap.

Both charts compute counts dynamically from the input CSV rather than
hardcoding them, so they stay correct if the dataset is re-verified.

Input:  data/processed/coded_dataset_numeric.csv
Output: outputs/figures/eag_separation_chart.png
        outputs/figures/icer_completeness_chart.png

Usage:
    python analysis/descriptive_charts.py
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
INPUT_FILE = PROCESSED_DIR / "coded_dataset_numeric.csv"

# NOTE: adjust FIGURES_DIR if your project uses a different output
# convention than outputs/figures/ - not verified against the existing
# uptake_comparison.py / dumbbell chart output paths.
FIGURES_DIR = Path(__file__).resolve().parents[2] / "outputs" / "figures"

# Fixed size of the verified training dataset (n=13). This number should be
# updated only if the dataset is re-verified and expanded.
DATASET_SIZE = 13

EAG_ORDER = ["0", "1", "2"]
OUTCOME_ORDER = ["recommended", "cdf_managed_access", "not_recommended"]
OUTCOME_COLORS = {
    "recommended": "#2a78d6",
    "cdf_managed_access": "#eb6834",
    "not_recommended": "#e34948",
}
OUTCOME_LABELS = {
    "recommended": "Recommended",
    "cdf_managed_access": "CDF managed access",
    "not_recommended": "Not recommended",
}

ICER_TYPE_ORDER = [
    "confidential",
    "lower_bound_only",
    "averaged_range",
    "single_value",
    "multi_value",
    "not_disclosed",
    "approx",
]
ICER_TYPE_LABELS = {
    "confidential": "Confidential",
    "lower_bound_only": "Lower bound only",
    "averaged_range": "Averaged range",
    "single_value": "Single value",
    "multi_value": "Multi value",
    "not_disclosed": "Not disclosed",
    "approx": "Approx",
}


def load_rows():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found at {INPUT_FILE}. "
            "Run analysis/clean_numeric_fields.py first."
        )
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_eag_separation_chart(rows, out_path):
    # counts[eag_level][outcome] = n
    counts = defaultdict(lambda: defaultdict(int))
    for row in rows:
        eag = row["eag_disagreement_ord"]
        outcome = row["outcome_3cat"]
        counts[eag][outcome] += 1

    n_per_eag = {eag: sum(counts[eag].values()) for eag in EAG_ORDER}
    x_labels = [f"EAG {eag} (n={n_per_eag.get(eag, 0)})" for eag in EAG_ORDER]

    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = [0] * len(EAG_ORDER)
    for outcome in OUTCOME_ORDER:
        values = [counts[eag].get(outcome, 0) for eag in EAG_ORDER]
        ax.bar(
            x_labels,
            values,
            bottom=bottom,
            label=OUTCOME_LABELS[outcome],
            color=OUTCOME_COLORS[outcome],
        )
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_ylabel("Number of appraisals")
    ax.set_title(f"Outcome by EAG disagreement level (n={DATASET_SIZE})")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def make_icer_completeness_chart(rows, out_path):
    type_counts = Counter(row["icer_base_gbp_type"] for row in rows)
    missing_types = set(type_counts) - set(ICER_TYPE_ORDER)
    if missing_types:
        print(f"WARNING: icer_base_gbp_type values not in ICER_TYPE_ORDER: {missing_types}")

    labels = [ICER_TYPE_LABELS[t] for t in ICER_TYPE_ORDER]
    values = [type_counts.get(t, 0) for t in ICER_TYPE_ORDER]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(labels, values, color="#2a78d6")
    ax.invert_yaxis()
    ax.set_xlabel("Number of appraisals")
    ax.set_title(f"ICER base case data type (n={DATASET_SIZE})")
    ax.set_xticks(range(0, max(values) + 2))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    rows = load_rows()
    if not rows:
        print(f"No rows found in {INPUT_FILE.name}")
        return

    # Optional sanity check: if actual number of rows differs from DATASET_SIZE,
    # warn but do not fail (the charts may still be useful).
    if len(rows) != DATASET_SIZE:
        print(f"WARNING: input contains {len(rows)} rows, but DATASET_SIZE is "
              f"set to {DATASET_SIZE}. Chart titles will show n={DATASET_SIZE} — "
              "update DATASET_SIZE if the dataset has changed.")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    eag_out = FIGURES_DIR / "eag_separation_chart.png"
    icer_out = FIGURES_DIR / "icer_completeness_chart.png"

    make_eag_separation_chart(rows, eag_out)
    make_icer_completeness_chart(rows, icer_out)

    n_usable_icer = sum(1 for r in rows if r["icer_base_gbp_numeric"] != "")
    print(f"Charts written to {FIGURES_DIR}")
    print(f"  {eag_out.name}")
    print(f"  {icer_out.name}")
    print(f"\nNOTE: {n_usable_icer}/{len(rows)} rows have a usable single-point ICER estimate;")
    print("the rest are confidential/not_disclosed/lower_bound_only/multi_value by")
    print("nature of the source documents. See icer_completeness_chart.png.")


if __name__ == "__main__":
    main()
