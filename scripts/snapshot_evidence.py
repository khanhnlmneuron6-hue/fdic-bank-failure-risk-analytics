from pathlib import Path
import sys,json,csv
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from fdic_risk.pipeline import source_root,sha,dump_json
from importlib.metadata import version
source=source_root();manifest=json.loads((source/'data/manifests/manifest_financials.json').read_text());rows=[]
for q,m in sorted(manifest.items()):
 if not isinstance(m,dict) or 'checks' not in m:continue
 checks=m['checks']
 rows.append({'quarter':q,'rows':checks['rows'],'api_total':checks['api_total'],'complete':bool(checks['rows']==checks['api_total']),'downloaded_utc':m.get('downloaded_utc'),'raw_sha256':m.get('raw_sha256'),'typed_sha256':m.get('typed_sha256')})
import pandas as pd
pd.DataFrame(rows).to_csv(root/'reports/tables/acquisition_completeness.csv',index=False)
small=json.loads((source/'data/manifests/manifest_small.json').read_text());summary={'financial_rows':sum(r['rows'] for r in rows),'quarters':len(rows),'fields':87,'quarters_match_api_total':all(r['complete'] for r in rows),'download_dates':sorted({r['downloaded_utc'][:10] for r in rows}),'small_tables':{k:{'rows':v['rows'],'api_total':v['api_total'],'downloaded_utc':v['downloaded_utc']} for k,v in small.items() if isinstance(v,dict) and 'rows' in v},'verification_scope':'existing acquisition manifests; source sha carried forward; no fresh API recount or redownload'}
dump_json(root/'reports/tables/acquisition_summary.json',summary)
packages=['numpy','pandas','polars','pyarrow','scipy','scikit-learn','imodels','matplotlib','seaborn','requests','PyYAML','joblib','pyspark','nbformat','nbclient','nbconvert','ipykernel','pytest','mlxtend','tqdm']
versions={p:version(p) for p in packages}
(root/'requirements.txt').write_text('# Verified execution environment: Python 3.11; Spark needs Java 17+\n'+'\n'.join(f'{k}=={v}' for k,v in versions.items())+'\n')
dump_json(root/'reports/tables/environment.json',versions)
print(summary)
