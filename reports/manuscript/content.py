# Manuscript narrative. Evidence values are read from saved aggregate tables.
acq=load('acquisition_summary.json');storage=load('storage_sizes.json')
test=read('test_metrics.csv');primary=[r for r in test if r['scope']=='all_test' and abs(float(r['q'])-policy['selected_q'])<1e-10];b3=next(r for r in primary if r['pipeline']=='B3')
v65=read('v65_branch_scores.csv');v62=read('v62_branch_scores.csv')
def vr(branch,scheme):return next(r for r in v65 if r['branch']==branch and r['scheme']==scheme)

intro('Introduction')
p('Bank supervision requires financial reports that remain comparable as institutions merge, reporting conventions change and economic conditions deteriorate. This project uses US bank data to examine how a central-bank supervision team could construct such a panel and use it to rank institutions for further review. The emphasis is on data preparation and processing, with bank-failure prediction providing an application through which to evaluate the resulting dataset.','first')
p('Earlier studies support the use of accounting information for this purpose. Petropoulos et al. found that random forests performed well in comparisons of models for US bank insolvency, including evaluation on later periods [13]. Their outcome includes assistance transactions as well as failures. The historical evidence in Correia, Luck and Verner links failures to deteriorating fundamentals and funding structures [14]. These findings inform the feature families considered here, while the present analysis defines its outcome as the first qualifying failure of an insured institution.')
p('The pipeline covers more than four decades of FDIC reports and was evaluated through chronological validation and a final holdout. Its selected model detected 68 of 78 holdout failures at an illustrative quarterly alert share of 3.53%, although a simpler reference achieved higher average precision.')

sec('Acquisition and storage')
sub('Source coverage and completeness')
p('The data were downloaded from the FDIC BankFind public API on 6 November 2026 [1]. Financials contains 1,682,616 reports spanning 170 quarters from 1984Q1 to 2026Q2, with 87 fields covering financial values, institutional identifiers and audit information. The accompanying Failures and Institutions tables contain 4,117 and 27,835 records, respectively. CERT identifies institutions across the three sources.','first')
p('The downloader requested a fixed field list and retrieved successive pages within each quarter, retrying interrupted requests. It retained the original responses as compressed JSON and recorded the requested fields, API totals and file hashes in acquisition manifests. All 170 quarterly row counts matched the totals recorded at download. These checks refer to the retained November snapshot, which may differ from later downloads as the FDIC revises its data.')
sub('Storage design and measured compression')
p('Raw response files were kept unchanged so that derived values could be traced to their inputs. Analytical tables were stored as typed Parquet files partitioned by report quarter, allowing transformations to select the required dates and columns [16, 17]. The acquisition manifests also support resumption by checking that completed partitions have the expected fields and hashes.')
fig('data_and_storage','Reporting coverage and storage requirements.',
 'Panel A counts financial reports by quarter. Panel B uses an identical projection of 1,350,892 rows and seven columns for 1984Q1-2011Q3. Sizes use decimal MB. Sources: acquisition_completeness.csv and storage_sizes.json.')
p(f'For the matched seven-column projection, CSV required {storage["csv_bytes"]/1e6:.2f} MB and Parquet with Zstd compression required {storage["parquet_zstd_bytes"]/1e6:.2f} MB. The resulting size ratio was {storage["ratio_csv_to_parquet"]:.2f}. This measurement supports the choice of Parquet for repeated analytical scans of the panel. The processing comparison in Section 3 uses the same projection.')

