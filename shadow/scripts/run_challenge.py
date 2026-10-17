#!/usr/bin/env python3
"""Post-R5 time-ordered shadow alert comparison on OEDI PVDAQ 2107 primary-18.

Designed AFTER outcomes were available; this is a retrospective pseudo-stream,
NOT a live deployment or a prespecified validation trial.
Only daily derived public-OEDI archives are admitted. Qatar owner data excluded.
Flags at day t use ONLY same-day PREDICTED/SET fields and previous-date labels.
All sampling is over originally admitted dates (not consecutive calendar days).
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DEF=Path(__file__).resolve().parents[1]
YEARS=(2021,2022,2023)
MODES=('STATIC','FRESH')
EPS=1e-9


def check(cond,msg):
    if not bool(cond): raise AssertionError(msg)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def margin(x):
    a=np.sort(np.asarray(x,float),axis=1)
    return 100*(a[:,-1]-a[:,-2])/a[:,-1]

def make_set(pa,pb,q):
    a=100*(pa.max(axis=1,keepdims=True)-pa)/pa.max(axis=1,keepdims=True)
    b=100*(pb.max(axis=1,keepdims=True)-pb)/pb.max(axis=1,keepdims=True)
    deficit=np.maximum(a,b)
    ok=deficit<=q
    for i in np.where(~ok.any(axis=1))[0]:ok[i,deficit[i].argmin()]=True
    return ok

def lag_batch_policy(delta, span=7):
    """For each *new* block, use only previous completed span of labels."""
    arr=np.asarray(delta,float);out=np.zeros(len(arr),dtype=bool)
    for i in range(len(arr)):
        b=i//span
        if b>0:
            prior=arr[(b-1)*span:b*span]
            check(len(prior)==span,'prior block not fully observed')
            out[i]=prior.mean()>0
    return out

def lag_month_policy(delta,dates):
    """At month m, compare previous calendar month's admitted-date labels only."""
    dates=pd.DatetimeIndex(dates)
    months=dates.to_period('M'); d=np.asarray(delta,float)
    flag=np.zeros(len(d),dtype=bool)
    for m in months.unique():
        idx=np.flatnonzero(months==m)
        past=np.flatnonzero(months==m-1)
        if len(past)>=3: flag[idx]=d[past].mean()>0
    return flag

def confusion(flags,events):
    flags=np.asarray(flags,bool);events=np.asarray(events,bool); n=len(flags)
    TP=int(np.sum(flags&events));FP=int(np.sum(flags&~events));FN=int(np.sum(~flags&events));TN=int(np.sum(~flags&~events))
    return dict(flagged_days=TP+FP,review_fraction_pct=100*(TP+FP)/n,material_event_days=TP+FN,
        true_positive_days=TP,nonmaterial_flagged_days=FP,missed_material_days=FN,
        precision_pct=(100*TP/(TP+FP)) if TP+FP else None,
        recall_pct=(100*TP/(TP+FN)) if TP+FN else None,
        specificity_pct=(100*TN/(TN+FP)) if TN+FP else None)

