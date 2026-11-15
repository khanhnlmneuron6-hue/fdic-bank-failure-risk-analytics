from pathlib import Path
import sys,os
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'));os.chdir(root)
from fdic_risk.backtest import run_full_backtest
run_full_backtest()
