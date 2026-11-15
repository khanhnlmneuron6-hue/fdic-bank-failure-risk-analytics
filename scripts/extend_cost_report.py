"""Post-freeze descriptive monetary severity and workload; never choose a new policy."""
from pathlib import Path
import sys,json
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
import numpy as np,pandas as pd
from datetime import date
from fdic_risk.pipeline import ROOT,source_root,dump_json
from fdic_risk.policy import alerts,read_failures,match_events,chain_counts
policy=json.loads((ROOT/'docs/cost_policy.json').read_text());p=pd.read_parquet(ROOT/'data/test_predictions_private.parquet');p.prediction_as_of=pd.to_datetime(p.prediction_as_of)
f=read_failures(date(2026,6,30));cpi=pd.read_csv(source_root()/'data/raw/macro_cpi_v1/CPIAUCNS_latest.csv');cpi.columns=['month','cpi'];cpi.month=pd.to_datetime(cpi.month).dt.to_period('M');f['month']=f.fd.dt.to_period('M');f=f.merge(cpi,on='month',how='left');f['severity']=pd.to_numeric(f.COST,errors='coerce')*policy['price_index_base']/pd.to_numeric(f.cpi,errors='coerce')
u=policy['selected_dev_result']['unknown_value_kusd'];rows=[];capacity=[]
for model in ['B3','core7_iRF','core7_LR']:
 d=p[['CERT','prediction_as_of','y_true',model]].rename(columns={model:'score'}).reset_index(drop=True)
 for q in sorted(set([policy['selected_q'],.01,.05,.1])):
  a=alerts(d,q);events=match_events(d,f);cohort=events[['CERT','fd','severity']].drop_duplicates(['CERT','fd']);hit=events.loc[a[events['index'].to_numpy()],['CERT','fd']].drop_duplicates();cohort=cohort.merge(hit.assign(hit=True),on=['CERT','fd'],how='left');miss=cohort.loc[cohort.hit.isna(),'severity'];new,rep,load=chain_counts(d,a)
  cost=110*4*(new+.5*rep)/1000;severity=float(miss.fillna(u).sum());caught=float(cohort.loc[cohort.hit==True,'severity'].fillna(u).sum())
  rows.append({'pipeline':model,'q':q,'review_cost_kusd_2012':cost,'missed_severity_kusd_2012':severity,'unknown_missed_events':int(miss.isna().sum()),'fixed_dev_unknown_value_kusd':u,'scenario_loss_kusd_2012':cost+.001*severity,'break_even_alpha_vs_never':cost/caught if caught else None,'note':'retrospective severity-weighted scenario; not realized savings'})
  for hn in [4.,12.]:
   for rho in [.25,.5,1.]:
    hours=hn*(load['new']+rho*load['repeat'])
    for fte in [1,2,4,8]:
     available=fte*520*.75*.5
     capacity.append({'pipeline':model,'q':q,'h_new':hn,'repeat_fraction':rho,'FTE':fte,'paid_hours_per_quarter':520,'productive_share':.75,'allocation_share':.5,'available_hours_scenario':available,'mean_hours':float(hours.mean()),'peak_hours':float(hours.max()),'quarters_over_capacity':int((hours>available).sum()),'quarters':len(hours),'escalation':'excluded from desk-review scope; sensitivity reported separately'})
pd.DataFrame(rows).to_csv(ROOT/'reports/tables/test_cost_scenarios.csv',index=False);pd.DataFrame(capacity).to_csv(ROOT/'reports/tables/test_workload_sensitivity.csv',index=False)
# Escalation is an uncertain increment per newly opened file, never asserted to occur at a measured rate.
e=[]
for rate in [0,.01,.05]:
 for hours in [335,1820]:
  e.append({'new_file_escalation_probability_scenario':rate,'hours_per_escalation_proxy':hours,'expected_extra_hours_per_new_file':rate*hours,'scope_limit':'OIG onsite-exam benchmark for banks up to USD1bn; not a universal marginal alert cost'})
pd.DataFrame(e).to_csv(ROOT/'reports/tables/escalation_sensitivity.csv',index=False)
print('Cost and workload descriptors completed; frozen policy unchanged')
