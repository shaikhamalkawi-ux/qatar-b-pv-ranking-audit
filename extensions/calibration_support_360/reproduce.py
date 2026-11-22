#!/usr/bin/env python3
"""Deterministic OEDI-only 360-window calibration-label omission replay.

Uses public OEDI PVDAQ 2107-derived daily observations already in this repository;
never accesses, reconstructs, or publishes restricted Qatar data.
This is retrospective sensitivity, not field-outage probability or a calibrated CI.
"""
from __future__ import annotations
import argparse
import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
INPUT = REPO / 'baseline/inputs/PRIMARY18_DAILY_MEASURED_AND_PREDICTED.csv'
FROZEN = HERE / 'expected/OEDI_360_SEVEN_CALENDAR_DAY_OMISSIONS_INDEPENDENT.csv'
INPUT_SHA256 = '99baab9035063af1e0d9136c971653dc3ab9f9704846b3bafc706b3aae659f2e'
FROZEN_SHA256 = '3d7da0206cde34ae0db9fbcd06476fa112fe93f0d9e46b439acf4c74b4a7bd55'


def require(ok: bool, text: str) -> None:
    if not bool(ok):
        raise AssertionError(text)


def sh(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(write_results: bool = False) -> pd.DataFrame:
    require(INPUT.is_file(), f'Public daily OEDI input absent: {INPUT}')
    require(FROZEN.is_file(), f'Frozen 360-row reference absent: {FROZEN}')
    require(sh(INPUT) == INPUT_SHA256, 'Daily input does not match source-locked OEDI hash')
    require(sh(FROZEN) == FROZEN_SHA256, 'Frozen reference output has changed')

    d = pd.read_csv(INPUT)
    require(len(d) == 789 and d.date.is_unique, 'Expected 789 unique archived dates')
    ids = sorted(c.removeprefix('y_') for c in d.columns if c.startswith('y_inv_'))
    require(len(ids) == 18 and 'inv_05' not in ids, 'Unexpected primary-18 channel list')
    Y = d[['y_' + k for k in ids]].to_numpy(float)
    A = d[['pA_' + k for k in ids]].to_numpy(float)
    B = d[['pB_' + k for k in ids]].to_numpy(float)
    require(np.isfinite(Y).all() and (Y > 0).all(), 'Invalid observed daily responses')
    require(np.isfinite(A).all() and np.isfinite(B).all(), 'Invalid model daily predictions')
    require((A.max(axis=1) > 0).all() and (B.max(axis=1) > 0).all(), 'Invalid predicted maxima')

    date = pd.to_datetime(d.date)
    year = date.dt.year.to_numpy()
    observed_best = Y.argmax(axis=1)
    daily_best = Y[np.arange(len(Y)), observed_best]
    pred_a = A.argmax(axis=1)
    pred_b = B.argmax(axis=1)
    regret_a = 100 * (daily_best - Y[np.arange(len(Y)), pred_a]) / daily_best
    regret_b = 100 * (daily_best - Y[np.arange(len(Y)), pred_b]) / daily_best
    gap_a = 100 * (A.max(axis=1)[:, None] - A) / A.max(axis=1)[:, None]
    gap_b = 100 * (B.max(axis=1)[:, None] - B) / B.max(axis=1)[:, None]
    deficit = np.maximum(gap_a, gap_b)
    observed_leader_score = deficit[np.arange(len(d)), observed_best]
    cal20 = year == 2020
    require(int(cal20.sum()) == 210, 'Expected 210 eligible calibration dates')

    windows = []
    for start in pd.date_range('2020-01-01', '2020-12-25', freq='D'):
        stop = start + pd.Timedelta(days=6)
        omitted = cal20 & (date >= start).to_numpy() & (date <= stop).to_numpy()
        kept = cal20 & ~omitted
        scores = np.sort(observed_leader_score[kept])
        n = len(scores)
        rank = min(math.ceil((n+1) * .90), n)-1
        q = float(scores[rank])
        hist = ids[np.argmax(Y[kept].mean(axis=0))]
        branch = 'A' if regret_a[kept].mean() < regret_b[kept].mean() else 'B'
        selected = deficit <= q + 1e-12
        empty = ~selected.any(axis=1)
        if np.any(empty):
            selected[empty, deficit[empty].argmin(axis=1)] = True
        row = {
            'start': start.strftime('%Y-%m-%d'), 'end': stop.strftime('%Y-%m-%d'),
            'removed': int(omitted.sum()), 'remaining': int(n),
            'calibration_q_pct': q, 'historic_reference': hist, 'calibration_point': branch,
        }
        for y in (2021, 2022, 2023):
            test = year == y
            s = selected[test]
            row[f'{y}_coverage_pct'] = 100 * s[np.arange(test.sum()), observed_best[test]].mean()
            row[f'{y}_mean_width'] = s.sum(axis=1).mean()
        windows.append(row)
    got = pd.DataFrame(windows)
    expected = pd.read_csv(FROZEN)
    require(list(got.columns) == list(expected.columns), 'Output column names/order differ')
    require(got.shape == expected.shape == (360,13), 'Expected 360 windows x 13 fields')
    for col in got:
        if pd.api.types.is_numeric_dtype(expected[col]):
            require(np.allclose(got[col], expected[col], rtol=0, atol=1e-8), f'Mismatch in {col}')
        else:
            require(got[col].astype(str).equals(expected[col].astype(str)), f'Mismatch in {col}')
    require((got.historic_reference == 'inv_14').all(), 'Historical reference changed')
    require((got.calibration_point == 'B').all(), 'Selected branch changed')
    require((got.removed > 0).sum() == 282 and (got.removed == 0).sum() == 78, 'Omission audit changed')
    require(abs(got.calibration_q_pct.min() - 11.3208736566) < 1e-9, 'Threshold lower witness differs')
    require(abs(got.calibration_q_pct.max() - 12.6438110910) < 1e-9, 'Threshold upper witness differs')

    if write_results:
        out = HERE / 'results'
        out.mkdir(exist_ok=True)
        got.to_csv(out / 'OEDI_360_SEVEN_CALENDAR_DAY_OMISSIONS_REPRODUCED.csv', index=False, float_format='%.12g')
    print('OEDI 360-WINDOW REPRODUCTION PASS: 360/360 rows, 13 fields, 210 calibration dates; ' 
          '282 nonempty windows, stable Branch B and inv_14, frozen result matched')
    return got

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-results', action='store_true')
    args = parser.parse_args()
    run(write_results=args.write_results)