sec('Data quality and panel construction')
sub('Financial reporting exceptions')
p('The quality checks distinguished unusual financial conditions from reporting problems. Negative equity and losses were retained as potential indicators of distress, while negative stock values and inconsistent accounting components were flagged for investigation. A ratio with a missing or nonpositive denominator remained undefined. Genuine zero balances, such as an absence of borrowing, were preserved.','first')
flags={r['flag']:r for r in read('source_quality_flags.csv')}
quality_rows=[
 ['Negative equity',integer(flags['q_neg_equity']['rows_flagged']),'Retain as an economically meaningful condition.'],
 ['Liabilities above assets',integer(flags['q_liab_gt_asset']['rows_flagged']),'Flag and reconcile with equity and other balance-sheet items.'],
 ['Suspected restart of YTD flows',integer(flags['q_ytd_break']['rows_flagged']),'Review the affected income sequence.'],
 ['Negative stock value',integer(flags['q_neg_stock']['rows_flagged']),'Investigate and isolate affected derived values where required.'],
 ['Nonpositive gross loans',integer(flags['q_den_nonpos_LNLSGR']['rows_flagged']),'Leave ratios using that denominator undefined.'],
 ['Nonpositive deposits',integer(flags['q_den_nonpos_DEP']['rows_flagged']),'Leave the loan-to-deposit ratio undefined.'],
]
tab('Selected exceptions identified by the automated quality checks.', ['Condition','Flagged rows','Treatment'],quality_rows,[158,76,225.28],
 'Scope: 1,350,892 raw reports, 1984Q1-2011Q3. Flags can overlap within a row. Flagged observations were reviewed under the financial rules described in the text. Source: source_quality_flags.csv.',numeric=(1,))
p('Income reporting required a separate treatment because Call Report income schedules record amounts accumulated since the start of the calendar year <cite key="ffiec" locator="Schedule RI-1"></cite>. The pipeline used a reported quarterly counterpart where available and otherwise calculated differences between consecutive reports for the same CERT. Trailing-twelve-month (TTM) measures required four consecutive calendar quarters.')
p('A decline across several YTD income items was treated as a possible change in the accounting basis. Affected TTM windows were set to missing under the rule identified as Y1 in the implementation. Limited accounting identities recovered selected historical values when consistency checks were satisfied. Subsequent successor relationships were reserved for audit evidence, so recovery of a predictor depended on information allowed by the feature construction rules.')
p('The rules also isolated an ambiguous real-estate decomposition in historical thrift reports. Each adjustment was recorded against the affected derived cell, with the original value retained. This record distinguishes missing history, undefined ratios and suspected reporting problems before imputation. Numerical parity checks confirmed that the revised feature builder reproduced the approved research representation within the specified tolerance.')
sub('Outcome definition and institution exits')
p('The binary target records whether institution i experiences its first qualifying failure during the four quarters following prediction date t. <i>T</i><sub>i</sub> denotes the date of that failure. Mergers and assistance transactions were classified separately.','first')
eq('',1)
p('The modelling population excluded observations after an institution had exited and observations outside the eligible insured population. Incomplete outcome horizons and uncertain exits were censored under the recorded population rules. Current institution metadata helped classify outcomes but was excluded from the predictor matrix. Because several reporting quarters can precede the same failure, the evaluation tracks both positive rows and unique failure events.')
sub('Information timing and analytical samples')
p('A financial report for quarter r was assumed available at the end of quarter r + 1. Features were joined to the corresponding prediction date using CERT and exact calendar quarters. This one-quarter lag approximates publication availability because historical release timestamps are unavailable in the retained snapshot.','first')
p('The final training sample ended at 2011Q4, with its outcomes complete by 31 December 2012. The year 2012 provided a gap before the holdout began in 2013Q1. The holdout ended at 2025Q2, allowing its one-year outcomes to be observed through 2026Q2. Table 2 reports the observations and failure events included at each stage.')
tab('Acquisition records and analytical populations.', ['Population','Rows','Positive rows','Failure events'],[
 'Panel A. Source records',
 ['Financials, 1984Q1-2026Q2',integer(acq['financial_rows']),'-','-'],
 ['Failures source',integer(acq['small_tables']['failures']['rows']),'-','Source records'],
 ['Institutions source',integer(acq['small_tables']['institutions']['rows']),'-','-'],
 'Panel B. Analytical samples',
 ['Final training, 1984Q2-2011Q4','1,306,763','10,564','2,729'],
 ['Validation, 1996-2011','594,873','1,981','514'],
 ['Initial holdout keys','280,267','-','-'],
 ['Less: unlabelled or ineligible','(6,404)','-','-'],
 ['Evaluable holdout, 2013Q1-2025Q2','273,863','257','78'],
 ],[224.28,80,78,77],
 'Validation counts are per primary scheme. The holdout population follows the registered eligibility and nonnull-label criteria. Sources: acquisition_summary.json, final_fit_manifest.json, B3_dev_operating_metrics.csv, test_population_reconciliation.json and test_metrics.csv.',numeric=(1,2,3))

