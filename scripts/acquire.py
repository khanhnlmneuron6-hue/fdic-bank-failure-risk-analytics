#!/usr/bin/env python3
"""Resumable FDIC acquisition. Download values stay private and are never committed."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import gzip,json,time,calendar,hashlib
from datetime import date,datetime,timezone
import requests,yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import polars as pl
from fdic_risk.pipeline import sha,dump_json

session=requests.Session();session.mount('https://',HTTPAdapter(max_retries=Retry(total=6,backoff_factor=.5,status_forcelist=[429,500,502,503,504])))
config=yaml.safe_load((ROOT/'config.yaml').read_text());schemas=json.loads((ROOT/'docs/acquisition_schema.json').read_text())

def acquire(endpoint,fields,quarter=None):
    stem=f'financials/REPDTE={quarter}' if quarter else endpoint
    raw=ROOT/'data/raw'/f'{stem}.jsonl.gz';typed=ROOT/'data/interim'/f'{stem}.parquet';meta=ROOT/'data/manifests'/f'{endpoint}_{quarter or "all"}.json'
    query={'fields':','.join(fields),'limit':10000,'offset':0,'sort_by':'CERT','sort_order':'ASC','format':'json'}
    if quarter:query['filters']=f'REPDTE:{quarter}'
    if meta.exists():
        m=json.loads(meta.read_text())
        if m['fields']==fields and raw.exists() and typed.exists() and sha(raw)==m['raw_sha256'] and sha(typed)==m['typed_sha256']:
            print('verified cache',stem);return
    pages=[];records=[];expected=None
    while True:
        response=session.get(f'https://api.fdic.gov/banks/{endpoint}',params=query,timeout=90);response.raise_for_status();obj=response.json()
        batch=obj.get('data',[]);total=int(obj['totals']['count']);expected=total if expected is None else expected
        if total!=expected:raise RuntimeError('API total changed during pagination; restart a fresh snapshot')
        records += [r['data'] for r in batch];pages.append(response.text)
        if len(records)>=total:break
        if not batch:raise RuntimeError('Empty page before declared total')
        query['offset']+=len(batch);time.sleep(.5)
    assert len(records)==expected
    raw.parent.mkdir(parents=True,exist_ok=True);typed.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(raw.with_suffix('.tmp'),'wt') as f:f.write('\n'.join(pages)+'\n')
    raw.with_suffix('.tmp').replace(raw)
    data=pl.DataFrame([{f:r.get(f) for f in fields} for r in records],infer_schema_length=None)
    str_fields={'REPDTE','STNAME','BKCLASS','CB','FAILDATE','ENDEFYMD','RESTYPE','RESTYPE1','NAME','SAVR'}
    if endpoint=='financials':
        data=data.select([pl.col(f).cast(pl.Int64,strict=False) if f=='CERT' else pl.col(f).cast(pl.String,strict=False) if f in str_fields else pl.col(f).cast(pl.Float64,strict=False) for f in fields])
    else:
        data=data.with_columns(pl.col('CERT').cast(pl.Int64,strict=False))
        for f in ['COST','ACTIVE','ULTCERT']:
            if f in data.columns:data=data.with_columns(pl.col(f).cast(pl.Float64,strict=False))
        for f in str_fields & set(data.columns):data=data.with_columns(pl.col(f).cast(pl.String,strict=False))
    data.write_parquet(typed,compression='zstd')
    dump_json(meta,{'endpoint':endpoint,'fields':fields,'query':query,'rows':data.height,'api_total':expected,'raw_sha256':sha(raw),'typed_sha256':sha(typed),'downloaded_utc':datetime.now(timezone.utc).isoformat()})
    print('downloaded',stem,data.height,flush=True)

if __name__=='__main__':
    fields=[x for v in config['financial_fields'].values() for x in v]
    for year in range(1984,2027):
        for month in [3,6,9,12]:
            dt=date(year,month,calendar.monthrange(year,month)[1])
            if dt>date(2026,6,30):continue
            acquire('financials',fields,dt.strftime('%Y%m%d'))
    for endpoint in ['failures','institutions']:acquire(endpoint,schemas[endpoint])
    macro=ROOT/'data/raw/macro_cpi_v1/CPIAUCNS_latest.csv';macro.parent.mkdir(parents=True,exist_ok=True)
    if not macro.exists():
        response=session.get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS',timeout=90);response.raise_for_status();macro.write_bytes(response.content)
        dump_json(macro.with_suffix('.json'),{'source':'https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS','sha256':sha(macro),'scope':'retrospective constant-price severity only; never a predictor'})

    records=[json.loads(p.read_text()) for p in (ROOT/'data/manifests').glob('financials_*.json')]
    financial_manifest={}
    for rec in records:
        quarter=rec['query']['filters'].split(':')[-1]
        financial_manifest[quarter]={**rec,'checks':{'rows':rec['rows'],'api_total':rec['api_total'],'rows_match_api':rec['rows']==rec['api_total']},'complete':rec['rows']==rec['api_total']}
    dump_json(ROOT/'data/manifests/manifest_financials.json',financial_manifest)
    dump_json(ROOT/'data/manifests/manifest_small.json',{endpoint:json.loads((ROOT/f'data/manifests/{endpoint}_all.json').read_text()) for endpoint in ['failures','institutions']})
