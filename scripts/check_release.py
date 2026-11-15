"""Read-only release consistency checks; never fits or accesses private test rows."""
from pathlib import Path
import sys,json,hashlib,csv
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
import nbformat
import pandas as pd
import numpy as np
from fdic_risk.pipeline import dump_json,sha
from fdic_risk.presentation import unpack_results
unpack_results()
checks={}
nb=nbformat.read(root/'notebooks/fdic_bank_failure_early_warning.ipynb',as_version=4);nbformat.validate(nb)
cells=[c for c in nb.cells if c.cell_type=='code'];checks['notebook_code_cells_executed']=all(c.execution_count is not None for c in cells)
checks['notebook_no_error_outputs']=not any(o.output_type=='error' for c in cells for o in c.outputs)
checks['curated_notebook_cells']=len(nb.cells)==37
p=pd.read_csv(root/'reports/tables/feature_parity.csv');checks['feature_parity']=p.mismatch_rows.sum()==0
s=pd.read_csv(root/'reports/tables/spark_parity.csv');checks['engine_parity']=s['match'].all()
x=json.loads((root/'reports/tables/explainability_checks.json').read_text());checks['shap_tests']=all(x['toy_tests'].values()) and x['final_model_SHAP_additivity_max_abs_error']<1e-9
t=pd.read_csv(root/'reports/tables/test_metrics.csv');checks['confusion_reconciliation']=bool(np.all(t.TP+t.FP+t.FN+t.TN==t.rows));checks['event_bounds']=bool(np.all(t.caught_events<=t.events));checks['test_years_mature']=json.loads((root/'config_final.json').read_text())['test_end']=='2025-06-30'
checks['test_one_scoring_pass']=json.loads((root/'reports/tables/test_run_manifest.json').read_text())['test_passes']==1
manifest=json.loads((root/'docs/evidence_manifest.json').read_text());checks['historical_aggregate_hashes']=all(sha(root/r['file'])==r['sha256'] for r in manifest['files'])
protocol=json.loads((root/'docs/frozen_test_protocol.json').read_text());checks['frozen_policy_unchanged']=sha(root/'docs/cost_policy.json')==protocol['policy_sha256'];checks['frozen_feature_config_unchanged']=sha(root/'config_final.json')==protocol['feature_config_sha256']
if (root/'models/B3/model.joblib').exists():checks['frozen_models_unchanged']=all(sha(root/'models'/k/'model.joblib')==v for k,v in protocol['model_hashes'].items())
dump_json(root/'reports/tables/release_checks.json',{k:bool(v) for k,v in checks.items()});print(checks);assert all(checks.values())