sec('Scalable processing')
sub('Comparable transformations in pandas and Polars')
p('The processing comparison applied the same scan, exact-quarter self-join, financial ratios and quarterly aggregation to the seven-column projection. CSV types were supplied explicitly. Each pandas and Polars operation was repeated three times under a warm operating-system cache, and numerical equivalence was checked before execution times were compared.','first')
bench=read('storage_processing_benchmarks.csv');spark=load('spark_mllib_demo.json')
bench_labels=['pandas: CSV scan','pandas: Parquet scan','Polars: Parquet scan','Polars: two-column projection','Polars: join, ratios and aggregate','pandas: join, ratios and aggregate']
tab('Execution times for the matched local workload.', ['Operation','Seconds','Measurement'],
 [[label,fmt(r['median_seconds'],4),'Median of three repetitions'] for label,r in zip(bench_labels,bench)]+[['Spark: local query',fmt(spark['spark_query_seconds_startup_excluded'],4),'One action, startup excluded']],
 [239.28,60,160],
 'The projection comprises CERT, REPDTE, ASSET, EQ, LNLSGR, NCLNLS and NETINC. Measurements used a macOS arm64 laptop with 10 logical CPUs. The Spark query ran in local[2] mode. Its timing is reported separately from the repeated pandas/Polars benchmark. Sources: storage_processing_benchmarks.csv, storage_sizes.json and spark_mllib_demo.json.',numeric=(1,))
p('Polars completed the join, ratios and aggregation in a median 0.073 seconds, compared with 0.569 seconds for pandas. Parquet scans were also faster than the CSV scan in this workload. The optimized Polars plan reused the scan through a cache and projected the right-hand join input to the required keys and income column. The query was collected after the transformations and aggregation [17]. Exact calendar keys ensured that a missing quarter remained a gap rather than becoming the previous available row.')
sub('Spark results and implications for scaling')
p('The Spark implementation reproduced the benchmark transformations and agreed with pandas and Polars on all reported aggregate columns. The maximum floating-point difference was approximately 5 × 10<super>-14</super>. Its query action took 2.943 seconds after startup. The saved physical plan includes an adaptive execution plan, join stages and an ordered final result, providing a basis for examining partitioning and exchanges [18].','first')
p('The acquisition and panel-processing tasks completed on the laptop. For this workload, local Polars avoided the scheduling overhead evident in the Spark demonstration. A cluster would become relevant for wider transaction joins, concurrent analytical jobs or workloads whose intermediate results exceed local memory. That decision would require measurements of memory consumption and shuffle volume at the intended scale, since the present timing comparison covers a local execution only.')

sec('Feature construction and preprocessing')
sub('Financial representation')
p('The feature pool comprised 21 economic groups constructed from the 87 source fields. Capital adequacy and asset quality describe loss absorption and impaired exposures, while earnings, funding ratios and portfolio concentrations provide further measures of financial condition [13, 14]. Groups combined current levels, TTM income measures and changes over four quarters.','first')
tab('Feature families and construction rules.', ['Family','Representation'],[
 ['Capital and asset quality','Equity/assets, noncurrent loans, other real estate (ORE)/assets and nonperforming assets (NPA)/assets.'],
 ['Earnings and provisions','Return on assets (ROA), net interest margin (NIM) and provisions based on validated quarterly flows.'],
 ['Concentration and liquidity','Four real-estate shares, cash/assets and securities/assets.'],
 ['Changes over four quarters','Differences matched by CERT and the exact quarter four periods earlier.'],
 ['Loss-buffer measures','Texas proxy, nonpositive-buffer indicator, buffer gap/assets and uncovered noncurrent loans/assets.'],
 ],[125,334.28],
 'Exact formulas and column order are recorded in final_feature_contracts.csv. Financial amounts use thousands of USD and ratios use percent. Unavailable histories remain missing until preprocessing.')