def run(root:Path):
    inp=root/'inputs';out=root/'results';out.mkdir(exist_ok=True,parents=True)
    files=sorted(inp.iterdir());check(len(files)==9,'expected 8 daily input CSV files and one original JSON')
    lock=json.loads((root/'qa'/'INPUT_SOURCE_LOCK_SHA256.json').read_text())['files']
    check(set(lock)=={f.name for f in files},'input inventory diverged from source lock')
    check(all(sha(f)==lock[f.name] for f in files),'input SHA-256 mismatch from approved OEDI-derived archive')
    w=pd.read_csv(inp/'PRIMARY18_DAILY_MEASURED_AND_PREDICTED.csv',parse_dates=['date'])
    supp=pd.read_csv(inp/'PRIMARY18_DAILY_SUPPORT.csv',parse_dates=['date'])
    check(len(w)==789 and not w.date.duplicated().any(),'wide record count/duplicates')
    check(len(supp)==len(w) and set(supp.date)==set(w.date),'support dates')
    ids=[s[2:] for s in w if s.startswith('y_inv_')]
    check(len(ids)==18 and len(set(ids))==18 and 'inv_05' not in ids,'primary-18 admission')
    Y=['y_'+k for k in ids];A=['pA_'+k for k in ids];B=['pB_'+k for k in ids];E=['E_'+k for k in ids]
    check(w[Y+A+B+E].notna().all().all(),'missing numerical input')
    cal20=w[w.date.dt.year==2020].copy();check(len(cal20)==210,'historical calibration days')
    hist=cal20[Y].mean().idxmax()[2:];check(hist=='inv_14','calibration-only winner')
    H=ids.index(hist)
    yc=cal20[Y].to_numpy(float)
    true_gap=margin(yc)
    T=float(np.quantile(true_gap,.90,method='linear'))
    T_sensitivity={'half':T/2,'primary':T,'double':T*2}
    check(.4<T<.6,'calibrated consequence separation outside anticipated 2020 band')
    fconfig={int(z['year']):z for z in json.loads((inp/'PRIMARY18_FRESH_REVALIDATION.json').read_text())}
    check(set(fconfig)==set(YEARS),'fresh pre-outcome settings')
    index=w.set_index('date')
    pre_records=[]; post_records=[]; metrics=[]; featurecal=[]; ci_diag=[]; timestamp_qa=[]
    for year in YEARS:
      for mode in MODES:
        fname=f'PRIMARY18_{year}_STATIC_DAILY_OUTCOMES.csv' if mode=='STATIC' else f'PRIMARY18_{year}_APR_DEC_FRESH.csv'
        locked=pd.read_csv(inp/fname,parse_dates=['date']).sort_values('date').reset_index(drop=True)
        n=len(locked);check(len(locked.date.unique())==n,'evaluation day duplicates')
        check(set(locked.date).issubset(set(w.date)),'unmatched days')
        if mode=='STATIC':
            check(set(locked.date)==set(w.loc[w.date.dt.year==year,'date']),'static day identity')
            calibration=cal20
            q=12.578505387788798
            predcols=B
        else:
            calibration=w[(w.date.dt.year==year)&(w.date.dt.month<=3)].copy()
            check(len(calibration)==int(fconfig[year]['n_cal_dates']),'fresh calendar calibration count')
            check(int(fconfig[year]['n_eval_dates'])==n,'fresh days')
            check(calibration.date.max()<locked.date.min(),'future leakage in calibration')
            q=float(fconfig[year]['fresh_q'])
            predcols=A
        c_margin=margin(calibration[predcols].to_numpy(float))
        q20=float(np.quantile(c_margin,.20,method='linear'))
        degenerate=bool(np.ptp(c_margin)<1e-10)
        featurecal.append({'year':year,'mode':mode,'calibration_period':
               '2020_CALENDAR' if mode=='STATIC' else f'{year}_JAN_MAR',
               'n_calibration_dates':len(calibration),'historical_2020_reference':hist,
               'predicted_margin_q20_pct':q20,
               'calibration_predicted_margin_range_pct':float(np.ptp(c_margin)),
               'margin_noninformative_constant':int(degenerate),
               'full_set_cutoff':18,'set_calibration_q_pct':q})
        g=index.loc[locked.date]
        obs=g[Y].to_numpy(float); pre=g[predcols].to_numpy(float); pa=g[A].to_numpy(float);pb=g[B].to_numpy(float); e=g[E].to_numpy(float)
        check(np.isfinite(obs).all() and np.isfinite(pre).all(),'no finite inputs')
        top=np.argmax(obs,axis=1);mp=np.argmax(pre,axis=1)
        npred=np.array(ids)[mp]; ntrue=np.array(ids)[top]
        check(np.array_equal(npred,locked.predicted_leader.to_numpy()) and np.array_equal(ntrue,locked.observed_leader.to_numpy()),'replayed leaders differ')
        model_reg=100*(obs.max(axis=1)-obs[np.arange(n),mp])/obs.max(axis=1)
        hist_reg=100*(obs.max(axis=1)-obs[:,H])/obs.max(axis=1)
        delta=model_reg-hist_reg
        check(np.max(np.abs(model_reg-locked.regret_pct.to_numpy()))<EPS,'R5 regret mismatch')
        model_E=e.max(axis=1)-e[np.arange(n),mp];hist_E=e.max(axis=1)-e[:,H]
        check(np.max(np.abs(model_E-locked.specific_energy_regret_kwh_per_kwac.to_numpy()))<EPS,'physical regret mismatch')
        k=make_set(pa,pb,q)
        check(np.array_equal(k.sum(axis=1),locked.set_size.to_numpy()),'candidate-set size replay')
        for i in range(n):
            check(';'.join(np.array(ids)[k[i]])==locked.set_members.iloc[i], 'candidate membership replay')
        m=margin(pre)
        # Explicit decision information boundaries:
        # same-date feature-derived predicted margin/set + previous dates' LABELS only.
        # +/- 1e-10 guard acknowledges machine precision in constant Branch A margin.
        s1=npred!=hist
        lowmargin=m<=q20+1e-10
        fullset=k.sum(axis=1)==18
        s2=lowmargin | fullset
        s3=lag_batch_policy(delta,7)
        s3alt=lag_batch_policy(delta,14)
        s3month=lag_month_policy(delta,locked.date)
        # Pre-outcome rows never include labels/current y, nor any retrospective event.
        for i,dt in enumerate(locked.date):
            prefix={'year':year,'mode':mode,'date':str(dt.date()),'admitted_samples':int(locked.n_samples.iloc[i]),
                    'predicted_leader':str(npred[i]),'historical_reference':hist,
                    'predicted_margin_pct':float(m[i]),'candidate_set_size':int(k[i].sum()),
                    'margin_q20_calibration_pct':q20,'flag_S1_disagreement':int(s1[i]),
                    'flag_S2_margin_or_full_set':int(s2[i]),'flag_S2_margin_only':int(lowmargin[i]),
                    'flag_S2_full_set_only':int(fullset[i]),'flag_S3_lagged_7retained':int(s3[i]),
                    'flag_S3_lagged_14retained':int(s3alt[i]),'flag_S3_lagged_calendar_month':int(s3month[i]),
                    'previous_full_7day_block_available':int(i>=7),
                    'design':'RETROSPECTIVE_SHADOW_PRE_OUTCOME_MASKED'}
            pre_records.append(prefix)
            post_records.append({**prefix,'observed_leader_post_label':str(ntrue[i]),
               'model_regret_pct_post_label':float(model_reg[i]),
               'historical_regret_pct_post_label':float(hist_reg[i]),
               'model_excess_regret_pp_post_label':float(delta[i]),
               'model_physical_shortfall_kwh_per_kwac_post_label':float(model_E[i]),
               'historical_physical_shortfall_kwh_per_kwac_post_label':float(hist_E[i]),
               'model_excess_physical_shortfall_kwh_per_kwac_post_label':float(model_E[i]-hist_E[i]),
               'event_material_primary_post_label':int(delta[i]>T)})
        policies={'S1_DISAGREEMENT':s1,'S2_MARGIN_OR_FULLSET':s2,
          'S3_7RETAINED_LAGGED':s3,'S2a_MARGIN_ONLY':lowmargin,'S2b_FULLSET_ONLY':fullset,
          'S3a_14RETAINED_LAGGED':s3alt,'S3b_PREV_CALENDAR_MONTH':s3month}
        for level,thr in T_sensitivity.items():
            event=delta>thr
            for pn,f in policies.items():
                result=confusion(f,event)
                result.update(year=year,mode=mode,policy=pn,materiality_level=level,
                    material_threshold_pp=thr,dates=n,
                    flagged_model_excess_energy_sum_kwh_per_kwac=float((model_E[f]-hist_E[f]).sum()),
                    missed_model_excess_energy_sum_kwh_per_kwac=float((model_E[~f & event]-hist_E[~f & event]).sum()),
                    baseline_event_prevalence_pct=100*float(event.mean()),
                    batch_review_sessions=int(math.ceil(n/7)) if pn=='S3_7RETAINED_LAGGED' else
                         int(math.ceil(n/14)) if pn=='S3a_14RETAINED_LAGGED' else
                         int(locked.date.dt.to_period('M').nunique()) if pn=='S3b_PREV_CALENDAR_MONTH' else None,
                    pure_predictive_margin_constant=int(degenerate))
                metrics.append(result)
        # For each trigger, distinguish same-date queue flag from previous completed block review sessions.
        timestamp_qa.append({'year':year,'mode':mode,'n_eval_dates':n,'first_eval':str(locked.date.min().date()),
          'last_eval':str(locked.date.max().date()),'calibration_last_date':str(calibration.date.max().date()),
          'gap_over_1_calendar_day_pct':100*float((locked.date.diff().dt.days.iloc[1:]>1).mean()),
          'n_lagged7_periodic_review_sessions':int(math.ceil(n/7)),
          'n_monthly_review_sessions':int(locked.date.dt.to_period('M').nunique()),
          'n_lagged7_warmup_dates':min(7,n)})
        # Prefix-only adversarial check: no result on any date t can change when labels AFTER t are deleted.
        for end in sorted({1,2,7,8,max(1,n//2),n}):
            cut=delta[:end]
            check(np.array_equal(s3[:end],lag_batch_policy(cut,7)),'S3 7-day lookahead')
            check(np.array_equal(s3alt[:end],lag_batch_policy(cut,14)),'S3 14-day lookahead')
            check(np.array_equal(s3month[:end],lag_month_policy(cut,locked.date[:end])),'S3 monthly lookahead')
    pre_df=pd.DataFrame(pre_records);post_df=pd.DataFrame(post_records);met=pd.DataFrame(metrics)
    check(len(pre_df)==748 and len(post_df)==748,'record total')
    check(pre_df.mode.tolist()==post_df.mode.tolist(),'evaluation pairing') if False else None
    check(not any(('observed' in c or 'regret' in c or 'physical' in c or 'event_material' in c or 'post_label' in c) for c in pre_df.columns),'prelabel outcome column leaking')
    check(not pre_df.isna().any().any(),'missing prelabel values')
    assert all((post_df.event_material_primary_post_label== (post_df.model_excess_regret_pp_post_label>T).astype(int)))
    save={
      'SOURCE_CALIBRATION_GATE.csv':pd.DataFrame(featurecal),
      'PRE_OUTCOME_SHADOW_FLAGS.csv':pre_df,
      'POST_OUTCOME_SHADOW_AUDIT.csv':post_df,
      'POLICY_COMPARISON_ALL_THRESHOLDS.csv':met,
      'SUPPORT_AND_REVIEW_SCHEDULE.csv':pd.DataFrame(timestamp_qa),
    }
    for name,data in save.items(): data.to_csv(out/name,index=False,float_format='%.12g')
    qa={'status':'PASS','scope':'PUBLIC_OEDI_ARCHIVED_DAILY_DERIVED_PRIMARY18_ONLY',
       'analysis_design':'EXPLORATORY_POST_OUTCOME_TIME_ORDERED_SHADOW_REPLAY_NOT_PREREGISTERED',
       'R5_unchanged':True,'Qatar_telemetry_used':False,'n_2020_calibration_days':210,
       'historical_baseline':hist,'primary_event_threshold_2020_q90_true_top2_margin_pp':T,
       'materiality_levels_threshold_pp':T_sensitivity,
       'n_records_per_mode_year':timestamp_qa,
       'input_sha256':{f.name:sha(f) for f in files},
       'outcome_leakage_check':'PASS same-day outcomes never entered policies, prefix invariance for lagged rules',
       'note':'Predictions are daily aggregates built from same-day measured meteorology; this is not an ahead-of-day forecast or pre-measurement alarm.',
       'note2':'Review session count for periodic policy != number of flag-days; compare these separately. No observer intervention or operational cost measured.',
       'uncertainty':'descriptive only; thresholds chosen from historical calibration, policy rules devised after R5 outcomes; no multiple comparisons adjustment',
       'submission_state':'HOLD, pending science and data-owner approval'}
    (out/'QA_AND_SOURCE_PROVENANCE.json').write_text(json.dumps(qa,indent=2)+'\n')
    print('SHADOW RULE COMPARISON PASS',len(pre_df),'paired pre/post rows','threshold=',T)
    print(met.query('materiality_level=="primary" and policy in ["S1_DISAGREEMENT","S2_MARGIN_OR_FULLSET","S3_7RETAINED_LAGGED"]')[['year','mode','policy','flagged_days','material_event_days','true_positive_days','missed_material_days','precision_pct','recall_pct']].to_string(index=False))
    return qa

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('--root',default=str(ROOT_DEF))
    args=pa.parse_args();run(Path(args.root).resolve())
