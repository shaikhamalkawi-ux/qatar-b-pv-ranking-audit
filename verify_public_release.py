#!/usr/bin/env python3
"""Public OEDI-only post-run verification. No restricted Qatar data used."""
from pathlib import Path
import json, pandas as pd, numpy as np, hashlib
ROOT=Path(__file__).resolve().parent

def required(ok,msg):
    if not ok:raise AssertionError(msg)

# Reference outputs are an independent frozen artifact from the original audit.
for path in ['ANNUAL_BASELINE_SUMMARY.csv','PRIMARY18_FRESH_VS_BASELINES_SUMMARY.csv','PAIRED_BLOCK_BOOTSTRAP_INTERVALS.csv']:
    a=pd.read_csv(ROOT/'baseline'/'expected'/path)
    b=pd.read_csv(ROOT/'baseline'/'results'/path)
    required(a.shape==b.shape and list(a)==list(b),f'Schema mismatch: {path}')
    for k in a.columns:
        if pd.api.types.is_numeric_dtype(a[k]) and pd.api.types.is_numeric_dtype(b[k]):
            required(np.allclose(a[k].to_numpy(float),b[k].to_numpy(float),rtol=2e-9,atol=2e-9,equal_nan=True),f'Numeric mismatch: {path}/{k}')
        else:
            required(a[k].fillna('NA').astype(str).equals(b[k].fillna('NA').astype(str)),f'Text mismatch: {path}/{k}')
for path in ['POLICY_COMPARISON_ALL_THRESHOLDS.csv','SOURCE_CALIBRATION_GATE.csv']:
    a=pd.read_csv(ROOT/'shadow'/'expected'/path)
    b=pd.read_csv(ROOT/'shadow'/'results'/path)
    required(a.shape==b.shape and list(a)==list(b),f'Shadow schema mismatch: {path}')
    for col in a:
        if pd.api.types.is_numeric_dtype(a[col]) and pd.api.types.is_numeric_dtype(b[col]):
            required(np.allclose(a[col].to_numpy(float),b[col].to_numpy(float),rtol=2e-9,atol=2e-9,equal_nan=True),f'Shadow numeric mismatch {path}/{col}')
        else:
            required(a[col].fillna('NA').astype(str).equals(b[col].fillna('NA').astype(str)),f'Shadow text mismatch {path}/{col}')
# Discourage accidental Qatar-derived additions during later maintenance.
for p in ROOT.rglob('*'):
    if not p.is_file() or '.git' in p.parts: continue
    forbidden_extensions={'.zip','.pdf','.docx','.xls','.xlsx','.eml','.msg','.pem','.key','.ipynb'}
    required(p.suffix.lower() not in forbidden_extensions,f'Binary/forbidden file: {p}')
    required(p.stat().st_size<3000000,f'Unexpected large payload: {p}')
    if p.suffix in ('.csv','.json'):
        content=p.read_text(encoding='utf-8',errors='replace').lower()
        for term in ('@hbku.edu.qa','@hct.ac.ae','perc-m7','shj-m5','gpoa_2','gpoa_3','gpoa_4','e_13_'):
            required(term not in content,f'Sensitive content: {p} {term}')
print('PUBLIC OEDI-ONLY AUDIT PASS: 5 frozen comparator tables, no restricted Qatar payload')
