# Qatar B — PV ranking audit: public OEDI-only reproduction

**Scope:** Public NREL/Open Energy Data Initiative (OEDI) PVDAQ System 2107 operational-channel replay. This repository **does not** contain the restricted Qatar field data, confidential PV module/vendor/channel crosswalks, Qatar analysis binaries, emails, the manuscript under author approval, or the owner's restricted release archive.

**Study:** *Prediction Accuracy Can Improve While PV Candidate Ranking Degrades: Physical Materiality, Revalidation, and External Field Transport* (Energy Reports R6 author-review manuscript). Public status of this repository **does not** mean author or Qatar data-owner approval of the unpublished paper.

## What reviewers can reproduce

1. **Baseline policy audit** (`baseline/`): re-evaluates static model selection against exact expected uniform-random and 2020-calibration best-channel choices; measures regret, admitted-window AC-specific-energy shortfall, and size-matched random-set behavior for the primary 18-channel cohort and the distinct secondary 23-channel sensitivity. Includes 5/7/14 retained-date moving-block uncertainty and fresh-label comparison for primary 18.
2. **Retrospective shadow-alert challenge** (`shadow/`): evaluates three review-trigger families on 748 primary-cohort mode-year records, with positive and negative outcomes. This is an **after-the-fact, time-ordered pseudo-stream**; it is not a prospective early-warning or deployed operator system.

The input CSVs are **derived, archived, daily OEDI quantities**, not the original 5-minute source and not a new raw-to-final recomputation of preprocessing or forecast fitting. This bundle is intended for **conditional reproduction of the already admitted OEDI decision endpoints**. The Qatar branch remains outside the public replay.

## Run

Requires **Python >=3.10**, `numpy` and `pandas` (tested with Python 3.11+, numpy 2.x, pandas 2.2.x). From the repository root:

```sh
python -m pip install -r requirements.txt
python baseline/scripts/reproduce_baselines.py --input-dir baseline/inputs --output-dir baseline/results
python shadow/scripts/run_challenge.py --root shadow
python shadow/scripts/independent_verify.py
python verify_public_release.py
```

Running commands does not require the private Qatar archive. Reproduction checks compare the key annual tables numerically against frozen reference tables, with a strict floating-point tolerance. See `docs/verification.json` for the locally exercised clean-run gate.

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

The paper's public-code reference may cite **this repository only after its actual GitHub URL is verified**. This repository supports the OEDI external component, **not** the confidential Qatar calculations. Do not describe the study as fully open-data reproducible.
