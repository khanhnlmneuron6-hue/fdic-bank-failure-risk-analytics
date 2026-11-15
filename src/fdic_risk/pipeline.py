"""Data acquisition, deterministic financial features and frozen final fits.

All filesystem writes target this independent project. The research project is read-only.
"""
from __future__ import annotations
import calendar, gc, gzip, hashlib, json, os, platform, time, warnings
from datetime import date, datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl
import joblib
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from . import rules as r
ROOT=Path(__file__).resolve().parents[2]
# The insured class set is taken from the actual approved population rule (D4).
r.INSURED_CLASSES={"N","NM","SM","SB","SI","SL","OI"}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def dump_json(path, obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+'\n');os.replace(tmp,path)

def source_root():
    env=os.environ.get('FDIC_SOURCE_ROOT')
    if env:return Path(env).resolve()
    p=ROOT/'.local/source_root.txt'
    return Path(p.read_text().strip()) if p.exists() else ROOT

def cfg():return json.loads((ROOT/'config_final.json').read_text())

def read_financials(scope_end, source=None):
    """Quarter-file pruning precedes collection; no post-cutoff quarter is loaded."""
    source=source or source_root();folder=source/'data/interim/financials'
    files=sorted(p for p in folder.glob('*.parquet') if ''.join(c for c in p.stem if c.isdigit())[-8:]<=scope_end.strftime('%Y%m%d'))
    if not files:raise FileNotFoundError('No typed financials. Run scripts/acquire.py or set FDIC_SOURCE_ROOT.')
    return pl.scan_parquet(files).filter(pl.col('REPDTE')<=scope_end.strftime('%Y%m%d')).collect()

