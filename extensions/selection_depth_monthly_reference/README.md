# Selection-depth and same-calendar-month reference diagnostics

This extension adds deterministic, explicitly post-outcome analyses of the existing primary-18 OEDI PVDAQ 2107 daily array. It changes no earlier inputs, model coefficients, thresholds, baseline results, or shadow-alert results. It contains no Qatar telemetry, equipment identities, private scripts, correspondence, manuscript, or author-approval material.

## Run

From the repository root, after installing the existing requirements:

```sh
python extensions/selection_depth_monthly_reference/reproduce.py
```

Outputs are written under this directory's `results/`. The script verifies the SHA-256 of the existing 789-row daily array; checks the earlier 424-date evaluation support; independently verifies observed selected ranks by sorting; and confirms the fixed Branch-A choice on 324 fresh evaluation dates. No extra data download, refit, random sampling, or new weighting is required.

## What the results support

- Static wrong selections outside the observed top two: 121/132, 123/126, and 128/140 in 2021, 2022, and 2023. Median wrong-choice observed rank is eight in each year. Rank depth is paired with relative regret and admitted-window AC kWh/kWac; it is not proof of a large or sensor-resolvable physical loss.
- The same-month reference is selected by mean normalized daily response in each available month of 2020. March has no calibration support, so it is unavailable: no fallback is invented. Static comparisons use 125, 124, and 138 identical supported dates; the earlier all-date static results remain unchanged.
- On those dates, the annual-2020 comparator retains lower regret than static Branch B in all three years. The monthly-2020 comparator is not uniformly better: its 2022 regret is 2.156%, versus 1.723% for B. This unfavorable result must be retained.
- Fresh April-end Branch A has greater regret than both references in 2021 and less in 2022-2023. Its order is fixed by its coefficients and it always selects `inv_11`; this is branch reselection, not a newly learned weather-varying ranking.

## Interpretation boundary

Direct admissible common-support measurements already suffice to rank observed normalized output. These diagnostics evaluate the reliability of comparative statements produced by a previously fitted model; they do not prove that prediction is necessary when measurements are available. Shared calendar labels do not match weather or operating states. January/February 2020 calibration is sparse, and July 2023 has one retained date. No operational alert, realized savings, causal equipment effect, uncertainty-resolved ranking, or universal historical-policy superiority is demonstrated.

This extension supports conditional reproduction from archived derived OEDI arrays, not reconstruction from the original five-minute source or reproduction of the restricted Qatar branch. Existing upstream-data attribution and repository reuse restrictions remain unchanged. The earlier reviewer snapshot `b552f77c4dc6e4341f60759a6c3ac2db985c9d85` remains accessible and unmodified.