p('Forward selection used histogram gradient boosting (HGB) to evaluate economic groups within each training window. After the modelling procedure was selected, the selector was fitted again on the complete development sample, retaining 12 groups with 20 columns. Four additional loss-buffer measures brought the final candidate to 24 predictors. This candidate is labelled B3 in the experiment records and in the result tables.')
p('The additional measures describe impaired assets relative to tangible capital and loan-loss reserves. The Texas proxy uses noncurrent loans plus ORE in its numerator and equity less intangibles plus reserves in its denominator. A separate indicator records a nonpositive denominator, while the gap and uncovered-loan measures express shortfalls relative to total assets. These features were introduced after earlier development comparisons, which is relevant to the selection uncertainty discussed in Section 6.')
sub('Preprocessing within training samples')
p('For each fit, the pipeline estimated domain-specific clipping bounds from the training sample and then fitted median imputation to the same observations. Signed financial quantities and changes retained their permitted signs, with special handling for sparse positive tails. The capper implementation is named ContractCapperV4 in the source code. Logistic regression additionally used standardization fitted on the training sample. A fit was stopped if any predictor had entirely missing training values.','first')
p('A separate record retained the reasons for missing values after imputation. These reasons were not supplied to the model as predictors. Median imputation without missingness indicators can therefore make an imputed value indistinguishable from an observed value at the median. Earlier comparisons examined alternative clipping and indicator specifications, and the final model retained the representation selected during development. Their results apply to the tested specifications and evaluation periods.')

sec('Modelling and validation')
sub('Chronological validation and evaluation metrics')
p('Validation covered 16 years from 1996 to 2011 under fixed-origin, expanding, rolling-five-year and rolling-ten-year training schemes. The schedule therefore comprised 64 folds but only 49 distinct training windows, allowing identical training samples to share a fit. Feature selection and preprocessing were repeated within each training window, with label maturity and a four-quarter gap enforced.','first')
p('The primary comparison used the fixed-origin and rolling-five-year schemes. Ranking was assessed with non-interpolated average precision (AP), computed from the precision-recall curve [10]. Mean annual AP gave equal weight to years containing positive rows, excluding 2005 from development because it had no positives. Pooled AP was computed over all observations together. In equation (2), <i>R</i><sub>k</sub> and <i>P</i><sub>k</sub> denote recall and precision at successive score thresholds, and the set of years containing positives is <i>Y</i><sub>+</sub>.')
eq('',2)
p('Precision and row recall assessed the quarterly alerts, while event recall measured the proportion of unique failures preceded by at least one eligible positive-quarter alert. Lead time and alert volume described the timing and workload of detection. These quantities are useful alongside AP when failures are rare [21].')
p('Development selection combined mean annual AP and event recall at a reference 5% alert share across the two primary schemes. The minimax relative-regret criterion, recorded as D43 in the research documentation, favored B3. The 5% share represented an evaluation preference. The subsequent cost analysis selected the final illustrative alert share separately. Repeated inspection and extension of the candidate set can introduce selection optimism despite chronological splitting [2].')
sub('Models and development results')
p('The selected model used an iterative random forest (iRF), which reweights feature sampling across successive forests [20]. It contained 50 trees with maximum depth 6 and a minimum leaf size of 50, fitted over three reweighting iterations. Bootstraps used for interaction discovery were disabled in the predictive implementation [9]. This specification was held fixed in the reported iRF comparisons.','first')
p('The controls comprised iRF and logistic regression fitted to seven core features. These were equity/assets, noncurrent loans, reserves/loans, ROA, loans/deposits, borrowing/assets and log assets. Development experiments also evaluated an expanded feature pool and XGBoost classifier and ranking models, with tuning conducted inside the corresponding training samples.')
fig('model_comparison','Model comparison under the two primary validation schemes.',
 'Points report mean annual AP. The forward + T iRF specification is B3, with T denoting its four loss-buffer features. XGBoost used the seven core features plus T. Comparisons used the full training samples. Source: v65_branch_scores.csv.')
