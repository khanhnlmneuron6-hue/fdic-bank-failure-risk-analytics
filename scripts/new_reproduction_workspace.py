"""Create a private reproduction workspace without overwriting published evidence."""
from pathlib import Path
import shutil,sys
src=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/new_reproduction_workspace.py /absolute/new/folder')
dst=Path(sys.argv[1]).expanduser().resolve()
if dst.exists():raise SystemExit('Destination must not exist; no files will be overwritten.')
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('data','models','.local','.git','__pycache__','.ipynb_checkpoints'))
(dst/'data').mkdir();(dst/'models').mkdir();(dst/'.local').mkdir()
for name in ['frozen_test_protocol.json','cost_policy.json']:
 p=dst/'docs'/name
 if p.exists():p.rename(p.with_name('published_'+p.name))
for p in list((dst/'reports/tables').glob('test*')):
 hist=dst/'reports/published_test_evidence';hist.mkdir(exist_ok=True);p.rename(hist/p.name)
print('Private reproduction workspace:',dst)
print('The published holdout is already known. This is fixed-protocol reproduction, not a new independent validation.')
print('Next: python scripts/acquire.py; python scripts/run_pipeline.py --mode rebuild --spark --evaluate-test')
