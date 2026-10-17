#!/usr/bin/env python3
"""Exploratory, leak-free-at-policy-selection OEDI baseline audit for Qatar B R5.

Immutable inputs: archived daily objects derived exclusively from the publicly
available PVDAQ System 2107 OEDI operational-channel data.

No Qatar owner data are used; no baseline replaces frozen R5 results.
Random policies are reported as EXACT daily expectations, not sampled simulations.
Bootstrap uncertainty reflects ordered DATE variation, not actual random policy draws.
This post-outcome work is exploratory (not prospectively preregistered).
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

YEARS = (2021, 2022, 2023)
SEED = 20261017
B = 5000
BLOCKS = (5, 7, 14)
TOL = 1e-9

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def audit(cond, message):
    if not bool(cond):
        raise AssertionError(message)

def expected_random_subset(y, E, size):
    """Exact expected best-in-set regret of uniform size-k subset, no sampling.

    If candidate at descending true rank j (0-index) is best in the subset,
    that subset contains j and k-1 of the N-j-1 worse candidates.
    """
    n=len(y); k=int(size)
    audit(1<=k<=n, 'invalid set size')
    order=np.argsort(-y,kind='stable'); yy=y[order]; ee=E[order]
    denom=math.comb(n,k)
    weights=np.array([math.comb(n-j-1,k-1)/denom if n-j>=k else 0.0 for j in range(n)])
    audit(abs(weights.sum()-1)<1e-12, 'random set weights do not sum to 1')
    return (k/n, np.sum(weights * (yy[0]-yy)/yy[0]*100), np.sum(weights*(ee[0]-ee)))

def circle_bootstrap_mean_ci(arr, block, B=5000, seed=SEED):
    """7-retained-date (or B sensitivity) circular moving-block date bootstrap.

    Calendar dates may have gaps. Each sampled block consists of consecutive
    archived retained days, not calendar-day contiguous samples.
    """
    arr=np.asarray(arr,float)
    audit(arr.ndim==1 and len(arr)>0 and np.all(np.isfinite(arr)),'invalid paired values')
    n=len(arr);k=min(int(block),n)
    rng=np.random.default_rng(seed)
    blockcounts=int(np.ceil(n/k))
    starts=rng.integers(0,n,size=(B,blockcounts))
    offsets=np.arange(k)
    ix=(starts[:,:,None]+offsets[None,None,:])%n
    sampled=arr[ix.reshape(B,blockcounts*k)[:,:n]].mean(axis=1)
    return [float(v) for v in np.quantile(sampled,[0.025,0.975])]

def metrics_with_ci(d, cohort, year):
    keymap={
      'model_minus_uniform_regret_pp':'model_minus_uniform_regret_pp',
      'model_minus_historical_regret_pp':'model_minus_historical_regret_pp',
      'model_minus_historical_wrong_pp':'model_minus_historical_wrong_pp',
      'model_minus_historical_physical_kwh_per_kwac':'model_minus_historical_physical_kwh_per_kwac',
      'set_coverage_minus_size_matched_random_pp':'set_coverage_minus_size_matched_random_pp',
      'set_regret_minus_size_matched_random_pp':'set_regret_minus_size_matched_random_pp',
    }
    out=[]
    for j,(k,col) in enumerate(keymap.items()):
        row={'cohort':cohort,'year':year,'contrast':k,'estimate':float(d[col].mean()),'n_dates':len(d),
             'bootstrap_unit':'ordered retained date','resample_type':'circular moving block',
             'primary_block_dates':7,'seed':SEED,'B':B}
        for block in BLOCKS:
            row[f'ci95_block{block}_lo'],row[f'ci95_block{block}_hi']=circle_bootstrap_mean_ci(d[col],block,B,SEED+100000*year+j*137+block)
        out.append(row)
    return out

def run_cohort(input_dir,out_dir,cohort):
    dat=pd.read_csv(input_dir/f'{cohort}_DAILY_MEASURED_AND_PREDICTED.csv',parse_dates=['date'])
    audit(not dat.date.duplicated().any(),'duplicated daily dates')
    ids=[x.removeprefix('y_') for x in dat.columns if x.startswith('y_inv_')]
    N=len(ids)
    audit(N==(18 if cohort=='PRIMARY18' else 23),'unexpected cohort size')
    y_cols=['y_'+i for i in ids]; E_cols=['E_'+i for i in ids];pB_cols=['pB_'+i for i in ids]
    audit(all(x in dat.columns for x in E_cols+pB_cols),'missing daily values')
    audit(np.isfinite(dat[y_cols+E_cols+pB_cols].to_numpy()).all(),'nonfinite daily fields')
    audit((dat[y_cols]>0).all().all(),'nonpositive daily normalized response')
    years=dat.date.dt.year
    cal=dat.loc[years==2020]
    dev=dat.loc[years.isin([2018,2019])]
    audit(len(cal)>0 and len(dev)>0,'empty development or calibration')
    winner_cal=cal[y_cols].mean().idxmax().removeprefix('y_')
    winner_dev=dev[y_cols].mean().idxmax().removeprefix('y_')
    # Calibration selection uses no 2021, 2022, or 2023 labels.
    res=[];bydate=[];cis=[];checks=[]
    for year in YEARS:
        lock=pd.read_csv(input_dir/f'{cohort}_{year}_STATIC_DAILY_OUTCOMES.csv')
        source=dat.loc[years==year].copy()
        lock['date']=pd.to_datetime(lock['date'])
        audit(not lock.date.duplicated().any(),'duplicate eval date')
        audit(set(lock.date)==set(source.date),f'year {year} dates differ from archived')
        g=source.set_index('date').loc[lock.date].reset_index()
        obs=g[y_cols].to_numpy(float); predicted=g[pB_cols].to_numpy(float); E=g[E_cols].to_numpy(float)
        samples=g.n_samples.to_numpy(int)
        audit(len(g)==len(lock), 'bad merge length')
        audit((obs>0).all(),'bad observed values')
        audit(np.max(np.abs(E-obs*samples[:,None]/12))<1e-10,'E/y/n consistency error')
        top=obs.max(axis=1);imax=np.argmax(obs,axis=1)
        audit(np.all((obs==top[:,None]).sum(axis=1)==1),'exact measured ties require a policy')
        audit(np.all(np.array(ids)[imax]==lock.observed_leader.to_numpy()),'observed leaders not reproduced')
        pred_ix=np.argmax(predicted,axis=1)
        audit(np.all(np.array(ids)[pred_ix]==lock.predicted_leader.to_numpy()),'prediction leaders not reproduced')
        model_reg=100*(top-obs[np.arange(len(g)),pred_ix])/top
        model_phy=E[np.arange(len(g)),imax]-E[np.arange(len(g)),pred_ix]
        audit(np.max(np.abs(model_reg-lock.regret_pct.to_numpy()))<1e-9,'point regret reproduction failed')
        audit(np.max(np.abs(model_phy-lock.specific_energy_regret_kwh_per_kwac.to_numpy()))<1e-9,'physical regret reproduction failed')
        j=ids.index(winner_cal);z=ids.index(winner_dev)
        hist_reg=100*(top-obs[:,j])/top
        dev_reg=100*(top-obs[:,z])/top
        hist_phy=E[np.arange(len(g)),imax]-E[:,j]
        dev_phy=E[np.arange(len(g)),imax]-E[:,z]
        rand_reg=100*(top-obs.mean(axis=1))/top
        rand_phy=E[np.arange(len(g)),imax]-E.mean(axis=1)
        hist_wrong=(imax!=j).astype(int)
        dev_wrong=(imax!=z).astype(int)
        rand_wrong=np.full(len(g),1-1/N)
        sizes=lock.set_size.to_numpy(int)
        rand_set_cov=[];rand_set_reg=[];rand_set_phy=[]
        obs_cov=[];obs_set_reg=[];obs_set_phy=[]
        for idx in range(len(g)):
            members=str(lock.set_members.iloc[idx]).split(';')
            audit(all(m in ids for m in members),'unknown set member')
            audit(len(members)==sizes[idx] and len(set(members))==sizes[idx],'bad set size/membership')
            setidx=[ids.index(m) for m in members]
            covered=int(imax[idx] in setidx)
            bestmember=setidx[np.argmax(obs[idx,setidx])]
            setreg=100*(top[idx]-obs[idx,bestmember])/top[idx]
            setphy=E[idx,imax[idx]]-E[idx,bestmember]
            audit(covered==int(lock.set_coverage.iloc[idx]),'set coverage reproduction failed')
            audit(abs(setreg-lock.set_regret_pct.iloc[idx])<1e-9,'set regret reproduction failed')
            obs_cov.append(covered);obs_set_reg.append(setreg);obs_set_phy.append(setphy)
            rr=expected_random_subset(obs[idx],E[idx],sizes[idx]);rand_set_cov.append(rr[0]);rand_set_reg.append(rr[1]);rand_set_phy.append(rr[2])
        top2=np.sort(obs,axis=1)[:,-2]
        margin_pct=100*(top-top2)/top
        d=pd.DataFrame({
            'date':lock.date.dt.strftime('%Y-%m-%d'), 'year':year,'cohort':cohort,'n_candidates':N,
            'observed_leader':lock.observed_leader,'model_predicted_leader':lock.predicted_leader,
            'hist2020_calibration_only_candidate':winner_cal,
            'hist2018_19_dev_only_candidate':winner_dev,
            'top_two_observed_margin_pct':margin_pct,'n_samples':samples,
            'model_wrong':lock.wrong.to_numpy(int),'model_regret_pct':model_reg,
            'model_physical_kwh_per_kwac':model_phy,
            'uniform_expected_wrong':rand_wrong, 'uniform_expected_regret_pct':rand_reg,
            'uniform_expected_physical_kwh_per_kwac':rand_phy,
            'hist2020_wrong':hist_wrong,'hist2020_regret_pct':hist_reg,
            'hist2020_physical_kwh_per_kwac':hist_phy,
            'hist2018_19_wrong':dev_wrong,'hist2018_19_regret_pct':dev_reg,
            'hist2018_19_physical_kwh_per_kwac':dev_phy,
            'model_set_size':sizes, 'model_set_coverage':obs_cov,
            'model_set_regret_pct':obs_set_reg,'model_set_physical_kwh_per_kwac':obs_set_phy,
            'size_matched_random_expected_coverage':rand_set_cov,
            'size_matched_random_expected_set_regret_pct':rand_set_reg,
            'size_matched_random_expected_set_physical_kwh_per_kwac':rand_set_phy,
        })
        d['model_minus_uniform_regret_pp']=d.model_regret_pct-d.uniform_expected_regret_pct
        d['model_minus_historical_regret_pp']=d.model_regret_pct-d.hist2020_regret_pct
        d['model_minus_historical_wrong_pp']=100*(d.model_wrong-d.hist2020_wrong)
        d['model_minus_historical_physical_kwh_per_kwac']=d.model_physical_kwh_per_kwac-d.hist2020_physical_kwh_per_kwac
        d['set_coverage_minus_size_matched_random_pp']=100*(d.model_set_coverage-d.size_matched_random_expected_coverage)
        d['set_regret_minus_size_matched_random_pp']=d.model_set_regret_pct-d.size_matched_random_expected_set_regret_pct
        bydate.append(d); cis.extend(metrics_with_ci(d,cohort,year))
        summary={'cohort':cohort,'year':year,'dates':len(g),'candidates':N,
            'hist2020_candidate':winner_cal,'hist2018_19_candidate':winner_dev,
            'model_wrong_pct':100*d.model_wrong.mean(), 'uniform_wrong_expected_pct':100*d.uniform_expected_wrong.mean(),
            'hist2020_wrong_pct':100*d.hist2020_wrong.mean(),'hist2018_19_wrong_pct':100*d.hist2018_19_wrong.mean(),
            'model_regret_pct':d.model_regret_pct.mean(),'uniform_expected_regret_pct':d.uniform_expected_regret_pct.mean(),
            'hist2020_regret_pct':d.hist2020_regret_pct.mean(),'hist2018_19_regret_pct':d.hist2018_19_regret_pct.mean(),
            'model_phys_kwh_per_kwac':d.model_physical_kwh_per_kwac.mean(),'uniform_expected_phys_kwh_per_kwac':d.uniform_expected_physical_kwh_per_kwac.mean(),
            'hist2020_phys_kwh_per_kwac':d.hist2020_physical_kwh_per_kwac.mean(),'hist2018_19_phys_kwh_per_kwac':d.hist2018_19_physical_kwh_per_kwac.mean(),
            'model_set_size':d.model_set_size.mean(),'model_set_coverage_pct':100*d.model_set_coverage.mean(),
            'size_matched_random_expected_coverage_pct':100*d.size_matched_random_expected_coverage.mean(),
            'model_set_regret_pct':d.model_set_regret_pct.mean(),'size_matched_random_expected_set_regret_pct':d.size_matched_random_expected_set_regret_pct.mean(),
            'median_observed_top_two_margin_pct':float(d.top_two_observed_margin_pct.median()),
            'wrong_model_daily_regret_le_0_1_pct_count':int(((d.model_wrong==1)&(d.model_regret_pct<=0.1)).sum())}
        res.append(summary)
        checks.append({'cohort':cohort,'year':year,'n_dates':len(g), 'point_leader_replay':'PASS','set_membership_replay':'PASS',
                       'physical_replay':'PASS','value_replay':'PASS','n_candidates':N,'zero_ties':True,'calibration_only':True})
    all_daily=pd.concat(bydate,ignore_index=True)
    all_daily.to_csv(out_dir/f'{cohort}_BASELINE_DAILY.csv',index=False,float_format='%.13g')
    return res,cis,checks,all_daily

def test_small_random():
    y=np.array([1.,.8,.55,.2]); E=y*3
    for k in range(1,5):
        subsets=list(itertools.combinations(range(4),k))
        a=np.mean([int(0 in subs) for subs in subsets]); b=np.mean([(y.max()-y[list(subs)].max())/y.max()*100 for subs in subsets]);c=np.mean([(E.max()-E[list(subs)].max()) for subs in subsets])
        a2,b2,c2=expected_random_subset(y,E,k)
        audit(np.max(np.abs(np.array([a,b,c])-np.array([a2,b2,c2])))<1e-12, 'exact random subset formula test failed')

def run_fresh_comparison(input_dir, out_dir):
    """Evaluation uses the SAME Apr-Dec days for static, fresh and 2020 historical.

    Only PRIMARY18 has a locked fresh-label outcome file. Never fabricate
    SECONDARY23 fresh-label results.
    """
    cohort='PRIMARY18'
    dat=pd.read_csv(input_dir/f'{cohort}_DAILY_MEASURED_AND_PREDICTED.csv',parse_dates=['date'])
    ycols=[c for c in dat.columns if c.startswith('y_inv_')]
    ids=[c.removeprefix('y_') for c in ycols]
    cal=dat.loc[dat.date.dt.year==2020]
    histid=cal[ycols].mean().idxmax().removeprefix('y_'); jj=ids.index(histid)
    dat=dat.set_index('date')
    allrows=[];annual=[]; ci=[]
    for year in YEARS:
        static=pd.read_csv(input_dir/f'{cohort}_{year}_APR_DEC_STATIC.csv')
        fresh=pd.read_csv(input_dir/f'{cohort}_{year}_APR_DEC_FRESH.csv')
        audit(static.date.equals(fresh.date),'fresh static dates mismatch')
        check=dat.loc[pd.to_datetime(static.date)]
        obs=check[ycols].to_numpy();E=check[['E_'+i for i in ids]].to_numpy()
        mx=obs.max(axis=1);winner=np.argmax(obs,axis=1)
        hh=100*(mx-obs[:,jj])/mx
        hp=E.max(axis=1)-E[:,jj]
        # Original R5 fresh outcomes independently re-evaluated against y and E.
        fresh_ix=np.array([ids.index(s) for s in fresh.predicted_leader.to_numpy()])
        fresh_r=100*(mx-obs[np.arange(len(obs)),fresh_ix])/mx
        fresh_p=E.max(axis=1)-E[np.arange(len(obs)),fresh_ix]
        audit(np.max(np.abs(fresh_r-fresh.regret_pct.to_numpy()))<TOL,'fresh regret replication mismatch')
        audit(np.max(np.abs(fresh_p-fresh.specific_energy_regret_kwh_per_kwac.to_numpy()))<TOL,'fresh energy replication mismatch')
        audits=[];rand_set_cov=[];rand_set_reg=[]
        for j in range(len(fresh)):
            sids=str(fresh.set_members.iloc[j]).split(';')
            audit(len(sids)==int(fresh.set_size.iloc[j]),'fresh set membership mismatch')
            idx=[ids.index(z) for z in sids]
            coverage=int(ids[winner[j]] in sids)
            regret=100*(mx[j]-np.max(obs[j,idx]))/mx[j]
            audit(coverage==int(fresh.set_coverage.iloc[j]),'fresh set coverage mismatch')
            audit(abs(regret-fresh.set_regret_pct.iloc[j])<TOL,'fresh set regret mismatch')
            t=expected_random_subset(obs[j],E[j],len(sids))
            rand_set_cov.append(t[0]);rand_set_reg.append(t[1])
        df=pd.DataFrame({
          'date':static.date,'year':year,'n_candidates':18,
          'hist2020_candidate':histid,
          'static_wrong':static.wrong.to_numpy(),
          'fresh_wrong':fresh.wrong.to_numpy(),
          'hist2020_wrong':(winner!=jj).astype(int),
          'static_regret_pct':static.regret_pct.to_numpy(),
          'fresh_regret_pct':fresh_r,
          'hist2020_regret_pct':hh,
          'static_physical_kwh_per_kwac':static.specific_energy_regret_kwh_per_kwac.to_numpy(),
          'fresh_physical_kwh_per_kwac':fresh_p,
          'hist2020_physical_kwh_per_kwac':hp,
          'fresh_set_coverage':fresh.set_coverage.to_numpy(),
          'fresh_set_size':fresh.set_size.to_numpy(),
          'fresh_set_regret_pct':fresh.set_regret_pct.to_numpy(),
          'matched_uniform_set_expected_coverage':rand_set_cov,
          'matched_uniform_set_expected_regret_pct':rand_set_reg,
        })
        df['fresh_minus_hist_regret_pp']=df.fresh_regret_pct-df.hist2020_regret_pct
        df['fresh_minus_hist_wrong_pp']=100*(df.fresh_wrong-df.hist2020_wrong)
        df['fresh_minus_hist_physical_kwh_per_kwac']=df.fresh_physical_kwh_per_kwac-df.hist2020_physical_kwh_per_kwac
        df['fresh_minus_static_regret_pp']=df.fresh_regret_pct-df.static_regret_pct
        df['fresh_set_cov_minus_size_matched_random_pp']=100*(df.fresh_set_coverage-df.matched_uniform_set_expected_coverage)
        df['fresh_set_regret_minus_size_matched_random_pp']=df.fresh_set_regret_pct-df.matched_uniform_set_expected_regret_pct
        allrows.append(df)
        annual.append({'cohort':cohort,'year':year,'period':'Apr-Dec' if year!=2023 else 'Apr-Oct', 'dates':len(df),'hist2020_candidate':histid,
                       'static_regret_pct':df.static_regret_pct.mean(),'fresh_regret_pct':df.fresh_regret_pct.mean(), 'hist2020_regret_pct':df.hist2020_regret_pct.mean(),
                       'static_wrong_pct':100*df.static_wrong.mean(),'fresh_wrong_pct':100*df.fresh_wrong.mean(),'hist2020_wrong_pct':100*df.hist2020_wrong.mean(),
                       'static_phys_kwh_per_kwac':df.static_physical_kwh_per_kwac.mean(),'fresh_phys_kwh_per_kwac':df.fresh_physical_kwh_per_kwac.mean(),'hist2020_phys_kwh_per_kwac':df.hist2020_physical_kwh_per_kwac.mean(),
                       'fresh_set_size':df.fresh_set_size.mean(),'fresh_set_coverage_pct':100*df.fresh_set_coverage.mean(), 'same_size_random_set_coverage_pct':100*df.matched_uniform_set_expected_coverage.mean(),
                       'fresh_set_regret_pct':df.fresh_set_regret_pct.mean(),'same_size_random_set_regret_pct':df.matched_uniform_set_expected_regret_pct.mean()})
        for k,metric in enumerate(['fresh_minus_hist_regret_pp','fresh_minus_hist_wrong_pp','fresh_minus_hist_physical_kwh_per_kwac','fresh_minus_static_regret_pp','fresh_set_cov_minus_size_matched_random_pp','fresh_set_regret_minus_size_matched_random_pp']):
            row={'year':year,'contrast':metric,'estimate':df[metric].mean(),'n_dates':len(df),'B':B,'seed':SEED,'bootstrap_unit':'retained date','bootstrap_type':'circular moving block'}
            for block in BLOCKS:
                row[f'ci95_block{block}_lo'],row[f'ci95_block{block}_hi']=circle_bootstrap_mean_ci(df[metric],block,B,SEED+year*100001+k*11+block)
            ci.append(row)
    pd.concat(allrows,ignore_index=True).to_csv(out_dir/'PRIMARY18_FRESH_VS_BASELINES_DAILY.csv',index=False,float_format='%.13g')
    pd.DataFrame(annual).to_csv(out_dir/'PRIMARY18_FRESH_VS_BASELINES_SUMMARY.csv',index=False,float_format='%.13g')
    pd.DataFrame(ci).to_csv(out_dir/'PRIMARY18_FRESH_VS_BASELINES_CI.csv',index=False,float_format='%.13g')
    return annual,ci


def calibration_stability(input_dir,out_dir):
    """Sensitivity of 2020 fixed-best candidate under blocked recalibration.

    This evaluates how sensitive the *selected baseline identity* is to
    temporal variation in the available calibration period. The 2021-2023
    outcome data are NOT involved in this selection.
    """
    output=[]
    for c in ['PRIMARY18','SECONDARY23']:
        d=pd.read_csv(input_dir/f'{c}_DAILY_MEASURED_AND_PREDICTED.csv')
        ycols=[x for x in d if x.startswith('y_inv_')]
        arr=d.loc[d.date.str.startswith('2020-'),ycols].to_numpy(float)
        ids=[x.removeprefix('y_') for x in ycols]; n=len(arr);audit(n>7,'too little calibration')
        true=ids[np.argmax(arr.mean(axis=0))]
        for block in BLOCKS:
            rng=np.random.default_rng(SEED+len(ids)*100+block)
            starts=rng.integers(0,n,size=(B,int(np.ceil(n/block))))
            ix=((starts[:,:,None]+np.arange(block)[None,None,:])%n).reshape(B,-1)[:,:n]
            sel=np.argmax(arr[ix].mean(axis=1),axis=1)
            for i,count in sorted(enumerate(np.bincount(sel,minlength=len(ids))),key=lambda x:-x[1]):
                if count:
                    output.append({'cohort':c,'calibration_year':2020,'block_retained_dates':block,'candidate':ids[i],
                                   'selection_rate':count/B,'n_resamples':B,'observed_selection':true,'calibration_dates':n})
        audit(true in [r['candidate'] for r in output if r['cohort']==c],'calibration selection missing')
    pd.DataFrame(output).to_csv(out_dir/'CALIBRATION_BEST_IDENTITY_BOOTSTRAP.csv',index=False,float_format='%.13g')
    return output


def candidate_rule_sensitivity(input_dir,out_dir):
    output=[]
    for c in ['PRIMARY18','SECONDARY23']:
        d=pd.read_csv(input_dir/f'{c}_DAILY_MEASURED_AND_PREDICTED.csv')
        cols=[x for x in d if x.startswith('y_inv_')];ids=[x.removeprefix('y_') for x in cols]
        cal=d[d.date.str.startswith('2020-')];dev=d[d.date.str.startswith(('2018-','2019-'))]
        arr=cal[cols].to_numpy();modes=np.argmax(arr,axis=1)
        choices={
          '2020_calibration_mean':ids[np.argmax(arr.mean(axis=0))],
          '2020_calibration_median':ids[np.argmax(np.median(arr,axis=0))],
          '2020_calibration_modal_daily_leader':ids[np.argmax(np.bincount(modes,minlength=len(ids)))],
          '2018_19_development_mean':ids[np.argmax(dev[cols].to_numpy().mean(axis=0))]
        }
        for year in YEARS:
            g=d[d.date.str.startswith(str(year)+'-')]
            y=g[cols].to_numpy();mx=y.max(axis=1);imax=np.argmax(y,axis=1)
            for name,cand in choices.items():
                j=ids.index(cand)
                output.append({'cohort':c,'year':year,'selection_rule':name,'candidate':cand,
                'n_dates':len(g),'wrong_pct':100*np.mean(imax!=j),
                'regret_pct':float(np.mean(100*(mx-y[:,j])/mx))})
    pd.DataFrame(output).to_csv(out_dir/'CALIBRATION_SELECTION_RULE_SENSITIVITY.csv',index=False,float_format='%.13g')
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input-dir',required=True)
    ap.add_argument('--output-dir',required=True)
    a=ap.parse_args(); input_dir=Path(a.input_dir);out_dir=Path(a.output_dir);out_dir.mkdir(parents=True,exist_ok=True)
    test_small_random()
    summaries=[]; ci=[]; tests=[]; all_cohorts={}
    for cohort in ('PRIMARY18','SECONDARY23'):
        sm,ss,qa,d=run_cohort(input_dir,out_dir,cohort);summaries.extend(sm);ci.extend(ss);tests.extend(qa);all_cohorts[cohort]=d
    fresh_annual,fresh_ci=run_fresh_comparison(input_dir,out_dir)
    calibration_results=calibration_stability(input_dir,out_dir)
    candidate_rules=candidate_rule_sensitivity(input_dir,out_dir)
    # One pooled observational summary; do not pool incompatible cohort candidate universes.
    pd.DataFrame(summaries).to_csv(out_dir/'ANNUAL_BASELINE_SUMMARY.csv',index=False,float_format='%.13g')
    pd.DataFrame(ci).to_csv(out_dir/'PAIRED_BLOCK_BOOTSTRAP_INTERVALS.csv',index=False,float_format='%.13g')
    (out_dir/'BASELINE_QA.json').write_text(json.dumps({'random_subset_enumeration':'PASS','year_cohort_assertions':tests,'result':'PASS','n_daily_rows':sum(len(v) for v in all_cohorts.values()),'note':'Exploratory post-outcome baseline analysis, original R5 results untouched'},indent=2))
    inputs=[f for f in sorted(input_dir.glob('*.csv')) if f.name.endswith(('DAILY_MEASURED_AND_PREDICTED.csv','STATIC_DAILY_OUTCOMES.csv'))]
    (out_dir/'INPUT_SHA256.csv').write_text('source_name,sha256,size_bytes\n'+''.join(f'{x.name},{sha256(x)},{x.stat().st_size}\n' for x in inputs))
    (out_dir/'METHODS_SPECIFICATION.json').write_text(json.dumps({
     'project':'Project 10 — Qatar B R5','status':'EXPLORATORY — POST-OUTCOME, NOT PREREGISTERED',
     'source':'Archived OEDI PVDAQ 2107 public-source daily derived objects distributed with this repository',
     'unit':'one retained evaluation date; no mixing of distinct primary and secondary cohorts',
     'static_point_model':'Frozen R5 Branch B predicted argmax pB',
     'uniform_random_point':'Exact per-date expectation of uniformly drawing 1 of 18 (primary) or 23 (secondary) candidates; no simulation',
     'historical_best_2020':'Single fixed candidate with largest 2020 calibration-date mean normalized daily response y; ties resolved by order of fixed input columns',
     'historical_best_2018_19':'Development-only mean daily response selected from 2018–2019; descriptive sensitivity',
     'matched_random_set':'Exact uniform subset of size equal to each date\'s frozen R5 set; expected top1 coverage k/N, expected best-member regret using hypergeometric order-statistics',
     'regret_pct':'100*(max_i y_i - y_selected)/max_i y_i',
     'physical':'max_i E_i - E_selected in admitted-window AC kWh/kWac, with E_i=n_samples/12 * y_i',
     'uncertainty':'Paired circular moving-block date bootstrap with 5000 resamples for block sizes 5, 7 and 14 retained dates, stratified by year and cohort. This uncertainty does not include random-action selection variance.',
     'seed':SEED,'n_bootstrap':B,'primary_block_length_retained_dates':7,
     'caveats':['No causal claim','No comparison to Qatar DC values','OEDI 23-channel secondary cohort has unequal source-record module quantities','2020-calibration comparator uses the same 2020 observed labels available to the frozen calibration procedure','The exercise was proposed after inspecting primary outcomes; results are exploratory not independent confirmation','A constant leader may be operationally inadmissible as a real dispatch/switch policy absent system-level technical constraints']
    },indent=2))
    print('QA PASS; n daily',sum(len(v) for v in all_cohorts.values()))
    print('CALIBRATION BOOTSTRAP',pd.DataFrame(calibration_results).to_string(index=False))
    print('FRESH vs HIST\n',pd.DataFrame(fresh_annual).to_string(index=False,float_format=lambda f:f'{f:.5f}'))
    print('FRESH vs HIST CIs\n',pd.DataFrame(fresh_ci).to_string(index=False,float_format=lambda f:f'{f:.5f}'))
    print(pd.DataFrame(summaries).to_string(index=False,float_format=lambda f:f'{f:.5f}'))
    print(pd.DataFrame(ci).to_string(index=False,float_format=lambda f:f'{f:.5f}'))

if __name__=='__main__':main()
