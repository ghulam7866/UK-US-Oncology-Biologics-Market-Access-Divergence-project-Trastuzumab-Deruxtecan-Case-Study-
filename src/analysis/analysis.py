"""
Enhuertu project — descriptive logistic regression analysis of NICE TA outcomes.

IMPORTANT FRAMING:
This is an n=13 dataset with 2 minority-class (rejected) outcomes. The logistic
regression below is fitted for DESCRIPTIVE / ILLUSTRATIVE purposes only — to
formalise an observed association and to demonstrate (not just assert) why the
sample is too small to support a genuinely predictive model. See the three
diagnostics at the bottom: leave-one-out coefficient sensitivity, a formal
minimum-N / EPV calculation, and an in-sample confusion matrix labelled as
an overfitting check rather than a performance claim.

UPDATED to read the final coded_dataset_numeric.csv, apply the
comparator_is_chemo_excluded filter only when that feature is actually in
use, explicitly handle the 2 cdf_managed_access rows (outcome_binary = n/a)
by dropping them from this binary model, and report all sample sizes
dynamically (via len(df)/len(FEATURES)) rather than hardcoded, so printed
figures can't drift out of sync with the actual filtered data again.
"""

import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# ---------------------------------------------------------------------------
# 1. Data
# ---------------------------------------------------------------------------
# Paths derived from this file's location (script is in <root>/analysis/)
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs" / "figures"

# Read the final numeric dataset (output of clean_numeric_fields.py)
df_full = pd.read_csv(DATA_DIR / "coded_dataset_numeric.csv")

FEATURES = ["eag_disagreement_ord", "end_of_life"]

# Only apply the comparator_is_chemo exclusion when that feature is actually
# in use. TA632 has clean, usable data for every other feature (e.g. it's
# fully valid here for eag_disagreement_ord/end_of_life) — the exclusion
# exists because comparator_is_chemo has no single correct value for TA632,
# not because the row is bad data generally.
if "comparator_is_chemo" in FEATURES:
    df = df_full[df_full["comparator_is_chemo_excluded"] != "True"].copy()
else:
    df = df_full.copy()

# CDF-handling decision: NICE_TA704 and NICE_TA862 are cdf_managed_access
# outcomes (outcome_binary = "n/a" in source data, read as NaN by pandas).
# Decision: drop them from this binary model rather than collapse them into
# "recommended" or "rejected" — managed access is a genuinely distinct
# regulatory outcome, and forcing it into a binary would misrepresent it.
# outcome_3cat retains all three categories for any future multinomial model.
n_before_cdf_drop = len(df)
df = df[df["outcome_binary"].notna()].copy()
n_dropped_cdf = n_before_cdf_drop - len(df)
if n_dropped_cdf:
    print(f"NOTE: dropped {n_dropped_cdf} cdf_managed_access row(s) "
          f"(outcome_binary undefined) — see CDF-handling decision above.")

df["outcome_binary"] = df["outcome_binary"].astype(int)

X = df[FEATURES].values
y = df["outcome_binary"].values
ids = df["appraisal_id"].values

print("=" * 70)
print("DATA")
print("=" * 70)
print(df[["appraisal_id"] + FEATURES + ["outcome_binary"]].to_string(index=False))
print(f"\nn = {len(df)}, positive (recommended) = {y.sum()}, "
      f"negative (rejected) = {len(y) - y.sum()}")

# Flag any appraisals that share identical feature values but disagree on
# outcome — these are informative in their own right: no model, however
# sophisticated, can separate them on these features alone.
dupes = df.groupby(FEATURES)["outcome_binary"].nunique()
contradictory = dupes[dupes > 1]
if len(contradictory):
    print("\nNOTE: identical feature combinations with different outcomes found —")
    print("these cases cannot be separated by this feature set no matter what")
    print("model is used, and point to an omitted variable:")
    mask = df.set_index(FEATURES).index.isin(contradictory.index)
    print(df.loc[mask, ["appraisal_id"] + FEATURES + ["outcome_binary"]].to_string(index=False))

# ---------------------------------------------------------------------------
# 2. Full-sample logistic regression (descriptive, not predictive)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("FULL-SAMPLE LOGISTIC REGRESSION (descriptive only — see caveats below)")
print("=" * 70)

full_model = LogisticRegression(C=np.inf, max_iter=1000)
full_model.fit(X, y)

full_coefs = dict(zip(FEATURES, full_model.coef_[0]))
full_intercept = full_model.intercept_[0]