def prepare_features(scope_end=date(2011,9,30), verify_dev=True):
    """Rebuild the feature-only path; outcomes never enter any feature expression.

    Historical I01 quarantine is fixed after retrospective discovery, not a vintage-PIT claim.
    """
    out=ROOT/'data/processed';out.mkdir(parents=True,exist_ok=True)
    financials=read_financials(scope_end)
    pit,_=r.build_pit_view(financials);del financials;gc.collect()
    lay,d8log=r.apply_d8(pit);flows=r.build_flows(pit)
    fc=r.build_core_features(lay,flows)
    recon=r.reconcile_roa_1985(lay,flows)
    mi=r.build_model_inputs(fc,lay,recon)
    candidates=r.build_feature_candidates(lay,flows)
    extra=['nim_ttm','provision_loans_ttm','brokered_assets','efficiency_ttm']
    base=mi.select(*r.KEY3,'qi',*r.CORE,'fit_exclude_i01').join(candidates.select(*r.KEY3,*extra),on=r.KEY3,validate='1:1')
    classes=r.classify_ytd_quarters(pit,flows,scope_end)
    recovered=r.dq_fill(base,r.i01x_recovery_log(base,lay,flows,recon))
    qlog=r.dq_quarantine_log(recovered,classes,lay)
    y1=r.dq_apply(recovered,qlog)
    pool,_=r.build_pool_features(lay,flows,classes)
    clean,status,changes,relations=r.prepare_pool_clean(y1,pool,lay,flows,scope_end)
    # Match the registered model-population support before forming changes; a report
    # excluded from that support must not silently become a lag source in the refactor.
    if scope_end<=date(2011,9,30):
        population_keys=dev_labels().select(r.KEY3)
    else:
        if not (ROOT/'docs/frozen_test_protocol.json').exists():raise PermissionError('Freeze protocol before constructing test features')
        ap=source_root()/'data/processed/split_audit/audit_rows.parquet'
        audit=pl.scan_parquet(ap).filter(pl.col('y_audit').is_not_null() & (pl.col('prediction_as_of')<=date(2025,6,30))).select(r.KEY3).collect() if ap.exists() else rebuild_audit(date(2026,6,30)).filter(pl.col('y_audit').is_not_null()).select(r.KEY3)
        population_keys=audit
    clean=clean.join(population_keys,on=r.KEY3,how='semi').sort(r.KEY3)
    change_base=['eq_assets','noncurrent_loans','reserve_loans','roa_ttm','loans_deposits','borrowed_assets','ore_assets','npa_assets']
    prev=clean.select('CERT',(pl.col('qi')+4).alias('qi'),*[pl.col(c).alias(c+'__l4') for c in change_base])
    clean=clean.join(prev,on=['CERT','qi'],how='left',validate='1:1').with_columns(*[(pl.col(c)-pl.col(c+'__l4')).alias(c+'_chg4') for c in change_base]).drop([c+'__l4' for c in change_base])
    clean=clean.join(r.v59_block_T(lay),on=r.KEY3,how='left',validate='1:1')
    clean=clean.with_columns(prediction_as_of=pl.col('report_period_end').dt.offset_by('3mo').dt.month_end(),label_end=pl.col('report_period_end').dt.offset_by('15mo').dt.month_end()).sort(r.KEY3)
    # Exact parity on approved dev rows is required before final fitting or test access.
    parity=[]
    ref=source_root()/'data/processed/exp_3d/v57/frames/frame_D0.parquet'
    if verify_dev and ref.exists():
        old=pl.read_parquet(ref).filter(pl.col('prediction_as_of')<=date(2011,12,31))
        cols=[c for c in old.columns if c in clean.columns and c not in ['prediction_as_of','label_end']]
        both=old.select(*r.KEY3).join(clean.select(*r.KEY3,*[c for c in cols if c not in r.KEY3]),on=r.KEY3,how='left',validate='1:1').sort(r.KEY3)
        old=old.sort(r.KEY3)
        for c in cols:
            a,b=old[c],both[c]
            eq=a.eq_missing(b)
            bad=int((~eq).sum());maxdiff=None
            if a.dtype.is_float():
                maxdiff=(a-b).abs().max()
                bad=int(((a.is_null()!=b.is_null())|((a-b).abs().fill_null(0)>1e-10)).sum())
            parity.append({'column':c,'mismatch_rows':bad,'max_abs_diff':maxdiff})
        pl.DataFrame(parity).write_csv(ROOT/'reports/tables/feature_parity.csv')
        assert all(p['mismatch_rows']==0 for p in parity),[p for p in parity if p['mismatch_rows']]
    clean.write_parquet(out/f'features_to_{scope_end}.parquet',compression='zstd')
    d8log.group_by('field','reason').len().sort('field','reason').write_csv(ROOT/'reports/tables/zero_rule_summary.csv')
    qlog.group_by('policy','feature').len().sort('policy','feature').write_csv(ROOT/'reports/tables/quarantine_summary.csv')
    status.group_by('nco_status').len().write_csv(ROOT/'reports/tables/missing_source_summary.csv')
    dump_json(out/f'features_to_{scope_end}.json',{'rows':clean.height,'columns':clean.columns,'sha256':sha(out/f'features_to_{scope_end}.parquet'),'scope_end':scope_end,'parity_columns':len(parity),'source':'typed FDIC financials; scientific rules from documented research snapshot'})
    return clean

def dev_labels():
    """Read only approved dev keys/labels; validate maturity at the final fit cutoff."""
    source=source_root()/'data/processed/exp_3d/v57/frames/frame_D0.parquet'
    if source.exists():
        return pl.scan_parquet(source).filter(pl.col('prediction_as_of')<=date(2011,12,31)).select(*r.KEY3,'y_audit').collect()
    return rebuild_audit(date(2012,12,31)).filter(pl.col('prediction_as_of')<=date(2011,12,31)).filter(pl.col('y_audit').is_not_null()).select(*r.KEY3,'y_audit')

