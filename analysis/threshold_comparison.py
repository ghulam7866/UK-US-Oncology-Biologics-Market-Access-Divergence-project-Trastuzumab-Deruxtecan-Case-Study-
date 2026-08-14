"""
Component 3.4 — UK vs US cost-effectiveness threshold comparison.

Data provenance (stated explicitly, not blended):
  - UK £30,000 base threshold: from own dataset (threshold_gbp column,
    all 8-9 appraisals were assessed against this figure).
  - UK £50,000 end-of-life ceiling: legacy EoL modifier that applied to
    several appraisals in the dataset (end_of_life=1 rows); NICE's own
    stated practice pre-2023 methods update, not from a single TA row.
  - UK £25,000-35,000: NICE's revised standard threshold, effective
    April 2026 (post-dates most appraisals in the dataset — shown as a
    forward marker, not what the sampled TAs were actually judged against).
  - US $100,000-150,000: ICER's publicly stated value-assessment
    threshold range, cited externally (not from own extraction pipeline,
    since no US ICER evaluations are in the underlying dataset).

Layout: top row shows both systems in their own native currency (the
figures as actually published/used). Bottom panel shows the same four
ranges converted to a single common currency (USD) purely for visual
scale comparison — both versions are kept, rather than collapsing to
just one, since native currency is what's operationally meaningful and
normalized currency is what's visually comparable.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

UK_COLOR = "#1f4e79"      # dark blue — UK/NICE
US_COLOR = "#c0504d"      # brick red — US/ICER
UK_LIGHT = "#8faec9"

GBP_TO_USD = 1.33  # checked at time of writing, not live — flagged in footnote

def make_plot():
    fig = plt.figure(figsize=(15.5, 9.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.8], hspace=0.55, wspace=0.4)
    ax_uk = fig.add_subplot(gs[0, 0])
    ax_us = fig.add_subplot(gs[0, 1])
    ax_norm = fig.add_subplot(gs[1, :])

    # ---------------------------------------------------------------------
    # Row 1, left: UK panel (native £)
    # ---------------------------------------------------------------------
    uk_rows = [
        ("NICE standard\n(threshold at time\nof appraisals in dataset)", 20000, 30000, UK_COLOR, False),
        ("NICE end-of-life\nmodifier ceiling\n(legacy, pre-2023 methods)", 20000, 50000, UK_LIGHT, False),
        ("NICE standard\n(revised, from Apr 2026)", 25000, 35000, UK_COLOR, True),
    ]

    for i, (label, lo, hi, color, is_new) in enumerate(uk_rows):
        if is_new:
            ax_uk.plot([lo, hi], [i, i], color=color, linewidth=8, solid_capstyle="round",
                       alpha=0.25, zorder=2)
            ax_uk.plot([lo, hi], [i, i], color=color, linewidth=1.5, solid_capstyle="round",
                       alpha=0.9, zorder=3)
        else:
            ax_uk.plot([lo, hi], [i, i], color=color, linewidth=8, solid_capstyle="round",
                       alpha=1.0, zorder=2)
        for x in (lo, hi):
            ax_uk.plot(x, i, "o", color=color, markersize=9,
                       markeredgecolor="white" if not is_new else color,
                       markeredgewidth=2 if is_new else 1.5,
                       fillstyle="none" if is_new else "full", zorder=4)
        ax_uk.text(hi + 2000, i, f"£{lo:,.0f}\u2013£{hi:,.0f}" + (" *" if is_new else ""),
                   va="center", fontsize=9.5, color="#333333")

    ax_uk.set_yticks(range(len(uk_rows)))
    ax_uk.set_yticklabels([r[0] for r in uk_rows], fontsize=9)
    ax_uk.set_xlabel("£ per QALY gained", fontsize=10)
    ax_uk.set_title("UK — NICE (native currency)", fontsize=12, fontweight="bold", color=UK_COLOR, pad=10)
    ax_uk.set_xlim(0, 78000)
    ax_uk.set_ylim(-0.7, 2.7)
    ax_uk.spines[["top", "right", "left"]].set_visible(False)
    ax_uk.grid(axis="x", linestyle=":", linewidth=0.6, alpha=0.4)
    ax_uk.tick_params(axis="y", length=0)

    # ---------------------------------------------------------------------
    # Row 1, right: US panel (native $)
    # ---------------------------------------------------------------------
    us_lo, us_hi = 100000, 150000
    ax_us.plot([us_lo, us_hi], [0, 0], color=US_COLOR, linewidth=8, solid_capstyle="round", zorder=3)
    for x in (us_lo, us_hi):
        ax_us.plot(x, 0, "o", color=US_COLOR, markersize=9,
                   markeredgecolor="white", markeredgewidth=1.5, zorder=4)
    ax_us.text(us_hi + 6000, 0, f"${us_lo:,.0f}\u2013${us_hi:,.0f}", va="center",
               fontsize=9.5, color="#333333")

    ax_us.set_yticks([0])
    ax_us.set_yticklabels(["ICER value-assessment\nthreshold range\n(standing policy figure)"], fontsize=9)
    ax_us.set_xlabel("$ per QALY gained", fontsize=10)
    ax_us.set_title("US — ICER (native currency)", fontsize=12, fontweight="bold", color=US_COLOR, pad=10)
    ax_us.set_xlim(0, 260000)
    ax_us.set_ylim(-0.7, 2.7)
    ax_us.spines[["top", "right", "left"]].set_visible(False)
    ax_us.grid(axis="x", linestyle=":", linewidth=0.6, alpha=0.4)
    ax_us.tick_params(axis="y", length=0)

    # ---------------------------------------------------------------------
    # Row 2: normalized comparison panel (all four ranges converted to USD)
    # ---------------------------------------------------------------------
    norm_rows = [
        ("NICE standard (at time of dataset)", 20000 * GBP_TO_USD, 30000 * GBP_TO_USD, UK_COLOR, False),
        ("NICE end-of-life ceiling (legacy)", 20000 * GBP_TO_USD, 50000 * GBP_TO_USD, UK_LIGHT, False),
        ("NICE standard (revised, Apr 2026)", 25000 * GBP_TO_USD, 35000 * GBP_TO_USD, UK_COLOR, True),
        ("ICER value-assessment range", us_lo, us_hi, US_COLOR, False),
    ]

    for i, (label, lo, hi, color, is_new) in enumerate(norm_rows):
        if is_new:
            ax_norm.plot([lo, hi], [i, i], color=color, linewidth=8, solid_capstyle="round", alpha=0.25, zorder=2)
            ax_norm.plot([lo, hi], [i, i], color=color, linewidth=1.5, solid_capstyle="round", alpha=0.9, zorder=3)
        else:
            ax_norm.plot([lo, hi], [i, i], color=color, linewidth=8, solid_capstyle="round", zorder=2)
        for x in (lo, hi):
            ax_norm.plot(x, i, "o", color=color, markersize=9,
                         markeredgecolor="white" if not is_new else color,
                         markeredgewidth=2 if is_new else 1.5,
                         fillstyle="none" if is_new else "full", zorder=4)
        ax_norm.text(hi + 4000, i, f"${lo:,.0f}\u2013${hi:,.0f}" + (" *" if is_new else ""),
                     va="center", fontsize=9.5, color="#333333")

    ax_norm.set_yticks(range(len(norm_rows)))
    ax_norm.set_yticklabels([r[0] for r in norm_rows], fontsize=9.5)
    ax_norm.set_xlabel("$ per QALY gained (UK figures converted at ~1.33 GBP/USD)", fontsize=10)
    ax_norm.set_title("Currency-normalized comparison — all four ranges in USD", fontsize=12, fontweight="bold", pad=10)
    ax_norm.set_xlim(0, 260000)
    ax_norm.set_ylim(-0.7, 3.7)
    ax_norm.spines[["top", "right", "left"]].set_visible(False)
    ax_norm.grid(axis="x", linestyle=":", linewidth=0.6, alpha=0.4)
    ax_norm.tick_params(axis="y", length=0)

    # ---------------------------------------------------------------------
    # Title, legend, footnote — laid out with dedicated space so nothing overlaps
    # ---------------------------------------------------------------------
    fig.suptitle("Cost-effectiveness thresholds: UK (NICE) vs US (ICER)",
                 fontsize=15, fontweight="bold", y=0.995)
    fig.text(0.5, 0.945,
             "Even after NICE's 2026 revision and FX conversion, the UK threshold remains roughly 2\u20135x more conservative than the US floor",
             ha="center", fontsize=10.5, color="#555555", style="italic")

    legend_elements = [
        mpatches.Patch(color=UK_COLOR, label="Threshold at time appraisals in dataset were assessed"),
        mpatches.Patch(color=UK_LIGHT, label="Legacy end-of-life ceiling (pre-2023 methods)"),
        mpatches.Patch(color=UK_COLOR, alpha=0.3, label="* Revised threshold, effective Apr 2026 (post-dates dataset)"),
        mpatches.Patch(color=US_COLOR, label="ICER value-assessment threshold"),
    ]
    # Legend gets its own horizontal strip between the panels and the footnote,
    # rather than floating over either — avoids the overlap from the previous version.
    fig.legend(handles=legend_elements, loc="lower center", ncol=2, fontsize=8.5,
               frameon=False, bbox_to_anchor=(0.5, 0.06))

    fig.text(0.5, 0.015,
             "Source: UK figures from own NICE TA dataset (threshold_gbp field, n=8-9 appraisals) and NICE published methods guidance.\n"
             "US figure cited externally from ICER's published value-assessment framework (no US ICER evaluations are in the underlying\n"
             "dataset). Normalized panel uses a GBP/USD rate of ~1.33, checked at time of writing (not live) — for illustrative scale\n"
             "comparison only; native-currency figures above remain the operationally meaningful ones for each system.",
             ha="center", fontsize=7.5, color="#777777")

    # Reserve fixed space at the bottom for legend + footnote instead of tight_layout,
    # which was compressing that space and causing the overlap.
    fig.subplots_adjust(top=0.87, bottom=0.16, left=0.20, right=0.90)
    return fig


if __name__ == "__main__":
    fig = make_plot()
    OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "figures"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / "threshold_comparison.png", dpi=180)
    print(f"Saved threshold_comparison.png to {OUTPUT_DIR}")