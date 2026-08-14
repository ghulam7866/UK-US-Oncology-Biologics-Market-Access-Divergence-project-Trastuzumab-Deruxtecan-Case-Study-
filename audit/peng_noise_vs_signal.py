import re
from pathlib import Path

CORPUS_DIR = Path(r"C:\Users\44782\Desktop\Medtech_market_sizing_project") / "data" / "raw" / "nlp_raw data"
text = (CORPUS_DIR / "us_peng_2023.txt").read_text(encoding="utf-8")

patterns = [
    r"willingness[- ]to[- ]pay",
    r"\bWTP\b",
    r"per QALY",
    r"cost-effective(?:ness)? use of (?:NHS )?resources",
    r"acceptable ICER",
    r"official WTP threshold",
    r"(?:£|\$)\d[\d,]*\s*(?:per QALY|threshold|WTP)",
    r"(?:threshold|WTP)\s+of\s+(?:£|\$)\d",
]

for p in patterns:
    matches = re.findall(p, text, flags=re.IGNORECASE)
    print(f"{p!r}: {len(matches)} -> {matches[:5]}")