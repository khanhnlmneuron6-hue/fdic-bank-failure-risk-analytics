# Source and claim audit

Reviewed 15 November 2026 for the pdfLaTeX report. A longer bibliography does not validate an assumption. This audit separates external support, project measurements and quantities that remain unidentified.

## What was incomplete in the preceding report

1. Data, costs, AP, SHAP and ALE had focused citations, but engineering claims about columnar storage, lazy optimizations and Spark execution lacked nearby primary documentation.
2. The iRF software reference did not also cite the underlying algorithm paper. A paper describing iRF does not justify 50 trees, depth 6 or the particular selected features.
3. Bank-failure literature was not clearly positioned against this project's different target and evaluation cohorts.
4. The OIG report EVAL-20-002 is dated **December 2019**, despite the fiscal-year identifier 20. Generic 2020 attribution was inaccurate.
5. Citations were manually numbered and metadata were abbreviated. The report now uses BibTeX to generate numbered citations and a bibliography ordered by first citation. References begins on a separate page.
6. The report cover had not placed every course-required data count/event count on page one. The TeX front matter now does so, while the actual repository URL still awaits creation.

## External evidence checked in this round

| Claim | Primary source / locator | What it supports; limit |
|---|---|---|
| Public financial data and endpoint definitions | [FDIC API](https://api.fdic.gov/banks/docs/) | Source identity and documented fields. Does not certify this project's historical cleaning rules or vintages. |
| Income is year-to-date | [FFIEC 031/041 instructions, June 2026](https://www.ffiec.gov/sites/default/files/data/reporting-forms/FFIEC031_FFIEC041_202606_i.pdf), printed RI-1, PDF p. 28 | Calendar-YTD reporting convention. The current edition alone does not prove every historical rule in 1984; project-specific recoveries require their own provenance. |
| Failed-bank loss estimates are revised | [FDIC testimony](https://www.fdic.gov/news/speeches/2024/oversight-prudential-regulators-0), loss-estimate discussion | Receivership loss estimates change with asset sales, liabilities and expenses. Not proof that any warning averts those losses. |
| Columnar format and compression | [Apache Parquet overview](https://parquet.apache.org/docs/overview/) | Storage design. The actual 3.80x ratio comes from the project's matched projection. |
| Projection/predicate pushdown and lazy plans | [Polars optimizations](https://docs.pola.rs/user-guide/lazy/optimizations/) | Engine capabilities. Measured timing comes from the saved benchmark; no universal speed claim. |
| Spark planning, joins, shuffles and tuning | [Spark 4.3.0 performance tuning](https://spark.apache.org/docs/4.3.0/sql-performance-tuning.html) | Execution mechanisms. A local demonstration does not establish cluster speedup. |
| Bank-failure model context | [Petropoulos et al. (2020)](https://doi.org/10.1016/j.ijforecast.2019.11.005), abstract, data/validation sections in local PDF | Comparisons including RF/logit and out-of-time evaluation. Their failure/assistance target differs; no raw AP leaderboard comparison is made. |
| Financial feature motivation | [Correia, Luck and Verner, June 2025 version](https://arxiv.org/abs/2506.06082v1), introductory/data sections in local PDF | Fundamental deterioration and funding patterns; not validation of this exact feature set or a claim to reproduce their study. |
| iRF algorithm | [Basu et al. (2018)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5828575/), algorithm description | Iterative feature reweighting and interaction discovery. The predictive-only imodels recipe and settings remain project choices. |
| Selection optimism | [Cawley and Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html), abstract and model-selection sections | Repeated optimization can overfit selection criteria. Clean reruns do not erase adaptivity. |
| PR interpretation under imbalance | [Saito and Rehmsmeier (2015)](https://doi.org/10.1371/journal.pone.0118432), simulation section/Fig. 5 | PR performance changes with class composition. Does not make annual AP normalization mandatory. |
| Preference-based warning evaluation | [Sarlin (2013)](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1509.pdf) | Explicit policymaker loss preferences. Does not identify this project's alpha or review productivity. |
| USD 110/hour | [OCC 2011-46](https://www.occ.gov/static/rescinded-bulletins/bulletin-2011-46.pdf), PDF p. 4 | Historical special-examination/investigation fee. Not an FDIC wage or a measured marginal offsite-review cost. |
| First/repeat review time | [OIG EVAL-20-002](https://fdicoig.gov/sites/default/files/reports/2022-08/20-002EVAL.pdf), printed p. 11, PDF p. 15 | Interviews with 32 case managers: six reported first reviews of four hours or less; five described 12 hours; repeat effort also varied. Supports heterogeneous scenarios, not a population mean. |
| Escalation workload | [OIG AUD-12-011](https://www.fdicoig.gov/sites/default/files/reports/2022-08/12-011AUD.pdf), Table 3, PDF p. 14 | 335-1,820-hour risk-management examination benchmarks for banks up to USD 1bn. Not a fee for each model alert or all bank sizes. |
| Explanations | [Tree SHAP](https://arxiv.org/abs/1802.03888); [ALE](https://arxiv.org/abs/1612.08468) | Algorithmic definitions and interpretation limits. Custom implementation checks are project evidence, not proof of causality or independent generalization. |
| Typesetting | [microtype](https://ctan.org/pkg/microtype); [Michaillat's source](https://github.com/pmichaillat/latex-paper) | Character protrusion/font expansion and inspected layout patterns. No claim that the lecturer used this repository. |

The FDIC interactive failures-help page opened but returned no readable text to the browser tool. It is retained as a field-reference link in the source index, not described as newly read or quoted. No source is cited merely because it appeared in a search result.

## Empirical evidence belongs to the project

- Acquisition counts and completeness: `acquisition_summary.json` and `acquisition_completeness.csv`; recorded snapshot verification, no new API census in this round.
- Sample reconciliation: `final_fit_manifest.json`, `test_population_reconciliation.json`, `test_metrics.csv`.
- Timings and engine agreement: `storage_processing_benchmarks.csv`, `storage_sizes.json`, `spark_parity.csv` and saved query plans.
- Development comparisons: versioned historical CSVs and `docs/evidence_manifest.json`. No new historical 64-fold execution is claimed.
- Frozen holdout: saved metrics/run manifest plus the frozen protocol. No fitting, reselection, cost refit or scoring occurred during this report revision.
- Explanations: sample scope and numerical checks in `explainability_checks.json`.

## What adding references cannot settle

| Remaining quantity / claim | Current status | Evidence needed |
|---|---|---|
| Actual FDIC or local marginal review cost | Proxy and scenario only | Review logs, staff costs and task-level time measurements |
| Repeat effort, available capacity and escalation probability | Declared assumptions, sensitivity tables | Observed workflow histories and staffing allocation |
| Avoidable fraction of missed-event severity (alpha) | Not causally identified | Credible intervention-effect evidence and a decision-maker's utility specification |
| Perfect point-in-time historical dataset | Not established | Publication/revision vintages and historical release calendars |
| Economic meaning of every suspicious restart / historical null | Project rules and audit evidence, not universal causal adjudication | Record-specific accounting documentation |
| Optimal iRF hyperparameters or D43 preference rule | Tested choices, disclosed adaptivity | Predeclared independent comparisons under an appropriate evaluation design |
| Production readiness or realized savings | Not established | Prospective monitoring, validated capacity/costs and governance |

The report's cost section now explicitly states that review workload is prediction-derived while unit costs and preferences are not estimated from this bank panel. The course request for data-estimated FP/FN costs is thus not fully closed by more citations. The illustrative frozen policy remains unchanged.

The GitHub URL is the other concrete submission item still requiring human action. It is not fabricated in the report.
