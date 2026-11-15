# Sources and implementation attribution

Source access was tracked separately from implementation checks. A citation supports a method or definition; it does not establish that the project's numerical configuration is optimal. Historical research source logs remain in the private snapshot. The focused sources below support this curated release.

| Source | Use and limit |
|---|---|
| [FDIC BankFind API documentation](https://api.fdic.gov/banks/docs/) | Financials, Failures and Institutions field definitions; thousand-USD units. Revised snapshots are not original publication vintages. |
| [FDIC estimated-loss help](https://banks.data.fdic.gov/bankfind-suite/failures/help) | COST is estimated DIF loss, not the loss causally avoidable by this alert model. Current values can be revised. |
| [FFIEC Call Report instructions](https://www.ffiec.gov/resources/reporting-forms) | Accounting definitions and YTD flows. The limited recovery rules are project-specific identities, not a claim to reconstruct every merger's accounting. |
| [scikit-learn 1.7 AP](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html) | Non-interpolated AP; source `_ranking.py` checked in the research. Annual averaging is a project evaluation choice. |
| [scikit-learn threshold decisions](https://scikit-learn.org/1.7/modules/classification_threshold.html) | Separate statistical scores and decision rules; thresholds require validation separate from fitting. |
| [Cawley & Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html) | Model-selection overfitting and adaptive development limits; a clean rerun does not remove selection bias. Abstract and project research review used. |
| [imodels v3.0.4 iRF source](https://github.com/csinva/imodels/tree/v3.0.4/imodels/tree/iterative_random_forest) | Actual custom forest implementation, feature resampling, sample weights and tree arrays. The installed 3.0.4 code, rather than current master, is authoritative. |
| [XGBoost v3.0.5](https://github.com/dmlc/xgboost/tree/v3.0.5) | Historical classifier/ranker controls only. Wrapper, MAP objective and ranking metric code were checked; library MAP is not sklearn AP. Not required for the final iRF replay. |
| [Polars lazy API](https://docs.pola.rs/user-guide/lazy/) | Projection pushdown and lazy plans; actual execution plan and timings are supplied. |
| [Apache Spark documentation](https://spark.apache.org/docs/latest/) | Local Spark SQL/DataFrame and MLlib pipeline demonstration. Version 4.3.0 was used; local measurements do not prove cluster speedup. |
| [Sarlin (2013), ECB WP 1509](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1509.pdf) | Policy preferences and loss-sensitive EWS evaluation. Does not identify this project's preferred costs, alpha or capacity. Sections 2-2.3 were reviewed in the research. |
| [Elkan (2001)](https://cseweb.ucsd.edu/~elkan/rescale.pdf) | Cost-sensitive decisions. A calibrated per-row Bayes cutoff is not applied to the event/alert-chain objective here. |
| [OCC Bulletin 2011-46, PDF p.4](https://www.occ.gov/static/rescinded-bulletins/bulletin-2011-46.pdf) | Verified USD110/hour fee for special examinations/investigations in the 2012 fee schedule. Proxy only; not a measured FDIC hourly employment cost. |
| [FDIC OIG EVAL-20-002, printed p.11](https://fdicoig.gov/sites/default/files/reports/2022-08/20-002EVAL.pdf) | Interviews with 32 case managers describe heterogeneous first and repeat offsite-review times. Supports scenarios, not population means or model-specific review times. |
| [FDIC OIG AUD-12-011](https://www.fdicoig.gov/sites/default/files/reports/2022-08/12-011AUD.pdf) | Research reviewed Table 3 onsite examination-hour benchmarks. These are not the marginal cost of every model alert and cannot be generalized to every bank size. |
| [FRED CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS) | Latest CPI snapshot converts retrospective severity to 2012 prices. This is not a feature, COST vintage or forecast of future wages. |
| [Lundberg, Erion & Lee, Tree SHAP](https://arxiv.org/abs/1802.03888) | Cover-based Tree SHAP algorithm implemented for imodels arrays. Actual code is inherited from the research, validated against toy brute-force Shapley and final additivity. Not a direct call to `shap.TreeExplainer`. |
| [Apley & Zhu, ALE](https://arxiv.org/abs/1612.08468) | Local-effect plots for dependent predictors. The release uses development-sample ALE, not causal effects. |

## Implementation and attribution

Financial transformations and the custom SHAP/ALE implementation were adapted from the project research notebook. Original cell identifiers and checksums are recorded in `docs/rule_provenance.json`. The notebook and report distinguish historical development comparisons from the final evaluation.

Claude and OpenAI Codex assisted implementation, research and editing. Dependencies retain their respective licences. Report layout drew on [pmichaillat/latex-paper](https://github.com/pmichaillat/latex-paper); no template source or third-party paper is included in this repository. The methodological source audit is in `docs/SOURCE_AUDIT.md`.
