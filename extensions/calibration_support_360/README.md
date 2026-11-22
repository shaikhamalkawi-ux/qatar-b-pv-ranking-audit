# 360-window OEDI calibration-support sensitivity (public-only)

**Study context:** *Auditing PV Performance Rankings Beyond Prediction Accuracy: Evidence from Qatar and Public Inverter Data* (Qatar B, R7R7-EP11 author-review version). This folder reproduces the **public OEDI PVDAQ System 2107** calibration-support omission sensitivity already reported in Section 7.4, Figure 10, Table 9 and Supplementary Tables S26-S27. It does **not** reproduce restricted Qatar data, instrument/event details, source-product crosswalks or the entire original five-minute OEDI preprocessing/fitting workflow.

## Source and exact input

- Existing repository daily input: `baseline/inputs/PRIMARY18_DAILY_MEASURED_AND_PREDICTED.csv`.
- Frozen SHA-256: `99baab9035063af1e0d9136c971653dc3ab9f9704846b3bafc706b3aae659f2e`.
- Independent 360-row public-derived expected ledger: `expected/OEDI_360_SEVEN_CALENDAR_DAY_OMISSIONS_INDEPENDENT.csv`.
- Frozen ledger SHA-256: `3d7da0206cde34ae0db9fbcd06476fa112fe93f0d9e46b439acf4c74b4a7bd55`.
- Upstream public record: NREL/OEDI PVDAQ 2107 (Deline et al., DOI `10.25984/1846021`).

## Reproduce and verify

From the public repository root, after `python -m pip install -r requirements.txt`:

```bash
python extensions/calibration_support_360/reproduce.py --write-results
```

The script enforces both input hashes and independently calculates all **360 seven-calendar-day omission windows** (2020-01-01 through 2020-12-25), then compares every row of the resulting **13-column** ledger with the archived expected ledger (numeric absolute tolerance `1e-8`). It writes the reproduced output only to an ignored local `results/` folder; running it does **not** update the reference file.

Expected terminal result:

```text
OEDI 360-WINDOW REPRODUCTION PASS: 360/360 rows, 13 fields, 210 calibration dates; 282 nonempty windows, stable Branch B and inv_14, frozen result matched
```

## Supported findings, not inferred claims

- Original full-support 2020 calibration uses 210 eligible dates. Of 360 omission windows, 282 remove at least one eligible date and 78 remove none.
- The point-model Branch B and the historical-reference channel `inv_14` remain unchanged across all windows.
- The 90% candidate-set threshold varies from approximately 11.3209% to 12.6438%; held-out 2022 observed-leader coverage ranges from 84.44% to 88.89% on **the same** 135 dates.
- These are finite, overlapping counterfactual calibration-support deletions, **not** independent failures, sampled missingness, guaranteed set coverage, field-outage probabilities, or confidence intervals.
- Inputs here are archived derived **AC** inverter observations. Do not pool with restricted Qatar **DC** kWh/kWp and do not treat comparison regret as recoverable energy.

## Data and use boundary

The frozen ledger is a derived public-OEDI statistical output. It contains no restricted Qatar field records, no owner correspondence, no private mapping, and no author-review manuscript. The upstream data licence and repository's existing reuse boundaries continue to govern. Please contact the original Qatar data owner for any access request to the restricted study branch.
