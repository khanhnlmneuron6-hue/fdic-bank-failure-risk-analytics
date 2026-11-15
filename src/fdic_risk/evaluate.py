"""A frozen, one-time holdout evaluation; replay reads saved outputs only."""
import json,os,warnings,time
from datetime import date,datetime,timezone
import numpy as np
import pandas as pd
import polars as pl
import joblib
from .pipeline import ROOT,cfg,sha,dump_json,prepare_features,source_root
from .policy import summarize,alerts,read_failures,chain_counts

def freeze():
    config=cfg();policy=json.loads((ROOT/'docs/cost_policy.json').read_text())
    models={k:json.loads((ROOT/'models'/k/'manifest.json').read_text()) for k in ['B3','core7_iRF','core7_LR']}
    p=ROOT/'docs/frozen_test_protocol.json'
    record={'frozen_utc':datetime.now(timezone.utc).isoformat(),'author':'Nguyễn Lê Nam Khánh','student_id':'11230976','approved_by_user':config['test_permission'],'main_pipeline':'B3','controls':['core7_iRF','core7_LR'],'window':[config['test_start'],config['test_end']],'feature_config_sha256':sha(ROOT/'config_final.json'),'policy_sha256':sha(ROOT/'docs/cost_policy.json'),'model_hashes':{k:v['model_sha256'] for k,v in models.items()},'model_columns':{k:v['columns'] for k,v in models.items()},'primary_q':policy['selected_q'],'reference_q':[.01,.05,.1],'primary_cost_scenario':policy,'test_periods':[['2013-2019','2013-01-01','2019-12-31'],['2020-2022','2020-01-01','2022-12-31'],['2023-2025','2023-01-01','2025-06-30']],'metrics':['AP-D7','pooled AP','ROC-AUC','confusion matrix','precision','row recall','unique event recall','lead time','alert volume','gross review workload'],'rules':['no refit, threshold or feature change after viewing test','one prediction pass per frozen model; multiple predeclared metrics from that pass','COST/latest CPI are retrospective severity descriptors, not historically available causal savings','post-test failure cases are for explanation only; no model selection','test state cold-starts; no backfilled 2012 alerts']}
    if p.exists():
        old=json.loads(p.read_text())
        assert old['model_hashes']==record['model_hashes'] and old['policy_sha256']==record['policy_sha256'],'frozen contract differs'
        return old
    dump_json(p,record);return record

