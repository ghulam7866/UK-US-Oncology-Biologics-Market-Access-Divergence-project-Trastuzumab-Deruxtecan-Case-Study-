"""
3.2 Cross-Border Payer Resistance Analysis
Lightweight keyword/phrase-based theme extraction (not fine-tuned) applied to
NICE evaluation committee discussion documents and US cost-effectiveness
literature discussion/limitations sections, for the Enhertu (trastuzumab
deruxtecan) HER2-low breast cancer case study.

Method: regex phrase matching, case-insensitive, counted per document,
normalized to occurrences per 1,000 words to control for the large length
disparity between NICE committee discussions (~3,600-3,700 words) and US
paper discussion sections (~900-1,000 words).

CHANGE LOG:
- Comparator theme: apostrophe pattern now matches both straight (') and
  curly (\u2019) apostrophes in "physician's choice".
- Price/threshold theme: replaced bare "£\\d" / "$\\d" catch-alls with
  patterns requiring the currency figure to co-occur with threshold/WTP
  language.
- Counting method changed from summing per-pattern matches independently
  to a single combined regex pass, patterns sorted longest-first to prevent
  overlapping matches.
- Fixed truncated number match in "threshold of $X" pattern – now consumes
  the full number (including commas) to prevent a leftover digit fragment
  from being re-matched by the standalone "per QALY" pattern.
"""

import re
import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Paths: raw data is in data/raw/nlp_raw_data; outputs go to outputs/
ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "raw" / "nlp_raw data"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Document registry
# ---------------------------------------------------------------------------
DOCUMENTS = {
    "NICE_TA_HER2low_2024": {
        "path": CORPUS_DIR / "nice_ta_her2low_2024.txt",
        "market": "UK (NICE)",
        "label": "NICE TA\n(HER2-low, 2024)\nNOT recommended",
    },
    "NICE_TA_HER2positive_2022": {
        "path": CORPUS_DIR / "nice_ta_her2positive_2022.txt",
        "market": "UK (NICE)",
        "label": "NICE TA\n(HER2-positive, 2022)\nManaged access",
    },
    "US_Peng_2023": {
        "path": CORPUS_DIR / "us_peng_2023.txt",
        "market": "US (academic CEA)",
        "label": "Peng et al. 2023\n(Clin Ther)",
    },
    "US_Shi_2023": {
        "path": CORPUS_DIR / "us_shi_et_al_2023.txt",
        "market": "US (academic CEA)",
        "label": "Shi et al. 2023\n(PLOS ONE)",
    },
}

# ---------------------------------------------------------------------------
# Theme dictionary
# ---------------------------------------------------------------------------
THEMES = {
    "Immature / extrapolated survival data": [
        r"\bimmatur\w*\b",
        r"\bextrapolat\w*\b",
        r"beyond the (?:observation|follow-up|trial follow-up)",
        r"long[- ]term (?:overall )?survival",
        r"parametric (?:survival )?(?:distribution|model|function)",
        r"data (?:is|are|was|were) mature",
        r"small number of deaths",
    ],
    "Surrogate endpoint validity (PFS\u2192OS)": [
        r"surrogate",
        r"translate into (?:an? )?(?:overall survival|long[- ]term)",
        r"good surrogate for overall survival",
        r"progression-free survival.{0,40}overall survival",
    ],
    "Comparator selection / composition disputes": [
        r"\bcomparator\b",
        r"physician['\u2019]?s choice",
        r"\bTPC\b",
        r"treatment of physician choice",
        r"not fully generalisable",
        r"reflect(?:s|ed)? NHS clinical practice",
        r"standard care",
        r"(?:vs\.?|versus|compared (?:with|to)|alternative to)\s+chemotherapy",
        r"chemotherapy\s+arm",
    ],
    "Population / trial generalizability": [
        r"generalis\w*",
        r"generaliz\w*",
        r"representative",
        r"real[- ]world",
        r"trial population",
        r"clinical trial participants",
    ],
    "Utility / quality-of-life value uncertainty": [
        r"utility value",
        r"utilit(?:y|ies)\b",
        r"EQ-5D",
        r"post-progression utility",
        r"quality of life",
        r"disutilit\w*",
    ],
    "Subgroup / small sample uncertainty": [
        r"subgroup",
        r"small (?:number|sample|size)",
        r"sample size",
        r"interpreted with caution",
        r"small percentage",
    ],
    "Structural / model assumption uncertainty": [
        r"structural(?:ly)?",
        r"assumption",
        r"partitioned survival model",
        r"proportional hazard",
        r"model hypothesis",
        r"highly uncertain",
    ],
    "Price / cost-effectiveness threshold ambiguity": [
        r"willingness[- ]to[- ]pay",
        r"\bWTP\b",
        r"per QALY",
        r"cost-effective(?:ness)? use of (?:NHS )?resources",
        r"acceptable ICER",
        r"official WTP threshold",
        r"(?:£|\$)\d[\d,]*\s*(?:per QALY|threshold|WTP)",
        # FIXED: consume the full number (including commas) after "of"
        r"(?:threshold|WTP)\s+of\s+(?:£|\$)\d[\d,]*",
    ],
}

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def count_theme_hits(text: str, patterns: list[str]) -> int:
    """Count occurrences of any pattern, avoiding double-counting via a
    single combined regex pass, patterns sorted longest-first."""
    ordered = sorted(patterns, key=len, reverse=True)
    combined = "|".join(f"(?:{p})" for p in ordered)
    return len(re.findall(combined, text, flags=re.IGNORECASE))


