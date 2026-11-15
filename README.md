# Bank-Failure Early Warning Using FDIC Data

**Nguyễn Lê Nam Khánh · 11230976 · National Economics University · BFT65B**

This project prepares FDIC financial reports for bank-failure prediction and evaluates the review workload associated with a quarterly alert list.

[Read the report](reports/FDIC_Risk_Analytics_Report.pdf) · [Open the executed notebook](notebooks/fdic_bank_failure_early_warning.ipynb)

## Data and findings

The acquisition covers 1,682,616 financial reports, 170 quarters and 87 source fields, downloaded on 6 November 2026. Development used 64 chronological validation folds. The final holdout covers prediction quarters 2013Q1–2025Q2, with 273,863 eligible observations and 78 failures.

| Model | Mean annual AP, holdout | Failures detected at the 3.53% alert share |
|---|---:|---:|
| Development-selected iRF (B3) | 0.251 | 68/78 |
| Seven-feature iRF | 0.310 | 68/78 |
| Seven-feature logistic regression | 0.267 | 69/78 |

B3 produced 212 true-positive and 9,310 false-positive bank-quarter alerts. The simpler forest ranked the holdout more accurately; the model was not changed after inspecting these results. The alert share comes from an illustrative cost scenario, not measured supervisory capacity.

## What the pipeline does

1. Downloads Financials, Failures and Institutions from the FDIC API, with completeness checks and resumable partitions.
2. Cleans financial reporting exceptions and constructs quarterly flows, ratios, changes and failure labels.
3. Compares pandas and Polars processing and checks selected calculations with local Spark.
4. Applies preprocessing within training samples, compares models through time and evaluates the fixed final specifications.
5. Reports ranking, event detection, lead time, review costs and model explanations.

## Run the notebook

Use Python 3.11. Create a virtual environment, then run:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python -m pytest -q
python scripts/run_pipeline.py --mode replay
python scripts/check_release.py
```

Alternatively, open `notebooks/fdic_bank_failure_early_warning.ipynb` and run all cells. Saved outputs are already included. The notebook restores its required aggregate inputs from `results/summary_tables.zip`; it does not download bank-level data, train models or score the holdout again. Generated tables and figures stay outside version control. Model seeds are fixed in `config_final.json`.

## Reconstruct the calculations from raw reports

Create a separate workspace so that the published evaluation remains unchanged:

```bash
python scripts/new_reproduction_workspace.py /absolute/path/to/fdic-reproduction
cd /absolute/path/to/fdic-reproduction
python scripts/acquire.py
python scripts/run_pipeline.py --mode rebuild --spark --evaluate-test
```

Spark requires Java 17 or later. The selected 64-fold backtest can take hours. Historical comparisons of other selectors and model families are supplied as recorded summaries; this command reproduces the selected procedure rather than every research experiment. New downloads may differ because FDIC revises historical values. Reproducing this published holdout is not a new independent validation.

## Repository contents

| Location | Purpose |
|---|---|
| `notebooks/` | Executed notebook following the course pipeline |
| `src/fdic_risk/` | Financial transformations, models, metrics, costs and explanations |
| `scripts/` | Acquisition, execution and verification commands |
| `docs/` | Required schemas, feature groups, policy, SQL example and source audit |
| `results/summary_tables.zip` | Only the aggregate outputs required by the notebook and checks |
| `reports/` | Final PDF, processing plans and one result figure |
| `tests/` | Checks for alert policies and financial preprocessing |
| `references/` | Research, software and implementation attribution |

Raw reports, processed bank-level datasets, fitted models, research pilots, editing notes, duplicate HTML exports and LaTeX working files are not included.

## Limitations and sources

The source data contain revisions, publication dates are approximated by a quarterly lag, and some historical reporting rules were identified retrospectively. Repeated development comparisons can introduce selection bias. Review effort and intervention effects were not measured; the cost results describe stated scenarios. SHAP and ALE describe model associations.

Sources are listed in [references](references/README.md), with cost and information-timing qualifications in the [source audit](docs/SOURCE_AUDIT.md). Claude and OpenAI Codex assisted implementation, research and editing.

Repository: https://github.com/khanhnlmneuron6-hue/fdic-bank-failure-risk-analytics
