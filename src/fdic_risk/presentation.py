"""Build a concise, portable evidence notebook. No model fit or test access on replay."""
from pathlib import Path
import json,os
import nbformat as nbf
from .pipeline import ROOT

def unpack_results(include_test=True):
    """Restore published aggregate outputs; never overwrite new calculations."""
    from zipfile import ZipFile
    archive = ROOT / 'results/summary_tables.zip'
    target = ROOT / 'reports/tables'
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if Path(name).name != name:
                raise ValueError('Unexpected path in result archive')
            if not include_test and name.startswith('test'):
                continue
            path = target / name
            if not path.exists():
                path.write_bytes(bundle.read(name))

def build_notebook(execute=False, include_saved_test=True):
    unpack_results(include_test=include_saved_test)
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s))
    def code(s):cells.append(nbf.v4.new_code_cell(s))
    md('''# Financial Data Engineering & Bank-Failure Early Warning
**Nguyễn Lê Nam Khánh · 11230976 · BFT65B, National Economics University**

An auditable FDIC pipeline for extracting, reconciling and analysing financial reports, with a time-ordered risk-ranking model and transparent alert-cost scenarios.

This is the **curated portfolio edition**. Research pilots and debugging cells have been removed. Functions live in `src/fdic_risk/`; this notebook presents the pipeline and its evidence in execution order. Historical development experiments are retained as clearly identified aggregate results. Final fits, storage/processing measurements, Spark checks and the frozen holdout evaluation were executed for this edition.''')
    md('''## 1. Executive findings
The study covers 1,682,616 financial reports, 170 quarters and 87 source fields. These fields are not 87 predictors. The selected B3 procedure uses forward-HGB feature groups plus a four-column loss-buffer block; its final fit has 24 predictors.

On the once-evaluated holdout, B3 does **not** dominate the simpler references: core7+iRF has higher AP. A high proportion of detected failure events also coexists with many false alerts. This notebook reports that trade-off explicitly.

**Decision scope:** support an analyst's offsite-review shortlist, not automatic closure, default probabilities certified for regulation, or a claim of realized cost savings.''')
    code('''from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "config_final.json").exists())
sys.path.insert(0, str(ROOT / "src"))
TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.figsize": (10, 4.5), "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
read = lambda name: pd.read_csv(TABLES / name)
load = lambda name: json.loads((TABLES / name).read_text())
config = json.loads((ROOT / "config_final.json").read_text())
policy = json.loads((ROOT / "docs/cost_policy.json").read_text())
test = read("test_metrics.csv")
primary = test[(test.scope == "all_test") & np.isclose(test.q, policy["selected_q"])].copy()
display(primary[["pipeline", "AP_D7", "AP_pooled", "ROC_AUC", "caught_events", "events", "precision", "row_recall", "alerts"]].round(4))''')
    md('''## 2. Question, target and information time
The target is failure in `(prediction_as_of, prediction_as_of + 4 quarters]`. A report dated quarter `r` is assumed available at the end of `r+1`. This is a conservative release-lag assumption, not an observed publication timestamp.

Mergers and assistance are not failures. Only the first qualifying FAILURE of a CERT creates its failure label. Observations outside the insured population, already exited institutions, incomplete horizons and unverifiable censoring follow documented exclusion rules. Failure dates and exit evidence are used for labels, never as predictors.

The source provides revised values and a current Institutions snapshot. Historical I01 quarantine was discovered retrospectively. Accordingly, the project is **not a vintage-perfect real-time simulation**.''')
    md('''## 3. Acquisition and storage
`config.yaml` fixes the 87 requested fields and 1984Q1–2026Q2 scope. `scripts/acquire.py` pages through the FDIC API with retry, validates page totals, retains compressed raw JSON responses and writes typed Parquet. Resume requires matching raw/typed hashes and field lists.

Raw files are immutable inputs. Public GitHub deliverables contain code and aggregate evidence only; all bank-level data and fitted models stay ignored.''')
    code('''acquisition = load("acquisition_summary.json")
display(pd.DataFrame([{"financial_rows": acquisition["financial_rows"], "quarters": acquisition["quarters"], "source_fields": acquisition["fields"], "all_quarter_totals_match": acquisition["quarters_match_api_total"], "download_dates": ", ".join(acquisition["download_dates"])}]))
display(read("acquisition_completeness.csv")[["quarter", "rows", "api_total", "complete"]].head(5))''')
    code('''a = read("acquisition_completeness.csv")
fig, ax = plt.subplots()
ax.plot(pd.to_datetime(a.quarter.astype(str)), a.rows, color="#087e8b")
ax.set(title="Reporting banks per quarter · acquisition scope", xlabel="Report date", ylabel="Bank-quarter reports")
fig.tight_layout(); fig.savefig(FIGURES / "reporting_banks.png", dpi=150); plt.show()''')
    md('''## 4. Automated quality checks and financial reconciliation
The quality layer distinguishes true zeros, structurally unavailable ratios, nonpositive denominators, negative but legitimate capital/earnings, unverified negative stocks and suspicious YTD accounting restarts. It records every quarantine instead of deleting all unusual banks.

For YTD flows, exact CERT/calendar-quarter joins replace row shifts. TTM requires four consecutive quarters. Verified accounting identities recover a limited historical window; suspected accounting-basis restarts are quarantined. No successor relationship from a later snapshot is silently used to reconstruct predictors. No future filling or interpolation is performed.

`docs/reconciliation_queries.sql` provides SQL extraction and reconciliation examples. Differences such as `ASSET != LIAB + EQ` are review exceptions, not automatic deletion rules.''')
    code('''display(read("source_quality_profile.csv").sort_values("missing_share", ascending=False).head(10))
display(read("source_quality_flags.csv").sort_values("rows_flagged", ascending=False).head(8))
display(read("zero_rule_summary.csv").sort_values("len", ascending=False).head(10))
display(read("quarantine_summary.csv"))
display(read("missing_source_summary.csv"))''')
    md('''### Refactor parity
The curated feature builder was checked against the approved research representation on the same development keys. This verifies the refactor's numerical behavior; it does not prove that every historical reporting value or economic assumption is correct.''')
    code('''parity = read("feature_parity.csv")
assert parity.mismatch_rows.sum() == 0
print(f"{len(parity)} columns checked: zero mismatched development values at the declared tolerance.")
display(parity.head(8))''')
    md('''## 5. Scalable processing: measured comparisons
Storage measurements use the same 7-column projection and 1984Q1–2011Q3 rows, not the full 87-field table. The pandas and Polars queries perform the same exact-quarter self-join, financial ratios and quarterly aggregation. Three repetitions are summarized by the median; reads use a warm OS cache.

Polars exposes projection pushdown, lazy planning and parallel execution. Spark reproduces the same calculation locally; numerical reconciliation checks precede performance interpretation. Spark is **not assumed faster** on this laptop-sized dataset.''')
    code('''storage = load("storage_sizes.json")
display(pd.DataFrame([storage])[["rows", "columns", "csv_bytes", "parquet_zstd_bytes", "ratio_csv_to_parquet"]].round(2))
bench = read("storage_processing_benchmarks.csv")
display(bench[["operation", "median_seconds", "runs"]].round(3))''')
    code('''fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].bar(["CSV", "Parquet Zstd"], [storage["csv_bytes"]/1e6, storage["parquet_zstd_bytes"]/1e6], color=["#8b9ca9", "#087e8b"])
axes[0].set(title="Same projected data, different storage", ylabel="File size (MB)")
q = bench[bench.operation.str.contains("join")]
axes[1].barh(q.operation.str.replace(" scan + exact-quarter join + ratios + aggregate", "", regex=False).str.replace(" lazy", "", regex=False), q.median_seconds, color=["#087e8b", "#8b9ca9"])
axes[1].set(title="Join + ratios + quarterly aggregate", xlabel="Median elapsed seconds · 3 warm-cache runs")
fig.tight_layout(); fig.savefig(FIGURES / "storage_processing.png", dpi=150); plt.show()''')
    code('''display(read("spark_parity.csv"))
spark_demo = load("spark_mllib_demo.json")
display(pd.DataFrame([{k: spark_demo[k] for k in ["spark_version", "master", "spark_query_seconds_startup_excluded", "validation_year", "validation_rows", "positive_rows", "AP", "ROC_AUC"]}]).round(4))
print("Polars plan excerpt:\\n", (ROOT / "reports/polars_plan.txt").read_text()[:1100])
print("Spark plan excerpt:\\n", (ROOT / "reports/spark_plan.txt").read_text()[:1100])''')
    md('''Spark MLlib is a separate, time-ordered LR demonstration: fit through 2009, evaluate 2011; train-fitted approximate median, vector assembly, scaling and regularized logistic regression. Its preprocessing and penalty differ from sklearn, so it is not presented as a matched estimator comparison.

**When would a cluster help?** The full acquired panel is feasible locally. A cluster becomes a candidate when wider transactional joins, repeated multi-entity workloads, concurrency or memory exceed the measured laptop capacity. The local experiment does not establish a universal row-count or speed threshold for a cluster.''')
    md('''## 6. Feature contracts and train-only preprocessing
The research path started with 87 source fields, screened them economically and technically, then built 21 economic feature groups. Groups contain levels, TTM measures and exact four-quarter changes. Forward-HGB selected groups on each outer-train window; the four loss-buffer features were subsequently added as an adaptive hypothesis (B3).

The final dev-only selection contains 12 original groups / 20 columns plus the four T columns. Selection on final dev is a **refit of the selected procedure**, not an independent validation of that exact set.

`ContractCapperV4 → train median → iRF` preserves the tested recipe. LR adds StandardScaler. Cap/no-cap and missing-indicator branches were investigated; their results do not establish that indicators or uncapped trees are universally useless. Structural nulls remain explicit in quality ledgers even when a median is used at model input.''')
    code('''contracts = read("final_feature_contracts.csv")
display(contracts[["feature", "formula"]])
print("Final B3 predictors:", len(config["B3_columns"]))
print("Excluded from X: CERT, outcome dates, labels, exit evidence and retrospective audit flags.")''')
    md('''## 7. Time-ordered validation and feature-selection evidence
Historical evaluation uses 64 folds: 16 validation years (1996–2011) under fixed-origin, expanding, rolling-5-year and rolling-10-year schemes. Identical training windows can share fits, giving 49 distinct outer-train groups. Selection and tuning occur only inside outer-train, with label maturity enforced and a four-quarter gap.

Forward, backward, floating selection, GA, stepwise logit, mRMR, stability selection and certified group lasso were explored. The unconverged original group-lasso branch is excluded. These historical investigations are preserved as evidence, rather than rerun or silently relabelled as new results.

AP-D7 is the equal-year mean over years with positive rows. The adaptive D43 minimax rule combines AP-D7 and unique-event recall at a reference 5% budget across fixed-origin/rolling-5y. It is a disclosed preference rule, not a theorem that 5% is optimal. The inner selector still optimizes AP, not a multi-objective loss.''')
    code('''folds = read("split_inner_folds.csv")
folds = folds[folds.candidate == "A_recent"]
display(folds.groupby("scheme").agg(folds=("val_year", "size"), first_year=("val_year", "min"), last_year=("val_year", "max")))
print("Total validation folds:", len(folds))
for name in ["exp3d_fs1_d7.csv", "exp3d_fs1_mmr.csv"]:
    if (TABLES / name).exists():
        print(name)
        selected_table = read(name)
        if "pipeline" in selected_table:
            selected_table = selected_table[~selected_table.pipeline.str.startswith("glasso|", na=False)]
        display(selected_table.head(10))''')
    md('''## 8. Model comparisons and what did not improve performance
LR/HGB, Elastic-Net, EBM, RuleFit, kernel approximations and iRF were compared at different research stages. Sample-based FM1 results are not mixed with full-train FT1 results. GRU remained a pilot. Extended feature selection (B8) and nested-tuned XGBoost did not establish an overall improvement over B3 under the registered comparison.

The v65 comparison has 17 outer trains / 32 validation folds for fixed-origin and rolling-5y. XGBoost classifier and ranker each use 12 configurations selected on time-ordered inner sklearn AP. XGBoost's internal MAP is not substituted for sklearn AP.''')
    code('''fm = read("exp3d_fm1_d7.csv")
print("Historical FM1 sample-only comparison: same positive + 20% negative training sample; do not mix with full-train scores below.")
display(fm[fm.pipeline.str.startswith("fwd_hgb|")].pivot(index="pipeline", columns="scheme", values="d7").round(4))
v65 = read("v65_branch_scores.csv")
branches = ["B0", "B1", "B2", "B3", "XGBc_tuned|core7T", "XGBr_tuned|core7T"]
compare = v65[v65.branch.isin(branches)]
display(compare[["branch", "scheme", "ap_d7", "caught_5", "precision_5", "row_recall_5"]].round(4))
pivot = compare.pivot(index="branch", columns="scheme", values="ap_d7").reindex(branches)
ax = pivot.plot.bar(color=["#087e8b", "#d17b49"], figsize=(11, 4.5))
ax.set(title="Development AP-D7 · historical, full-train comparisons", ylabel="Mean annual AP", xlabel="")
plt.xticks(rotation=20, ha="right"); plt.tight_layout(); plt.savefig(FIGURES / "model_comparison.png", dpi=150); plt.show()''')
    md('''## 9. Class imbalance and performance across periods
Event recall can be high when the model flags just one of a failing bank's positive quarters. AP also reflects how positive bank-quarters rank throughout the list. These are complementary outcomes.

AP also depends on prevalence. A quiet-period AP is not directly comparable to crisis-period AP without reporting class composition; calibration alone does not fix ranking. The project retains raw AP and operational metrics rather than changing evaluation definitions to make values higher.''')
    code('''periods = compare[compare.branch == "B3"][["scheme", "ap_1996-2000", "ap_2001-2007", "ap_2008-2011"]].set_index("scheme")
periods.T.plot.bar(color=["#087e8b", "#d17b49"], figsize=(9, 4))
plt.title("B3 development AP-D7 by economic period"); plt.ylabel("Mean annual AP"); plt.xticks(rotation=0); plt.tight_layout(); plt.savefig(FIGURES / "period_AP.png", dpi=150); plt.show()
years = read("dev_event_counts_by_year.csv")
display(years[years.scheme == "fixed_origin"][["year", "rows", "positive_rows", "positive_rate", "events_with_eligible_window"]])''')
    md('''## 10. Costs, alert chains and a frozen policy scenario
The action is an offsite desk review. Every reviewed alert costs work, including a true alert. A continuous quarterly alert is a repeat review; a missed/non-alerted quarter starts a new file next time. This cold-start/reset rule is an assumption.

`Loss(q) = 110 × 4 × (new_files + 0.5 × repeat_reviews) / 1000 + alpha × missed_event_severity_kUSD2012`.

Each missed event is counted once. Zero COST stays zero; missing severity uses a dev-only median. Latest revised COST and CPI are retrospective descriptors, not costs known to supervisors at the historical decision date.

**Evidence vs assumptions:** OCC's USD110/hour special-examination fee is a proxy, not measured FDIC labour cost. FDIC OIG interview statements motivate 4/12-hour scenarios, not a population average. Repeat effort, productive time, escalation and avoidable-loss fraction are unobserved. The primary `alpha=0.001`, 4 hours and repeat fraction 0.5 are declared illustrative choices, not estimated causal effectiveness.

The final policy minimizes the declared scenario loss over a stated finite q grid on fixed-origin dev predictions; rolling-5y is a sensitivity check. No claim of continuous/global or universally optimal threshold is made. No probability cutoff formula is applied to uncalibrated iRF scores.''')
    code('''costs = read("cost_scenarios.csv")
winners = costs.sort_values(["loss_kusd_2012", "alerts", "q"]).groupby(["scheme", "alpha"], as_index=False).first()
display(winners[["scheme", "alpha", "q", "caught_events", "events", "hours", "peak_quarter_hours", "loss_kusd_2012"]].round(4))
print("Frozen primary q:", policy["selected_q"], "| scenario alpha:", policy["alpha_primary"])
fig, ax = plt.subplots()
for alpha in [.0001, .001, .01]:
    z = costs[(costs.scheme == "fixed_origin") & np.isclose(costs.alpha, alpha)]
    ax.plot(z.q*100, z.loss_kusd_2012/1000, marker="o", label=f"alpha={alpha:g}")
ax.set(xlabel="Quarterly alert share (%)", ylabel="Illustrative loss (million USD 2012)", title="Threshold choice changes with the stated cost preference")
ax.legend(); fig.tight_layout(); fig.savefig(FIGURES / "cost_sensitivity.png", dpi=150); plt.show()''')
    md('''Escalation is a separate uncertain increment, not silently priced as a full onsite exam for every alert. Capacity scenarios convert paid hours to productive hours allocated to this task. Historical peak load is reported; it is not a future capacity guarantee. We do not tune cost assumptions to obtain a desirable alert budget or model winner.''')
    code('''display(read("escalation_sensitivity.csv"))
workload = read("test_workload_sensitivity.csv")
display(workload[(workload.pipeline == "B3") & np.isclose(workload.q, policy["selected_q"]) & (workload.h_new == 4) & (workload.repeat_fraction == .5)][["FTE", "available_hours_scenario", "mean_hours", "peak_hours", "quarters_over_capacity", "quarters"]].round(2))''')
    md('''## 11. Final fit and one-time holdout evaluation
The selected B3 procedure and two predeclared controls were fitted on dev as-of dates through 2011Q4, with all training labels matured by 2012-12-31. The final feature set is the dev-only selection B plus the T block. Models, schemas, seeds, preprocessing, policy and SHA hashes were frozen before constructing test features.

The user authorized one evaluation in this independent edition. The holdout is as-of 2013Q1–2025Q2. The gap year 2012 is not used to fit the models or backfill alert state. Reopening this notebook **replays saved aggregate outputs**.

A technical pre-prediction count check first stopped because the locked key universe also contained out-of-population/censored observations. Applying the pre-existing nonnull-label rule reconciled the cohort. No score had been produced and no model or policy changed during that technical resume.''')
    code('''display(pd.DataFrame([load("test_population_reconciliation.json")]))
display(primary[["pipeline", "q", "AP_D7", "AP_pooled", "ROC_AUC", "TP", "FP", "FN", "TN", "precision", "row_recall", "event_recall", "lead_median_quarters"]].round(4))
run_manifest = load("test_run_manifest.json")
print("Scoring passes:", run_manifest["test_passes"], "| rows:", run_manifest["rows"], "| positive rows:", run_manifest["positive_rows"])'''.replace('load("test_population','json.loads((TABLES / "test_population').replace('reconciliation.json")]))','reconciliation.json").read_text())]))').replace('run_manifest = load("test_run_manifest.json")','run_manifest = json.loads((TABLES / "test_run_manifest.json").read_text())'))
    code('''b3 = primary[primary.pipeline == "B3"].iloc[0]
cm = np.array([[b3.TN, b3.FP], [b3.FN, b3.TP]], dtype=int)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].imshow(np.log1p(cm), cmap="Blues")
for i in range(2):
    for j in range(2): axes[0].text(j, i, f"{cm[i,j]:,}", ha="center", va="center", color="white" if np.log1p(cm[i,j])>9 else "black", fontsize=12)
axes[0].set(xticks=[0,1], yticks=[0,1], xticklabels=["No alert", "Alert"], yticklabels=["Non-failure row", "Failure row"], title=f"B3 test confusion matrix · q={b3.q:.2%}\\nColour uses log(1+count); labels are actual counts")
curves = read("pr_curve_display.csv")
for name, z in curves[curves.series.str.startswith("Test")].groupby("series", sort=False): axes[1].step(z.recall, z.precision, where="post", label=name)
axes[1].set(xlabel="Bank-quarter recall", ylabel="Precision", title="Holdout precision–recall curves")
axes[1].legend(); fig.tight_layout(); fig.savefig(FIGURES / "holdout_results.png", dpi=150); plt.show()''')
    code('''display(test[(test.scope != "all_test") & (test.pipeline == "B3")][["scope", "rows", "positive_rows", "AP_D7", "precision", "row_recall", "caught_events", "events", "event_recall"]].round(4))
display(read("test_cost_scenarios.csv").query("pipeline == 'B3'").round(4))''')
    md('''**Interpretation:** B3 is the preselected model, not the holdout winner. Core7+iRF has higher holdout AP-D7; LR detects one additional unique event at the primary budget. B3 still produces many false alerts. No model is reselected, tuned or relabelled after seeing this comparison. The study supports an auditable review tool, not a production-readiness claim.''')
    md('''## 12. Explainability: what the fitted model uses
The custom imodels forest is explained using exact path-dependent Tree SHAP on its actual tree arrays and training cover. Toy brute-force comparisons and final additivity checks validate the implementation. These attributions explain probabilities after cap/median preprocessing, not unobserved missing values or causal economic effects.

The SHAP overview uses 96 uniformly sampled development training rows; ALE uses 20,000 training rows. These are **in-sample model descriptions**, not independent evidence of generalization. ALE is used in place of a broad PDP grid to reduce unsupported combinations of correlated financial ratios.''')
    code('''shap_summary = read("final_B3_shap.csv")
shap_summary.head(12).sort_values("mean_abs_SHAP_probability").plot.barh(x="feature", y="mean_abs_SHAP_probability", color="#087e8b", legend=False, figsize=(9, 5))
plt.xlabel("Mean |SHAP| · probability scale"); plt.title("B3 associations in a development training sample"); plt.tight_layout(); plt.savefig(FIGURES / "B3_SHAP.png", dpi=150); plt.show()
fig, axes = plt.subplots(2, 2, figsize=(11, 7))
for ax, feature in zip(axes.ravel(), ["eq_assets", "noncurrent_loans", "roa_ttm", "texas_proxy"]):
    al = read(f"final_B3_ALE_{feature}.csv"); ax.plot(al.edge, al.ale, color="#087e8b"); ax.axhline(0, color="grey", linewidth=.6); ax.set(title=feature, xlabel="Feature value (%)", ylabel="Centered probability effect")
fig.tight_layout(); fig.savefig(FIGURES / "B3_ALE.png", dpi=150); plt.show()
checks = json.loads((TABLES / "explainability_checks.json").read_text())
print("SHAP additivity max error:", checks["final_model_SHAP_additivity_max_abs_error"])''')
    md('''## 13. Conclusions and transfer to Vietnam
**Q1 — storage and processing:** typed, compressed Parquet and lazy Polars are practical for this panel on a laptop. The measured benchmark and matching Spark plan support the design; a cluster is justified by workload and memory constraints, not the word “big”.

**Q2 — quality:** the pipeline separates accounting semantics, suspicious values, structural gaps and model imputation. Reversible ledgers and exact-quarter joins make changes reviewable. Revised data, historical quarantine and snapshot-based exit evidence limit point-in-time claims.

**Q3 — modelling:** data support honestly separated development and holdout evaluation, but model complexity did not ensure better generalization. The final comparison exposes a stronger simple-reference AP and a large false-alert workload. Cost preferences remain hypothetical and require operational validation.

For Vietnam, replace US Call Report definitions with SBV/local accounting mappings, obtain publication vintages and event definitions, validate local ownership/funding structures, and estimate reviewer time/capacity from workflow logs. US coefficients, thresholds and proxy fees should not be transferred unchanged.''')
    md('''## 14. Reproducibility and source trail
- **Fast review:** Run All in this notebook reads committed aggregate evidence and regenerates figures. No data download, fit or test access occurs.
- **Scientific implementation:** `src/fdic_risk/rules.py`, `pipeline.py`, `policy.py`, `backtest.py`, `benchmarks.py`, `explain.py`.
- **From raw:** see README for acquisition, the explicit expensive dev-backtest replay and private final-fit workflow. Fresh downloads can differ because source values are revised.
- **Checks:** train-only preprocessing, boundary ties, event deduplication, repeat chains, undefined metrics, feature parity, engine parity, model reload and SHAP additivity.
- **Integrity:** `docs/evidence_manifest.json`, `rule_provenance.json`, `frozen_test_protocol.json` and aggregate run manifests.
- **Research limits:** repeated adaptive development comparisons can create selection bias. Neither bootstrap intervals nor a clean rerun erase it. The holdout was not used to improve this release.
- **AI disclosure:** Claude and OpenAI Codex assisted research, implementation and review; authorship remains the student's responsibility. All claims should be understood and defensible at interview.

References and direct links are listed in `references/README.md`. The public repository URL is added after repository creation; no public repository has been created automatically.''')
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3.11 (FDIC)','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'}})
    setup = next(c for c in nb.cells if c.cell_type == 'code')
    setup.source = setup.source.replace('TABLES = ROOT', 'from fdic_risk.presentation import unpack_results\nunpack_results(include_test=' + repr(include_saved_test) + ')\nTABLES = ROOT', 1)
    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            cell.source = cell.source.replace('The public repository URL is added after repository creation; no public repository has been created automatically.', 'Repository: https://github.com/khanhnlmneuron6-hue/fdic-bank-failure-risk-analytics. Published aggregate inputs are restored from results/summary_tables.zip; bank-level datasets are not included.')
    path=ROOT/'notebooks/fdic_bank_failure_early_warning.ipynb';nbf.write(nb,path)
    if execute:
        from nbclient import NotebookClient
        # Execute in the current verified Python environment, independent of a global kernelspec.
        from jupyter_client import KernelManager
        km=KernelManager(kernel_name='python3');km.kernel_spec.argv=[__import__('sys').executable,'-m','ipykernel_launcher','-f','{connection_file}']
        client=NotebookClient(nb,km=km,timeout=180,resources={'metadata':{'path':str(ROOT)}})
        client.execute();nbf.write(nb,path)
        from nbconvert import HTMLExporter
        html,_=HTMLExporter(template_name='lab').from_notebook_node(nb)
        (ROOT/'reports/portfolio.html').write_text(html)
    return path
