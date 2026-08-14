#!/usr/bin/env python3
"""
verify_ta992_timeline.py

Verifies the TA992 (trastuzumab deruxtecan, HER2-low) process timeline
against NICE's own "History" page, and specifically investigates the
appeal-date anomaly: the appeal documents are dated 14 Nov 2024 --
*after* the guidance itself was published on 29 Jul 2024, which is the
wrong order for a normal appeal-then-publish sequence.

This script does NOT resolve the anomaly on its own. It (a) confirms
the page still shows what we think it shows, (b) flags the ordering
problem explicitly rather than silently accepting it, and (c) if you've
downloaded the appeal Word docs, pulls out any dates mentioned *inside*
the letters themselves -- which is what actually resolves whether the
appeal ran before publication (and NICE just uploaded the letters late)
or whether there was a second, later appeal process.

USAGE
-----
1. Save a local copy of the History page:
   https://www.nice.org.uk/guidance/ta992/history
   -> browser "Save Page As... > Webpage, HTML only"
   -> save as data/raw/HTML/ta992_history.html

2. (Optional but recommended) Download the four appeal documents from
   the same page (they're .doc/.docx MSWord files) into:
   data/raw/Word/ta992_scrutiny_letter.docx
   data/raw/Word/ta992_response_to_scrutiny_letter.docx
   data/raw/Word/ta992_final_scrutiny_letter.docx
   data/raw/Word/ta992_appeal_letter.docx
   (If NICE serves old-format .doc rather than .docx, python-docx can't
   read it -- open and re-save as .docx in Word first.)

3. Adjust the paths below if your filenames/folders differ, then run:

       python verify_ta992_timeline.py
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Missing dependency: pip install beautifulsoup4 lxml")

try:
    import docx
    HAVE_DOCX = True
except ImportError:
    HAVE_DOCX = False

# ---------------------------------------------------------------------------
# Paths -- adjust to match your project layout
# ---------------------------------------------------------------------------
HISTORY_PAGE = Path("data/raw/HTML/History _ Trastuzumab deruxtecan for treating HER2-low "
                     "metastatic or unresectable breast cancer after chemotherapy _ Guidance "
                     "_ NICE.htm")

APPEAL_DOCS = {
    "Scrutiny letter": Path("data/raw/Word/scrutiny-letter.docx"),
    "Response to scrutiny letter": Path("data/raw/Word/response-to-scrutiny-letter.docx"),
    "Final scrutiny letter": Path("data/raw/Word/final-scrutiny-letter.docx"),
    "Appeal letter": Path("data/raw/Word/appeal-letter.docx"),
}

# ---------------------------------------------------------------------------
# Reference: what the History page showed as of this verification pass.
# These fragments are CONFIRMED correct by the --dump-titles output.
# ---------------------------------------------------------------------------
REFERENCE_MILESTONES = [
    # (section, title_fragment, expected_date)
    ("Consultation on suggested remit", "Draft scope post referral", date(2022, 10, 21)),
    ("Invitation to participate", "Final scope", date(2023, 1, 6)),
    ("Draft guidance", "Appraisal consultation document", date(2023, 9, 26)),
    ("Final draft guidance", "Final draft guidance", date(2024, 3, 5)),
    ("Appeal", "Scrutiny letter", date(2024, 11, 14)),
    ("Appeal", "Appeal letter", date(2024, 11, 14)),
]

GUIDANCE_PUBLISHED_DATE = date(2024, 7, 29)
DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{4})\b"
)

# ---------------------------------------------------------------------------
# Corrected parser: uses real DOM structure (p.card__heading > a, skips
# section‑overview cards that have no "Published:" date), and normalises
# non‑breaking spaces in titles so they match REFERENCE_MILESTONES.
# ---------------------------------------------------------------------------
def parse_history_page(path: Path):
    """
    Real DOM (as of 2026-08-02): NICE's History page uses <article class="card">
    blocks. Titles live in <p class="card__heading"><a>...</a></p>. Dates live in
    <dl class="card__metadata"> with <dt>Published:</dt> / <dd>date</dd>.
    Section‑overview cards (like "Appeal" or "Final draft guidance") have NO date
    and must be skipped.
    """
    if not path.exists():
        return None
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    entries = []

    for card in soup.select("article.card"):
        # --- Section: nearest preceding h3 ---
        section = None
        prev_h3 = card.find_all_previous("h3")
        if prev_h3:
            section = prev_h3[0].get_text(strip=True)

        # --- Title: inside p.card__heading > a ---
        title = None
        heading_p = card.select_one("p.card__heading")
        if heading_p:
            link = heading_p.find("a")
            if link:
                title = link.get_text(" ", strip=True)   # preserve word spacing
        # Fallback (just in case markup drifts)
        if not title:
            a = card.find("a")
            if a:
                title = a.get_text(" ", strip=True)
        if not title:
            continue

        # Normalize whitespace: NICE's markup uses non-breaking spaces (\xa0)
        # between some words, which don't match a plain " " in
        # REFERENCE_MILESTONES fragments even though they render identically.
        title = re.sub(r"\s+", " ", title.replace("\xa0", " ")).strip()

        # --- Date: dl.card__metadata > dt:Published: + dd ---
        date_val = None
        meta_dl = card.select_one("dl.card__metadata")
        if meta_dl:
            dt = meta_dl.find("dt", string=re.compile(r"Published:"))
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    date_str = dd.get_text(strip=True)
                    try:
                        date_val = datetime.strptime(date_str, "%d %B %Y").date()
                    except ValueError:
                        pass

        # Cards with a title but no date are section overviews – skip
        if date_val is None:
            continue

        entries.append((section, title, date_val))

    return entries


def debug_dump_titles(path: Path):
    """Print every article.card's section, title, date, and a snippet of
    the card's HTML to help identify the correct title selectors.
    """
    print("=" * 70)
    print("ARTICLE.CARD DUMP (titles + dates)")
    print("=" * 70)
    if not path.exists():
        print(f"FILE NOT FOUND: {path}")
        return
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")

    for i, card in enumerate(soup.select("article.card"), 1):
        prev = card.find_all_previous("h3")
        section = prev[0].get_text(strip=True) if prev else "(no preceding h3)"

        # Use same extraction logic as the main parser
        title = None
        heading_p = card.select_one("p.card__heading")
        if heading_p:
            link = heading_p.find("a")
            if link:
                title = link.get_text(" ", strip=True)
        if not title:
            a = card.find("a")
            if a:
                title = a.get_text(" ", strip=True)
        title = re.sub(r"\s+", " ", title.replace("\xa0", " ")).strip() if title else ""

        date_str = "?"
        meta_dl = card.select_one("dl.card__metadata")
        if meta_dl:
            dt = meta_dl.find("dt", string=re.compile(r"Published:"))
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    date_str = dd.get_text(strip=True)

        print(f"\n--- Card {i} ---")
        print(f"Section : {section}")
        print(f"Title   : {title}")
        print(f"Date    : {date_str}")
        print(f"HTML snippet:\n{str(card)[:400]}\n")


def check_reference_match(entries):
    print("-" * 70)
    print("CHECK 1: Does the saved History page match what we verified?")
    print("-" * 70)
    if entries is None:
        print(f"  FILE NOT FOUND: {HISTORY_PAGE}")
        return False

    all_ok = True
    for section, title_fragment, expected_date in REFERENCE_MILESTONES:
        match = next(
            (e for e in entries
             if title_fragment.lower() in e[1].lower()
             and section.lower() in (e[0] or "").lower()),
            None,
        )
        if match is None:
            print(f"  [MISSING] '{title_fragment}' under '{section}' not found on saved page")
            all_ok = False
        elif match[2] != expected_date:
            print(f"  [CHANGED] '{title_fragment}': page now shows {match[2]:%d %b %Y}, "
                  f"expected {expected_date:%d %b %Y}")
            all_ok = False
        else:
            print(f"  [OK] '{title_fragment}' -- {expected_date:%d %b %Y}")
    return all_ok


def check_chronology(entries):
    print("\n" + "-" * 70)
    print("CHECK 2: Chronological ordering (flags the known anomaly)")
    print("-" * 70)
    if entries is None:
        print("  Skipped -- no local page to check.")
        return

    final_draft = next((e[2] for e in entries if "final draft guidance" in e[1].lower()), None)
    appeal_dates = [e[2] for e in entries if (e[0] or "").lower() == "appeal"]

    if final_draft:
        print(f"  Final draft guidance:    {final_draft:%d %b %Y}")
    print(f"  Guidance published:      {GUIDANCE_PUBLISHED_DATE:%d %b %Y}  (from Overview page)")
    if appeal_dates:
        print(f"  Appeal docs (site date): {min(appeal_dates):%d %b %Y}")

    if appeal_dates and min(appeal_dates) > GUIDANCE_PUBLISHED_DATE:
        print("\n  [FLAGGED] Appeal documents are dated AFTER the guidance was")
        print("  published. This is not normal appeal-then-publish order.")
        print("  Two explanations remain open:")
        print("    (a) NICE's 'Published' date = when uploaded to site, not")
        print("        when the appeal actually happened (likely ran before")
        print("        29 Jul 2024, site just updated later)")
        print("    (b) A second appeal/correction process occurred after")
        print("        publication, meaning 29 Jul 2024 wasn't fully final")
        print("  -> see CHECK 3 below if appeal letter .docx files are present.")
    else:
        print("\n  [OK] Ordering is consistent with a normal appeal-then-publish sequence.")


def extract_dates_from_docx(path: Path):
    if not path.exists():
        return None
    if not HAVE_DOCX:
        return "SKIPPED (python-docx not installed)"
    try:
        d = docx.Document(str(path))
    except Exception as e:
        return f"COULD NOT READ ({e}) -- if this is a legacy .doc file, re-save as .docx"

    full_text = "\n".join(p.text for p in d.paragraphs)
    hits = []
    for m in DATE_PATTERN.finditer(full_text):
        day, month_name, year = m.groups()
        context = full_text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
        hits.append((f"{day} {month_name} {year}", " ".join(context.split())))
    return hits


def check_appeal_letters():
    print("\n" + "-" * 70)
    print("CHECK 3: Dates mentioned INSIDE the appeal letters")
    print("-" * 70)
    print("  (This is what actually resolves the anomaly -- e.g. a line like")
    print("   'we received your notice of appeal on [date]' tells you the")
    print("   real event date, independent of the site's upload date.)\n")

    any_found = False
    for label, path in APPEAL_DOCS.items():
        result = extract_dates_from_docx(path)
        print(f"  {label} ({path}):")
        if result is None:
            print("    FILE NOT FOUND")
        elif isinstance(result, str):
            print(f"    {result}")
        elif not result:
            print("    No explicit dates found in the text.")
        else:
            any_found = True
            for date_str, context in result:
                print(f"    {date_str}  ...\"{context}\"")
        print()

    if not any_found:
        print("  No appeal letters found/parsed. Download them (see docstring)")
        print("  to resolve the anomaly properly rather than guessing.")


def main():
    if "--dump-titles" in sys.argv:
        debug_dump_titles(HISTORY_PAGE)
        return
    if "--debug" in sys.argv:
        debug_dump_titles(HISTORY_PAGE)
        return

    print("=" * 70)
    print("TA992 TIMELINE VERIFICATION")
    print("=" * 70)

    entries = parse_history_page(HISTORY_PAGE)
    ref_ok = False
    if entries:
        for e in entries[:5]:
            print("   ", e)
        ref_ok = check_reference_match(entries)
        check_chronology(entries)
        check_appeal_letters()

    print("\n" + "=" * 70)
    if entries is None:
        print("VERDICT: INCOMPLETE -- History page not found locally.")
    elif not ref_ok:
        print("VERDICT: PAGE HAS DRIFTED from what was previously verified --")
        print("review the [MISSING]/[CHANGED] lines above before citing dates.")
    else:
        print("VERDICT: Page matches prior verification. The appeal-date")
        print("anomaly remains open until Check 3 has letter text to review --")
        print("do not assert a specific explanation in the write-up until then.")
    print("=" * 70)


if __name__ == "__main__":
    main()
