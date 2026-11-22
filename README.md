# Qatar B — PV ranking audit: public OEDI-only reproduction

**Author and maintainer:** Ghassan Malkawi  
**Affiliation:** Higher Colleges of Technology, Al Ain, United Arab Emirates.

**Reviewer access:** This is a public repository. The OEDI-only code and derived daily inputs can be inspected or downloaded without collaborator invitations. Use the commands below to reproduce the documented decision-endpoint checks.

**Scope:** Public NREL/Open Energy Data Initiative (OEDI) PVDAQ System 2107 operational-channel replay. This repository **does not** contain the restricted Qatar field data, confidential PV module/vendor/channel crosswalks, Qatar analysis binaries, emails, the manuscript under author approval, or the owner's restricted release archive.

**Current manuscript (author review):** *Auditing PV Performance Rankings Beyond Prediction Accuracy: Evidence from Qatar and Public Inverter Data* (Qatar B R7R7-EP11; *Solar* journal target, not submitted). Public status of this OEDI-only repository **does not** mean all-coauthor, Qatar data-owner, or journal approval of the paper.

## What reviewers can reproduce

1. **Baseline policy audit** (`baseline/`): re-evaluates static model selection against exact expected uniform-random and 2020-calibration best-channel choices; measures regret, admitted-window AC-specific-energy shortfall, and size-matched random-set behavior for the primary 18-channel cohort and the distinct secondary 23-channel sensitivity. Includes 5/7/14 retained-date moving-block uncertainty and fresh-label comparison for primary 18.
2. **Retrospective shadow-alert challenge** (`shadow/`): evaluates three review-trigger families on 748 primary-cohort mode-year records, with positive and negative outcomes. This is an **after-the-fact, time-ordered pseudo-stream**; it is not a prospective early-warning or deployed operator system.

3. **2020 calibration-support deletion sensitivity** (`extensions/calibration_support_360/`): independently reconstructs all 360 seven-calendar-day removal windows from the SHA-256-locked 789-row public-derived daily input, then verifies the complete 360-row, 13-column result against a separately frozen ledger. It contains neither confidential Qatar data nor a new model fit. See the [reproduction instructions](extensions/calibration_support_360/README.md).

The input CSVs are **derived, archived, daily OEDI quantities**, not the original 5-minute source and not a new raw-to-final recomputation of preprocessing or forecast fitting. This bundle is intended for **conditional reproduction of the already admitted OEDI decision endpoints**. The Qatar branch remains outside the public replay.

## Run

Requires **Python >=3.10**, `numpy` and `pandas` (tested with Python 3.11+, numpy 2.x, pandas 2.2.x). From the repository root:

```sh
python -m pip install -r requirements.txt
python baseline/scripts/reproduce_baselines.py --input-dir baseline/inputs --output-dir baseline/results
python shadow/scripts/run_challenge.py --root shadow
python shadow/scripts/independent_verify.py
python extensions/selection_depth_monthly_reference/reproduce.py
python extensions/calibration_support_360/reproduce.py --write-results
python verify_public_release.py
```

These steps are also defined in [the public OEDI-only verification workflow](.github/workflows/oedi_public_repro.yml) and [the verification guide](docs/OEDI_PUBLIC_VERIFICATION_STEPS.md). The 360-window extension independently verifies its own input hash and complete frozen expected ledger. Running commands does not require the private Qatar archive. Reproduction checks compare the key annual tables numerically against frozen reference tables, with a strict floating-point tolerance. See `docs/verification.json` for the locally exercised clean-run gate.

## Interpretation and limits

- This is a **post-outcome exploratory audit**. Do not label as preregistered or prospective validation.
- The 2020 baseline uses **calibration-period labels only**; it is not a physically switchable inverter policy.
- Uniform-random regret is an **exact within-date conditional expectation**, not realized random trials.
- Candidate-set regret is an **ex-post best-member shortfall**, not feasible within-set action regret. Near-universal sets have low selection resolution.
- Historical-year comparisons differ in calendar support; uncertainty resamples *retained dates*, which need not be consecutive calendar days.
- The OEDI `E` energy columns concern **AC kWh/kWac** on admitted windows; the restricted Qatar physical measure is **DC kWh/kWp** and is **not pooled**.
- The shadow alerts cannot be interpreted as before-day predictions because forecast features include same-day measured meteorology; observed same-day outcomes are withheld for retrospective evaluation only.

## Provenance and rights

Public underlying source: Deline et al. (2021), **Photovoltaic Data Acquisition (PVDAQ) Public Datasets**, OEDI/NREL, DOI [10.25984/1846021](https://doi.org/10.25984/1846021). System: PVDAQ 2107. See also [openEDI documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md).

This package redistributes daily derived analysis objects from the public operational-channel cohort only. The original source and its terms govern the upstream dataset. **No license to use private Qatar project material is conveyed.** This repository does not currently grant a new general software-reuse license; publishing the code for reviewer inspection does not itself certify permission to reuse third-party inputs.

Correspondence/permission requests for the private Qatar branch must go to the original data owner. Do not file private data or owner correspondence as public GitHub issues.

## Relationship to the manuscript

The manuscript links to the public repository at https://github.com/shaikhamalkawi-ux/qatar-b-pv-ranking-audit in its Data availability and reproducibility section. Repository citation metadata identify **Ghassan Malkawi** as the sole software author; upstream data attribution is retained separately. This repository supports the OEDI external component, **not** the confidential Qatar calculations. Original baseline reviewer snapshot `b552f77c4dc6e4341f60759a6c3ac2db985c9d85` and selection-depth/month-reference source snapshot `bde04df0dcc3f37e63ba755a4146c07819d02cb6` remain unchanged. The new 360-window code and frozen ledger are published under `extensions/calibration_support_360/`. See [EP11 public synchronization and scope](docs/EP11_PUBLIC_SYNC_SCOPE.md). Do not describe the study as fully open-data reproducible.
