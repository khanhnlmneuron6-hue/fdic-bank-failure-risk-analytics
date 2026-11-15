#!/usr/bin/env python3
"""Replay portable results, or explicitly rebuild private computational artifacts."""
from pathlib import Path
import sys,argparse,os
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'));os.chdir(root)
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('VECLIB_MAXIMUM_THREADS','1');os.environ.setdefault('MPLCONFIGDIR',str(root/'.local/matplotlib'))
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['replay','rebuild'],default='replay');p.add_argument('--spark',action='store_true');p.add_argument('--evaluate-test',action='store_true');a=p.parse_args()
if a.mode=='rebuild':
    from fdic_risk.pipeline import prepare_features,fit_final
    if (root/'reports/tables/test_run_manifest.json').exists():raise SystemExit('This workspace has already evaluated its holdout. Keep frozen results; use a separate reproduction workspace to rebuild, without retuning on the published test.')
    f=prepare_features();fit_final(f)
    from fdic_risk.quality import build_quality_report
    build_quality_report()
    from fdic_risk.policy import select_cost_policy
    from fdic_risk.pipeline import source_root
    if not (source_root()/'data/processed/exp_3d/v61/arms').exists() and not (root/'data/backtest_reproduction/predictions.parquet').exists():
        from fdic_risk.backtest import run_full_backtest
        run_full_backtest()
    select_cost_policy()
    from fdic_risk.benchmarks import run_benchmarks
    run_benchmarks(run_spark=a.spark)
    if a.evaluate_test:
        from fdic_risk.evaluate import evaluate_once
        evaluate_once()
        import runpy
        runpy.run_path(str(root/'scripts/extend_cost_report.py'),run_name='__main__')
        runpy.run_path(str(root/'scripts/export_public_diagnostics.py'),run_name='__main__')
        from fdic_risk.explain import run_explanations
        run_explanations()
from fdic_risk.presentation import build_notebook
build_notebook(execute=True)
print('Saved notebooks/fdic_bank_failure_early_warning.ipynb and reports/portfolio.html')
