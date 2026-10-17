#!/usr/bin/env python3
"""Independent assertions over source + output, deliberately not importing the generation module."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
p=Path(__file__).resolve().parents[1]
q=p/'results';i=p/'inputs'
lock=json.loads((p/'qa'/'INPUT_SOURCE_LOCK_SHA256.json').read_text())['files']
assert {f.name for f in i.iterdir()}==set(lock)
assert all(hashlib.sha256(f.read_bytes()).hexdigest()==lock[f.name] for f in i.iterdir())
pre=pd.read_csv(q/'PRE_OUTCOME_SHADOW_FLAGS.csv',parse_dates=['date'])
post=pd.read_csv(q/'POST_OUTCOME_SHADOW_AUDIT.csv',parse_dates=['date'])
stats=pd.read_csv(q/'POLICY_COMPARISON_ALL_THRESHOLDS.csv')
cal=pd.read_csv(q/'SOURCE_CALIBRATION_GATE.csv')
w=pd.read_csv(i/'PRIMARY18_DAILY_MEASURED_AND_PREDICTED.csv',parse_dates=['date']);w=w.set_index('date')
assert len(pre)==len(post)==748
assert not any(s in col for col in pre for s in ['observed','regret','physical','post_label','event_material'])
assert pre[['year','mode','date']].equals(post[['year','mode','date']])
assert set(cal['year'])=={2021,2022,2023} and len(cal)==6
assert all(cal.query('mode=="FRESH"')['margin_noninformative_constant']==1)
assert all(cal.query('mode=="STATIC"')['margin_noninformative_constant']==0)
assert len(stats)==6*7*3
for (year,mode),d in post.groupby(['year','mode'],sort=True):
    d=d.sort_values('date').reset_index(drop=True)
    expected=100*(w.loc[d.date,'y_inv_14'].to_numpy()- np.array([w.loc[t,'y_'+k] for t,k in zip(d.date,d.predicted_leader)],float))/ w.loc[d.date,[c for c in w.columns if c.startswith('y_')]].max(axis=1).to_numpy()
    assert np.max(np.abs(expected-d.model_excess_regret_pp_post_label.to_numpy()))<1e-9
    assert (d['flag_S1_disagreement']==(d.predicted_leader!=d.historical_reference)).all()
    assert not ((d.flag_S1_disagreement==0)&(d.model_excess_regret_pp_post_label>1e-10)).any()
    for s in ['flag_S3_lagged_7retained','flag_S3_lagged_14retained']:
        n=7 if s.endswith('7retained') else 14
        for j in range(len(d)):
            b=j//n
            expected_flag=0 if b==0 else int(d.model_excess_regret_pp_post_label.iloc[(b-1)*n:b*n].mean()>0)
            assert d.loc[j,s]==expected_flag,(year,mode,j,s)
    cc=cal[(cal.year==year)&(cal['mode']==mode)].iloc[0]
    threshold=float(cc.predicted_margin_q20_pct)
    expected_s2=((d.predicted_margin_pct<=threshold+1e-10)|(d.candidate_set_size==18)).astype(int)
    assert (d.flag_S2_margin_or_full_set==expected_s2).all()
    for lvl,t in [('half',0.5),('primary',1),('double',2)]:
        threshold=(json.loads((q/'QA_AND_SOURCE_PROVENANCE.json').read_text())['primary_event_threshold_2020_q90_true_top2_margin_pp'])*t
        events=d.model_excess_regret_pp_post_label>threshold
        for policy,col in [('S1_DISAGREEMENT','flag_S1_disagreement'),('S2_MARGIN_OR_FULLSET','flag_S2_margin_or_full_set'),('S3_7RETAINED_LAGGED','flag_S3_lagged_7retained')]:
            row=stats[(stats.year==year)&(stats['mode']==mode)&(stats.policy==policy)&(stats.materiality_level==lvl)].iloc[0]
            alarm=d[col].astype(bool)
            assert row.true_positive_days==int((alarm&events).sum())
            assert row.missed_material_days==int((~alarm&events).sum())
            assert row.flagged_days==int(alarm.sum())
            assert row.material_event_days==int(events.sum())
# QA record must mention all limitation boundaries.
qa=json.loads((q/'QA_AND_SOURCE_PROVENANCE.json').read_text())
assert qa['R5_unchanged'] and not qa['Qatar_telemetry_used']
assert 'not an ahead-of-day forecast' in qa['note']
assert qa['submission_state'].startswith('HOLD')
print('INDEPENDENT VERIFY PASS: 748 daily records, 6 mode-year streams, 3 thresholds, 3 main policies, no observed outcome in pre-outcome table')
