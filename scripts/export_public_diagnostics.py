from pathlib import Path
import sys,json
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
import pandas as pd,numpy as np
from sklearn.metrics import precision_recall_curve
from fdic_risk.pipeline import ROOT
from fdic_risk.policy import dev_predictions,read_failures,match_events
from datetime import date
curves=[];year=[]
dev=dev_predictions()
for scheme in ['fixed_origin','rolling_5y']:
 d=dev[dev.scheme==scheme];pr,re,_=precision_recall_curve(d.y_true,d.score);ix=np.unique(np.r_[0, np.where(np.diff(re)!=0)[0], np.where(np.diff(re)!=0)[0]+1, len(pr)-1])
 curves += [{'series':'Dev B3 '+scheme,'precision':float(pr[i]),'recall':float(re[i]),'prevalence':float(d.y_true.mean())} for i in ix]
 f=read_failures(date(2012,12,31));ev=match_events(d.reset_index(drop=True),f)
 for y,g in d.groupby(pd.to_datetime(d.prediction_as_of).dt.year):
  e=ev[pd.to_datetime(ev.prediction_as_of).dt.year==y][['CERT','fd']].drop_duplicates()
  year.append({'scheme':scheme,'year':y,'rows':len(g),'positive_rows':int(g.y_true.sum()),'positive_rate':float(g.y_true.mean()),'events_with_eligible_window':len(e),'note':'events can appear in adjacent years; do not sum annual counts'})
t=pd.read_parquet(ROOT/'data/test_predictions_private.parquet')
for label in ['B3','core7_iRF','core7_LR']:
 pr,re,_=precision_recall_curve(t.y_true,t[label]);ix=np.unique(np.r_[0, np.where(np.diff(re)!=0)[0], np.where(np.diff(re)!=0)[0]+1, len(pr)-1])
 curves += [{'series':'Test '+label,'precision':float(pr[i]),'recall':float(re[i]),'prevalence':float(t.y_true.mean())} for i in ix]
pd.DataFrame(curves).to_csv(ROOT/'reports/tables/pr_curve_display.csv',index=False);pd.DataFrame(year).to_csv(ROOT/'reports/tables/dev_event_counts_by_year.csv',index=False)
# Safe workload and formula comparisons; no institution-level export.
from fdic_risk.pipeline import cfg
c=cfg();formulas={'eq_assets':'100 * EQ / ASSET','noncurrent_loans':'100 * NCLNLS / LNLSGR','reserve_loans':'100 * LNATRES / LNLSGR','roa_ttm':'100 * sum(last 4 quarterly NETINC flows) / ASSET','nim_ttm':'100 * sum4(INTINC_flow - EINTEXP_flow) / ASSET','provision_loans_ttm':'100 * sum4(ELNATR_flow) / LNLSGR','ore_assets':'100 * ORE / ASSET','npa_assets':'100 * (NCLNLS + ORE) / ASSET','cash_assets':'100 * CHBAL / ASSET','securities_assets':'100 * SC / ASSET','cd_assets':'100 * LNRECONS / ASSET','cre_assets':'100 * LNRENRES / ASSET','multifam_assets':'100 * LNREMULT / ASSET','resid_assets':'100 * LNRERES / ASSET','texas_proxy':'100 * (NCLNLS + ORE) / (EQ - INTAN + LNATRES); proxy, not official Texas ratio','texas_den_nonpos':'1 if observed loss-buffer denominator <= 0; null if inputs missing','buffer_gap_assets':'100 * (NCLNLS + ORE - EQ + INTAN - LNATRES) / ASSET','uncovered_ncl_assets':'100 * (NCLNLS - LNATRES) / ASSET'}
rows=[]
for col in c['B3_columns']:
 formula=formulas.get(col, f'{col[:-5]}[t] - {col[:-5]}[t-4] by CERT and exact calendar quarter' if col.endswith('_chg4') else 'See field contract')
 rows.append({'feature':col,'formula':formula,'availability':'report quarter + one-quarter assumed release lag; changes use past exact-quarter records only','missing':'undefined ratio or unavailable/isolated source remains null until train-fitted median; no blanket zero-to-null conversion','preprocessing':'train-only ContractCapperV4 and median; no scaler for iRF'})
pd.DataFrame(rows).to_csv(ROOT/'reports/tables/final_feature_contracts.csv',index=False)
