"""Counterexamples for policies that can silently change reported performance."""
import numpy as np
import pandas as pd
from fdic_risk.policy import alerts,chain_counts,summarize
from fdic_risk.pipeline import make_model,feature_contract
from fdic_risk.rules import ContractCapperV4

def toy(scores):
    return pd.DataFrame({'CERT':range(len(scores)),'prediction_as_of':pd.to_datetime(['2000-03-31']*len(scores)),'score':scores,'y_true':[0]*len(scores)})

def test_boundary_tie_is_excluded_as_a_block():
    d=toy([.9,.8,.8,.1]);assert alerts(d,.5).tolist()==[True,False,False,False]

def test_never_and_always():
    d=toy([.4,.3,.2]);assert alerts(d,0).sum()==0;assert alerts(d,1).sum()==3

def test_repeat_requires_adjacent_calendar_quarter():
    d=pd.DataFrame({'CERT':[1,1,1],'prediction_as_of':pd.to_datetime(['2000-03-31','2000-06-30','2000-12-31'])})
    n,r,_=chain_counts(d,np.array([True,True,True]));assert (n,r)==(2,1)

def test_repeated_quarters_count_one_event():
    d=pd.DataFrame({'CERT':[1,1,2],'prediction_as_of':pd.to_datetime(['2000-03-31','2000-06-30','2000-06-30']),'y_true':[1,1,0],'score':[.8,.9,.1]})
    f=pd.DataFrame({'CERT':[1],'fd':pd.to_datetime(['2000-08-01'])})
    m=summarize(d,np.array([True,True,False]),f);assert m['events']==1 and m['caught_events']==1 and m['TP']==2

def test_no_positive_is_undefined():
    d=toy([.3,.2]);f=pd.DataFrame({'CERT':pd.Series([],dtype=int),'fd':pd.to_datetime([])})
    m=summarize(d,alerts(d,0),f);assert m['AP_D7'] is None and m['event_recall'] is None and m['precision'] is None

def test_cap_state_does_not_learn_on_transform():
    x=np.array([[-5.,0.],[0.,1.],[5.,2.],[10.,np.nan]])
    cap=ContractCapperV4(['eq_assets','noncurrent_loans'],feature_contract(['eq_assets','noncurrent_loans'])).fit(x)
    before=cap.upper_bounds_.copy();cap.transform(np.array([[1e8,1e8]]));assert np.array_equal(before,cap.upper_bounds_);assert cap.transform(x)[0,0]<0

def test_all_missing_training_column_refused():
    import pytest
    with pytest.raises(ValueError):ContractCapperV4(['eq_assets'],{'eq_assets':'signed'}).fit(np.array([[np.nan],[np.nan]]))