def evaluate_once(technical_resume=False):
    output=ROOT/'reports/tables/test_metrics.csv'
    if output.exists():return pd.read_csv(output)
    protocol=freeze();marker=ROOT/'.local/test_access_record.json'
    if marker.exists():
        old=json.loads(marker.read_text())
        assert technical_resume and not (ROOT/'data/test_predictions_private.parquet').exists(), 'A test retry is allowed only before any model predictions exist'
        assert old['protocol_sha256']==sha(ROOT/'docs/frozen_test_protocol.json')
        old['technical_resume_before_prediction']='Locked keys include ineligible/censored rows. Apply the already registered y_audit-not-null population filter before count reconciliation; no test predictions or metrics had been produced.'
        old['resume_utc']=datetime.now(timezone.utc).isoformat();dump_json(marker,old)
    else:
        with marker.open('x') as f:json.dump({'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'docs/frozen_test_protocol.json')},f)
    for name,digest in protocol['model_hashes'].items():assert sha(ROOT/'models'/name/'model.joblib')==digest
    assert sha(ROOT/'config_final.json')==protocol['feature_config_sha256']
    feature_path=ROOT/'data/processed/features_to_2025-03-31.parquet'
    if feature_path.exists():
        fm=json.loads(feature_path.with_suffix('.json').read_text());assert sha(feature_path)==fm['sha256']
        features=pl.read_parquet(feature_path)
    else:features=prepare_features(date(2025,3,31),verify_dev=True)
    lock=source_root()/'data/processed/split_audit/test_keys_locked.parquet'
    if lock.exists():
        keys=pl.read_parquet(lock)
        if 'y_audit' not in keys.columns:
            keys=keys.join(pl.scan_parquet(source_root()/'data/processed/split_audit/audit_rows.parquet').filter(pl.col('prediction_as_of').is_between(date(2013,3,31),date(2025,6,30))).select('CERT','report_period_end','y_audit').collect(),on=['CERT','report_period_end'],validate='1:1')
        raw_locked_rows=keys.height
        excluded=keys.filter(pl.col('y_audit').is_null()).height
        keys=keys.filter(pl.col('y_audit').is_not_null()).select('CERT','report_period_end','y_audit')
        dump_json(ROOT/'reports/tables/test_population_reconciliation.json',{'locked_key_universe':raw_locked_rows,'excluded_unlabelled_or_out_of_population':excluded,'labelled_evaluation_rows':keys.height,'rule':'registered y_audit-not-null; no score-based exclusions'})
    else:
        from .pipeline import rebuild_audit
        keys=rebuild_audit(date(2026,6,30)).filter(pl.col('prediction_as_of').is_between(date(2013,3,31),date(2025,6,30))&pl.col('y_audit').is_not_null()).select('CERT','report_period_end','y_audit')
    data=features.join(keys,on=['CERT','report_period_end'],how='inner',validate='1:1').sort(['CERT','report_period_end'])
    assert data.height==keys.height and data['y_audit'].null_count()==0
    assert data['label_end'].max()<=date(2026,6,30) and data['prediction_as_of'].min()>date(2012,12,31)
    failures=read_failures(date(2026,6,30));scores=data.select('CERT','report_period_end','prediction_as_of',pl.col('y_audit').alias('y_true')).to_pandas()
    scores.prediction_as_of=pd.to_datetime(scores.prediction_as_of)
    # Independently reconcile labels from event dates without changing any row or label.
    ff=scores[['CERT','prediction_as_of']].merge(failures[['CERT','fd']],on='CERT',how='left')
    expected=((ff.fd>ff.prediction_as_of)&(ff.fd<=ff.prediction_as_of+pd.DateOffset(years=1))).astype(int).to_numpy()
    assert np.array_equal(expected,scores.y_true.to_numpy()),'Holdout label/date reconciliation failed'
    all_scores=scores.copy();rows=[]
    for name,cols in protocol['model_columns'].items():
        model=joblib.load(ROOT/'models'/name/'model.joblib');X=data.select(cols).to_numpy().astype(float)
        pred=model.predict_proba(X)[:,1];assert np.isfinite(pred).all();all_scores[name]=pred
        scored=scores.assign(score=pred).reset_index(drop=True)
        for q in sorted(set([protocol['primary_q']]+protocol['reference_q'])):
            a=alerts(scored,q);m=summarize(scored,a,failures);new,repeat,load=chain_counts(scored,a)
            rows.append({'pipeline':name,'scope':'all_test','q':q,'policy':'primary_cost_scenario' if q==protocol['primary_q'] else 'reference_budget',**m,'new_files':new,'repeat_reviews':repeat,'gross_review_hours_scenario':4*(new+.5*repeat),'peak_review_hours_quarter_scenario':float((4*(load['new']+.5*load['repeat'])).max())})
        for label,start,end in protocol['test_periods']:
            d=scored[scored.prediction_as_of.between(start,end)].reset_index(drop=True)
            if len(d):rows.append({'pipeline':name,'scope':label,'q':protocol['primary_q'],'policy':'primary_cost_scenario',**summarize(d,alerts(d,protocol['primary_q']),failures)})
    all_scores.to_parquet(ROOT/'data/test_predictions_private.parquet',index=False)
    result=pd.DataFrame(rows);result.to_csv(output,index=False)
    dump_json(ROOT/'reports/tables/test_run_manifest.json',{'protocol_sha256':sha(ROOT/'docs/frozen_test_protocol.json'),'rows':len(scores),'positive_rows':int(scores.y_true.sum()),'test_pred_sha256':sha(ROOT/'data/test_predictions_private.parquet'),'metrics_sha256':sha(output),'models':protocol['model_hashes'],'completed_utc':datetime.now(timezone.utc).isoformat(),'test_passes':1,'note':'display and report builds replay these outputs; no post-test tuning'})
    return result