p('B3 increased mean annual AP from 0.243 to 0.248 under fixed-origin validation and from 0.207 to 0.213 under rolling-five-year validation relative to the forward-selected forest without the additional loss-buffer measures. Selection from the expanded pool did not improve the two primary comparisons. Tuned XGBoost classifier and ranking models remained below the iRF candidates, with larger shortfalls under rolling-five-year training. Supplementary selector and model comparisons appear in Appendix A.')
sub('Variation across economic periods')
fig('period_ranking','B3 ranking performance and failure prevalence by period.',
 'Panel A reports mean annual AP. Panel B reports positive-row prevalence for the fixed-origin sample in each period. Source: v62_period.csv.')
p('Mean annual AP for B3 was approximately 0.060 during 2001-2007, compared with 0.522 during 2008-2011 under fixed-origin validation. Positive-row prevalence also increased from 0.052% to 1.380% between these periods. Since AP depends on the class distribution, the observed gap reflects a comparison of different economic and event environments as well as model performance [21].','first')
p('The prediction diagnostics found weaker ranking among observations nine to twelve months before failure and limited precision near the top of the list. A failure could still count as detected if the bank received an alert in a later positive quarter. High event recall can thus coexist with weaker early detection. Strictly monotone probability calibration preserves score ordering and would not address that ranking limitation by itself.')
sub('Alert policy and cost assumptions')
p('Each eligible institution received a risk score, and the alert policy selected a quarterly share q for an offsite desk review. The cost calculation distinguished new reviews from reviews repeated in consecutive quarters. A nonalerted or missing quarter started a new review when an alert next appeared, and the holdout review history began without prior alerts.','first')
p('Equation (3) combines review effort with the severity of missed failure events. Here c is the hourly cost in 2012 dollars, h is the time required for a first review, and ρ is repeat effort relative to a first review. <i>S</i><sub>missed</sub> sums missed-event severity in thousands of 2012 dollars, with each missed event counted once. The weight α specifies the decision scenario [3, 4].')
eq('',3)
tab('Inputs to the review-cost scenarios.', ['Input','Source or interpretation','Treatment'],[
 ['USD 110 per hour','Historical OCC fee [5]','Proxy for hourly review cost.'],
 ['4 or 12 hours','FDIC OIG interviews [6]','Alternative first-review scenarios.'],
 ['Repeat effort ρ','Unobserved workflow quantity','Values 0.25, 0.5 and 1, with 0.5 in the primary case.'],
 ['Severity weight α','Decision preference and intervention uncertainty','Grid from 0 to 0.1, with 0.001 in the primary case.'],
 ['FDIC COST and CPI','Estimated fund loss and price conversion [1, 8, 15]','2012 price basis, preserving zero and using a development-cohort median for missing severity.'],
 ['Capacity and escalation','Staffing assumptions and examination benchmarks [7]','Separate workload sensitivity calculations.'],
 ],[101,163,195.28],
 'COST measures estimated loss to the deposit insurance fund. Revised COST and CPI are used as retrospective severity weights. Scenario definitions are recorded in docs/cost_policy.json.')
p('The hourly proxy follows the OCC fee for special examinations and investigations <cite key="occ" locator="p. 4"></cite>. The 4- and 12-hour cases reflect heterogeneous review times reported in interviews with 32 case managers <cite key="oig2019" locator="p. 11"></cite>. Actual staff cost, repeat effort and intervention effectiveness were not estimated from the bank panel. The reported loss is consequently conditional on these assumptions.')
fig('cost_sensitivity','Sensitivity of development loss to the alert share and severity weight.',
 'B3 fixed-origin predictions with c = USD 110/hour, h = 4 and ρ = 0.5. The vertical line marks q = 3.53%, selected for α = 0.001 from the specified finite grid. Sources: cost_scenarios.csv and docs/cost_policy.json.')