for feat, coef in full_coefs.items():
    odds_ratio = np.exp(coef)
    print(f"  {feat:25s} coef = {coef:+.3f}   odds ratio = {odds_ratio:.2f}")
print(f"  {'intercept':25s} coef = {full_intercept:+.3f}")

if any(abs(c) > 10 for c in full_coefs.values()):
    print("\n  NOTE: these coefficient magnitudes are extreme (odds ratios near 0 or in the")
    print("  tens of thousands). This is a symptom of (quasi-)complete separation — with")
    print(f"  n={len(df)} after filtering, the {len(FEATURES)} features can nearly perfectly separate the classes, which causes")
    print("  unregularised logistic regression coefficients to diverge toward +/-infinity.")
    print("  This is NOT a sign of a strong, reliable effect. It is itself further evidence")
    print("  the sample is too small: real-world effect sizes are almost never this extreme,")
    print("  and the model is fitting noise-free separation that a larger, noisier sample")
    print("  would not reproduce. Reported as a diagnostic finding, not a substantive result.")

# ---------------------------------------------------------------------------
# 3. Leave-one-out (LOO) coefficient sensitivity check
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("LEAVE-ONE-OUT COEFFICIENT SENSITIVITY")
print("=" * 70)
print(f"Refitting the model {len(df)} times, each time dropping one appraisal,")
print("to show how much the coefficients move. Large swings = instability,")
print("i.e. the coefficients are being driven by individual data points")
print("rather than a stable underlying pattern.\n")

loo_results = []
for i in range(len(df)):
    mask = np.ones(len(df), dtype=bool)
    mask[i] = False
    X_loo, y_loo = X[mask], y[mask]

    if len(np.unique(y_loo)) < 2:
        loo_results.append({
            "dropped": ids[i],
            "eag_disagreement_ord": np.nan,
            "end_of_life": np.nan,
            "note": "UNFITTABLE — dropping this row removes a class entirely"
        })
        continue

    m = LogisticRegression(C=np.inf, max_iter=1000)
    m.fit(X_loo, y_loo)
    loo_results.append({
        "dropped": ids[i],
        "eag_disagreement_ord": m.coef_[0][0],
        "end_of_life": m.coef_[0][1],
        "note": ""
    })

loo_df = pd.DataFrame(loo_results)
print(loo_df.to_string(index=False))

fittable = loo_df.dropna(subset=["eag_disagreement_ord"])
print("\nCoefficient range across fittable LOO refits:")
for feat in FEATURES:
    vals = fittable[feat]
    print(f"  {feat:25s} min={vals.min():+.3f}  max={vals.max():+.3f}  "
          f"range={vals.max()-vals.min():.3f}  (full-sample coef={full_coefs[feat]:+.3f})")

n_unfittable = loo_df["note"].str.contains("UNFITTABLE").sum()
if n_unfittable > 0:
    print(f"\n{n_unfittable} of {len(df)} LOO refits could not even be fit because dropping "
          f"that single row eliminated one class entirely.")
    print("This is itself the finding: with only 2 negative cases, removing either")
    print("one collapses the classification problem. No amount of feature")
    print("engineering fixes this — it requires more minority-class data.")
else:
    print(f"\nAll {len(df)} LOO refits were fittable (dropping any single row still leaves "
          f"at least one case in each class), so the instability shows up in the")
    print("coefficient range above instead of in outright unfittability. With only 2 negative cases,")
    print("any one data point has outsized leverage over the fit.")

# ---------------------------------------------------------------------------
# 4. Formal minimum-N / EPV calculation
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("MINIMUM SAMPLE SIZE (EVENTS-PER-VARIABLE) CALCULATION")
print("=" * 70)

n_features = len(FEATURES)
n_events_actual = int(y.sum() if y.sum() < len(y) - y.sum() else len(y) - y.sum())
epv_conservative = 10
epv_loose = 5

min_events_conservative = epv_conservative * n_features
min_events_loose = epv_loose * n_features

print(f"Features in model: {n_features} ({', '.join(FEATURES)})")
print(f"Minority-class (rejected) events currently available: {n_events_actual}")
print(f"\nStandard EPV rule of thumb: 10-20 minority-class events per predictor")
print(f"  Conservative target (10 EPV): {min_events_conservative} rejected TAs needed")
print(f"  Loose/exploratory (5 EPV):    {min_events_loose} rejected TAs needed")
print(f"\nShortfall vs conservative target: {min_events_conservative - n_events_actual} "
      f"more rejected TAs required")
