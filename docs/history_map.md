# History map of the eligible pool (P0, 2026-11-12)

What lags or 4-quarter changes of each candidate would need, and whether they are reliable now. Coverage = share of dev population rows with a value at
both t and t−4 (exact CERT + quarter), from `reports/tables/hist_core_v1_pool_map_coverage.csv` (1984–89 / 1990–2011 range). Quality version:
pool_clean_v2 (17.43) for pool columns, e3_layer_v1 (R-I01X, Y1, BRO) for core. Only the 6 core ratios have lags built (`hist_core_v1`); nothing
here is a predictor yet. No mass lags over the 87 source fields.

Common to all rows: data start 1984Q1 (left-censored history before 1985Q1); 1985Q2 I01 quarantine propagates into lags 1985Q3–1986Q2; BankFind
values are revised, not first-filed (I68); mergers keep the acquirer's CERT, so a change across an absorption mixes two banks (audit flag
`hist_absorbed_bank_4q`, built from the current Institutions snapshot — not point-in-time); CALLFORM switches flagged (`hist_callform_change_4q`).

| Feature | Formula (unit) | Kind | History for lag 4 / change | Coverage t & t−4 | Structural missing / definition notes | Verdict |
|---|---|---|---|---|---|---|
| eq_assets | 100·EQ/ASSET (%) | level, signed | report t−4 | 0.72 / 0.98–0.99 | OI forms without EQ | **built (P0)** |
| noncurrent_loans | 100·NCLNLS/LNLSGR (%) | level | t−4 | 0.72 / 0.98–0.99 | LNLSGR null or ≤ 0 → undefined | **built** |
| reserve_loans | 100·LNATRES/LNLSGR (%) | level | t−4 | 0.72 / 0.97–0.98 | as above; CECL after 2020 (outside dev) | **built** |
| roa_ttm | 100·Σ4 NETINC_q / ASSET (%) | TTM flow, signed | flows t−7…t−4 (8 quarters) | 0.62 / 0.97–0.98 | Y1 K3 quarantine; D12 null flows | **built** |
| loans_deposits | 100·LNLSNET/DEP (%) | level | t−4 | 0.72 / 0.98–0.99 | DEP ≤ 0 → undefined | **built** |
| borrowed_assets | 100·OTHBOR/ASSET (%) | level | t−4 | 0.72 / 0.98–0.99 | — | **built** |
| log_assets | ln ASSET | log level | t−4 | 0.72 / 0.98–0.99 | a change = log growth; nominal | candidate (asset growth needs I03 policy) |
| nim_ttm | TTM net interest income / assets (%) | TTM flow, signed | 8 quarters | 0.57 / 0.92–0.95 | Y1; YTD restarts | candidate after core P1 |
| provision_loans_ttm | TTM provisions / loans (%) | TTM flow, signed | 8 quarters | 0.50 / 0.92–0.95 | Y1; LNLSGR undefined | candidate after core P1 |
| brokered_assets | BRO / ASSET (%) | level | t−4 | 0.70 / 0.98–0.99 | BRO policy (G-a quarantine) | candidate |
| ore_assets, npa_assets | ORE (+NCLNLS) / ASSET (%) | level | t−4 | 0.72 / 0.98–0.99 | negative stocks quarantined | candidate |
| loans_assets, cd/cre/multifam/resid/ci/consumer_assets | component / ASSET (%) | level | t−4 | 0.72 / 0.98–0.99 | TFR offsetting decomposition quarantined; component > LNLSGR = basis warning | candidate (concentration changes slow; low priority) |
| cash_assets, securities_assets | / ASSET (%) | level | t−4 | 0.72 / 0.98–0.99 | — | candidate |
| fedfunds_repo_assets | FREPP / ASSET (%) | level | t−4 | 0.72 / 0.98–0.99 | 64–72 % true zeros | low priority |
| intangibles_assets | INTAN / ASSET (%) | level | t−4 | 0.72 / 0.98–0.99 | 63–89 % zeros; jumps at mergers | **deferred** (merger artefact) |
| log_age, log_offices | ln(1+age), ln(1+OFFDOM) | structure | — | 0.81 / 0.98–0.99 | age change is deterministic | **not lagged** (no information) |
| core_dep_assets | COREDEP / ASSET | level | — | 0.72 / 0.98–0.99 | API definition differs by form (I58, I63) | **deferred** (refused by guard) |
| nco_ttm | Σ4 NTLNLS_q / LNLSGR (%) | TTM flow | 8 quarters | 0.51 / 0.93–0.98 | TFR gaps before 1990, mixed causes (I66) | **deferred** |
| past_due_30_89 | P3LNLS / LNLSGR | level | t−4 | from 2001 only | not reported before 2001 | **deferred** (late arm) |

Young banks (`before_first_report`) are kept; the P1 fallback scores them with the level-only model A (see notebook 17.46f).
