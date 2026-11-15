"""Automated source-field quality profile; diagnostic only, no model changes."""
from datetime import date
import polars as pl
from .pipeline import ROOT,read_financials
from .rules import build_pit_view

def build_quality_report():
    f=read_financials(date(2011,9,30));stats=[]
    for c,t in f.schema.items():
        row={'field':c,'dtype':str(t),'rows':f.height,'missing':f[c].null_count(),'missing_share':f[c].null_count()/f.height,'zero':None,'negative':None}
        if t.is_numeric():row.update(zero=int((f[c]==0).sum()),negative=int((f[c]<0).sum()))
        stats.append(row)
    pl.DataFrame(stats,infer_schema_length=None).write_csv(ROOT/'reports/tables/source_quality_profile.csv')
    pit,_=build_pit_view(f)
    counts=pl.DataFrame([{'flag':c,'rows_flagged':int(pit[c].fill_null(False).sum()),'meaning':'diagnostic exception, not necessarily error','scope':'1984Q1-2011Q3'} for c in pit.columns if c.startswith('q_') and pit[c].dtype==pl.Boolean])
    counts.write_csv(ROOT/'reports/tables/source_quality_flags.csv')
    return counts