s=policy['selected_dev_result']
p(f'Under the primary scenario, the development loss was minimized at q = {pct(policy["selected_q"],2)}. This produced {integer(s["alerts"])} alerts, comprising {integer(s["new_files"])} new reviews and {integer(s["repeat_reviews"])} repeats, and detected {s["caught_events"]} of {s["events"]} failures. Estimated review effort totaled {integer(s["hours"])} hours and peaked at {integer(s["peak_quarter_hours"])} hours in one quarter. Review cost was USD {s["review_cost_kusd_2012"]/1000:.3f} million and total scenario loss was USD {s["loss_kusd_2012"]/1000:.3f} million in 2012 prices.','first')
p('The selected share was fixed before the holdout evaluation. Rolling-five-year outcomes and alternative review durations were retained as sensitivity cases. Capacity calculations applied assumptions about productive hours and staff allocation, while escalation scenarios used examination workloads of 335-1,820 hours for banks with assets up to USD 1 billion <cite key="oig2012" locator="Table 3"></cite>. These quantities describe different supervisory activities and require local workflow evidence before operational use.')
sub('Final holdout evaluation')
p('B3 and the two seven-feature controls were fitted on the complete development sample after their specifications had been selected. The features and alert share were fixed before the 2013Q1-2025Q2 holdout was scored. Each model received one scoring pass on the 273,863 eligible observations, whose positive rate was 0.094%. The comparisons below were calculated from those saved predictions.','first')
body=['Panel A. Ranking performance']
for r in primary:
 body.append([{'B3':'B3','core7_iRF':'Seven-feature iRF','core7_LR':'Seven-feature logistic'}[r['pipeline']],fmt(r['AP_D7']),fmt(r['AP_pooled']),fmt(r['ROC_AUC'])])
body+=['Panel B. Detection at the 3.53% quarterly alert share', ['Model','Failures detected','Row recall','Precision']]
for r in primary:
 body.append([{'B3':'B3','core7_iRF':'Seven-feature iRF','core7_LR':'Seven-feature logistic'}[r['pipeline']],r['caught_events']+'/'+r['events'],pct(r['row_recall']),pct(r['precision'],2)])
tab('Ranking and detection on the final holdout.', ['Model','Annual AP','Pooled AP','ROC-AUC'],body,[156.28,110,96,97],
 'The holdout contains 273,863 bank-quarter observations, 257 positive rows and 78 failures. The same quarterly alert share applies to all models, with realized counts determined by the specified treatment of ties. Source: test_metrics.csv.',numeric=(1,2,3))
fig('holdout_ranking','Holdout precision-recall curves and the B3 alert-share comparison.',
 'Panel A uses all retained recall-change points. Panel B reports B3 at the predeclared alert shares. Sources: pr_curve_display.csv and test_metrics.csv.')
sub('Detection and review workload')
tab('B3 confusion matrix at a quarterly alert share of 3.53%.', ['Observed outcome','No alert','Alert','Total'],[
 ['Failure within one year',integer(b3['FN']),integer(b3['TP']),'257'],
 ['No failure within one year',integer(b3['TN']),integer(b3['FP']),'273,606'],
 ['Total','264,341','9,522','273,863'],
 ],[214.28,80,80,85],
 'The counting unit is a bank-quarter observation. Source: test_metrics.csv.',numeric=(1,2,3))
p(f'B3 detected 68 of 78 failures, giving event recall of {pct(b3["event_recall"],2)}. Of these, 49 failures were detected at least two quarters in advance. Across individual positive quarters, recall was {pct(b3["row_recall"],2)} and precision was {pct(b3["precision"],2)}. The confusion matrix contains 212 true positives and 9,310 false positives. Under the primary effort assumptions, these alerts required 23,004 review hours over the holdout, with a peak of 988 hours in one quarter.','first')
p('The seven-feature iRF achieved higher mean annual AP than B3, at 0.310 versus 0.251. Logistic regression detected one additional failure at the same quarterly share. B3 remained the candidate selected during development. Its stronger development performance did not carry over to the holdout ranking, and the additional representation did not improve this final comparison.')
sub('Spark MLlib demonstration')
p(f'The MLlib example fitted logistic regression using data through 2009 and evaluated it on 2011. The validation sample contained {integer(spark["validation_rows"])} rows, including {integer(spark["positive_rows"])} positives, and produced AP of {fmt(spark["AP"])} and ROC-AUC of {fmt(spark["ROC_AUC"])}. The pipeline included approximate-median imputation, vector assembly, scaling and regularization. Because these settings differ from the scikit-learn controls, this example evaluates the Spark modelling workflow separately from the principal model comparison.','first')
sub('Model interpretation')
fig('explainability','Development-sample explanations of B3.',
 'Panel A reports mean absolute Tree SHAP contributions in percentage points for 96 uniformly sampled training observations. Panel B reports first-order ALE for equity/assets using 20,000 training observations. Sources: final_B3_shap.csv and final_B3_ALE_eq_assets.csv.')
