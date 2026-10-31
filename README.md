# UK/US Market Access Divergence in HER2-Targeted Breast Cancer Therapies: A Trastuzumab Deruxtecan Case Study

A market access analysis comparing how the UK (NICE) and US payer systems evaluate
the same medicine, trastuzumab deruxtecan (T-DXd, brand name Enhertu), across two
distinct indications (HER2-positive and HER2-low metastatic breast cancer).

The project combines a verified n=13 dataset of NICE technology appraisals, a
four-document regex-based theme comparison of NICE and US cost-effectiveness literature,
and a single-medicine case study illustrating indication-level and jurisdictional
divergence in reimbursement outcomes.

**Start here:** the full report is in [`outputs/documentation/enhertu_project_writeup.pdf`](./outputs/documentation/enhertu_project_writeup.pdf)

Data and sources as of August 2026.

---

## Headline findings

1. **EAG disagreement** between a company's model and NICE's External Assessment
   Group (EAG) is the strongest observed predictor of appraisal outcome in the
   verified n=13 dataset. Of the 11 appraisals with a binary outcome (after
   excluding two managed access appraisals), none of the four with substantial
   disagreement was recommended. Complete separation prevents a stable regression
   estimate, so this finding is descriptive and hypothesis-generating, not a
   validated model.
2. **Surrogate endpoint validity** (PFS to OS extrapolation) is an active point of
   contest in the NICE appraisals reviewed and was not found in the US academic
   cost-effectiveness papers analysed alongside them. This suggests a structural
   difference in evidence standards, not a difference in emphasis.
3. **A positive reimbursement outcome for one indication carries no guarantee
   for another.** T-DXd was recommended with managed access under TA862 (roughly
   600 eligible NHS patients annually) while TA992 was rejected, leaving no routine
   NHS funding route. Medicine, manufacturer, and appraising body were constant,
   but the evidence base and comparator were not, so the contrast is consistent
   with indication-level cost-effectiveness driving the outcome without isolating it.
4. **NICE's most generous historical threshold, converted to USD, remains below
   the floor of the US ICER benchmark range**, a persistent gap not attributable
   to currency or reporting convention.

Full findings, limitations, and strategic implications are in the report.

---

## Strategic implications

For a company or investor navigating a comparable multi-indication, multi-market
launch, four practical implications follow from these findings:

- **EAG disagreement is an early diligence signal.** The EAG's critique of a
  company's submitted model reaches stakeholders before the committee decides.
  A signal of substantial disagreement should trigger an internal pricing and
  evidence review at that point, not at final appraisal.
- **UK-style surrogate endpoint justification should be planned at trial design
  stage**, not treated as a by-product of a US-oriented evidence package. This
  evidence is costly to generate retroactively once trial design is fixed.
- **Each indication should be underwritten independently.** A positive
  reimbursement decision for one indication is not a track record that de-risks
  another, even for the same molecule and manufacturer.
- **Global list price should be stress-tested against the UK threshold before
  the US benchmark.** The risk appears asymmetric: a price calibrated to US
  willingness-to-pay carries a significant risk of UK rejection in a way the
  reverse does not, favouring UK-specific pricing agreements built in from launch
  rather than negotiated reactively after a NICE rejection.

Full mechanism and reasoning for each point is in Section 4 of the report.

---

## Repository structure

```text
├── outputs/
│   ├── figures/                   # All figures referenced in the report (numbered by section)
│   └── documentation/             # Report memo PDF + supplementary methodology docs
├── src/
│   ├── data_sourcing/             # Scripts to pull and extract raw source data
│   ├── analysis/                  # Core analysis: coding, charts, threshold and uptake comparisons
│   └── audit/                     # Verification, separation diagnostics, and data QA scripts
├── data/
│   ├── processed/                 # Derived datasets, extraction logs, matched text outputs
│   └── raw/
│       └── sources.md             # Links to all primary sources
└── README.md
```

---

## Data and sourcing

This project draws on publicly available NICE technology appraisals, US
government (CMS) documents, and published academic cost-effectiveness literature.

**Raw source documents (PDFs, full appraisal text, NICE guidance pages) are not
committed to this repository.** Instead, [`data/raw/sources.md`](./data/raw/sources.md)
lists every source used, with its official URL and the date it was accessed, so
the underlying data can be independently re-pulled and checked against this
project's extracted figures. Full-text extractions can be regenerated by running
`src/data_sourcing/extract_nice_pdfs.py` against the linked PDFs.

