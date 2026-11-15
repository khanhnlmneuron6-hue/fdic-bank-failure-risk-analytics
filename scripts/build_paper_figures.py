#!/usr/bin/env python3
"""Publication figures from saved aggregates only; no fitting or scoring."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import os
os.environ.setdefault('MPLCONFIGDIR',str(ROOT_CACHE := Path(__file__).resolve().parents[1]/'.local/matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'reports/tables'; OUT=ROOT/'reports/figures/paper';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'STIXGeneral','font.size':9.5,'axes.titlesize':10,'axes.labelsize':9.5,'legend.fontsize':8.5,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'xtick.major.width':.65,'ytick.major.width':.65,'savefig.facecolor':'white','figure.facecolor':'white','pdf.fonttype':42})
NAVY='#1D3557';GRAY='#7A8188';TEAL='#287D8E'
read=lambda n:pd.read_csv(T/n)
load=lambda n:json.loads((T/n).read_text())
def save(fig,name):
 fig.savefig(OUT/(name+'.png'),dpi=230,bbox_inches='tight',pad_inches=.035)
 fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight',pad_inches=.035)
 plt.close(fig)

a=read('acquisition_completeness.csv');s=load('storage_sizes.json');b=read('storage_processing_benchmarks.csv')
fig,ax=plt.subplots(1,2,figsize=(6.2,2.55),layout='constrained')
ax[0].plot(pd.to_datetime(a.quarter.astype(str)),a.rows/1000,color=NAVY,lw=1.35)
ax[0].set(title='A. Reporting institutions',ylabel='Reports per quarter (thousands)',xlabel='Report year')
ax[1].bar(['CSV','Parquet\nZstd'],[s['csv_bytes']/1e6,s['parquet_zstd_bytes']/1e6],width=.5,color=[GRAY,NAVY])
ax[1].set(title='B. Identical seven-column projection',ylabel='File size (MB)',ylim=(0,82))
for i,v in enumerate([s['csv_bytes']/1e6,s['parquet_zstd_bytes']/1e6]):ax[1].text(i,v+1.5,f'{v:.2f}',ha='center',fontsize=9)
save(fig,'data_and_storage')

v=read('v65_branch_scores.csv');names=['B1','B0','B3','XGBc_tuned|core7T','XGBr_tuned|core7T'];labels=['Seven-feature iRF','Forward iRF','Forward + T iRF','Tuned XGB classifier','Tuned XGB ranker']
fig,ax=plt.subplots(figsize=(6.2,2.8),layout='constrained');y=np.arange(len(names))
for scheme,offset,color,mark,label in [('fixed_origin',-.12,NAVY,'o','Fixed origin'),('rolling_5y',.12,TEAL,'D','Rolling 5 years')]:
 vals=[float(v[(v.branch==n)&(v.scheme==scheme)].ap_d7.iloc[0]) for n in names]
 ax.scatter(vals,y+offset,c=color,marker=mark,s=25,label=label,zorder=3)
 for x,yy in zip(vals,y+offset):ax.text(x+.003,yy,f'{x:.3f}',va='center',fontsize=8.5,color=color)
ax.set(yticks=y,yticklabels=labels,xlabel='Mean annual AP',xlim=(.14,.285));ax.invert_yaxis();ax.legend(frameon=False,loc='lower right');ax.grid(axis='x',alpha=.18,lw=.5)
save(fig,'model_comparison')

v=read('v62_period.csv');v=v[(v.branch=='B3') & v.scheme.isin(['fixed_origin','rolling_5y'])]
fig,ax=plt.subplots(1,2,figsize=(6.2,2.8),layout='constrained');periods=['1996-2000','2001-2007','2008-2011'];x=np.arange(3)
for sc,off,c,label in [('fixed_origin',-.17,NAVY,'Fixed origin'),('rolling_5y',.17,TEAL,'Rolling 5 years')]:
 z=v[v.scheme==sc].set_index('period').loc[periods]
 ax[0].bar(x+off,z.ap_year_mean,width=.30,color=c,label=label,edgecolor='white',linewidth=.4,hatch='' if sc=='fixed_origin' else '//')
 for xx,yy in zip(x+off,z.ap_year_mean):ax[0].text(xx,yy+.012,f'{yy:.3f}',ha='center',fontsize=8)
z=v[v.scheme=='fixed_origin'].set_index('period').loc[periods]
ax[0].set(title='A. Ranking by economic period',xticks=x,xticklabels=['1996-2000','2001-07','2008-11'],ylabel='Mean annual AP',ylim=(0,.63));ax[0].legend(frameon=False,fontsize=8)
ax[1].bar(x,z.prevalence*100,width=.48,color=GRAY)
for xx,yy in zip(x,z.prevalence*100):ax[1].text(xx,yy+.03,f'{yy:.3f}%',ha='center',fontsize=8)
ax[1].set(title='B. Positive bank-quarter prevalence',xticks=x,xticklabels=['1996-2000','2001-07','2008-11'],ylabel='Positive rows (%)',ylim=(0,1.65))
save(fig,'period_ranking')

c=read('cost_scenarios.csv');fig,ax=plt.subplots(figsize=(6.2,2.7),layout='constrained')
for alpha,col,sty in [(.0001,GRAY,':'),(.001,NAVY,'-'),(.01,TEAL,'--')]:
 z=c[(c.scheme=='fixed_origin') & np.isclose(c.alpha,alpha)].sort_values('q')
 ax.plot(z.q*100,z.loss_kusd_2012/1000,color=col,ls=sty,lw=1.3,marker='o',ms=2.5,label=f'alpha = {alpha:g}')
ax.axvline(3.53,color=NAVY,lw=.7,ls=':');ax.set_yscale('log');ax.set(xlabel='Quarterly alert share (%)',ylabel='Scenario loss (million USD, 2012; log scale)');ax.legend(frameon=False,ncol=3,loc='upper center')
save(fig,'cost_sensitivity')

pr=read('pr_curve_display.csv');test=read('test_metrics.csv');policy=json.loads((ROOT/'docs/cost_policy.json').read_text());primary=test[(test.scope=='all_test')&np.isclose(test.q,policy['selected_q'])]
fig,ax=plt.subplots(1,2,figsize=(6.2,2.75),layout='constrained')
# Keep every stored recall-change point. Downsampling by uniform thresholds distorts PR curves.
for k,col,sty,label in [('B3',NAVY,'-','B3'),('core7_iRF',TEAL,'--','Seven-feature iRF'),('core7_LR',GRAY,':','Seven-feature logistic')]:
 matches=[s for s in pr.series.unique() if 'Test' in s and k in s]
 if not matches:raise ValueError((k,pr.series.unique()))
 z=pr[pr.series==matches[0]]
 ax[0].step(z.recall,z.precision,where='post',color=col,ls=sty,lw=1,label=label)
ax[0].set(title='A. Holdout precision-recall curves',xlabel='Row recall',ylabel='Precision',xlim=(0,1),ylim=(0,1.025));ax[0].legend(frameon=False)
z=test[(test.pipeline=='B3')&(test.scope=='all_test')].sort_values('q')
ax[1].plot(z.q*100,z.event_recall*100,'o-',color=NAVY,label='Event recall',ms=3,lw=1)
ax[1].plot(z.q*100,z.precision*100,'s--',color=TEAL,label='Row precision',ms=3,lw=1)
ax[1].set(title='B. B3 at predeclared alert budgets',xlabel='Quarterly alert share (%)',ylabel='Percent',ylim=(0,103));ax[1].legend(frameon=False,loc='center right')
save(fig,'holdout_ranking')

sh=read('final_B3_shap.csv').sort_values('mean_abs_SHAP_probability').tail(8)
fig,ax=plt.subplots(1,2,figsize=(6.2,2.8),layout='constrained')
ax[0].barh(sh.feature.str.replace('_',' ',regex=False),sh.mean_abs_SHAP_probability*100,color=NAVY,height=.65)
ax[0].set(title='A. In-sample Tree SHAP',xlabel='Mean absolute contribution (pp)')
z=read('final_B3_ALE_eq_assets.csv');ax[1].plot(z.edge,z.ale*100,color=NAVY,lw=1.3);ax[1].axhline(0,color=GRAY,lw=.6);ax[1].set(title='B. Capital adequacy: first-order ALE',xlabel='Equity / assets (%)',ylabel='Centered effect (pp)')
save(fig,'explainability')
print('Six paper figure pairs written from unchanged aggregate evidence.')
