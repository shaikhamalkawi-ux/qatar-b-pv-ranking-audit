# Public OEDI-only verification (Qatar B)

Install Python 3.11 and dependencies from `requirements.txt` before running:

```bash
python baseline/scripts/reproduce_baselines.py --input-dir baseline/inputs --output-dir baseline/results
python shadow/scripts/run_challenge.py --root shadow
python shadow/scripts/independent_verify.py
python extensions/selection_depth_monthly_reference/reproduce.py
python extensions/calibration_support_360/reproduce.py --write-results
python verify_public_release.py
```

All commands operate on public-OEDI derived daily inputs already in this repository; they do not contact or reconstruct the Qatar field archive. Existing baseline and shadow checks retain their original frozen expected tables. The 360-window extension additionally pins both its input and its 360-row expected ledger by SHA-256 and checks numeric values row-by-row.

These scripts are **retrospective reproductions** and provide no prospective alert validation, power-flow, verified fault causation, switchable equipment recommendation or realized energy saving.