This approach was taken to respect the terms of use of Crown-copyright NICE
guidance and copyrighted academic literature, while keeping the full pipeline
reproducible from public sources.

**What *is* included**: the derived, coded dataset (`data/processed/`), including
the verified n=13 NICE appraisal dataset, extraction logs, exclusion reports, and
theme-extraction outputs, since these represent this project's own analytical
work, not reproductions of third-party documents.

**Source of truth:** `coded_dataset_final.csv` is the authoritative coded dataset.
An earlier working file, `draft_coding_verified.csv`, is not committed.

**Dates:** NICE page dates can differ from the issue dates printed inside the
documents themselves. Where they differ, this project uses the document date and
notes the discrepancy in the report.

---

## Methodology summary

The project draws on three evidence bases, each with a different sample size and
evidentiary weight:

1. **A verified n=13 dataset** of NICE technology appraisals for HER2-targeted
   breast cancer therapies, independently cross-checked against primary NICE
   guidance documents using purpose-built verification scripts
   (`verify_trial_data.py`, `verify_ta992_timeline.py`, `verify_cms_j9358.py`).
2. **A four-document regex-based thematic comparison** (`theme_extraction.py`) of two
   NICE appraisals against two US academic cost-effectiveness papers, using
   keyword-based extraction normalised per 1,000 words.
3. **A single-medicine, two-indication case study** of T-DXd (TA862 vs. TA992),
   illustrating indication-level divergence in reimbursement outcome with
   medicine, manufacturer, and appraising body constant. The two appraisals
   differ in trial evidence, comparator, population, and date, so the case
   is suggestive and not a controlled comparison.

A predictive model (logistic regression / gradient boosting) was deliberately
**not** used for the n=13 dataset after diagnostic testing showed complete
separation and severe leave-one-out coefficient instability, a known failure
mode of maximum-likelihood estimation at small sample sizes. The diagnostics are
in `[path to regression / leave-one-out script]`. This is documented as a
methodological finding in its own right (see report, Section 3.1 and
Methodology Appendix B) rather than smoothed over.

Full methodology, including the rationale for shifting the illustrative case
study anchor from TA992 to TA862, is documented in the report's Methodology
Appendix.

---

## Reproducing this analysis

### Dependencies

Install all required Python packages with:

```bash
pip install -r requirements.txt
```

The [`requirements.txt`](./requirements.txt) file in the repository root lists the exact packages and minimum versions needed.

### Steps

1. Clone the repository and `cd` into it.

2. Install dependencies as above.

3. Pull primary source documents using the URLs in `data/raw/sources.md`.

4. Regenerate raw text/data inputs:

```bash
python src/data_sourcing/clinicaltrials_pull.py
python src/data_sourcing/extract_nice_pdfs.py
python src/data_sourcing/search_key_figures.py
```

5. Regenerate the coded dataset:

```bash
python src/analysis/clean_numeric_fields.py
python src/analysis/recode_variables.py
```

6. Reproduce the core analysis and figures:

```bash
python src/analysis/analysis.py
python src/analysis/descriptive_charts.py
python src/analysis/theme_extraction.py
python src/analysis/threshold_comparison.py
python src/analysis/uptake_comparison.py
```

7. Reproduce audit and diagnostic checks:

```bash
python src/audit/verify_trial_data.py
python src/audit/separation_checks.py
python src/audit/verify_ta992_timeline.py
python src/audit/verify_cms_j9358.py
python src/audit/check_cdf_false_positives.py
python src/audit/peng_noise_vs_signal.py
```

---

## Limitations

Every finding in this report carries its own explicitly stated limitation and
is scoped to the evidence base that produced it. See the report for full detail.
In brief:

- The n=13 dataset supports descriptive, hypothesis-generating findings, not a
  validated predictive model.
- The four-document thematic comparison describes those specific texts, not a
  representative sample of NICE or US CEA literature generally.
- The T-DXd case study illustrates frictions that may recur elsewhere in NICE's
  broader appraisal activity but does not establish their frequency.
- Figures and outcomes for TA862 and TA992 reflect the appraisals as at August
  2026 and may have been superseded since.
- This analysis is scoped to the UK and US systems specifically. Institutional
  mechanisms identified here do not generalise to other jurisdictions without
  further comparative work (see report, Section 2.5, for a brief discussion of
  how Australia's PBS illustrates a third position on the evidence-versus-price
  spectrum).

---

## About

This project was built as a dual-audience portfolio piece: a student portfolio piece
and a market-access-consulting-style memo.

Ghulam Mustafa · Contact: bw004616@student.reading.ac.uk or gm408737@gmail.com
