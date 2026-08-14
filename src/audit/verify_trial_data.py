"""
verify_trial_data.py

Cross-checks the already-fetched ClinicalTrials.gov raw JSON snapshots
(data/raw/{NCT_ID}_raw.json) against independently sourced reference
values, and inspects the completion-date fields to explain why a trial
still shows ACTIVE_NOT_RECRUITING years after its primary results were
published.

This does NOT hit any API -- it only reads the raw JSON files you've
already saved locally from clinicaltrials_pull.py.

Usage:
    python verify_trial_data.py
"""

import json
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# ---------------------------------------------------------------------------
# Reference values -- sourced independently, NOT from CT.gov itself.
# Each entry records the value, the source, and why it's trustworthy.
# ---------------------------------------------------------------------------

REFERENCE = {
    "NCT03529110": {  # DESTINY-Breast03
        "label": "DESTINY-Breast03 (HER2+, 2L -- TA862 anchor trial)",
        "expected_enrollment": 524,
        "source": (
            "Cortes J, et al. Trastuzumab Deruxtecan versus Trastuzumab "
            "Emtansine for Breast Cancer. N Engl J Med 2022;386:1143-1154 "
            "(PubMed abstract: 'Among 524 randomly assigned patients...')"
        ),
    },
    "NCT03734029": {  # DESTINY-Breast04
        "label": "DESTINY-Breast04 (HER2-low -- TA992 side)",
        "expected_enrollment": 557,
        "source": (
            "Modi S, Jacot W, Yamashita T, et al. Trastuzumab deruxtecan "
            "in previously treated HER2-low advanced breast cancer. "
            "N Engl J Med. 2022;387(1):9-20. (corroborated by ASCO Post "
            "and MSKCC meeting coverage, June 2022)"
        ),
    },
}


def load_raw(nct_id: str) -> dict:
    path = RAW_DIR / f"{nct_id}_raw.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No raw snapshot found for {nct_id} at {path} -- "
            f"run clinicaltrials_pull.py first."
        )
    return json.loads(path.read_text())


def check_enrollment(nct_id: str, data: dict) -> dict:
    """Compare CT.gov's registered enrollment count against the
    independently sourced reference value."""
    protocol = data.get("protocolSection", {})
    design = protocol.get("designModule", {})
    enrollment = design.get("enrollmentInfo", {})

    ctgov_count = enrollment.get("count")
    ctgov_type = enrollment.get("type")
    ref = REFERENCE[nct_id]

    match = ctgov_count == ref["expected_enrollment"]

    return {
        "nct_id": nct_id,
        "label": ref["label"],
        "ctgov_enrollment": ctgov_count,
        "ctgov_enrollment_type": ctgov_type,
        "reference_enrollment": ref["expected_enrollment"],
        "match": match,
        "reference_source": ref["source"],
    }


def check_status_explanation(nct_id: str, data: dict) -> dict:
    """Inspect primaryCompletionDate vs completionDate to see whether
    ACTIVE_NOT_RECRUITING is explained by an open long-term follow-up
    (primary completion long past, overall completion still pending)
    rather than asserting this from general knowledge."""
    protocol = data.get("protocolSection", {})
    status_module = protocol.get("statusModule", {})

    overall_status = status_module.get("overallStatus")
    primary_completion = status_module.get("primaryCompletionDateStruct", {})
    completion = status_module.get("completionDateStruct", {})

    primary_date = primary_completion.get("date")
    overall_date = completion.get("date")

    explanation = "UNVERIFIED -- inspect manually"
    if overall_status == "ACTIVE_NOT_RECRUITING" and primary_date and overall_date:
        if overall_date > primary_date:
            explanation = (
                f"CONSISTENT with long-term follow-up: primary completion "
                f"({primary_date}) precedes overall completion ({overall_date}), "
                f"so OS follow-up is plausibly still open."
            )
        else:
            explanation = (
                f"INCONSISTENT -- primary ({primary_date}) and overall "
                f"({overall_date}) completion dates don't support the "
                f"follow-up explanation. Flag for manual review."
            )

    return {
        "nct_id": nct_id,
        "overall_status": overall_status,
        "primary_completion_date": primary_date,
        "overall_completion_date": overall_date,
        "explanation": explanation,
    }


def main():
    print("=" * 70)
    print("ENROLLMENT VERIFICATION")
    print("=" * 70)
    for nct_id in REFERENCE:
        data = load_raw(nct_id)
        result = check_enrollment(nct_id, data)
        status = "MATCH" if result["match"] else "MISMATCH -- investigate"
        print(f"\n{result['label']} ({nct_id})")
        print(f"  CT.gov enrollment:   {result['ctgov_enrollment']} "
              f"({result['ctgov_enrollment_type']})")
        print(f"  Reference enrollment: {result['reference_enrollment']}")
        print(f"  Status: {status}")
        print(f"  Source: {result['reference_source']}")

    print("\n" + "=" * 70)
    print("STATUS EXPLANATION CHECK (ACTIVE_NOT_RECRUITING)")
    print("=" * 70)
    for nct_id in REFERENCE:
        data = load_raw(nct_id)
        result = check_status_explanation(nct_id, data)
        print(f"\n{REFERENCE[nct_id]['label']} ({nct_id})")
        print(f"  Overall status: {result['overall_status']}")
        print(f"  Primary completion date: {result['primary_completion_date']}")
        print(f"  Overall completion date: {result['overall_completion_date']}")
        print(f"  {result['explanation']}")


if __name__ == "__main__":
    main()