p('Path-dependent Tree SHAP was calculated from the fitted trees and the weighted number of training observations reaching each node [11]. Numerical checks compared the implementation with brute-force Shapley calculations on small examples and verified additivity for the fitted model. The attributions refer to the representation after clipping and median imputation.','first')
p('Accumulated local effects (ALE) describe changes in model predictions within local feature intervals, which reduces reliance on the broad combinations of correlated inputs used in conventional partial-dependence plots [12]. Both explanations used development observations. Their role is to describe the fitted model, with correlated accounting measures potentially sharing attribution.')

sec('Conclusions and implications for Vietnam')
sub('Storage, quality and early-warning performance')
p('The storage and processing results support a local columnar workflow for this panel. Retaining original response files preserved the acquisition record, while quarter-partitioned Parquet reduced storage and supported selective scans. Polars executed the matched transformation faster than pandas on the measured workload. Spark reproduced the calculations, although wider or concurrent workloads would be needed to assess a cluster advantage.','first')
p('The main financial-data problems involved ambiguous zeros, missing histories, uncertain exits and changes in the basis of reported income. Exact calendar joins and records of reporting exceptions allowed these cases to receive distinct treatments before modelling. Historical data revisions and the assumed reporting lag remain limitations to evaluation using information available at the time. The rule isolating ambiguous historical thrift reports was also developed retrospectively. Together, these limitations prevent the evaluation from reproducing a dataset constructed solely from information available at each historical prediction date.')
p('The holdout results support evaluating a review list through ranking and workload together. B3 detected most observed failures at the selected share but generated many false alerts, while the seven-feature iRF ranked the same holdout more accurately. Repeated development comparisons and the later addition of loss-buffer features may have favored the selected candidate [2]. Since the holdout has now been evaluated, further model development would require a separate test window for an independent assessment.')
p('Review costs remain a substantive empirical gap. Alert counts and review chains were measured from predictions, whereas unit effort and the weight on missed severity came from external proxies and scenario choices. Operational review logs would be needed to estimate those quantities and assess whether warnings change subsequent losses. The current cost results describe the specified decision scenarios.')
sub('Adaptation to Vietnam')
p('An application in Vietnam would begin by mapping State Bank of Vietnam reporting definitions to the local balance-sheet and income fields, with institution identifiers linked through mergers and exits. Historical publication dates and revisions would be needed to reconstruct the information available at each prediction date. Distress outcomes would also need a local definition consistent with the intended supervisory action.','first')
p('The review policy would then be estimated from local case-handling times, staff allocation and escalation records. Differences in funding structure and supervisory practice would require validation of the features and ranking model on Vietnamese institutions. The acquisition procedures, accounting checks and evaluation methods provide a starting point for that local validation.')

sec('Reproducibility')
p('The accompanying code and executed notebook document the acquisition rules, financial transformations and evaluation procedure. The presentation notebook reads aggregate result tables, while separate commands reconstruct the private calculations from the documented data snapshot. Historical selector and model comparisons were retained with checksums identifying their source files. Final model fits, processing benchmarks and the holdout scoring were executed for this edition.','first')
tab('Materials provided with the project.', ['Material','Contents'],[
 ['Executed notebook','Pipeline narrative and recorded outputs in 37 cells.'],
 ['Source modules and tests','Acquisition, panel construction, features, metrics, review costs and numerical checks.'],
 ['Aggregate tables and figures','Development comparisons, processing measurements, holdout results and sensitivity calculations.'],
 ['Data and fitted models','Stored outside the public bundle, with acquisition and reconstruction instructions in the README.'],
 ['Documentation','Source attribution, feature definitions, evaluation protocol and software requirements.'],
 ],[139.28,320],
 'The selected modelling procedure has an extracted 64-fold replay implementation. Its full historical search was not rerun during preparation of this report. Documentation identifies the origin of inherited and newly computed results.',barrier_after=True)
