"""
separation_checks.py

Diagnostic (not predictive) separation checks: for each candidate predictor
field, crosstab it against outcome_3cat and report whether any value of the
predictor perfectly separates (or nearly separates) the outcome categories.

This is descriptive pattern-checking on a small (n=13) hand-verified dataset,
not a statistical test - no p-values or confidence intervals are computed,
and none should be inferred from this output.

Input:  data/processed/coded_dataset_final.csv  (output of recode_variables.py)
Output: printed report to console, plus data/processed/separation_report.csv
        (one row per predictor-value x outcome cell)

Usage:
    python analysis/separation_checks.py
"""

import csv
from collections import defaultdict
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
INPUT_FILE  = PROCESSED_DIR / "coded_dataset_final.csv"
OUTPUT_FILE = PROCESSED_DIR / "separation_report.csv"
EXCLUSION_OUTPUT_FILE = PROCESSED_DIR / "exclusion_report.csv"

ID_COLUMN = "appraisal_id"
OUTCOME_COLUMN = "outcome_3cat"

# Fields to check against the outcome. Add to this list as new candidate
# predictors are coded - the script does not need to change, just this list.
CANDIDATE_PREDICTORS = [
    "uplift_applied",
    "era",
    "eag_disagreement_ord",
    "end_of_life",
]

# Fields whose relationship to outcome_3cat is partly definitional rather
# than independently predictive - i.e. the field was coded with knowledge of
# the outcome, so "perfect separation" here confirms coding consistency more
# than it reveals a causal or predictive pattern. Flagged explicitly in the
# report rather than silently presented as a finding.
CIRCULAR_PREDICTORS = {
    "uplift_applied": (
        "uplift_applied was coded FROM the outcome (e.g. 'applied_insufficient' "
        "means EoL/severity weighting was applied AND the outcome was still "
        "negative). Perfect separation against outcome_3cat is expected by "
        "construction and should not be reported as an independent finding."
    ),
}


def build_crosstab(rows, predictor_field):
    """Return {predictor_value: {outcome_value: [appraisal_ids]}}."""
    ct = defaultdict(lambda: defaultdict(list))
    for row in rows:
        ct[row[predictor_field]][row[OUTCOME_COLUMN]].append(row[ID_COLUMN])
    return ct


def check_separation(crosstab):
    """
    Return True if every predictor value maps to exactly one outcome category
    (i.e. no predictor value co-occurs with more than one outcome category).
    """
    for predictor_value, outcomes in crosstab.items():
        if len(outcomes) > 1:
            return False
    return True


def check_exclusions(crosstab, all_outcome_values):
    """
    A weaker, more common pattern than full separation: for a given predictor
    value, which outcome categories are NEVER observed alongside it?

    Distinguishes:
      - MEANINGFUL exclusion: the predictor value has >=2 observations total,
        and still never touches a particular outcome category. This is a
        real pattern worth reporting.
      - TRIVIAL exclusion: the predictor value has only 1 observation, so it
        can only ever show 1 outcome category by definition - "excluding"
        the other categories tells you nothing. Reported separately so it
        doesn't get mistaken for a finding.

    Returns a list of dicts: {predictor_value, excluded_outcome, n_obs, trivial}
    """
    results = []
    for predictor_value, outcomes in crosstab.items():
        n_obs = sum(len(ids) for ids in outcomes.values())
        observed_outcomes = set(outcomes.keys())
        excluded = all_outcome_values - observed_outcomes
        for excluded_outcome in excluded:
            results.append({
                "predictor_value": predictor_value,
                "excluded_outcome": excluded_outcome,
                "n_obs": n_obs,
                "trivial": n_obs < 3,
            })
    return results


