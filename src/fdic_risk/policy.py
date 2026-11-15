"""Ranking metrics and transparent event/alert-chain loss scenarios."""
from __future__ import annotations
from datetime import date
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import average_precision_score,roc_auc_score,confusion_matrix
from .pipeline import ROOT,source_root,sha,dump_json

def alerts(scores,q):
    """Top floor(q*n) per quarter; drop the entire boundary tie if it crosses quota."""
    a=np.zeros(len(scores),bool)
    for _,g in scores.groupby('prediction_as_of',sort=True):
        k=int(np.floor(q*len(g)))
        if not k:continue
        if k==len(g):a[g.index]=True;continue
        v=g.score.to_numpy();cut=np.partition(v,len(v)-k)[len(v)-k]
        gt=v>cut;ge=v>=cut
        a[g.index]=ge if ge.sum()<=k else gt
    return a

def match_events(scores,failures):
    """Eligible events have at least one positive prediction window; counted once."""
    x=scores.loc[scores.y_true==1,['CERT','prediction_as_of']].reset_index().merge(failures,on='CERT',how='inner')
    asof=pd.to_datetime(x.prediction_as_of);end=asof+pd.DateOffset(years=1)
    return x.loc[(x.fd>asof)&(x.fd<=end)].copy()

def summarize(scores,a,failures):
    y=scores.y_true.to_numpy(dtype=int);s=scores.score.to_numpy();tn,fp,fn,tp=confusion_matrix(y,a,labels=[0,1]).ravel()
    events=match_events(scores,failures);all_ev=events[['CERT','fd']].drop_duplicates()
    hits=events.loc[a[events['index'].to_numpy()]]
    first=hits.groupby(['CERT','fd'],as_index=False).prediction_as_of.min()
    lead=(first.fd-pd.to_datetime(first.prediction_as_of)).dt.days/91.3125
    ap_year=[]
    for _,g in scores.groupby(pd.to_datetime(scores.prediction_as_of).dt.year):
        if g.y_true.sum()>0:ap_year.append(average_precision_score(g.y_true,g.score))
    pos=int(y.sum())
    return {'rows':len(y),'positive_rows':pos,'prevalence':float(y.mean()),'AP_D7':float(np.mean(ap_year)) if ap_year else None,'AP_pooled':float(average_precision_score(y,s)) if pos else None,'ROC_AUC':float(roc_auc_score(y,s)) if 0<pos<len(y) else None,'TP':int(tp),'FP':int(fp),'FN':int(fn),'TN':int(tn),'alerts':int(a.sum()),'precision':float(tp/(tp+fp)) if tp+fp else None,'row_recall':float(tp/pos) if pos else None,'FPR':float(fp/(fp+tn)) if fp+tn else None,'accuracy':float((tp+tn)/len(y)),'always_negative_accuracy':float(1-y.mean()),'events':len(all_ev),'caught_events':len(first),'event_recall':len(first)/len(all_ev) if len(all_ev) else None,'lead_median_quarters':float(lead.median()) if len(lead) else None,'events_lead_ge_2q':int((lead>=2).sum()),'event_recall_lead_ge_2q':float((lead>=2).sum()/len(all_ev)) if len(all_ev) else None}

def chain_counts(scores,a):
    d=scores[['CERT','prediction_as_of']].copy();d['alert']=a;d['position']=np.arange(len(d))
    dt=pd.to_datetime(d.prediction_as_of);d['qi']=dt.dt.year*4+dt.dt.quarter-1
    d=d.sort_values(['CERT','qi']);prev_q=d.groupby('CERT').qi.shift();prev_alert=d.groupby('CERT').alert.shift(fill_value=False)
    d['repeat']=d.alert & prev_alert & ((d.qi-prev_q)==1);d['new']=d.alert & ~d.repeat
    q=d.groupby('prediction_as_of')[['new','repeat']].sum()
    return int(d.new.sum()),int(d['repeat'].sum()),q

def read_failures(cutoff):
    p=source_root()/'data/interim/failures.parquet'
    d=pl.scan_parquet(p).filter(pl.col('CERT').is_not_null()&(pl.col('RESTYPE')=='FAILURE')).with_columns(fd=pl.col('FAILDATE').str.strptime(pl.Date,'%m/%d/%Y')).filter(pl.col('fd')<=cutoff).sort('CERT','fd').unique('CERT',keep='first').select('CERT','fd','COST').collect().to_pandas()
    d.fd=pd.to_datetime(d.fd);return d

