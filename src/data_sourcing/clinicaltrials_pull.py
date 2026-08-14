"""
Pulls DESTINY-Breast04 (NCT03734029) trial data from the ClinicalTrials.gov
API v2, extracts the fields needed for the HTA outcome/discount model,
and writes both a raw JSON snapshot and a flat processed CSV row.

API docs: https://clinicaltrials.gov/data-api/api
No API key required.

Usage:
    python clinicaltrials_pull.py
"""

import json
import requests
from pathlib import Path

NCT_IDS = [
    "NCT03529110",  # DESTINY-Breast03 (HER2+, 2L — TA862 anchor trial)
    "NCT03734029",  # DESTINY-Breast04 (HER2-low — TA992 side)
]
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def fetch_study(nct_id: str) -> dict:
    """Fetch the full study record from ClinicalTrials.gov API v2."""
    resp = requests.get(f"{BASE_URL}/{nct_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_raw(data: dict, nct_id: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{nct_id}_raw.json"
    out_path.write_text(json.dumps(data, indent=2))
    return out_path


def extract_features(data: dict) -> dict:
    """
    Pull out the fields feeding the HTA outcome/discount model:
    phase, cohort size, primary endpoint(s), and status.

    NOTE: field paths below are based on the documented v2 schema as of
    early 2026. Print `data.keys()` and inspect `protocolSection` after
    your first live run to confirm nothing has shifted before trusting
    this blindly.
    """
    protocol = data.get("protocolSection", {})

    design = protocol.get("designModule", {})
    identification = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    outcomes = protocol.get("outcomesModule", {})
    enrollment = design.get("enrollmentInfo", {})

    primary_outcomes = outcomes.get("primaryOutcomes", [])
    secondary_outcomes = outcomes.get("secondaryOutcomes", [])

    features = {
        "nct_id": identification.get("nctId"),
        "brief_title": identification.get("briefTitle"),
        "phase": design.get("phases", []),
        "enrollment_count": enrollment.get("count"),
        "enrollment_type": enrollment.get("type"),  # ACTUAL vs ESTIMATED
        "overall_status": status_module.get("overallStatus"),
        "primary_endpoints": [o.get("measure") for o in primary_outcomes],
        "secondary_endpoints": [o.get("measure") for o in secondary_outcomes],
        "study_type": design.get("studyType"),
        "allocation": design.get("designInfo", {}).get("allocation"),
    }

    assert features["nct_id"], (
        "Extraction returned no nctId -- schema drift likely, "
        "check protocolSection structure before trusting this row"
    )
    return features


def save_processed(features: dict, nct_id: str) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"{nct_id}_features.json"
    out_path.write_text(json.dumps(features, indent=2))
    return out_path


def main():
    for nct_id in NCT_IDS:
        print(f"Fetching {nct_id} from ClinicalTrials.gov...")
        data = fetch_study(nct_id)

        raw_path = save_raw(data, nct_id)
        print(f"Raw snapshot saved: {raw_path}")

        features = extract_features(data)
        processed_path = save_processed(features, nct_id)
        print(f"Extracted features saved: {processed_path}")
        print(json.dumps(features, indent=2))
        print("-" * 60)


if __name__ == "__main__":
    main()