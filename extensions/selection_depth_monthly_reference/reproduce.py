#!/usr/bin/env python3
"""Post-outcome OEDI diagnostics; no refit, sampling, raw Qatar data or deployment claim."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'results'
INPUT = ROOT / 'baseline/inputs/PRIMARY18_DAILY_MEASURED_AND_PREDICTED.csv'
EXPECTED_SHA = '99baab9035063af1e0d9136c971653dc3ab9f9704846b3bafc706b3aae659f2e'


def run():
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError('Input hash differs from the audited daily-array snapshot')
    OUT.mkdir(parents=True, exist_ok=True)
    a = pd.read_csv(INPUT)
    assert len(a) == 789 and not a.date.duplicated().any()
    dates = pd.to_datetime(a.date)
    a['year'], a['month'] = dates.dt.year, dates.dt.month
    cs = [c[2:] for c in a if c.startswith('y_inv_')]
    assert len(cs) == 18 and 'inv_05' not in cs
    y = a[['y_' + c for c in cs]].to_numpy()
    p = a[['pB_' + c for c in cs]].to_numpy()
    pa = a[['pA_' + c for c in cs]].to_numpy()
    assert np.isfinite(y).all() and (y > 0).all()
    ii = np.arange(len(a)); best = y.max(axis=1)
    bi, ai = p.argmax(axis=1), pa.argmax(axis=1)
    assert ((y == best[:, None]).sum(axis=1) == 1).all()
    assert ((p == p.max(axis=1)[:, None]).sum(axis=1) == 1).all()
    a['B_rank'] = 1 + (y > y[ii, bi][:, None]).sum(axis=1)
    a['B_regret_pct'] = 100 * (best - y[ii, bi]) / best
    a['B_physical_kwh_per_kwac'] = (best - y[ii, bi]) * a.n_samples / 12
    a['A_regret_pct'] = 100 * (best - y[ii, ai]) / best
    a['A_choice'] = np.array(cs)[ai]
    assert (a.A_choice == 'inv_11').all()
    assert np.max(np.ptp(pa / pa[:, [0]], axis=0)) < 1e-11
    cal = a[a.year == 2020]
    assert len(cal) == 210
    annual = cal[['y_' + c for c in cs]].mean().idxmax()[2:]
    assert annual == 'inv_14'
    mapping, calibration = {}, []
    for month in range(1, 13):
        g = cal[cal.month == month]
        candidate = g[['y_' + c for c in cs]].mean().idxmax()[2:] if len(g) else None
        mapping[month] = candidate
        calibration.append(dict(month=month, calibration_dates=len(g), candidate=candidate))
    assert mapping[3] is None  # no fallback or interpolation for unsupported March
    a['annual2020_regret_pct'] = 100 * (best - a['y_' + annual]) / best
    a['monthly2020_candidate'] = a.month.map(mapping)
    a['monthly2020_regret_pct'] = [
        100 * (best[j] - a.iloc[j]['y_' + c]) / best[j] if c is not None else np.nan
        for j, c in enumerate(a.monthly2020_candidate)
    ]
    ev = a[a.year >= 2021].copy()
    depth, paired = [], []
    for year, g in ev.groupby('year'):
        w = g[g.B_rank > 1]
        depth.append(dict(year=int(year), dates=len(g), wrong_dates=len(w),
            outside_observed_top2=int((w.B_rank > 2).sum()),
            outside_top2_pct_of_wrong=100 * (w.B_rank > 2).mean(),
            median_observed_rank_wrong=w.B_rank.median(),
            median_regret_pct_wrong=w.B_regret_pct.median(),
            median_physical_kwh_per_kwac_wrong=w.B_physical_kwh_per_kwac.median()))
        for mode in ['STATIC', 'FRESH']:
            selected = g if mode == 'STATIC' else g[g.month >= 4]
            selected = selected[selected.monthly2020_candidate.notna()]
            col = 'B_regret_pct' if mode == 'STATIC' else 'A_regret_pct'
            paired.append(dict(mode=mode, year=int(year), paired_dates=len(selected),
                model_regret_pct=selected[col].mean(),
                annual2020_regret_pct=selected.annual2020_regret_pct.mean(),
                monthly2020_regret_pct=selected.monthly2020_regret_pct.mean()))
    d = pd.DataFrame(depth)
    assert d.wrong_dates.tolist() == [132, 126, 140]
    assert d.outside_observed_top2.tolist() == [121, 123, 128]
    # Independently verify vectorized ranks with Python sorting.
    for _, row in ev.iterrows():
        winner = max(cs, key=lambda c: row['pB_' + c])
        order = sorted(cs, key=lambda c: -row['y_' + c])
        assert order.index(winner) + 1 == row.B_rank
    frames = {'SELECTION_DEPTH_SUMMARY.csv': d,
        'PAIRED_MONTH_REFERENCE_SUMMARY.csv': pd.DataFrame(paired).sort_values(['mode', 'year']),
        'MONTHLY_2020_REFERENCE.csv': pd.DataFrame(calibration),
        'CALENDAR_DATE_COUNTS.csv': pd.crosstab(a.month, a.year).reindex(range(1, 13), fill_value=0).reset_index(),
        'R7_DAILY_AUDIT.csv': ev[['date', 'year', 'month', 'B_rank', 'B_regret_pct',
            'B_physical_kwh_per_kwac', 'A_choice', 'A_regret_pct', 'annual2020_regret_pct',
            'monthly2020_candidate', 'monthly2020_regret_pct']]}
    for name, frame in frames.items():
        frame.to_csv(OUT / name, index=False, float_format='%.12g', lineterminator='\n')
    report = dict(status='PASS', input_sha256=EXPECTED_SHA, static_dates=len(ev),
        fresh_dates=int((ev.month >= 4).sum()), fixed_branch_A_choice='inv_11',
        unavailable_monthly_reference=[3], scope='Post-outcome derived-array audit only')
    (OUT / 'REPRODUCTION_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    print(d.to_string(index=False))
    print(pd.DataFrame(paired).to_string(index=False))
    print('REPRODUCTION: PASS')


if __name__ == '__main__':
    run()