def dev_predictions():
    rebuilt=ROOT/'data/backtest_reproduction/predictions.parquet'
    if rebuilt.exists():
        return pl.read_parquet(rebuilt).filter((pl.col('pipeline')=='B3')&pl.col('scheme').is_in(['fixed_origin','rolling_5y'])).to_pandas()
    directory=source_root()/'data/processed/exp_3d/v61/arms';out=[]
    for p in sorted(directory.glob('*/manifest.json')):
        m=json.loads(p.read_text());tag=m.get('tag','')
        if m.get('label')!='B3' or not (tag.startswith('fixed_origin') or tag.startswith('rolling_5y_')):continue
        fp=p.parent/'predictions.parquet';assert sha(fp)==m['pred_sha256']
        d=pl.read_parquet(fp).to_pandas();d['scheme']='fixed_origin' if tag.startswith('fixed_origin') else 'rolling_5y';out.append(d)
    if not out:raise FileNotFoundError('Research B3 predictions unavailable; run the documented research replay/export or provide the frozen private predictions.')
    d=pd.concat(out,ignore_index=True);d.prediction_as_of=pd.to_datetime(d.prediction_as_of)
    assert d.prediction_as_of.max()<=pd.Timestamp('2011-12-31')
    return d

def select_cost_policy():
    """Declared preference scenario, not an estimate of causal intervention savings.

    Actual costs are revised outcomes, so this is retrospective severity-weighted
    selection. No claim that historical supervisors knew these values is made.
    """
    predictions=dev_predictions();fail=read_failures(date(2012,12,31))
    cpi_path=source_root()/'data/raw/macro_cpi_v1/CPIAUCNS_latest.csv'
    cpi=pd.read_csv(cpi_path);cpi.columns=['month','cpi'];cpi.month=pd.to_datetime(cpi.month).dt.to_period('M')
    # Latest CPI snapshot is used only to express retrospective severity in constant prices, never as a model feature.
    cpi.cpi=pd.to_numeric(cpi.cpi,errors='coerce');base=float(cpi.loc[cpi.month.dt.year==2012,'cpi'].mean())
    fail['month']=fail.fd.dt.to_period('M');fail=fail.merge(cpi,on='month',how='left');fail['real_cost_kusd']=pd.to_numeric(fail.COST,errors='coerce')*base/fail.cpi
    qs=[0,.0025,.005,.01,.02,.0353,.05,.075,.1,.15,.2,.3,.5,.75,1.0]
    scenarios={'hourly_usd_2012':110.,'h_new':4.,'repeat_fraction':.5,'alpha_primary':.001,'alpha_grid':[0.,.00001,.0001,.001,.01,.1],'description':'Illustrative severity-weighted decision loss, not operationally validated budget or causal savings','cost_price_basis':'annual-mean 2012 CPI, latest snapshot (retrospective pricing)','price_index_base':base,'unknown_cost':'median of nonmissing nonnegative event severity in the dev cohort; 0 remains 0','selection_scheme':'fixed_origin','tie_break':'lowest loss, then fewer alerts, then smaller q','q_grid':qs,'repeat_rule':'new file after any non-alerted or missing calendar quarter; cold start'}
    rows=[];summ=[]
    for scheme in ['fixed_origin','rolling_5y']:
        d=predictions.loc[predictions.scheme==scheme].reset_index(drop=True);ev=match_events(d,fail);cohort=ev[['CERT','fd','real_cost_kusd']].drop_duplicates(['CERT','fd'])
        u=float(cohort.real_cost_kusd.median());lookup=cohort.set_index(['CERT','fd']).real_cost_kusd.fillna(u)
        for q in qs:
            a=alerts(d,q);new,rep,load=chain_counts(d,a)
            caught=ev.loc[a[ev['index'].to_numpy()],['CERT','fd']].drop_duplicates()
            hit_index=pd.MultiIndex.from_frame(caught);miss=lookup.loc[~lookup.index.isin(hit_index)]
            hours=scenarios['h_new']*(new+scenarios['repeat_fraction']*rep);review=110*hours/1000
            for alpha in scenarios['alpha_grid']:
                rows.append({'scheme':scheme,'q':q,'alpha':alpha,'alerts':int(a.sum()),'new_files':new,'repeat_reviews':rep,'hours':hours,'peak_quarter_hours':float((4*(load['new']+.5*load['repeat'])).max()),'review_cost_kusd_2012':review,'missed_severity_kusd_2012':float(miss.sum()),'unknown_severity_events':int(cohort.real_cost_kusd.isna().sum()),'unknown_value_kusd':u,'events':len(cohort),'caught_events':len(caught),'loss_kusd_2012':review+alpha*float(miss.sum())})
            if q in [.01,.05,.1]:summ.append({'scheme':scheme,'q':q,**summarize(d,a,fail)})
    table=pd.DataFrame(rows);table.to_csv(ROOT/'reports/tables/cost_scenarios.csv',index=False)
    pd.DataFrame(summ).to_csv(ROOT/'reports/tables/B3_dev_operating_metrics.csv',index=False)
    choice=table[(table.scheme=='fixed_origin')&(table.alpha==scenarios['alpha_primary'])].sort_values(['loss_kusd_2012','alerts','q']).iloc[0].to_dict()
    policy={**scenarios,'selected_q':choice['q'],'selected_dev_result':choice,'status':'frozen illustrative policy; preference alpha not empirically identified'}
    dump_json(ROOT/'docs/cost_policy.json',policy)
    predictions.to_parquet(ROOT/'data/dev_predictions_private.parquet',index=False)
    return policy