print(f"Shortfall vs loose target:        {max(min_events_loose - n_events_actual, 0)} "
      f"more rejected TAs required")

base_rate_low, base_rate_high = 0.10, 0.15
for target_label, target_events in [("conservative", min_events_conservative),
                                     ("loose", min_events_loose)]:
    lo = int(np.ceil(target_events / base_rate_high))
    hi = int(np.ceil(target_events / base_rate_low))
    print(f"  Implied total dataset size ({target_label} target, "
          f"10-15% base rejection rate assumption): ~{lo}-{hi} total TAs")

# ---------------------------------------------------------------------------
# 5. In-sample confusion matrix (overfitting check, NOT a performance claim)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("IN-SAMPLE CONFUSION MATRIX (overfitting diagnostic, not a claim of accuracy)")
print("=" * 70)

y_pred = full_model.predict(X)
cm = confusion_matrix(y, y_pred)
print("Predicted vs actual (rows = actual, cols = predicted), order = [0=rejected, 1=recommended]:")
print(cm)
in_sample_acc = (y_pred == y).mean()
print(f"\nIn-sample accuracy: {in_sample_acc:.0%}")
print(f"\nInterpretation: with n={len(df)} and {len(FEATURES)} features, near-perfect in-sample fit is")
print("EXPECTED and is a diagnostic of overfitting, not evidence of a good model.")
print("This number is reported to make the overfitting visible, not to claim")
print(f"the model works. No held-out test set exists at this sample size (n={len(df)}).")

# ---------------------------------------------------------------------------
# 6. Plots
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# (a) LOO coefficient sensitivity plot
ax = axes[0]
x_pos = np.arange(len(loo_df))
width = 0.35
eag_vals = loo_df["eag_disagreement_ord"].values.astype(float)
eol_vals = loo_df["end_of_life"].values.astype(float)
ax.bar(x_pos - width/2, np.nan_to_num(eag_vals), width, label="eag_disagreement_ord", color="#c0504d")
ax.bar(x_pos + width/2, np.nan_to_num(eol_vals), width, label="end_of_life", color="#4472c4")
ax.axhline(full_coefs["eag_disagreement_ord"], color="#c0504d", linestyle="--", linewidth=1, alpha=0.7)
ax.axhline(full_coefs["end_of_life"], color="#4472c4", linestyle="--", linewidth=1, alpha=0.7)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x_pos)
ax.set_xticklabels(loo_df["dropped"], rotation=45, ha="right")
ax.set_ylabel("Coefficient value")
ax.set_title("LOO coefficient sensitivity\n(dashed = full-sample coefficient)")

# *** THE ONLY CHANGE — moved legend outside the plot to stop blocking first 5 bars ***
ax.legend(fontsize=8, loc='upper left', bbox_to_anchor=(1.02, 1))

for i, note in enumerate(loo_df["note"]):
    if "UNFITTABLE" in note:
        ax.text(i, 0, "unfittable", rotation=90, ha="center", va="bottom", fontsize=7, color="gray")

# (b) EPV shortfall bar chart
ax = axes[1]
labels = [f"Current\n(n={n_events_actual} rejected)", "Loose target\n(5 EPV)", "Conservative target\n(10 EPV)"]
values = [n_events_actual, min_events_loose, min_events_conservative]
colors = ["#c0504d", "#f2b134", "#4472c4"]
ax.bar(labels, values, color=colors)
ax.set_ylabel("Rejected (minority-class) TAs")
ax.set_title("Minority-class events: actual vs required")
for i, v in enumerate(values):
    ax.text(i, v + 0.3, str(v), ha="center", fontweight="bold")

# (c) Confusion matrix heatmap
ax = axes[2]
im = ax.imshow(cm, cmap="Blues")
ax.set_xticks([0, 1]); ax.set_xticklabels(["Rejected", "Recommended"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Rejected", "Recommended"])
ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
ax.set_title(f"In-sample confusion matrix\n(overfitting check — acc={in_sample_acc:.0%}, n={len(df)})")
for i in range(2):
    for j in range(2):
        ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                 color="white" if cm[i, j] > cm.max()/2 else "black", fontsize=14)

plt.tight_layout()
# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_DIR / "diagnostics.png", dpi=150)
print(f"\nSaved figure: {OUTPUT_DIR / 'diagnostics.png'}")
