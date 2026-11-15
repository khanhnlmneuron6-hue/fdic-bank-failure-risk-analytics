# Curated portfolio release

Author: Nguyễn Lê Nam Khánh, student ID 11230976.

## Current report update (15 November 2026)

The report is titled **Bank-Failure Early Warning Using FDIC Data**, with the
subtitle **Data Engineering, Temporal Validation and Review Costs**. References
starts on its own page and contains 21 automatically numbered entries, matching
numeric citations in the text. The current PDF has 14 main pages including the
cover and references, one appendix page, 11 tables and six figures.

The additional wording review clarified missing-value records, weighted tree-node
counts used in SHAP, prediction-quarter ranges and the pre-prediction population
check. Editorial sources and decisions are recorded in EDITORIAL_REVIEW.md.
Scientific tables, the notebook, fitted models, feature configuration and cost
policy were preserved. No fitting, tuning or holdout scoring occurred in this edit.
The older entries below document earlier versions and their then-current counts.

The original working project remains unchanged. An independent private notebook snapshot was taken before curation; the curated notebook is rebuilt from inspected scientific functions and versioned aggregate evidence, not by deleting arbitrary cells and hoping dependencies remain intact.

## Retained
- Source acquisition scope, field contracts, D8 zero semantics, exact-quarter flows and TTM, I01/D15 recovery and Y1/BRO quarantine, final forward-HGB feature provenance, train-only preprocessing.
- Historical multi-selector/multi-model development summaries with origin SHA records.
- B3 as the development-selected candidate, core7 iRF/LR as fixed controls, explicit adaptive-selection limitations.

## Newly executed
- Feature-parity reconstruction on dev before fitting; final three pipelines with saved models and exact reload checks.
- CSV/Parquet and pandas/Polars benchmarks; local Spark output reconciliation and MLlib time-split demonstration.
- B3 cost/chain/workload scenarios; scenario policy frozen before test construction.
- The authorized holdout scoring pass and all predeclared reference-budget outputs.
- Final-model development SHAP/ALE with numerical validation, portable notebook execution and report generation.

## Deliberately not implied
- The historical 64-fold research, all selectors, model pilots and v65 tuning were not rerun during formatting. Their aggregate evidence is historical. The selected forward path can be explicitly replayed with `scripts/reproduce_backtest.py`; this newly extracted replay command has not itself completed a new 64-fold execution in the curated edition.
- No new threshold/model was selected after holdout outcomes. Core7 iRF's stronger holdout AP is reported without making it the retrospectively selected winner.
- No causal savings, measured FDIC labour cost, regulator-approved staffing capacity or universally optimal q is claimed.

## Technical evaluation resume
The initial pre-prediction test check stopped on a cohort-size assertion: 280,267 locked keys include 6,404 rows with no evaluable label / outside the modelling population. The existing nonnull-label rule gives 273,863 evaluable rows, 257 positive rows and 78 events. Before any scores were produced, that reconciliation was fixed and logged; models and policy remained frozen. There was one successful prediction pass per model. Do not describe this as an uninterrupted first execution.

## Remaining human action
The public repository was created at https://github.com/khanhnlmneuron6-hue/fdic-bank-failure-risk-analytics. Its URL is now recorded in the author metadata, report cover and README. Review the work before course submission; publication does not establish compliance with every course requirement.

The long AI-assistance paragraph in Section 7 was subsequently removed at the
author's request. The project README retains its disclosure. The assignment's
requirement to cite AI tools in the report still needs to be addressed before
course submission.


## Academic report redesign (15 November 2026)
The PDF was rewritten as a continuous serif manuscript, with numbered sections,
10 booktabs-style tables, six source-backed publication figures, explicit panel
notes and supplementary comparisons. Typography sources and actual files read
are documented in REPORT_STYLE_GUIDE.md. The renderer is ReportLab, not LaTeX.
The previous PDF and generator are retained privately under .local. All existing
scientific aggregates, models, notebook outputs and frozen policy/config remain
unchanged; no fit or test scoring was performed in this formatting round.


## pdfLaTeX edition (15 November 2026)
Replaced the ReportLab renderer with an editable LaTeX manuscript, local style
and BibTeX database. Actual build: pdfLaTeX, BibTeX and two pdfLaTeX passes,
with shell escape disabled. Times-like 11 pt text, a single paragraph/heading
system, microtype, proper math and embedded vector charts replace manual font
and paragraph settings. The palette is navy, teal and gray.

The bibliography now contains 23 cited entries. Nearby citations were added for
engineering, YTD reporting, iRF and bank-failure context. EVAL-20-002 is dated
December 2019; its interview times support scenarios, not estimated mean review
costs. SOURCE_AUDIT.md records unresolved empirical cost and point-in-time limits.
The course-required source/sample/event counts are now on the first page.

All saved scientific tables, notebook outputs, fitted models, feature config and
frozen policy remain unchanged. No model fit or holdout scoring was performed.
The private TeX runtime, build logs, source-paper extracts and previous PDF are
excluded from the public export.

Standalone LaTeX source archive independently recompiled: all 14 pages match
the report text. Final checks found no overfull boxes, missing glyphs or unresolved
citations. The log retains the expected epstopdf notice that shell escape is
disabled; all graphics are already PDF, so EPS conversion is unused.


## Prose revision to the assignment structure (15 November 2026)
Rewrote the abstract, body and notes around the six assignment parts, with a
separate reproducibility section. Removed repeated defensive clauses and
submission instructions from the manuscript. Technical identifiers are defined
where needed, and mean annual AP is used as the display name for AP-D7.

Added one data-quality table from existing aggregates and revised chart labels
without changing plotted values or the approved typography/palette. Bibliography
notes were cleaned and layout-source credit moved to supporting attribution.
Scientific references, model settings, estimates, cost assumptions and limitations
retain their meaning. The source retains the actual all-missing-feature failure
behavior rather than adopting the reviewer's incorrect exclusion example.

EDITORIAL_REVIEW.md records the inspected writing guidance and the response to
reviewer comments. No new model fit, cost-policy selection or holdout scoring was
performed. The original data/results and style file remain unchanged.