def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: input file not found at {INPUT_FILE}")
        print("Run analysis/recode_variables.py first to produce coded_dataset_final.csv.")
        return

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No rows found in {INPUT_FILE.name}")
        return

    missing_outcome = OUTCOME_COLUMN not in rows[0]
    if missing_outcome:
        print(f"ERROR: expected outcome column '{OUTCOME_COLUMN}' not found.")
        print(f"Available columns: {list(rows[0].keys())}")
        return

    n = len(rows)
    print(f"Separation checks on n={n} appraisals\n")
    if n < 20:
        print(f"NOTE: n={n} is small. Perfect or near-perfect separation on a")
        print("sample this size is a descriptive pattern, not a statistically")
        print("significant result - no p-values or effect sizes are computed")
        print("or implied by this report.\n")

    all_outcome_values = {row[OUTCOME_COLUMN] for row in rows}

    report_rows = []
    exclusion_rows = []

    for predictor in CANDIDATE_PREDICTORS:
        if predictor not in rows[0]:
            print(f"WARNING: predictor column '{predictor}' not found in input - skipping.\n")
            continue

        crosstab = build_crosstab(rows, predictor)
        separated = check_separation(crosstab)
        exclusions = check_exclusions(crosstab, all_outcome_values)

        print(f"=== {predictor} x {OUTCOME_COLUMN} ===")
        if predictor in CIRCULAR_PREDICTORS:
            print(f"CAUTION: {CIRCULAR_PREDICTORS[predictor]}")

        for predictor_value in sorted(crosstab):
            outcomes = crosstab[predictor_value]
            outcome_summary = ", ".join(
                f"{outcome}={len(ids)}" for outcome, ids in outcomes.items()
            )
            print(f"  {predictor_value}: {outcome_summary}")
            for outcome, ids in outcomes.items():
                report_rows.append({
                    "predictor": predictor,
                    "predictor_value": predictor_value,
                    "outcome_3cat": outcome,
                    "n": len(ids),
                    "appraisal_ids": "; ".join(ids),
                    "circular_caveat": CIRCULAR_PREDICTORS.get(predictor, ""),
                })

        if separated:
            flag = " (CIRCULAR BY CONSTRUCTION - see caution above)" if predictor in CIRCULAR_PREDICTORS else " (independently informative pattern)"
            print(f"  -> PERFECT SEPARATION{flag}")
        else:
            print(f"  -> no clean separation")

        # Report exclusions - the weaker but often more realistic pattern
        meaningful = [e for e in exclusions if not e["trivial"]]
        trivial = [e for e in exclusions if e["trivial"]]

        if meaningful:
            circular_note = " (interpret with the same caution as above)" if predictor in CIRCULAR_PREDICTORS else ""
            print(f"  Meaningful exclusions{circular_note}:")
            for e in sorted(meaningful, key=lambda x: (x["predictor_value"], x["excluded_outcome"])):
                print(f"    {predictor}={e['predictor_value']!r} (n={e['n_obs']}) never co-occurs with "
                      f"outcome_3cat={e['excluded_outcome']!r}")
        if trivial:
            print(f"  ({len(trivial)} trivial exclusion(s) omitted - predictor value has only 1 "
                  f"observation, so excluding other outcomes is definitional, not informative)")

        for e in exclusions:
            exclusion_rows.append({
                "predictor": predictor,
                "predictor_value": e["predictor_value"],
                "n_obs": e["n_obs"],
                "excluded_outcome": e["excluded_outcome"],
                "trivial": e["trivial"],
                "circular_caveat": CIRCULAR_PREDICTORS.get(predictor, ""),
            })

        print()

    # Write reports
    if report_rows:
        fieldnames = ["predictor", "predictor_value", "outcome_3cat", "n", "appraisal_ids", "circular_caveat"]
        with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)
        print(f"Report written to {OUTPUT_FILE.name}")

    if exclusion_rows:
        with EXCLUSION_OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["predictor", "predictor_value", "n_obs", "excluded_outcome", "trivial", "circular_caveat"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(exclusion_rows)
        print(f"Exclusion report written to {EXCLUSION_OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