p('The initial holdout population check stopped before prediction because its key list included unlabelled or ineligible records. Applying the existing label and population rules excluded 6,404 records from the 280,267 listed observations, leaving 273,863 eligible observations for evaluation. Model specifications and the alert share were unchanged during this correction. The execution record is retained with the evaluation protocol.')

begin_appendix()
sec('Supplementary selector and model comparisons')
p('The following tables retain the stages of development in which selectors and model families were compared. Their experimental samples and selection rules are identified in the notes.','first')
sub('Ranking and event detection')
body=[]
for sc,label in [('fixed_origin','Panel A. Fixed-origin validation'),('rolling_5y','Panel B. Rolling-five-year validation')]:
 body.append(label)
 for branch,desc in [('B1','Seven-feature iRF'),('B0','Forward iRF'),('B3','Forward + T iRF')]:
  z=vr(branch,sc);body.append([desc,fmt(z['ap_d7']),z['caught_1']+'/514',z['caught_5']+'/514',pct(z['precision_5'],2)])
tab('Ranking and failure detection at the reference alert shares.', ['Model','Annual AP','Detected at 1%','Detected at 5%','Precision at 5%'],body,[139.28,64,87,87,82],
 'Each scheme contains 594,873 rows, 1,981 positive rows and 514 failures. T denotes the four loss-buffer features. Source: v65_branch_scores.csv.',numeric=(1,2,3,4))
sub('Selector and model-family comparisons')
fs=read('exp3d_fs1_d7.csv');valid=[r for r in fs if not r['pipeline'].startswith('glasso|')]
ordered=sorted(valid,key=lambda r:float(r['fs_score']),reverse=True)[:8]
selector_names={'mrmr_full|lr':'mRMR + logistic','mrmr_hgb|lr':'mRMR-HGB + logistic','fwd_hgb|lr':'Forward-HGB + logistic','core7|lr':'Seven-feature logistic','stab_l1|lr':'L1 stability + logistic','sffs_hgb|lr':'Floating-HGB + logistic','fwd_hgb|hgb':'Forward-HGB + HGB','ga_hgb|lr':'Genetic-HGB + logistic'}
tab('Eight leading candidates in the selector comparison.', ['Selector and estimator','Fixed origin','Rolling 5y','Mean'],
 [[selector_names.get(r['pipeline'],r['pipeline']),fmt(r['fixed_origin']),fmt(r['rolling_5y']),fmt(r['fs_score'])] for r in ordered],
 [219.28,80,80,80],
 'The mean averages the two scheme-specific annual AP values. mRMR denotes minimum redundancy maximum relevance, and HGB denotes histogram gradient boosting. Candidates were ordered by that mean. Original group-lasso estimates without established convergence were excluded. Source: exp3d_fs1_d7.csv.',numeric=(1,2,3))
fm=read('exp3d_fm1_d7.csv');names=sorted({r['pipeline'] for r in fm if r['pipeline'].startswith('fwd_hgb|')});body=[]
model_names={'ebm_main':'Additive explainable boosting','ebm_pair':'Explainable boosting with pairwise terms','hgb':'Histogram gradient boosting','irf':'Iterative random forest','kernel':'Kernel approximation','lr':'Logistic regression','rulefit':'RuleFit'}
for name in names:
 z={r['scheme']:r for r in fm if r['pipeline']==name}
 if 'fixed_origin' in z and 'rolling_5y' in z:body.append([model_names.get(name.split('|')[-1],name),fmt(z['fixed_origin']['d7']),fmt(z['rolling_5y']['d7'])])
tab('Model families evaluated with the forward-selected representation.', ['Model','Fixed origin','Rolling 5y'],body,[279.28,90,90],
 'Training used all positives and a 20% negative subsample without weighting. Scores are mean annual AP. The principal B3 comparisons used the full training sample. Source: exp3d_fm1_d7.csv.',numeric=(1,2))