def build_frequency_table() -> pd.DataFrame:
    rows = []
    for doc_id, meta in DOCUMENTS.items():
        text = load_text(meta["path"])
        wc = word_count(text)
        for theme, patterns in THEMES.items():
            hits = count_theme_hits(text, patterns)
            per_1000 = (hits / wc) * 1000 if wc else 0.0
            rows.append(
                {
                    "document": doc_id,
                    "label": meta["label"],
                    "market": meta["market"],
                    "theme": theme,
                    "raw_hits": hits,
                    "word_count": wc,
                    "freq_per_1000_words": round(per_1000, 2),
                }
            )
    return pd.DataFrame(rows)


def aggregate_by_market(df: pd.DataFrame) -> pd.DataFrame:
    """Combine documents within each market, re-normalized by total corpus
    word count for that market."""
    agg_rows = []
    for market in df["market"].unique():
        sub = df[df["market"] == market]
        total_words = sub.drop_duplicates("document")["word_count"].sum()
        for theme in THEMES:
            total_hits = sub[sub["theme"] == theme]["raw_hits"].sum()
            per_1000 = (total_hits / total_words) * 1000 if total_words else 0.0
            agg_rows.append(
                {
                    "market": market,
                    "theme": theme,
                    "raw_hits": total_hits,
                    "total_words": total_words,
                    "freq_per_1000_words": round(per_1000, 2),
                }
            )
    return pd.DataFrame(agg_rows)


# ---------------------------------------------------------------------------
# Visuals
# ---------------------------------------------------------------------------
UK_COLOR = "#1f4e79"
US_COLOR = "#c0504d"

def plot_main_comparison(agg: pd.DataFrame, out_path: Path) -> None:
    pivot = agg.pivot(index="theme", columns="market", values="freq_per_1000_words")
    pivot = pivot.sort_values("UK (NICE)", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    y = range(len(pivot))
    height = 0.36

    ax.barh([i + height / 2 for i in y], pivot["UK (NICE)"], height=height,
            color=UK_COLOR, label="UK (NICE)")
    ax.barh([i - height / 2 for i in y], pivot["US (academic CEA)"], height=height,
            color=US_COLOR, label="US (academic CEA)")

    ax.set_yticks(list(y))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_xlabel("Frequency (occurrences per 1,000 words)")
    ax.set_title("Cross-Border Payer Resistance Themes: NICE vs US Cost-Effectiveness Literature\nEnhertu (trastuzumab deruxtecan), HER2-low advanced breast cancer",
                 fontsize=11, loc="left")
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=False, nbins=6))
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_small_multiples(df: pd.DataFrame, out_path: Path) -> None:
    themes = list(THEMES.keys())
    n_cols = 2
    n_rows = -(-len(themes) // n_cols)

    doc_order = list(DOCUMENTS.keys())
    doc_labels = [DOCUMENTS[d]["label"].replace("\n", " ") for d in doc_order]
    colors = [UK_COLOR if DOCUMENTS[d]["market"] == "UK (NICE)" else US_COLOR for d in doc_order]

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(11, 3 * n_rows))
    axes = axes.flatten()

    for i, theme in enumerate(themes):
        ax = axes[i]
        sub = df[df["theme"] == theme].set_index("document").loc[doc_order]
        ax.bar(range(len(doc_order)), sub["freq_per_1000_words"], color=colors)
        ax.set_title(theme, fontsize=9)
        ax.set_xticks(range(len(doc_order)))
        ax.set_xticklabels(doc_labels, fontsize=6.5, rotation=20, ha="right")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.2)

    for j in range(len(themes), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle("Theme Frequency by Individual Appraisal / Paper (per 1,000 words)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    # -----------------------------------------------------------------------
    # Spot-check: Peng's Price and Subgroup themes (suspiciously identical
    # frequency earlier). Print actual matches to confirm fix.
    # -----------------------------------------------------------------------
    peng_text = load_text(DOCUMENTS["US_Peng_2023"]["path"])
    for theme_name in ["Price / cost-effectiveness threshold ambiguity",
                       "Subgroup / small sample uncertainty"]:
        patterns = THEMES[theme_name]
        ordered = sorted(patterns, key=len, reverse=True)
        combined = "|".join(f"(?:{p})" for p in ordered)
        matches = re.findall(combined, peng_text, flags=re.IGNORECASE)
        print(f"\n{theme_name}: {len(matches)} matches")
        for m in matches:
            print(f"  {m!r}")
    print()

    # -----------------------------------------------------------------------
    # Main analysis
    # -----------------------------------------------------------------------
    df = build_frequency_table()
    agg = aggregate_by_market(df)

    df.to_csv(OUTPUT_DIR / "theme_frequency_by_document.csv", index=False)
    agg.to_csv(OUTPUT_DIR / "theme_frequency_by_market.csv", index=False)

    plot_main_comparison(agg, OUTPUT_DIR / "chart_uk_vs_us_theme_comparison.png")
    plot_small_multiples(df, OUTPUT_DIR / "chart_small_multiples_by_document.png")

    print("=== Per-document theme frequency (per 1,000 words) ===")
    print(df.pivot(index="theme", columns="label", values="freq_per_1000_words").to_string())
    print()
    print("=== Aggregated UK vs US theme frequency (per 1,000 words) ===")
    print(agg.pivot(index="theme", columns="market", values="freq_per_1000_words").to_string())
    print()
    print(f"Saved outputs to {OUTPUT_DIR}")