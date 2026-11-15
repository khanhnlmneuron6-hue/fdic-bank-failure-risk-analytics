"""Explicit full replay of the selected nested forward-HGB -> iRF procedure.

The published notebook replays aggregate historical evidence. This expensive command
rebuilds the selected path on the registered 64 folds when private raw inputs exist.
It never reads the holdout and never replaces published research evidence in place.
"""
import json,hashlib,time
from datetime import date
import numpy as np
import pandas as pd
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from .pipeline import ROOT,dev_labels,make_model,dump_json,cfg
GROUPS=json.loads((ROOT/'docs/feature_groups.json').read_text());UNITS=GROUPS['FS_UNITS'];ORDER=GROUPS['FS_UNIT_LIST']

def qend(d,k=0):return (pd.Timestamp(d)+pd.DateOffset(months=3*k)+pd.offsets.MonthEnd(0)).date()

def forward_select(train,fold,seed):
    """Mean inner AP, two time splits, all positives + 20% negatives weighted 5."""
    splits=[];cols=[c for u in ORDER for c in UNITS[u]]
    for i,back in enumerate([0,4],1):
        end=qend(fold['train_end'],-back);fit_end=qend(end,-8);val_start=qend(end,-3)
        fi=train.filter(pl.col('prediction_as_of')<=fit_end);va=train.filter(pl.col('prediction_as_of').is_between(val_start,end))
        if fi.is_empty() or va.is_empty() or fi['y_audit'].sum()==0 or va['y_audit'].sum()==0:continue
        assert fi['label_end'].max()<val_start
        y=fi['y_audit'].to_numpy();keep=(y==1)|(np.random.default_rng(seed+97*i).random(len(y))<.2)
        splits.append((fi.select(cols).to_numpy()[keep],y[keep],np.where(y[keep]==1,1.,5.),va.select(cols).to_numpy(),va['y_audit'].to_numpy()))
    if not splits:return ORDER.copy(),{'status':'default_no_usable_inner_split','fits':0,'path':[]}
    cache={};fits=0
    def score(units):
        nonlocal fits
        key=tuple(u for u in ORDER if u in units)
        if key in cache:return cache[key]
        ix=[cols.index(c) for u in key for c in UNITS[u]];scores=[]
        for X,y,w,V,z in splits:
            m=HistGradientBoostingClassifier(early_stopping=False,random_state=0,l2_regularization=10.).fit(X[:,ix],y,sample_weight=w)
            p=m.predict_proba(V[:,ix])[:,1];assert np.isfinite(p).all();scores.append(average_precision_score(z,p));fits+=1
        cache[key]=float(np.mean(scores));return cache[key]
    current=[];best=None;path=[]
    while len(current)<len(ORDER):
        candidates=[(score(current+[u]),ORDER.index(u),u) for u in ORDER if u not in current]
        winner=sorted(candidates,key=lambda v:(-round(v[0],12),v[1]))[0];current.append(winner[2]);path.append({'groups':current.copy(),'mean_inner_AP':winner[0]})
        if best is None or winner[0]>best[0]+1e-12:best=(winner[0],current.copy())
    return sorted(best[1],key=ORDER.index),{'status':'selected_on_inner_only','fits':fits,'path':path}

def run_full_backtest():
    data=pl.read_parquet(ROOT/'data/processed/features_to_2011-09-30.parquet').join(dev_labels(),on=['CERT','report_period_end'],how='inner').sort(['CERT','report_period_end'])
    fold_table=pl.read_csv(ROOT/'reports/tables/split_inner_folds.csv',try_parse_dates=True).filter(pl.col('candidate')=='A_recent')
    records=fold_table.sort('scheme','val_year').to_dicts();grouped={}
    for f in records:grouped.setdefault((f['scheme'],str(f['train_start']),str(f['train_end']),str(f['fit_date'])),[]).append(f)
    dest=ROOT/'data/backtest_reproduction';dest.mkdir(parents=True,exist_ok=True);provenance=[];preds=[]
    for group in grouped.values():
        fr=group[0];tag=f"{fr['scheme']}_{fr['val_year']}"+(f'_x{len(group)}' if len(group)>1 else '')
        seed=20261112+int(hashlib.sha256(tag.encode()).hexdigest()[:6],16)%100000
        train=data.filter(pl.col('prediction_as_of').is_between(fr['train_start'],fr['train_end'])&~pl.col('fit_exclude_i01'))
        assert train['label_end'].max()<=fr['fit_date']
        units,selection=forward_select(train,fr,seed)
        for label,cs in [('B0',[c for u in ORDER if u in units for c in UNITS[u]]),('B3',[c for u in ORDER if u in units for c in UNITS[u]]+['texas_proxy','texas_den_nonpos','buffer_gap_assets','uncovered_ncl_assets']),('core7_iRF',cfg()['core7_columns']),('core7_LR',cfg()['core7_columns'])]:
            model=make_model('lr' if label.endswith('LR') else 'irf',cs)
            if not label.endswith('LR'):model['model'].set_params(random_state=seed)
            model.fit(train.select(cs).to_numpy().astype(float),train['y_audit'].to_numpy().astype(int))
            for f in group:
                val=data.filter(pl.col('prediction_as_of').is_between(f['val_start'],f['val_end']))
                sv=model.predict_proba(val.select(cs).to_numpy().astype(float))[:,1]
                preds.append(val.select('CERT','report_period_end','prediction_as_of',pl.col('y_audit').alias('y_true')).with_columns(score=pl.Series(sv),pipeline=pl.lit(label),scheme=pl.lit(f['scheme']),val_year=pl.lit(f['val_year'])))
        provenance.append({'tag':tag,'seed':seed,'selected_units':units,**selection});dump_json(dest/f'{tag}.json',provenance[-1]);print('reproduced',tag,flush=True)
    all_pred=pl.concat(preds);all_pred.write_parquet(dest/'predictions.parquet')
    dump_json(dest/'manifest.json',{'groups':len(grouped),'folds':len(records),'scope':'development only','note':'new reproduction outputs; independently compare to immutable published aggregates, never overwrite them'})
    return all_pred