def rebuild_audit(data_end):
    """Reproduce population, first failure, competing exit and maturity rules."""
    source=source_root();fin=read_financials(data_end,source)
    keys=fin.select('CERT','BKCLASS',rd=pl.col('REPDTE').str.strptime(pl.Date,'%Y%m%d')).with_columns(qi=pl.col('rd').dt.year()*4+pl.col('rd').dt.quarter()-1)
    failure=pl.scan_parquet(source/'data/interim/failures.parquet').filter(pl.col('FAILDATE').str.strptime(pl.Date,'%m/%d/%Y')<=data_end).collect()
    inst=pl.read_parquet(source/'data/interim/institutions.parquet')
    ev=r.build_events(failure,data_end);ex=r.build_exits(keys,ev,inst,data_end)
    return r.build_audit(keys,ev,ex,data_end)

def feature_contract(cols):
    signed={'eq_assets','roa_ttm','nim_ttm','provision_loans_ttm','buffer_gap_assets','uncovered_ncl_assets'}
    logs={'log_assets','log_age','log_offices','texas_den_nonpos'}
    upper={'loans_deposits','loans_assets','cash_assets'}
    return {c:'signed_change' if c.endswith('_chg4') else 'log' if c in logs else 'signed' if c in signed else 'upper_only' if c in upper else 'nonneg' for c in cols}

def make_model(kind,cols):
    from imodels import IRFClassifier
    config=cfg()
    steps=[('cap',r.ContractCapperV4(cols,feature_contract(cols))),('median',SimpleImputer(strategy='median'))]
    if kind=='lr':steps += [('scale',StandardScaler()),('model',LogisticRegression(**config['lr']))]
    else:steps += [('model',IRFClassifier(random_state=config['seed'],n_jobs=2,**config['irf']))]
    return Pipeline(steps)

def fit_final(features):
    config=cfg();train=features.join(dev_labels(),on=r.KEY3,how='inner',validate='1:1').filter((pl.col('prediction_as_of')>=date.fromisoformat(config['train_start']))&~pl.col('fit_exclude_i01')).sort(r.KEY3)
    assert train['prediction_as_of'].max()==date(2011,12,31) and train['label_end'].max()<=date(2012,12,31)
    y=train['y_audit'].to_numpy().astype(int);out={}
    for name,kind,key in [('B3','irf','B3_columns'),('core7_iRF','irf','core7_columns'),('core7_LR','lr','core7_columns')]:
        cols=config[key];X=train.select(cols).to_numpy().astype(float)
        model=make_model(kind,cols);start=time.perf_counter()
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always');model.fit(X,y)
        assert not any(issubclass(w.category,ConvergenceWarning) for w in ws),f'{name}: convergence warning'
        if kind=='lr':assert model['model'].n_iter_.max()<config['lr']['max_iter']
        check=X[::max(1,len(X)//3000)];p=model.predict_proba(check)[:,1]
        assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        folder=ROOT/'models'/name;folder.mkdir(parents=True,exist_ok=True);joblib.dump(model,folder/'model.joblib')
        assert np.array_equal(p,joblib.load(folder/'model.joblib').predict_proba(check)[:,1])
        manifest={'pipeline':name,'model_sha256':sha(folder/'model.joblib'),'columns':cols,'seed':config['seed'],'train_rows':len(y),'positive_rows':int(y.sum()),'fit_seconds':time.perf_counter()-start,'reload_max_abs_diff':0.0,'train_end':config['train_end'],'label_cutoff':config['label_cutoff'],'selection_fingerprint':config['selection_fingerprint'],'config_sha256':sha(ROOT/'config_final.json'),'code_sha256':sha(Path(__file__)),'rules_sha256':sha(Path(r.__file__)),'python':platform.python_version(),'warnings':[str(w.message) for w in ws]}
        dump_json(folder/'manifest.json',manifest);out[name]=manifest
        print(name,'fit complete',manifest['fit_seconds'],flush=True)
        del X,model;gc.collect()
    dump_json(ROOT/'reports/tables/final_fit_manifest.json',out)
    return out
