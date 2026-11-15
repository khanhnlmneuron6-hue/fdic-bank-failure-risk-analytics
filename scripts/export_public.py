"""Export code and aggregate evidence only. No git commit, remote creation or upload."""
from pathlib import Path
import shutil,zipfile,json,hashlib
root=Path(__file__).resolve().parents[1];dest=root.parent/'fdic-risk-analytics-public'
if dest.exists():
    # This is the generated public export only, never the working or research project.
    marker=dest/'.public_export_marker'
    if not marker.exists():raise RuntimeError('Refuse to replace an unrecognized directory')
    shutil.rmtree(dest)
shutil.copytree(root,dest,ignore=shutil.ignore_patterns('data','models','.local','.git','__pycache__','.ipynb_checkpoints','.DS_Store','.pytest_cache'))
(dest/'.public_export_marker').write_text('Generated public-only export. No bank-level data or fitted binaries.\n')
files=[]
for p in sorted(dest.rglob('*')):
 if p.is_file():
  assert p.suffix not in ['.parquet','.joblib','.gz','.npz','.pyc'],p
  assert not any(t in p.parts for t in ['data','models','.local']),p
  files.append({'file':str(p.relative_to(dest)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(dest/'PUBLIC_FILES.json').write_text(json.dumps(files,indent=2))
archive=root.parent/'fdic-risk-analytics-public.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted(dest.rglob('*')):
  if p.is_file():z.write(p,Path(dest.name)/p.relative_to(dest))
print(dest);print(archive);print('Public files:',len(files),'ZIP bytes:',archive.stat().st_size)
