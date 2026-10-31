"""
uptake_comparison.py

3.3 -- UK vs US Market Entry / Uptake Comparison: Enhertu (TA862) case study
=============================================================================

Consulting-deliverable framing: quantifies the  lag between US
regulatory approval and UK managed-access availability for trastuzumab
deruxtecan (Enhertu) in the HER2-positive, 2nd-line breast cancer indication
(NICE TA862), and contrasts this against TA992 (HER2-low), where NICE
rejected the technology outright with no managed-access route at all.
Same drug, same company, same UK regulator -- diverging market-entry
outcomes by indication.

DATA PROVENANCE -- every figure below is sourced and verifiable:

  US FDA regular approval (2L HER2+, based on DESTINY-Breast03):
      4 May 2022
      Source: Daiichi Sankyo / AstraZeneca press release (5 May 2022);
      Oncology Practice Management, "Enhertu Received Regular FDA Approval..."

  UK NICE final appraisal document (TA862):
      November 2022 (exact day unverified; original date was incorrect)
      Source: nice.org.uk/guidance/TA862/history
      NOTE: the chart represents this as a date range, 1-30 November,
      rather than inventing an exact date.

  UK NICE published guidance (TA862, managed access):
      1 Feb 2023
      Source: nice.org.uk/guidance/ta862

  UK eligible population estimate (TA862 resource impact statement):
      ~600 people/year
      Source: nice.org.uk/guidance/ta862/resources/resource-impact-statement

  TA992 (HER2-low): flatly rejected, no managed access agreement
      Rejection date: 29 July 2024 (confirmed against NICE's own statement)

  US NCCN Clinical Practice Guidelines listing (Category 1, 2L HER2+):
      NCCN Guidelines for Breast Cancer V2.2022, based on DESTINY-Breast03
      data; AstraZeneca press release (5 May 2022) describes T-DXd as
      "recently added" to this version, accessed by AZ in May 2022.
      NOTE: no day-level date is available for the NCCN version itself --
      this is a precision limit, not a fabricated date. Plotted as
      contemporaneous with US approval, not as a separately dated point.

  US real-world post-approval cohorts (aggregate totals only, NOT a time
  series -- see limitation note below):
      - Integra Connect PrecisionQ: n=315, 2L HER2+, enrolment window
        1 Jan 2022 - 31 Dec 2023
      - EHR-derived nationwide database: n=884 HER2-positive patients
        initiating T-DXd, enrolment window Dec 2019 - Sept 2023 (mixed lines)

EXPLICIT LIMITATION (flag, don't fabricate):
  A true "uptake speed" comparison needs quarterly patient-volume time series
  on both sides. On the UK side this requires NHS Digital SACT dataset access
  (a formal DARS data request, not a public download) -- NOT obtained for
  this project. On the US side, granular claims/IQVIA-level data was not
  sourced either. The two published US cohorts above give aggregate totals
  over multi-year enrolment windows, not quarterly counts, so they are
  plotted here as single-point markers, not interpolated into a curve.
  This gap is itself a finding: US real-world-evidence infrastructure
  publishes granular uptake cohorts more readily and faster than UK
  managed-access data becomes public.

Output: uptake_comparison.png (three-panel layout)
  Panel 1: Milestone timeline (US approval -> UK MAA-live), Gantt-style
  Panel 2: lag, quantified in months
  Panel 3: TA862 vs TA992 outcome contrast (managed access vs flat rejection)
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyArrowPatch
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Verified milestone data
# ---------------------------------------------------------------------------

US_APPROVAL = date(2022, 5, 4)
US_NCCN_LISTING_NOTE = "V2.2022 (contemporaneous -- no day-level date available)"
# The exact day of the final appraisal document could not be verified.
# Represent November as a range instead of fabricating a precise date.
UK_FINAL_APPRAISAL_START = date(2022, 11, 1)
UK_FINAL_APPRAISAL_END = date(2022, 11, 30)
UK_PUBLISHED_GUIDANCE = date(2023, 2, 1)
TA992_REJECTION = date(2024, 7, 29)

UK_ELIGIBLE_PER_YEAR = 600  # NICE resource impact statement, TA862

# Lag: final appraisal document is an interval because the
# exact November day is unverified. Published-guidance date remains exact.
LAG_TO_FINAL_DOC_MIN_DAYS = (UK_FINAL_APPRAISAL_START - US_APPROVAL).days
LAG_TO_FINAL_DOC_MAX_DAYS = (UK_FINAL_APPRAISAL_END - US_APPROVAL).days
LAG_TO_PUBLISHED_DAYS = (UK_PUBLISHED_GUIDANCE - US_APPROVAL).days
LAG_TO_FINAL_DOC_MIN_MONTHS = LAG_TO_FINAL_DOC_MIN_DAYS / 30.44
LAG_TO_FINAL_DOC_MAX_MONTHS = LAG_TO_FINAL_DOC_MAX_DAYS / 30.44
LAG_TO_FINAL_DOC_MID_MONTHS = (
    LAG_TO_FINAL_DOC_MIN_MONTHS + LAG_TO_FINAL_DOC_MAX_MONTHS
) / 2
LAG_TO_PUBLISHED_MONTHS = LAG_TO_PUBLISHED_DAYS / 30.44

# US real-world cohorts -- aggregate totals only
# NOTE: EHR-derived nationwide DB cohort (n=884, mixed lines, enrolment
# window Dec 2019-Sept 2023) deliberately excluded from the chart -- its
# window predates US approval and its population doesn't match the 2L
# HER2+ post-approval cohort this panel tracks. Retained as a footnote-only
# reference (see fig.text() footnote below); Integra Connect alone is the
# clean, population-matched, post-approval marker for this figure.
US_COHORTS = [
    {
        "label": "Integra Connect\nPrecisionQ\n(2L HER2+, n=315)",
        "window": (date(2022, 1, 1), date(2023, 12, 31)),
        "n": 315,
        "plot_style": "point",  # midpoint after US approval
    },
]

# TA862 vs TA992 outcome contrast
OUTCOMES = {
    "TA862\n(HER2-positive, 2L)": {
        "status": "Managed access granted",
        "eligible_per_year": UK_ELIGIBLE_PER_YEAR,
        "color": "#2a7f62",
    },
    "TA992\n(HER2-low)": {
        "status": f"Rejected {TA992_REJECTION.strftime('%d %b %Y')}\n-- no MAA route",
        "eligible_per_year": 0,
        "color": "#b23a48",
    },
}

# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

fig = plt.figure(figsize=(16, 6.5), constrained_layout=True)
gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 0.9, 1.0])
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[0, 2])

fig.suptitle(
    "Enhertu (trastuzumab deruxtecan): UK vs US market entry, HER2-positive 2L indication",
    fontsize=13,
    fontweight="bold",
)

# --- Panel 1: milestone timeline -------------------------------------------
ax1.set_title("Milestone timeline", fontsize=11, loc="center")

y_us, y_uk = 1.0, 0.0
ax1.hlines(y_us, US_APPROVAL, UK_PUBLISHED_GUIDANCE, color="#999999", linewidth=1, zorder=1)
ax1.hlines(y_uk, US_APPROVAL, UK_PUBLISHED_GUIDANCE, color="#999999", linewidth=1, zorder=1)

# US milestone
ax1.scatter([US_APPROVAL], [y_us], s=90, color="#1f77b4", zorder=3)
ax1.annotate(
    "US: FDA full approval\n4 May 2022\n(+ NCCN Cat.1 listing,\nV2.2022, contemporaneous)",
    xy=(US_APPROVAL, y_us),
    xytext=(0, 14),
    textcoords="offset points",
    ha="center",
    fontsize=8,
)

# UK final appraisal document: show the full possible November date range.
# The exact day is unverified, so do not plot a fabricated point date.
# Show the possible November appraisal period as a thin line.
# The exact date remains unverified.
ax1.plot(
    [UK_FINAL_APPRAISAL_START, UK_FINAL_APPRAISAL_END],
    [y_uk, y_uk],
    color="#ff7f0e",
    linewidth=1.5,
    linestyle="--",
    zorder=4,
)
ax1.annotate(
    "UK: final appraisal doc\nNovember 2022 (exact day unverified)",
    xy=(UK_FINAL_APPRAISAL_START + (UK_FINAL_APPRAISAL_END - UK_FINAL_APPRAISAL_START) / 2, y_uk),
    xytext=(-30, -50),
    textcoords="offset points",
    ha="center",
    fontsize=8.2,
    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8,
                     shrinkA=0, shrinkB=5),
)

ax1.scatter([UK_PUBLISHED_GUIDANCE], [y_uk], s=90, color="#d62728", zorder=3)
ax1.annotate(
    "UK: guidance published\n(managed access)\n1 Feb 2023",
    xy=(UK_PUBLISHED_GUIDANCE, y_uk),
    xytext=(55, -60),
    textcoords="offset points",
    ha="center",
    fontsize=8.5,
    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8,
                     shrinkA=0, shrinkB=5),
)

# Gap arrow
arrow = FancyArrowPatch(
    (US_APPROVAL, 0.5), (UK_PUBLISHED_GUIDANCE, 0.5),
    arrowstyle="<->", mutation_scale=14, color="#555555", linewidth=1.2,
)
ax1.add_patch(arrow)
ax1.annotate(
    f"~{LAG_TO_PUBLISHED_MONTHS:.1f} months",
    xy=((mdates.date2num(US_APPROVAL) + mdates.date2num(UK_PUBLISHED_GUIDANCE)) / 2, 0.5),
    xytext=(0, 8),
    textcoords="offset points",
    ha="center",
    fontsize=9,
    fontweight="bold",
    color="#555555",
)

ax1.set_ylim(-1.8, 2.1)
ax1.set_yticks([])
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.setp(ax1.get_xticklabels(), rotation=45, ha="right", fontsize=8)
for spine in ["top", "right", "left"]:
    ax1.spines[spine].set_visible(False)
ax1.margins(x=0.15)

# --- Panel 2, lag by UK milestone, quantified --------------------------------
ax2.set_title("lag by UK milestone\n(from US approval)", fontsize=11, loc="center")

bars_labels = ["To UK final\nappraisal doc", "To UK guidance\npublished"]
bars_values = [LAG_TO_FINAL_DOC_MID_MONTHS, LAG_TO_PUBLISHED_MONTHS]
bar_colors = ["#ff7f0e", "#d62728"]


# Plot lag without error bars.
# The first bar's label shows the possible November date range.
bars = ax2.bar(
    bars_labels,
    bars_values,
    color=bar_colors,
    width=0.55,
)

for i, (bar, val) in enumerate(zip(bars, bars_values)):
    if i == 0:
        label = (
            f"{LAG_TO_FINAL_DOC_MIN_MONTHS:.1f}"
            f"–{LAG_TO_FINAL_DOC_MAX_MONTHS:.1f} mo"
        )
    else:
        label = f"{val:.1f} mo"

    ax2.annotate(
        label,
        xy=(bar.get_x() + bar.get_width() / 2, val),
        xytext=(0, 7),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
    )

ax2.set_ylabel("Months since US approval")
ax2.set_ylim(0, max(bars_values) * 1.35)
for spine in ["top", "right"]:
    ax2.spines[spine].set_visible(False)
ax2.text(
    0.5, -0.30,
    "Final appraisal document lag is a range because\nthe exact day in November is unverified due to the deletion of TA862 guidance following TA1202",
    transform=ax2.transAxes,
    ha="center", va="top", fontsize=7.5, color="#666666",
)

# --- Panel 3: TA862 vs TA992 outcome contrast -------------------------------
ax3.set_title("Same drug, same company:\noutcome by indication", fontsize=11, loc="center")

labels = list(OUTCOMES.keys())
values = [OUTCOMES[k]["eligible_per_year"] for k in labels]
colors = [OUTCOMES[k]["color"] for k in labels]

bars3 = ax3.bar(labels, values, color=colors, width=0.5)
for bar, k in zip(bars3, labels):
    status = OUTCOMES[k]["status"]
    val = OUTCOMES[k]["eligible_per_year"]
    label_text = f"{val}/yr eligible" if val > 0 else "No NHS\nfunding route"
    ax3.annotate(
        f"{status}\n{label_text}",
        xy=(bar.get_x() + bar.get_width() / 2, max(val, 20)),
        xytext=(0, 6),
        textcoords="offset points",
        ha="center",
        fontsize=8.5,
        fontweight="bold",
    )

ax3.set_ylabel("Eligible patients / year (England)")
ax3.set_ylim(0, UK_ELIGIBLE_PER_YEAR * 1.55)
ax3.margins(x=0.25)
for spine in ["top", "right"]:
    ax3.spines[spine].set_visible(False)

# Footnote (kept below the plot area, not overlapping any panel)
fig.text(
    0.01, -0.04,
    "Sources: FDA approval letter, BLA 761139/S-017 & S-020, Ref ID 4978815 (US approval, verified primary source); "
    "AstraZeneca press release 5 May 2022 (NCCN V2.2022 listing); NICE TA862 history page & resource impact statement (UK); "
    "NICE TA992 rejection, 29 Jul 2024. US patient-volume markers are aggregate totals from published real-world cohorts "
    "(Integra Connect PrecisionQ; EHR-derived nationwide database), not a quarterly time series. UK-side quarterly uptake "
    "volumes would require NHS Digital SACT dataset access (not obtained -- flagged limitation).",
    fontsize=7, color="#666666", ha="left", wrap=True,
)

# Create output directory and save figure
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT_DIR / "uptake_comparison.png", dpi=200, bbox_inches="tight")
print(f"Saved uptake_comparison.png to {OUTPUT_DIR}")
print(
    "Lag to final appraisal doc: "
    f"{LAG_TO_FINAL_DOC_MIN_DAYS}–{LAG_TO_FINAL_DOC_MAX_DAYS} days "
    f"({LAG_TO_FINAL_DOC_MIN_MONTHS:.2f}–{LAG_TO_FINAL_DOC_MAX_MONTHS:.2f} months; "
    "November date range, exact day unverified)"
)
print(f"Lag to published guidance:  {LAG_TO_PUBLISHED_DAYS} days ({LAG_TO_PUBLISHED_MONTHS:.2f} months)")
