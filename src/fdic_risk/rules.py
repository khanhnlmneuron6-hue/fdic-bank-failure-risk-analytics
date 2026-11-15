from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path
import calendar, math, hashlib, json, os, warnings
import numpy as np
import pandas as pd
import polars as pl
from sklearn.base import BaseEstimator, TransformerMixin, OneToOneFeatureMixin
from sklearn.utils.validation import check_is_fitted
KEY3 = ["CERT", "report_period_end"]
LAG_Q = 1
H_Q = 4
I01_REPDTE = "19850630"
def q_index(d):
    return d.year * 4 + (d.month - 1) // 3
STOCK_FIELDS = ['ASSET', 'DEP', 'DEPDOM', 'LIAB', 'LIABEQ', 'EQ', 'INTAN', 'RBCT1J', 'RWAJT', 'LNLSGR', 'LNLSNET', 'LNATRES', 'NCLNLS', 'NALNLS', 'P3ASSET', 'P9ASSET', 'NAASSET', 'P3LNLS', 'P9LNLS', 'ORE', 'LNRE', 'LNRECONS', 'LNRENRES', 'LNREMULT', 'LNRERES', 'LNREAG', 'LNCI', 'LNCON', 'SC', 'SCHA', 'SCHF', 'SCAF', 'SCAA', 'ERNAST', 'CHBAL', 'DDT', 'NTRTIME', 'OTHBOR', 'OTHBRF', 'FREPP', 'BRO', 'BROINS', 'COREDEP', 'VOLIAB', 'DEPINS', 'DEPUNINS', 'DEPLGAMT']
QCAL = pl.DataFrame({"qi": list(range(1900*4, 2031*4)), "qend": [date(i//4,(i%4+1)*3,calendar.monthrange(i//4,(i%4+1)*3)[1]) for i in range(1900*4,2031*4)]})
INSURED_CLASSES = {"N", "NM", "SM", "SB", "SI", "SL", "SA"}


YTD_PAIRS = [("NETINC", "NETINCQ"), ("NONII", "NONIIQ"), ("NTLNLS", "NTLNLSQ")]
COMPONENTS_LE_ASSET = ["LNLSGR", "LNLSNET", "ERNAST", "SC"]
DENOMINATORS = ["ASSET", "LNLSGR", "DEP", "ERNAST", "EQ"]
CAN_BE_NEGATIVE = {"EQ", "RBCT1J"}
NEXT_Q_CORE = ["ASSET", "DEP", "LNLSGR", "EQ", "INTINC"]
I01_FIELDS = ["ASSET", "DEP", "DEPDOM", "SPECGRP", "LIAB", "LIABEQ", "EQ", "EQV", "INTAN", "LNLSGR", "LNLSNET", "LNATRES",
              "NCLNLS", "NALNLS", "P9ASSET", "NAASSET", "P9LNLS", "NTLNLS", "ORE", "LNATRESR", "LNRE", "LNRECONS", "LNRENRES",
              "LNREMULT", "LNRERES", "LNREAG", "LNCI", "LNCON", "SC", "NETINC", "INTINC", "EINTEXP", "NONII", "NONIX", "ELNATR",
              "CHBAL", "LNLSDEPR", "DDT", "NTRTIME", "OTHBOR", "OTHBRF", "FREPP", "BRO", "BROINS"]
FLOW_TWIN = {"NETINC": "NETINCQ", "NONII": "NONIIQ", "NTLNLS": "NTLNLSQ"}
FLOW_FIELDS = ["NETINC", "NONII", "NTLNLS", "INTINC", "EINTEXP", "NONIX", "ELNATR"]
NONNEG_CUM = ["INTINC", "EINTEXP", "NONIX"]
FLOW_SRC = ["fdic_quarterly", "derived_q1", "derived_diff", "null_source_missing", "null_no_prev_quarter",
            "null_prev_missing", "null_ytd_discrepancy"]
FLOW_NEG_STATUS = {  # "allowed by definition" is NOT "each negative value verified"
    "NETINC": "negative allowed by definition (loss); individual values not verified",
    "NTLNLS": "negative allowed by definition (recoveries > charge-offs); individual values not verified",
    "ELNATR": "negative allowed by definition (provision release); individual values not verified",
    "NONII": "unverified - not a validated model input", "INTINC": "unverified - not a validated model input",
    "EINTEXP": "unverified - not a validated model input", "NONIX": "unverified - not a validated model input"}
D8_RULES_VERSION = "d8_v2_2026-11-09"
D8_CET1_FIRST = {"advanced_approaches": date(2014, 3, 31), "all_other": date(2015, 3, 31)}
D8_EXACT = {"EQV": ("EQ", "ASSET"), "LNATRESR": ("LNATRES", "LNLSGR"), "LNLSDEPR": ("LNLSNET", "DEP"),
            "IDLNCORR": ("LNLSNET", "COREDEP")}
D8_DEN_ONLY = {"RBCRWAJ": ("RBC", "RWAJT")}
D8_UNAVAILABLE = {"RBC1AAJ": "RBCT1 / AVASSETJ", "NPERFV": "NPERF / ASSET", "NCLNLSR": "NCLNLS / LNLSGRJ",
                  "LNRESNCR": "LNATRESJ / NCLNLS", "ROA": "NETINCA / ASSET5", "ROAPTX": "NETINBXA / ASSET5",
                  "NIMY": "NIMA / ERNAST5"}
D8_FIELDS = [*D8_EXACT, *D8_DEN_ONLY, "IDT1RWAJR", "IDT1CER", "RBC1RWAJ", "RBCT1J", "RWAJT", *D8_UNAVAILABLE]
D8_NULL_STATUS = {"zero_den_null", "zero_den_zero", "zero_num_null", "zero_num_input_null_script", "zero_not_applicable_regime"}
D8_TRUE_ZERO_STATUS = {"zero_numerator_zero"}
FEATURE_INPUTS = {   # feature -> raw fields it depends on (used by the lineage check below and by 3B)
    "eq_assets": ["EQ", "ASSET"], "noncurrent_loans": ["NCLNLS", "LNLSGR"], "reserve_loans": ["LNATRES", "LNLSGR"],
    "roa_ttm": ["NETINC", "ASSET"], "loans_deposits": ["LNLSNET", "DEP"], "borrowed_assets": ["OTHBOR", "ASSET"],
    "noncore_assets": ["NTRTIME", "OTHBOR", "ASSET"],
    "log_assets": ["ASSET"], "nim_ttm": ["INTINC", "EINTEXP", "ASSET"], "provision_loans_ttm": ["ELNATR", "LNLSGR"],
    "efficiency_ttm": ["NONIX", "INTINC", "EINTEXP", "NONII"], "asset_growth_4q": ["ASSET"], "brokered_assets": ["BRO", "ASSET"],
    "tier1_rwa": ["RBCT1J", "RWAJT"], "roa_q_ann": ["NETINC", "ASSET"]}
CORE = ["eq_assets", "noncurrent_loans", "reserve_loans", "roa_ttm", "loans_deposits", "borrowed_assets", "log_assets"]
CORE_RATIOS = {"eq_assets": ("EQ", "ASSET"), "noncurrent_loans": ("NCLNLS", "LNLSGR"), "reserve_loans": ("LNATRES", "LNLSGR"),
               "loans_deposits": ("LNLSNET", "DEP"), "borrowed_assets": ("OTHBOR", "ASSET")}
NEG_CHECK_NUM = ["NCLNLS", "LNATRES", "LNLSNET", "OTHBOR"]
I01_QI = q_index(date(1985, 6, 30))
ROA_RECON_TOL = 0.5
_q = {k: q_index(v) for k, v in {"843": date(1984, 9, 30), "844": date(1984, 12, 31), "851": date(1985, 3, 31), "853": date(1985, 9, 30),
                                  "854": date(1985, 12, 31), "861": date(1986, 3, 31)}.items()}
SUSPECT_SHARE = 0.9
NEG_ISOLATE = {"noncurrent_loans": "NCLNLS", "reserve_loans": "LNATRES", "borrowed_assets": "OTHBOR", "loans_deposits": "LNLSNET"}
LEGIT_MISS = {"den_null", "den_null_suspected_form_period", "den_zero", "den_negative", "num_null", "num_null_suspected_form_period",
              "num_negative_unverified", "window_history_incomplete", "window_flow_null_d12"}
MISS_COLS = [f"miss_{f}" for f in ["eq_assets", "noncurrent_loans", "reserve_loans", "roa_ttm", "loans_deposits", "borrowed_assets"]]
YTD_CLASS_VERSION = "ytd_class_v2_2026-11-10"
DQ_POLICIES = {
    "R-I01X": {"version": "dq_i01_ttm_identity_recovery_v1_2026-11-10", "features": ["nim_ttm", "provision_loans_ttm"],
               "rule": "reports 1985Q3, 1985Q4, 1986Q1 only: TTM = YTD_t + YTD_(Q4 previous year) - YTD_(t-4) (Q1-Q3), = YTD_t (Q4); same CERT, reports <= t only; "
                       "every input YTD present, reports t-3..t present, no D12 discrepancy quarter in the window, denominator > 0, D15 NETINC window 'reconciled' "
                       "(supporting evidence only); applied BEFORE Y1, so a recovered cell whose window holds a K3 quarter is quarantined again by Y1",
               "evidence": "accounting identity of year-to-date sums (R43); identity = flow-based TTM on every report outside the window (17.26; largely algebraic); "
                           "the masked 1985Q2 report itself is never used, 1986Q2 is not recoverable (needs YTD 1985Q2); no label is used",
               "sources": "R43, R47; notebook 15.1 (D15), 17.26"},
    "Y1": {"version": "dq_ttm_k3_quarantine_v1_2026-11-10", "features": ["roa_ttm", "provision_loans_ttm", "nim_ttm", "efficiency_ttm"],
           "rule": f"window t-3..t of the report contains a 'K3 suspected restart' quarter ({YTD_CLASS_VERSION})",
           "evidence": "heuristic for a change of reporting basis; mechanism documented (push down, R43; no FDIC adjustment, R47); cause of each row not verified",
           "sources": "R43, R47, R03; notebook 17.17"},
    "B1": {"version": "dq_bro_ga_quarantine_v1_2026-11-10", "features": ["brokered_assets"],
           "rule": "BRO > DEP and BRO > ASSET in the same report",
           "evidence": "BRO <= DEP by definition (R112) is violated 66-70x and BRO jumps 0 -> 579,000 -> 0; BRO <= ASSET is NOT a universal identity; temporary prudential policy, cause not verified",
           "sources": "R112, R03; notebook 17.18"}}
DQ_FEATURES = ["roa_ttm", "provision_loans_ttm", "nim_ttm", "efficiency_ttm", "brokered_assets"]
I01X_REPORTS = [date(1985, 9, 30), date(1985, 12, 31), date(1986, 3, 31)]
POOL_NUMS = {"ore_assets": "ORE", "npa_assets": None, "loans_assets": "LNLSGR", "cd_assets": "LNRECONS", "cre_assets": "LNRENRES", "multifam_assets": "LNREMULT",
             "resid_assets": "LNRERES", "ci_assets": "LNCI", "consumer_assets": "LNCON", "cash_assets": "CHBAL", "securities_assets": "SC",
             "core_dep_assets": "COREDEP", "fedfunds_repo_assets": "FREPP", "intangibles_assets": "INTAN"}
POOL_NONNEG = ["ORE", "NCLNLS", "LNLSGR", "LNRECONS", "LNRENRES", "LNREMULT", "LNRERES", "LNCI", "LNCON", "CHBAL", "SC", "COREDEP", "FREPP", "INTAN"]
POOL_CLEAN_KEYS = ['CERT', 'report_period_end']
POOL_CLEAN_RE_COMPONENTS = {'cd_assets': 'LNRECONS', 'cre_assets': 'LNRENRES',
                            'multifam_assets': 'LNREMULT', 'resid_assets': 'LNRERES'}
POOL_CLEAN_CORE = ['eq_assets','noncurrent_loans','reserve_loans','roa_ttm','loans_deposits','borrowed_assets','log_assets']
POOL_CLEAN_OLD_EXTRA = ['nim_ttm','provision_loans_ttm','brokered_assets']
POOL_CLEAN_NEW = ['ore_assets','npa_assets','nco_ttm','loans_assets','cd_assets','cre_assets','multifam_assets',
                  'resid_assets','ci_assets','consumer_assets','cash_assets','securities_assets','core_dep_assets',
                  'fedfunds_repo_assets','intangibles_assets','log_age','log_offices']
POOL_CLEAN_COLS = POOL_CLEAN_CORE + POOL_CLEAN_OLD_EXTRA + POOL_CLEAN_NEW
POOL_CLEAN_NUMS = {'loans_assets':'LNLSGR', **POOL_CLEAN_RE_COMPONENTS, 'ci_assets':'LNCI', 'consumer_assets':'LNCON', 'cash_assets':'CHBAL', 'securities_assets':'SC', 'core_dep_assets':'COREDEP', 'fedfunds_repo_assets':'FREPP', 'intangibles_assets':'INTAN'}




def q_index(d: date) -> int:
    # Calendar quarter number (year*4 + quarter-1): lags are computed on this, never on row order.
    return d.year * 4 + (d.month - 1) // 3


def repdte(d: date) -> str:
    return d.strftime("%Y%m%d")


def duplicate_key_report(fin: pl.DataFrame) -> pl.DataFrame:
    """Keys (CERT, REPDTE) that occur more than once, with the number of rows and the fields whose values conflict."""
    d = fin.filter(pl.struct("CERT", "REPDTE").is_duplicated())
    if d.height == 0:
        return pl.DataFrame({"CERT": [], "REPDTE": [], "rows": [], "conflicting_fields": []},
                            schema={"CERT": pl.Int64, "REPDTE": pl.String, "rows": pl.UInt32, "conflicting_fields": pl.String})
    fields = [c for c in fin.columns if c not in ("CERT", "REPDTE")]
    g = d.group_by("CERT", "REPDTE").agg(pl.len().alias("rows"), *[(pl.col(c).n_unique() > 1).alias(c) for c in fields])
    return g.select("CERT", "REPDTE", "rows",
                    conflicting_fields=pl.concat_str([pl.when(pl.col(c)).then(pl.lit(c + " ")).otherwise(pl.lit("")) for c in fields]).str.strip_chars())


class DuplicateKeyError(ValueError):
    pass


def build_tech_view(fin: pl.DataFrame) -> pl.DataFrame:
    """Technical/time standardisation of the typed Financials table. Source values are NOT changed: the source columns
    are passed through as they are; new columns are dates, calendar indices and quality flags.
    Flags prefixed q_ use only the report itself or earlier reports (known at the report's availability date).
    Flags prefixed audit_ use a LATER report and must never be used as predictors."""
    dups = duplicate_key_report(fin)
    if dups.height:
        raise DuplicateKeyError(f"{dups.height} duplicated (CERT, REPDTE) keys; first rows:\n{dups.head(10)}")
    t = (fin.with_columns(report_period_end=pl.col("REPDTE").str.strptime(pl.Date, "%Y%m%d"))
            .with_columns(qi=(pl.col("report_period_end").dt.year() * 4 + pl.col("report_period_end").dt.quarter() - 1).cast(pl.Int64))
            .with_columns(pq=pl.col("qi") + LAG_Q)
            .join(QCAL.rename({"qi": "pq", "qend": "available_at_assumed"}), on="pq", how="left", validate="m:1")
            .with_columns(prediction_as_of=pl.col("available_at_assumed"))
            .sort("CERT", "qi"))
    # dates: ESTYMD is stored as a number YYYYMMDD; parse without changing the source column
    t = t.with_columns(est_date=pl.col("ESTYMD").cast(pl.Int64, strict=False).cast(pl.String).str.strptime(pl.Date, "%Y%m%d", strict=False))
    t = t.with_columns(q_estymd_unparsed=pl.col("ESTYMD").is_not_null() & pl.col("est_date").is_null(),
                       q_estymd_after_report=pl.col("est_date") > pl.col("report_period_end"))
    # calendar continuity: previous report = same CERT at qi - 1 (join on the calendar index, not on row position)
    prev = t.select("CERT", qi=pl.col("qi") + 1, has_prev_q=pl.lit(True),
                    **{f"_p_{y}": y for y, _ in YTD_PAIRS})
    t = t.join(prev, on=["CERT", "qi"], how="left", validate="1:1").with_columns(pl.col("has_prev_q").fill_null(False)).sort("CERT", "qi")
    t = t.with_columns(gap_q_before=(pl.col("qi") - pl.col("qi").shift(1).over("CERT") - 1))   # quarters missing since last report
    # YTD consistency (same CERT, same year, consecutive calendar quarters; Q1 compared directly; else not checkable)
    q = pl.col("report_period_end").dt.quarter()
    checks = []
    for y, yq in YTD_PAIRS:
        flow = pl.when(q == 1).then(pl.col(y)).when(pl.col("has_prev_q")).then(pl.col(y) - pl.col(f"_p_{y}"))
        checks.append(pl.when(flow.is_not_null() & pl.col(yq).is_not_null()).then((flow - pl.col(yq)).abs() > 1).alias(f"_ytd_{y}"))
    t = t.with_columns(checks).with_columns(
        ytd_pairs_checked=pl.sum_horizontal([pl.col(f"_ytd_{y}").is_not_null().cast(pl.Int8) for y, _ in YTD_PAIRS]))
    # null = no pair checkable; otherwise True if any checkable pair breaks (avoid Kleene null from unchecked pairs)
    t = t.with_columns(q_ytd_break=pl.when(pl.col("ytd_pairs_checked") > 0)
                       .then(pl.any_horizontal([pl.col(f"_ytd_{y}").fill_null(False) for y, _ in YTD_PAIRS])))
    # accounting identities and signs (flags only; values unchanged)
    t = t.with_columns(
        q_neg_equity=pl.col("EQ") < 0,
        q_liab_gt_asset=pl.col("LIAB") > pl.col("ASSET"),
        q_dep_gt_asset=pl.col("DEP") > pl.col("ASSET"),
        q_bs_gap_01pct=(pl.col("ASSET") - pl.col("LIAB") - pl.col("EQ")).abs() > 0.001 * pl.col("ASSET").abs(),
        q_liabeq_gap=(pl.col("ASSET") - pl.col("LIABEQ")).abs() > 1,
        q_neg_stock=pl.any_horizontal([pl.col(f) < 0 for f in STOCK_FIELDS if f not in CAN_BE_NEGATIVE]),
        q_component_gt_asset=pl.any_horizontal([pl.col(f) > pl.col("ASSET") for f in COMPONENTS_LE_ASSET]),
        **{f"q_den_nonpos_{d}": pl.col(d) <= 0 for d in DENOMINATORS})
    # capital-ratio regimes (descriptive; boundaries from EDA 6 and 12 CFR 324.12) and zero flags (no conversion)
    yr = pl.col("report_period_end").dt.year()
    t = t.with_columns(
        capital_regime=pl.when(yr < 1990).then(pl.lit("1984_1989_pre_rbc")).when(yr < 2015).then(pl.lit("1990_2014"))
                         .when(yr < 2020).then(pl.lit("2015_2019_cet1")).otherwise(pl.lit("2020_plus_cblr_possible")),
        q_cap_zero_rbc=(pl.col("RBCRWAJ") == 0) | (pl.col("IDT1RWAJR") == 0) | (pl.col("RBC1RWAJ") == 0),
        q_cap_zero_cet1=pl.col("IDT1CER") == 0)
    # audit-only, uses the NEXT report: all core amounts identical to the next calendar quarter (copy of a later report)
    nxt = t.select("CERT", qi=pl.col("qi") - 1, **{f"_n_{c}": c for c in NEXT_Q_CORE})
    t = t.join(nxt, on=["CERT", "qi"], how="left", validate="1:1").with_columns(
        audit_equals_next_q=pl.all_horizontal([(pl.col(c) == pl.col(f"_n_{c}")) for c in NEXT_Q_CORE]).fill_null(False))
    return t.drop([c for c in t.columns if c.startswith("_")]).sort("CERT", "qi")


def apply_mask(fin: pl.DataFrame, repdte_value: str, fields: list[str]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Return (masked copy, log). Only rows with REPDTE == repdte_value and only `fields` are set to null; the log keeps
    every masked non-null source value (CERT, REPDTE, field, source_value) so the change is fully traceable."""
    missing = [f for f in fields if f not in fin.columns]
    if missing:
        raise KeyError(f"fields not in table: {missing}")
    hit = pl.col("REPDTE") == repdte_value
    log = pl.concat([fin.filter(hit & pl.col(f).is_not_null())
                        .select("CERT", "REPDTE", pl.lit(f).alias("field"), pl.col(f).cast(pl.Float64).alias("source_value"))
                     for f in fields]) if fields else pl.DataFrame()
    masked = fin.with_columns([pl.when(hit).then(None).otherwise(pl.col(f)).cast(fin.schema[f]).alias(f) for f in fields])
    return masked, log


def build_pit_view(fin: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Point-in-time source layer for later features: I01 mask, then the same technical standardisation as Section 6."""
    masked, log = apply_mask(fin, I01_REPDTE, I01_FIELDS)
    pit = build_tech_view(masked).with_columns(audit_i01_masked=pl.col("REPDTE") == I01_REPDTE)
    return pit, log


def _zstat(f: str, branches: list) -> pl.Expr:
    e = pl.when(pl.col(f).is_null()).then(pl.lit("null")).when(pl.col(f) != 0).then(pl.lit("nonzero"))
    for cond, lab in branches:
        e = e.when(cond).then(pl.lit(lab))
    return e.otherwise(pl.lit("zero_unverified")).alias(f"z8_{f}")


def _masked(c: str) -> pl.Expr:        # input set to null by the I01 mask (Section 7): its real value is unknown here
    return pl.col("audit_i01_masked") & pl.lit(c in I01_FIELDS)


def d8_status(pit: pl.DataFrame) -> pl.DataFrame:
    """One status column z8_<field> per field. Same report only (no future, no labels). Order matters: a verified reason
    (real denominator null/0, real numerator null) is applied before the unverified negative-denominator status."""
    rep = pl.col("report_period_end")
    out = []
    for f, (n, d) in D8_EXACT.items():
        out.append(_zstat(f, [(_masked(d), "zero_unverified_input_masked_i01"), (pl.col(d).is_null(), "zero_den_null"),
                              (pl.col(d) == 0, "zero_den_zero"), (_masked(n), "zero_unverified_input_masked_i01"),
                              (pl.col(n).is_null(), "zero_num_null"), (pl.col(d) < 0, "zero_unverified_den_negative"),
                              (pl.col(n) == 0, "zero_numerator_zero")]))
    for f, (n, d) in D8_DEN_ONLY.items():
        out.append(_zstat(f, [(_masked(d), "zero_unverified_input_masked_i01"), (pl.col(d).is_null(), "zero_den_null"),
                              (pl.col(d) == 0, "zero_den_zero"), (pl.col(d) < 0, "zero_unverified_den_negative"),
                              (pl.lit(True), "zero_unverified_input_unavailable")]))
    # IDT1RWAJR = percentage(IDT1JNOCB, RWAJ); script: IDT1JNOCB = (RBCT1J ?: 0) if INSFDIC==1 & CBLRIND==0 & IBA==0, else 0.
    # RBCT1J null -> numerator 0 in every branch -> the stored 0 carries no ratio information. RWAJ, INSFDIC, CBLRIND, IBA are
    # not downloaded: RBCT1J = 0 is kept but NOT treated as a verified zero ratio; RWAJT is NOT used in place of RWAJ.
    out.append(_zstat("IDT1RWAJR", [(_masked("RBCT1J"), "zero_unverified_input_masked_i01"),
                                    (pl.col("RBCT1J").is_null(), "zero_num_input_null_script"),
                                    (pl.col("RBCT1J") == 0, "zero_unverified_numerator_input_zero"),
                                    (rep < date(1990, 3, 31), "zero_unverified_regime_pre1990"),
                                    (pl.col("BKCLASS") == "NC", "zero_unverified_gate_noninsured"),
                                    (pl.lit(True), "zero_unverified_input_unavailable")]))
    # IDT1CER: CET1 ratio first reported 2014-03-31 (advanced approaches) / 2015-03-31 (all other institutions).
    out.append(_zstat("IDT1CER", [(rep < D8_CET1_FIRST["advanced_approaches"], "zero_not_applicable_regime"),
                                  (rep < D8_CET1_FIRST["all_other"], "zero_unverified_scope_2014"),
                                  (pl.lit(True), "zero_unverified_input_unavailable")]))
    out.append(_zstat("RBC1RWAJ", [((pl.col("RBCT1J") == 0) & (pl.col("RWAJT") > 0), "zero_numerator_zero")]))  # stored; identity 9.2
    out += [_zstat("RBCT1J", []), _zstat("RWAJT", [])]
    out += [_zstat(f, [(pl.lit(True), "zero_unverified_input_unavailable")]) for f in D8_UNAVAILABLE]
    return pit.select("CERT", "REPDTE", *out)


def apply_d8(pit: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(layer, log): zeros whose status is in D8_NULL_STATUS -> null; log keeps CERT, REPDTE, field, source_value, reason."""
    lay = pit.join(d8_status(pit), on=["CERT", "REPDTE"], how="left", validate="1:1")
    hit = lambda f: pl.col(f"z8_{f}").is_in(list(D8_NULL_STATUS))
    log = pl.concat([lay.filter(hit(f)).select("CERT", "REPDTE", pl.lit(f).alias("field"), pl.col(f).cast(pl.Float64).alias("source_value"),
                                                pl.col(f"z8_{f}").alias("reason")) for f in D8_FIELDS])
    lay = lay.with_columns([pl.when(hit(f)).then(None).otherwise(pl.col(f)).cast(pit.schema[f]).alias(f) for f in D8_FIELDS])
    return lay.sort("CERT", "qi"), log.with_columns(rule_version=pl.lit(D8_RULES_VERSION)).sort("field", "CERT", "REPDTE")


def build_flows(pit: pl.DataFrame) -> pl.DataFrame:
    """One row per (CERT, REPDTE) of `pit`; uses only the current and the previous calendar-quarter report.
    For each YTD field Y:
      flowd_Y    pure arithmetic (kept for comparison): Q1 -> Y; Q2-Q4 -> Y - Y(previous quarter) if that report exists;
      flow_q_Y   value for later use: FDIC quarterly twin if available, else flowd_Y; for fields WITHOUT a twin the value is
                 set to null on Q2-Q4 rows with a DETECTED YTD discrepancy (conservative option, pending audit);
      flow_src_Y source of flow_q_Y or reason for null;  q_flow_neg_Y  flow_q_Y < 0 (status in FLOW_NEG_STATUS).
    Row-level OBSERVATIONS (none of them confirms a cause; thresholds are my diagnostic criteria, not regulation):
      ytd_disc_n / ytd_disc_checkable  twins whose derived flow differs from the FDIC quarterly field by > 1 (detected discrepancy);
      ytd_disc_max      largest |derived - FDIC quarterly| over the twins (thousand USD);
      sig_netincq_eq_ytd  NETINCQ = NETINC YTD on Q2-Q4 (signature consistent with an income-basis restart; event not verified);
      obs_ytd_decrease_Y  YTD of INTINC / EINTEXP / NONIX below last quarter (observation to investigate);
      asset_jump_25     |ASSET / ASSET(previous quarter) - 1| > 25 % (diagnostic, supports but does not establish a combination).
    The mechanism classification (merger scope etc.) needs Institutions and lives in classify_ytd_discrepancy (8.6), not here."""
    q = pl.col("report_period_end").dt.quarter()
    prev = pit.select("CERT", qi=pl.col("qi") + 1, **{f"_p_{y}": y for y in FLOW_FIELDS}, _p_ASSET="ASSET", _p_exists=pl.lit(True))
    f = (pit.select("CERT", "REPDTE", "qi", "report_period_end", "ASSET", *FLOW_FIELDS, *FLOW_TWIN.values())
            .join(prev, on=["CERT", "qi"], how="left", validate="1:1").sort("CERT", "qi"))
    der = {}
    for y in FLOW_FIELDS:
        der[y] = (pl.when(pl.col(y).is_null()).then(None).when(q == 1).then(pl.col(y))
                    .when(pl.col("_p_exists").is_null()).then(None).otherwise(pl.col(y) - pl.col(f"_p_{y}")))
    f = f.with_columns(**{f"flowd_{y}": der[y] for y in FLOW_FIELDS})
    disc = {y: pl.when(pl.col(f"flowd_{y}").is_not_null() & pl.col(t).is_not_null()).then((pl.col(f"flowd_{y}") - pl.col(t)).abs() > 1)
            for y, t in FLOW_TWIN.items()}
    f = f.with_columns(**{f"_disc_{y}": e for y, e in disc.items()})
    f = f.with_columns(
        ytd_disc_checkable=pl.sum_horizontal([pl.col(f"_disc_{y}").is_not_null().cast(pl.Int8) for y in FLOW_TWIN]),
        ytd_disc_n=pl.sum_horizontal([pl.col(f"_disc_{y}").fill_null(False).cast(pl.Int8) for y in FLOW_TWIN]),
        ytd_disc_max=pl.max_horizontal([(pl.col(f"flowd_{y}") - pl.col(t)).abs() for y, t in FLOW_TWIN.items()]),
        sig_netincq_eq_ytd=(q > 1) & pl.col("_p_exists").is_not_null() & ((pl.col("NETINCQ") - pl.col("NETINC")).abs() <= 1)
                           & (pl.col("_p_NETINC").abs() > 1),
        **{f"obs_ytd_decrease_{y}": (q > 1) & (pl.col(y) < pl.col(f"_p_{y}")) for y in NONNEG_CUM},
        asset_jump_25=(pl.col("ASSET") / pl.col("_p_ASSET") - 1).abs() > 0.25)
    detected_q234 = (pl.col("ytd_disc_n") > 0) & (q > 1)          # Q1 has no subtraction, so a Q1 discrepancy cannot distort Q1 flows
    out = []
    for y in FLOW_FIELDS:
        reason_d = (pl.when(pl.col(y).is_null()).then(pl.lit("null_source_missing"))
                      .when(q == 1).then(pl.lit("derived_q1"))
                      .when(pl.col("_p_exists").is_null()).then(pl.lit("null_no_prev_quarter"))
                      .when(pl.col(f"_p_{y}").is_null()).then(pl.lit("null_prev_missing"))
                      .otherwise(pl.lit("derived_diff")))
        if y in FLOW_TWIN:
            t = pl.col(FLOW_TWIN[y])
            final = pl.when(t.is_not_null()).then(t).otherwise(pl.col(f"flowd_{y}"))
            src = pl.when(t.is_not_null()).then(pl.lit("fdic_quarterly")).otherwise(reason_d)
        else:
            final = pl.when(detected_q234).then(None).otherwise(pl.col(f"flowd_{y}"))
            src = pl.when(detected_q234 & pl.col(f"flowd_{y}").is_not_null()).then(pl.lit("null_ytd_discrepancy")).otherwise(reason_d)
        out += [final.alias(f"flow_q_{y}"), src.alias(f"flow_src_{y}")]
    f = f.with_columns(out).with_columns(**{f"q_flow_neg_{y}": pl.col(f"flow_q_{y}") < 0 for y in FLOW_FIELDS})
    keep = (["CERT", "REPDTE", "qi"] + [c for y in FLOW_FIELDS for c in (f"flowd_{y}", f"flow_q_{y}", f"flow_src_{y}", f"q_flow_neg_{y}")]
            + ["ytd_disc_checkable", "ytd_disc_n", "ytd_disc_max", "sig_netincq_eq_ytd"] + [f"obs_ytd_decrease_{y}" for y in NONNEG_CUM] + ["asset_jump_25"])
    res = f.select(keep)
    for y in FLOW_FIELDS:
        assert set(res[f"flow_src_{y}"].unique().to_list()) <= set(FLOW_SRC), y
    return res


def _cell_null_share(lay: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Null share of each input within the same report date x CALLFORM (same-quarter cross-section; audit classification only)."""
    return lay.group_by("REPDTE", "CALLFORM").agg([pl.col(c).is_null().mean().alias(f"ns_{c}") for c in cols])


def build_core_features(lay: pl.DataFrame, flows: pl.DataFrame) -> pl.DataFrame:
    """One row per report (CERT, REPDTE). Features use the report itself and, for roa_ttm, the 3 previous calendar quarters of
    the same CERT only. mc_<f> = missing cause (audit only, never a predictor); fq_neg_<field> = negative balance (audit only)."""
    keys = ["CERT", "qi"]
    assert lay.select(keys).is_unique().all() and flows.select(keys).is_unique().all()
    assert lay.height == flows.height and lay.select(keys).sort(keys).equals(flows.select(keys).sort(keys)), "flows must match the layer 1:1"
    ins = sorted({c for nd in CORE_RATIOS.values() for c in nd})
    ns = _cell_null_share(lay, ins)
    fl = flows.select("CERT", "qi", f0="flow_q_NETINC")
    w = fl
    for k in (1, 2, 3):
        w = w.join(fl.with_columns(qi=pl.col("qi") + k).rename({"f0": f"f{k}"}), on=keys, how="left", validate="1:1")
    # report existence for t-1..t-3 (a report row exists even when its flow is null)
    ex = lay.select(keys)
    for k in (1, 2, 3):
        w = w.join(ex.with_columns(qi=pl.col("qi") + k, **{f"has{k}": pl.lit(True)}), on=keys, how="left", validate="1:1")
    x = (lay.select("CERT", "REPDTE", "qi", "report_period_end", "CALLFORM", "audit_i01_masked", *ins)
            .join(w, on=keys, how="left", validate="1:1").join(ns, on=["REPDTE", "CALLFORM"], how="left", validate="m:1"))
    ttm = pl.col("f0") + pl.col("f1") + pl.col("f2") + pl.col("f3")
    exprs = {f: pl.when(pl.col(d) > 0).then(100 * pl.col(n) / pl.col(d)) for f, (n, d) in CORE_RATIOS.items()}
    exprs["roa_ttm"] = pl.when(pl.col("ASSET") > 0).then(100 * ttm / pl.col("ASSET"))
    exprs["log_assets"] = pl.when(pl.col("ASSET") > 0).then(pl.col("ASSET").log())
    x = x.with_columns(**exprs)
    masked = lambda c: pl.col("audit_i01_masked") & pl.lit(c in I01_FIELDS)
    def _null_cause(c):
        return (pl.when(masked(c)).then(pl.lit("i01_quarantine"))
                  .when(pl.col(f"ns_{c}") >= 0.9).then(pl.lit("input_not_reported_form_period"))
                  .otherwise(pl.lit("input_null_other")))
    mc = {}
    for f, (n, d) in CORE_RATIOS.items():
        mc[f"mc_{f}"] = (pl.when(pl.col(f).is_not_null()).then(pl.lit("observed"))
                           .when(pl.col(d).is_null()).then(_null_cause(d)).when(pl.col(d) <= 0).then(pl.lit("den_nonpos"))
                           .when(pl.col(n).is_null()).then(_null_cause(n)).otherwise(pl.lit("unexplained")))
    mc["mc_log_assets"] = (pl.when(pl.col("log_assets").is_not_null()).then(pl.lit("observed"))
                             .when(pl.col("ASSET").is_null()).then(_null_cause("ASSET")).otherwise(pl.lit("den_nonpos")))
    mc["mc_roa_ttm"] = (pl.when(pl.col("roa_ttm").is_not_null()).then(pl.lit("observed"))
                          .when(pl.col("ASSET").is_null()).then(_null_cause("ASSET")).when(pl.col("ASSET") <= 0).then(pl.lit("den_nonpos"))
                          .when(~(pl.col("has1").fill_null(False) & pl.col("has2").fill_null(False) & pl.col("has3").fill_null(False)))
                          .then(pl.lit("window_history_incomplete"))
                          .when(pl.any_horizontal([pl.col(f"f{k}").is_null() for k in range(4)])).then(pl.lit("window_flow_null_d12"))
                          .otherwise(pl.lit("unexplained")))
    # sensitivity variant (NOT the default): isolate every 4-quarter window that contains 1985-06-30
    in_win = pl.col("qi").is_between(I01_QI, I01_QI + 3)
    x = x.with_columns(**mc, roa_ttm_i01_strict=pl.when(in_win).then(None).otherwise(pl.col("roa_ttm")),
                       roa_window_has_1985q2=in_win,
                       **{f"fq_neg_{c}": pl.col(c) < 0 for c in NEG_CHECK_NUM})
    return x.select("CERT", "REPDTE", "qi", "report_period_end", *CORE, *[f"mc_{f}" for f in CORE], "roa_ttm_i01_strict",
                    "roa_window_has_1985q2", *[f"fq_neg_{c}" for c in NEG_CHECK_NUM]).sort("CERT", "qi")


def reconcile_roa_1985(lay: pl.DataFrame, flows: pl.DataFrame) -> pl.DataFrame:
    """CERT, qi, ttm_flow, ttm_check, diff, status for the three report quarters whose 4-quarter window contains 1985Q2."""
    y = lay.select("CERT", "qi", "NETINC")
    yt = lambda k: y.filter(pl.col("qi") == _q[k]).select("CERT", pl.col("NETINC").alias(f"y{k}"))
    fl = flows.select("CERT", "qi", f0="flow_q_NETINC")
    s = fl
    for k in (1, 2, 3):
        s = s.join(fl.with_columns(qi=pl.col("qi") + k).rename({"f0": f"f{k}"}), on=["CERT", "qi"], how="left", validate="1:1")
    s = s.filter(pl.col("qi").is_in([_q["853"], _q["854"], _q["861"]])).select("CERT", "qi", ttm_flow=pl.col("f0") + pl.col("f1") + pl.col("f2") + pl.col("f3"))
    for k in ["843", "844", "851", "853", "854", "861"]:
        s = s.join(yt(k), on="CERT", how="left", validate="m:1")
    chk = (pl.when(pl.col("qi") == _q["853"]).then(pl.col("y853") + pl.col("y844") - pl.col("y843"))
             .when(pl.col("qi") == _q["854"]).then(pl.col("y854"))
             .otherwise(pl.col("y861") + pl.col("y854") - pl.col("y851")))
    s = s.with_columns(ttm_check=chk).with_columns(diff=pl.col("ttm_flow") - pl.col("ttm_check"))
    return s.select("CERT", "qi", "ttm_flow", "ttm_check", "diff",
                    roa_recon=pl.when(pl.col("ttm_flow").is_null()).then(pl.lit("no_ttm"))
                                .when(pl.col("ttm_check").is_null()).then(pl.lit("not_checkable"))
                                .when(pl.col("diff").abs() <= ROA_RECON_TOL).then(pl.lit("reconciled")).otherwise(pl.lit("mismatch")))


def build_model_inputs(fc: pl.DataFrame, lay: pl.DataFrame, recon: pl.DataFrame) -> pl.DataFrame:
    ins = ["EQ", "ASSET", "NCLNLS", "LNLSGR", "LNATRES", "LNLSNET", "DEP", "OTHBOR"]
    ns = _cell_null_share(lay, ins)
    x = (fc.select("CERT", "REPDTE", "qi", "report_period_end", *CORE, *[f"mc_{f}" for f in CORE], "roa_ttm_i01_strict", "roa_window_has_1985q2")
           .join(lay.select("CERT", "REPDTE", "CALLFORM", "audit_i01_masked", *ins), on=["CERT", "REPDTE"], how="left", validate="1:1")
           .join(ns, on=["REPDTE", "CALLFORM"], how="left", validate="m:1")
           .join(recon.select("CERT", "qi", "roa_recon"), on=["CERT", "qi"], how="left", validate="1:1"))
    masked = lambda c: pl.col("audit_i01_masked") & pl.lit(c in I01_FIELDS)
    def _nullc(c, kind):
        return (pl.when(masked(c)).then(pl.lit("i01_quarantine"))
                  .when(pl.col(f"ns_{c}") >= SUSPECT_SHARE).then(pl.lit(f"{kind}_null_suspected_form_period")).otherwise(pl.lit(f"{kind}_null")))
    mx = {}
    for f, (n, d) in CORE_RATIOS.items():
        e = (pl.when(pl.col(d).is_null()).then(_nullc(d, "den")).when(pl.col(d) == 0).then(pl.lit("den_zero"))
               .when(pl.col(d) < 0).then(pl.lit("den_negative")).when(pl.col(n).is_null()).then(_nullc(n, "num")))
        if f in NEG_ISOLATE:
            e = e.when(pl.col(NEG_ISOLATE[f]) < 0).then(pl.lit("num_negative_unverified"))
        mx[f"mx_{f}"] = e.when(pl.col(f).is_not_null()).then(pl.lit("observed")).otherwise(pl.lit("unexplained"))
    mx["mx_log_assets"] = (pl.when(pl.col("ASSET").is_null()).then(_nullc("ASSET", "den")).when(pl.col("ASSET") == 0).then(pl.lit("den_zero"))
                             .when(pl.col("ASSET") < 0).then(pl.lit("den_negative")).otherwise(pl.lit("observed")))
    mx["mx_roa_ttm"] = (pl.when(pl.col("ASSET").is_null()).then(_nullc("ASSET", "den")).when(pl.col("ASSET") == 0).then(pl.lit("den_zero"))
                          .when(pl.col("ASSET") < 0).then(pl.lit("den_negative"))
                          .when(pl.col("mc_roa_ttm").is_in(["window_history_incomplete", "window_flow_null_d12"])).then(pl.col("mc_roa_ttm"))
                          .when(pl.col("roa_window_has_1985q2") & (pl.col("roa_recon") == "mismatch")).then(pl.lit("roa_1985_mismatch"))
                          .when(pl.col("roa_window_has_1985q2") & (pl.col("roa_recon") != "reconciled")).then(pl.lit("roa_1985_not_checkable"))
                          .when(pl.col("roa_ttm").is_not_null()).then(pl.lit("observed")).otherwise(pl.lit("unexplained")))
    x = x.with_columns(**mx)
    x = x.with_columns(**{f: pl.when(pl.col(f"mx_{f}") == "observed").then(pl.col(f)) for f in CORE},
                       **{f"miss_{f}": pl.col(f"mx_{f}").is_in(list(LEGIT_MISS)).cast(pl.Int8) for f in [c.removeprefix("miss_") for c in MISS_COLS]},
                       fit_exclude_i01=pl.col("REPDTE") == I01_REPDTE,
                       roa_ttm_d12=pl.col("roa_ttm"), roa_ttm_strict=pl.col("roa_ttm_i01_strict"))
    return x.select("CERT", "REPDTE", "qi", "report_period_end", *CORE, *MISS_COLS, *[f"mx_{f}" for f in CORE], "fit_exclude_i01",
                    "roa_ttm_d12", "roa_ttm_strict").sort("CERT", "qi")


def _ratio(num: pl.Expr, den: pl.Expr, scale: float = 100.0) -> pl.Expr:
    return pl.when(den > 0).then(scale * num / den)


def _ttm(fl: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Sum of the last 4 calendar quarters (t-3..t), only when all 4 quarterly flows exist for the same CERT (no gap)."""
    base = fl.select("CERT", "qi", *[pl.col(f"flow_q_{c}").alias(c) for c in cols])
    out = base
    for k in (1, 2, 3):
        out = out.join(base.with_columns(qi=pl.col("qi") + k).rename({c: f"{c}_l{k}" for c in cols}), on=["CERT", "qi"], how="left")
    return out.select("CERT", "qi", *[(pl.col(c) + pl.col(f"{c}_l1") + pl.col(f"{c}_l2") + pl.col(f"{c}_l3")).alias(f"ttm_{c}") for c in cols])


def build_feature_candidates(lay: pl.DataFrame, flows: pl.DataFrame) -> pl.DataFrame:
    t = _ttm(flows, ["NETINC", "INTINC", "EINTEXP", "NONII", "NONIX", "ELNATR"])
    a4 = lay.select("CERT", (pl.col("qi") + 4).alias("qi"), pl.col("ASSET").alias("ASSET_l4"))
    x = (lay.select("CERT", "REPDTE", "qi", "report_period_end", "audit_i01_masked", *sorted({c for v in FEATURE_INPUTS.values() for c in v} - {"NETINC", "INTINC", "EINTEXP", "NONII", "NONIX", "ELNATR"}))
            .join(t, on=["CERT", "qi"], how="left").join(flows.select("CERT", "qi", "flow_q_NETINC"), on=["CERT", "qi"], how="left")
            .join(a4, on=["CERT", "qi"], how="left"))
    return x.select("CERT", "REPDTE", "qi", "report_period_end", "audit_i01_masked",
        eq_assets=_ratio(pl.col("EQ"), pl.col("ASSET")),
        noncurrent_loans=_ratio(pl.col("NCLNLS"), pl.col("LNLSGR")),
        reserve_loans=_ratio(pl.col("LNATRES"), pl.col("LNLSGR")),
        roa_ttm=_ratio(pl.col("ttm_NETINC"), pl.col("ASSET")),
        loans_deposits=_ratio(pl.col("LNLSNET"), pl.col("DEP")),
        borrowed_assets=_ratio(pl.col("OTHBOR"), pl.col("ASSET")),
        noncore_assets=_ratio(pl.col("NTRTIME") + pl.col("OTHBOR"), pl.col("ASSET")),
        log_assets=pl.when(pl.col("ASSET") > 0).then(pl.col("ASSET").log()),
        nim_ttm=_ratio(pl.col("ttm_INTINC") - pl.col("ttm_EINTEXP"), pl.col("ASSET")),
        provision_loans_ttm=_ratio(pl.col("ttm_ELNATR"), pl.col("LNLSGR")),
        efficiency_ttm=_ratio(pl.col("ttm_NONIX"), pl.col("ttm_INTINC") - pl.col("ttm_EINTEXP") + pl.col("ttm_NONII")),
        asset_growth_4q=pl.when((pl.col("ASSET") > 0) & (pl.col("ASSET_l4") > 0)).then(pl.col("ASSET") / pl.col("ASSET_l4") - 1),
        brokered_assets=_ratio(pl.col("BRO"), pl.col("ASSET")),
        tier1_rwa=_ratio(pl.col("RBCT1J"), pl.col("RWAJT")),
        roa_q_ann=_ratio(4 * pl.col("flow_q_NETINC"), pl.col("ASSET"))).sort("CERT", "qi")


def classify_ytd_quarters(pit: pl.DataFrame, flows: pl.DataFrame, dev_end: date) -> pl.DataFrame:
    """One row per development report (CERT, qi): ytd_class, n_cmp, n_dec. Uses the report and the previous calendar-quarter report only."""
    cur = pit.filter(pl.col("report_period_end") <= dev_end).select("CERT", "qi", "report_period_end", "CALLFORM", *NONNEG_CUM)
    prv = cur.select("CERT", (pl.col("qi") + 1).alias("qi"), *[pl.col(y).alias(f"_p_{y}") for y in NONNEG_CUM])
    x = (cur.join(prv, on=["CERT", "qi"], how="left", validate="1:1")
            .join(flows.select("CERT", "qi", "ytd_disc_n"), on=["CERT", "qi"], how="left", validate="1:1")
            .with_columns(q=pl.col("report_period_end").dt.quarter(),
                          n_cmp=pl.sum_horizontal([(pl.col(y).is_not_null() & pl.col(f"_p_{y}").is_not_null()).cast(pl.Int8) for y in NONNEG_CUM]),
                          n_dec=pl.sum_horizontal([(pl.col(y) < pl.col(f"_p_{y}")).fill_null(False).cast(pl.Int8) for y in NONNEG_CUM])))
    return x.with_columns(ytd_class=pl.when(pl.col("q") == 1).then(pl.lit("Q1 (no subtraction)"))
                          .when(pl.col("ytd_disc_n").fill_null(0) > 0).then(pl.lit("D12 discrepancy"))
                          .when(pl.col("n_dec") >= 2).then(pl.lit("K3 suspected restart"))
                          .when(pl.col("n_dec") == 1).then(pl.lit("K1 single item"))
                          .when(pl.col("n_cmp") == 0).then(pl.lit("not_checkable"))
                          .when(pl.col("n_cmp") == 1).then(pl.lit("insufficient_evidence"))
                          .otherwise(pl.lit("OK"))).select("CERT", "qi", "report_period_end", "CALLFORM", "q", "n_cmp", "n_dec", "ytd_class")


def ytd_identity_ttm(lay: pl.DataFrame, items: list) -> pl.DataFrame:
    """CERT, qi, idt_<item>: TTM by the YTD identity; reports of the same CERT only; null when an input report / value is missing."""
    y = lay.select("CERT", "qi", "report_period_end", *items)
    q4p = y.select("CERT", "qi", *[pl.col(i).alias(f"_q4_{i}") for i in items])
    lag4 = y.select("CERT", (pl.col("qi") + 4).alias("qi"), *[pl.col(i).alias(f"_l4_{i}") for i in items])
    x = y.with_columns(_q=pl.col("report_period_end").dt.quarter(), _q4qi=pl.col("qi") - pl.col("report_period_end").dt.quarter())
    x = x.join(lag4, on=["CERT", "qi"], how="left").join(q4p.rename({"qi": "_q4qi"}), on=["CERT", "_q4qi"], how="left")
    return x.select("CERT", "qi", **{f"idt_{i}": pl.when(pl.col("_q") == 4).then(pl.col(i)).otherwise(pl.col(i) + pl.col(f"_q4_{i}") - pl.col(f"_l4_{i}")) for i in items})


def i01x_recovery_log(base: pl.DataFrame, lay: pl.DataFrame, flows: pl.DataFrame, roa_recon: pl.DataFrame) -> pl.DataFrame:
    """R-I01X cells to FILL (definition layer). base: one row per key with qi and the pre-recovery feature values; lay: point-in-time layer;
    flows: D12 flows (for the discrepancy check of the window); roa_recon: D15 table. No label is read."""
    idt = ytd_identity_ttm(lay.filter(pl.col("report_period_end") <= max(I01X_REPORTS)), ["INTINC", "EINTEXP", "ELNATR"])
    rep = lay.select("CERT", "qi").with_columns(_r=pl.lit(True)); disc = flows.select("CERT", "qi", _d=pl.col("ytd_disc_n").fill_null(0) > 0)
    w = base.filter(pl.col("report_period_end").is_in(I01X_REPORTS)).select(*KEY3, "qi", "nim_ttm", "provision_loans_ttm")
    for j in range(4):    # quarters qi - j: report present, no D12 discrepancy
        w = (w.join(rep.with_columns(qi=pl.col("qi") + j).rename({"_r": f"_r{j}"}), on=["CERT", "qi"], how="left")
              .join(disc.with_columns(qi=pl.col("qi") + j).rename({"_d": f"_d{j}"}), on=["CERT", "qi"], how="left"))
    w = (w.join(idt, on=["CERT", "qi"], how="left").join(lay.select("CERT", "qi", "ASSET", "LNLSGR"), on=["CERT", "qi"], how="left")
          .join(roa_recon.select("CERT", "qi", "roa_recon"), on=["CERT", "qi"], how="left")
          .with_columns(_ok=pl.all_horizontal([pl.col(f"_r{j}").fill_null(False) for j in range(4)]) & ~pl.any_horizontal([pl.col(f"_d{j}").fill_null(False) for j in range(4)])
                            & (pl.col("roa_recon") == "reconciled")))
    cand = {"nim_ttm": pl.when(pl.col("_ok") & (pl.col("ASSET") > 0)).then(100 * (pl.col("idt_INTINC") - pl.col("idt_EINTEXP")) / pl.col("ASSET")),
            "provision_loans_ttm": pl.when(pl.col("_ok") & (pl.col("LNLSGR") > 0)).then(100 * pl.col("idt_ELNATR") / pl.col("LNLSGR"))}
    out = []
    for f, e in cand.items():
        sel = w.with_columns(_v=e).filter(pl.col(f).is_null() & pl.col("_v").is_not_null() & pl.col("_v").is_finite())
        out.append(sel.select(*KEY3, feature=pl.lit(f), value_before=pl.lit(None, dtype=pl.Float64), value_after=pl.col("_v").cast(pl.Float64), policy=pl.lit("R-I01X"),
                              evidence=pl.lit("YTD identity; D15 window reconciled; no D12 discrepancy in t-3..t")))
    log = pl.concat(out).with_columns(version=pl.lit(DQ_POLICIES["R-I01X"]["version"]), reason=pl.lit(DQ_POLICIES["R-I01X"]["rule"]), sources=pl.lit(DQ_POLICIES["R-I01X"]["sources"]))
    return log.select(*KEY3, "feature", "value_before", "value_after", "policy", "version", "reason", "evidence", "sources").sort("feature", *KEY3)


def dq_fill(base: pl.DataFrame, log: pl.DataFrame) -> pl.DataFrame:
    """Write value_after into exactly the logged (previously null) cells; every other cell is returned unchanged."""
    out = base
    for f in log["feature"].unique().sort().to_list():
        m = log.filter(pl.col("feature") == f).select(*KEY3, _v="value_after")
        out = out.join(m, on=KEY3, how="left").with_columns(pl.coalesce(pl.col(f), pl.col("_v")).alias(f)).drop("_v")
    return out.select(base.columns)


def dq_quarantine_log(base: pl.DataFrame, qclass: pl.DataFrame, layer: pl.DataFrame) -> pl.DataFrame:
    """Cells to quarantine. base: one row per key with qi and the Y0 feature values; qclass: classify_ytd_quarters output; layer: raw stocks."""
    k = qclass.select("CERT", "qi", k3=pl.col("ytd_class") == "K3 suspected restart")
    w = base.select("CERT", "qi").unique()
    for j in range(4):   # quarter qi - j of the same CERT
        w = w.join(k.select("CERT", (pl.col("qi") + j).alias("qi"), pl.when(pl.col("k3")).then(pl.col("qi")).alias(f"k3q_{j}")), on=["CERT", "qi"], how="left")
    w = w.select("CERT", "qi", ev=pl.concat_list([f"k3q_{j}" for j in range(4)]).list.drop_nulls())
    b = base.join(w, on=["CERT", "qi"], how="left", validate="m:1")
    out = []
    for f in DQ_POLICIES["Y1"]["features"]:
        sel = b.filter(pl.col(f).is_not_null() & (pl.col("ev").list.len() > 0))
        out.append(sel.select(*KEY3, feature=pl.lit(f), value_before=pl.col(f).cast(pl.Float64), policy=pl.lit("Y1"),
                              evidence=pl.lit("K3 quarter qi in window: ") + pl.col("ev").cast(pl.List(pl.Utf8)).list.join(",")))
    g = (base.join(layer.select("CERT", "report_period_end", "BRO", "DEP", "ASSET"), on=KEY3, how="left", validate="1:1")
             .filter(pl.col("brokered_assets").is_not_null() & (pl.col("BRO") > pl.col("DEP")) & (pl.col("BRO") > pl.col("ASSET"))))
    out.append(g.select(*KEY3, feature=pl.lit("brokered_assets"), value_before=pl.col("brokered_assets").cast(pl.Float64), policy=pl.lit("B1"),
                        evidence=pl.concat_str([pl.lit("BRO="), pl.col("BRO").cast(pl.Int64).cast(pl.Utf8), pl.lit(" DEP="), pl.col("DEP").cast(pl.Int64).cast(pl.Utf8),
                                                  pl.lit(" ASSET="), pl.col("ASSET").cast(pl.Int64).cast(pl.Utf8)])))   # pl.format on floats panics in this polars build
    log = pl.concat(out).with_columns(value_after=pl.lit(None, dtype=pl.Float64),
                                      version=pl.col("policy").replace_strict({k: v["version"] for k, v in DQ_POLICIES.items()}),
                                      reason=pl.col("policy").replace_strict({k: v["rule"] for k, v in DQ_POLICIES.items()}),
                                      sources=pl.col("policy").replace_strict({k: v["sources"] for k, v in DQ_POLICIES.items()}))
    return log.select(*KEY3, "feature", "value_before", "value_after", "policy", "version", "reason", "evidence", "sources").sort("feature", *KEY3)


def dq_apply(base: pl.DataFrame, log: pl.DataFrame) -> pl.DataFrame:
    """Set exactly the logged cells to null; every other cell is returned unchanged."""
    out = base
    for f in log["feature"].unique().sort().to_list():
        m = log.filter(pl.col("feature") == f).select(*KEY3).with_columns(_q=pl.lit(True))
        out = out.join(m, on=KEY3, how="left").with_columns(pl.when(pl.col("_q").fill_null(False)).then(None).otherwise(pl.col(f)).alias(f)).drop("_q")
    return out.select(base.columns)


def k3_window_null(df: pl.DataFrame, cols: list, qclass: pl.DataFrame) -> tuple:
    """Null the listed TTM columns where the window t-3..t holds a K3 quarter (the Y1 rule of 17.20, as a function of a column list). Returns (df, log)."""
    k = qclass.select("CERT", "qi", k3=pl.col("ytd_class") == "K3 suspected restart")
    w = df.select("CERT", "qi").unique()
    for j in range(4):
        w = w.join(k.select("CERT", (pl.col("qi") + j).alias("qi"), pl.col("k3").alias(f"k{j}")), on=["CERT", "qi"], how="left")
    w = w.select("CERT", "qi", inwin=pl.any_horizontal([pl.col(f"k{j}").fill_null(False) for j in range(4)]))
    x = df.join(w, on=["CERT", "qi"], how="left")
    log = pl.concat([x.filter(pl.col("inwin") & pl.col(c).is_not_null()).select(*KEY3, feature=pl.lit(c), value_before=pl.col(c).cast(pl.Float64)) for c in cols])
    x = x.with_columns([pl.when(pl.col("inwin")).then(None).otherwise(pl.col(c)).alias(c) for c in cols]).drop("inwin")
    return x, log


def build_pool_features(lay: pl.DataFrame, flows: pl.DataFrame, qclass: pl.DataFrame) -> tuple:
    """New pool features for every report of `lay` (point-in-time D8 layer); returns (features keyed by CERT / report_period_end, isolation log)."""
    cols = ["CERT", "REPDTE", "qi", "report_period_end", "ASSET", "EQ", "ESTYMD", "OFFDOM", "P3LNLS", *POOL_NONNEG]
    x = lay.select(*[c for c in dict.fromkeys(cols)])
    t = _ttm(flows, ["NTLNLS"])
    x = x.join(t, on=["CERT", "qi"], how="left")
    neg = {c: pl.col(c) < 0 for c in POOL_NONNEG}
    iso = []
    exprs = {}
    for f, num in POOL_NUMS.items():
        if f == "npa_assets":
            bad = neg["NCLNLS"] | neg["ORE"]; val = _ratio(pl.col("NCLNLS") + pl.col("ORE"), pl.col("ASSET"))
        else:
            bad = neg[num]; val = _ratio(pl.col(num), pl.col("ASSET"))
        exprs[f] = pl.when(bad.fill_null(False)).then(None).otherwise(val)
        iso.append(x.filter(bad.fill_null(False) & (pl.col("ASSET") > 0)).select(*KEY3, feature=pl.lit(f), reason=pl.lit("negative reported stock: provisional isolation; historical mapping / offset basis may be unresolved")))
    est = pl.col("ESTYMD").cast(pl.Int64).cast(pl.Utf8).str.strptime(pl.Date, "%Y%m%d", strict=False)
    age = (pl.col("report_period_end") - est).dt.total_days() / 365.25
    exprs["log_age"] = pl.when(age >= 0).then((1 + age).log())
    iso.append(x.filter(age < 0).select(*KEY3, feature=pl.lit("log_age"), reason=pl.lit("ESTYMD after the report date")))
    exprs["log_offices"] = pl.when(pl.col("OFFDOM") >= 0).then((1 + pl.col("OFFDOM")).log())
    exprs["nco_ttm"] = _ratio(pl.col("ttm_NTLNLS"), pl.col("LNLSGR"))
    exprs["past_due_30_89"] = pl.when(pl.col("P3LNLS") >= 0).then(_ratio(pl.col("P3LNLS"), pl.col("LNLSGR")))      # LATE field (2001Q1+): separate arm only
    out = x.select("CERT", "qi", "report_period_end", **exprs)
    out, k3log = k3_window_null(out, ["nco_ttm"], qclass)
    log = pl.concat([pl.concat(iso), k3log.select(*KEY3, "feature", reason=pl.lit("nco_ttm window holds a K3 quarter (Y1 mechanism)"))], how="diagonal")
    return out.drop("qi"), log


def prepare_pool_clean(base, old_pool, source, flows, scope_end):
    """Label-blind fixed rules. Returns model candidates, status ledger, reversible edits and relation warnings.

    Relation warning != confirmed error. In particular LNLSGR is net of unearned income;
    a component > LNLSGR or > ASSET alone is NEVER auto-nulled / capped to 100.
    A negative, exactly offsetting TFR real-estate decomposition is quarantined jointly,
    because its individual shares have no verified interpretation; parent LNRE remains intact.
    """
    k = POOL_CLEAN_KEYS
    for name, frame in [('base',base),('old_pool',old_pool),('source',source)]:
        if frame.select(pl.struct(k).is_duplicated().any()).item():
            raise ValueError(f'{name}: duplicate keys')
        if frame['report_period_end'].max() > scope_end:
            raise ValueError(f'{name}: outside development report scope')
    flow_dates=flows.select(pl.col('REPDTE').cast(pl.String).str.replace_all('-', '').str.strptime(pl.Date,'%Y%m%d',strict=True)).to_series()
    if flow_dates.max() > scope_end:
        raise ValueError('flows outside development')
    out = base.join(old_pool.select(k + POOL_CLEAN_NEW + ['past_due_30_89']), on=k, how='left', validate='1:1').sort(k)
    src = out.select(k).join(source, on=k, how='left', validate='1:1')
    # Exact structural reconciliation, not a guess about the original accounting cause.
    comp = list(POOL_CLEAN_RE_COMPONENTS.values())
    src = src.with_columns(re_sum4=pl.sum_horizontal(comp, ignore_nulls=False),
                           re_negative=pl.any_horizontal([pl.col(c)<0 for c in comp]).fill_null(False))
    src = src.with_columns(re_ambiguous=((pl.col('CALLFORM')==100)&pl.col('re_negative')&
                 ((pl.col('re_sum4')-pl.col('LNRE')).abs()<=1)).fill_null(False))
    masked = src.filter('re_ambiguous').select(k).with_columns(_ambiguous=pl.lit(True))
    out = out.join(masked, on=k, how='left', validate='1:1')
    logs = []
    for f in POOL_CLEAN_RE_COMPONENTS:
        logs.append(out.filter(pl.col('_ambiguous').fill_null(False)&pl.col(f).is_not_null()).select(
            *k,feature=pl.lit(f),value_before=pl.col(f),value_after=pl.lit(None,dtype=pl.Float64),
            reason=pl.lit('TFR negative offsetting real-estate decomposition: joint quarantine; NOT a recovered true value')))
    out = out.with_columns([pl.when(pl.col('_ambiguous').fill_null(False)).then(None).otherwise(pl.col(f)).alias(f)
                            for f in POOL_CLEAN_RE_COMPONENTS]).drop('_ambiguous')
    # Nonfinite is not an economic value. Log, convert only derived cells, retain all source rows.
    for f in POOL_CLEAN_COLS + ['past_due_30_89']:
        bad = pl.col(f).is_nan() | pl.col(f).is_infinite()
        logs.append(out.filter(bad).select(*k,feature=pl.lit(f),value_before=pl.col(f),
                    value_after=pl.lit(None,dtype=pl.Float64),reason=pl.lit('nonfinite derived value')))
        out = out.with_columns(pl.when(bad).then(None).otherwise(pl.col(f)).alias(f))
    changes = pl.concat(logs).sort(k+['feature'])
    # Whole source windows, from current and previous reports only, for audit (never model columns).
    win = source.select('CERT','qi',present=pl.lit(1),
                        observed=pl.col('NTLNLSQ').is_not_null().cast(pl.Int8))
    w = win
    for lag in (1,2,3):
        w = w.join(win.with_columns(qi=pl.col('qi')+lag).rename({'present':f'present{lag}','observed':f'observed{lag}'}),
                   on=['CERT','qi'],how='left',validate='1:1')
    w = w.select('CERT','qi',n_reports=pl.sum_horizontal(['present',*[f'present{i}' for i in (1,2,3)]]),
                 n_source_quarters=pl.sum_horizontal(['observed',*[f'observed{i}' for i in (1,2,3)]]))
    st = src.select(*k,'qi','CALLFORM','LNLSGR').join(w,on=['CERT','qi'],how='left',validate='1:1').join(
         out.select(*k,'nco_ttm'),on=k,how='left',validate='1:1')
    st = st.with_columns(nco_status=pl.when(pl.col('nco_ttm').is_not_null()).then(pl.lit('observed_four_quarter_value'))
        .when(pl.col('LNLSGR').is_null()|(pl.col('LNLSGR')<=0)).then(pl.lit('denominator_unavailable_or_nonpositive'))
        .when(pl.col('n_reports')<4).then(pl.lit('insufficient_history_or_report_gap'))
        .when(pl.col('n_source_quarters')==0).then(pl.lit('entire_source_window_unavailable'))
        .when(pl.col('n_source_quarters')<4).then(pl.lit('incomplete_source_window'))
        .otherwise(pl.lit('quarterly_flow_or_quality_policy_missing')),
        source_scope_annotation=pl.when((pl.col('CALLFORM')==100)&(pl.col('report_period_end')<date(1990,1,1)))
            .then(pl.lit('TFR_pre1990_empirical_coverage_gap; official start date unverified')).otherwise(pl.lit('')))
    # Cross-column warning ledger. No automatic subset identity against net total.
    rel = []
    for f,num in POOL_CLEAN_NUMS.items():
        for total,kind in [('ASSET','above_assets_basis_review'),
                           *([('LNLSGR','above_net_of_unearned_income_total_basis_review')] if f in ['cd_assets','cre_assets','multifam_assets','resid_assets','ci_assets','consumer_assets'] else [])]:
            rel.append(src.filter(pl.col(num)>pl.col(total)+1).select(*k,'CALLFORM',
                feature=pl.lit(f),field=pl.lit(num),reported_component=pl.col(num),total_name=pl.lit(total),
                reported_total=pl.col(total),gap=pl.col(num)-pl.col(total),reason=pl.lit(kind),
                treatment=pl.lit('retain; cannot infer error without compatible basis / original report')))
    relations = pl.concat(rel).sort(k+['feature','total_name'])
    status = st.select(*k,'nco_status','n_reports','n_source_quarters','source_scope_annotation').join(
             src.select(*k,'re_ambiguous'),on=k,validate='1:1').sort(k)   # deterministic row order (Claude 2026-11-11: unsorted join output changed the file bytes and the manifest on every run)
    return out.sort(k), status, changes, relations


def build_events(fail: pl.DataFrame, data_end: date) -> pl.DataFrame:
    """One row per Failures record with a CERT and FAILDATE <= data_end. Audit table, not a label."""
    ev = (fail.filter(pl.col("CERT").is_not_null())
              .with_columns(fd=pl.col("FAILDATE").str.strptime(pl.Date, "%m/%d/%Y"))
              .filter(pl.col("fd") <= data_end)
              .with_columns(event_class=pl.when(pl.col("RESTYPE") == "FAILURE").then(pl.lit("failure"))
                                          .when(pl.col("RESTYPE") == "ASSISTANCE").then(pl.lit("assistance"))
                                          .otherwise(pl.lit("unclassified")))
              .sort("CERT", "fd"))
    ev = ev.with_columns(seq_in_class=pl.col("fd").rank("ordinal").over("CERT", "event_class").cast(pl.Int32))
    # label event = first FAILURE of a CERT: FAILDATE = date it ceased to be a privately held going concern
    # (FDIC dictionary); a later FAILURE record of the same CERT (FSLIC management takeover, later RTC resolution)
    # is kept for audit but does not create a second failure.
    ev = ev.with_columns(label_event=(pl.col("event_class") == "failure") & (pl.col("seq_in_class") == 1))
    return ev.select("CERT", "NAME", "fd", "RESTYPE", "RESTYPE1", "SAVR", "event_class", "seq_in_class", "label_event")


def build_exits(keys: pl.DataFrame, ev: pl.DataFrame, inst: pl.DataFrame, data_end: date) -> pl.DataFrame:
    """One row per CERT in Financials: last report and the evidence for why reporting stopped."""
    life = keys.group_by("CERT").agg(first_rd=pl.col("rd").min(), last_rd=pl.col("rd").max(), n_reports=pl.len())
    ff = ev.filter(pl.col("label_event")).select("CERT", first_failure=pl.col("fd"))
    asst = ev.filter(pl.col("event_class") == "assistance").select("CERT", "fd")
    a_after = (life.select("CERT", "last_rd").join(asst, on="CERT")
                   .filter(pl.col("fd") > pl.col("last_rd")).group_by("CERT").agg(assist_exit_date=pl.col("fd").min()))
    ins = inst.select("CERT", "ACTIVE", "CHANGEC1",
                      end=pl.col("ENDEFYMD").str.strptime(pl.Date, "%m/%d/%Y", strict=False),
                      ult=pl.col("ULTCERT").cast(pl.Int64, strict=False))
    x = (life.join(ff, on="CERT", how="left").join(a_after, on="CERT", how="left").join(ins, on="CERT", how="left")
             .with_columns(end=pl.when(pl.col("end").dt.year() < 2100).then(pl.col("end"))))
    stopped = pl.col("last_rd") < data_end
    x = x.with_columns(
        exit_class=pl.when(~stopped).then(pl.lit("none_observed"))
          .when(pl.col("first_failure").is_not_null()).then(pl.lit("failure"))
          .when(pl.col("assist_exit_date").is_not_null()).then(pl.lit("assistance_exit"))
          .when((pl.col("ACTIVE") == 0) & pl.col("ult").is_not_null() & (pl.col("ult") != pl.col("CERT"))
                & pl.col("end").is_not_null() & (pl.col("end") > pl.col("last_rd"))).then(pl.lit("merger_or_acquisition"))
          .when((pl.col("ACTIVE") == 0) & (pl.col("ult") == pl.col("CERT"))
                & pl.col("end").is_not_null() & (pl.col("end") > pl.col("last_rd"))).then(pl.lit("closure_unverified"))
          .otherwise(pl.lit("exit_unknown")))
    x = x.with_columns(exit_date=pl.when(pl.col("exit_class") == "failure").then(pl.col("first_failure"))
                                   .when(pl.col("exit_class") == "assistance_exit").then(pl.col("assist_exit_date"))
                                   .when(pl.col("exit_class").is_in(["merger_or_acquisition", "closure_unverified"])).then(pl.col("end")))
    return x


def build_audit(keys: pl.DataFrame, ev: pl.DataFrame, exits: pl.DataFrame, data_end: date) -> pl.DataFrame:
    """One row per Financials row (CERT, REPDTE). Timing columns, population status and an AUDIT label.
    keys: CERT, rd (report date), qi (calendar quarter index of rd), BKCLASS (bank class on that report; D4)."""
    a = (keys.select("CERT", "rd", "qi", "BKCLASS")
             .with_columns(pq=pl.col("qi") + LAG_Q)
             .join(QCAL.rename({"qi": "pq", "qend": "prediction_as_of"}), on="pq", how="left")
             .with_columns(report_period_end=pl.col("rd"), available_at_assumed=pl.col("prediction_as_of"))
             .join(QCAL.with_columns(pq=pl.col("qi") - H_Q).select("pq", label_end="qend"), on="pq", how="left")
             .join(exits.select("CERT", "first_failure", "exit_class", "exit_date", "last_rd"), on="CERT", how="left"))
    asst = ev.filter(pl.col("event_class") == "assistance").select("CERT", "fd")
    af = (a.select("CERT", "rd", "prediction_as_of", "label_end").join(asst, on="CERT", how="inner")
            .group_by("CERT", "rd").agg(
                post_assistance=(pl.col("fd") <= pl.col("prediction_as_of")).any(),
                assist_in_window=((pl.col("fd") > pl.col("prediction_as_of")) & (pl.col("fd") <= pl.col("label_end"))).any()))
    a = a.join(af, on=["CERT", "rd"], how="left").with_columns(pl.col("post_assistance", "assist_in_window").fill_null(False))
    asof, lend, ff = pl.col("prediction_as_of"), pl.col("label_end"), pl.col("first_failure")
    nonfail_exit = pl.col("exit_class").is_in(["assistance_exit", "merger_or_acquisition", "closure_unverified"])
    a = a.with_columns(pop_status=pl.when(ff.is_not_null() & (ff <= pl.col("rd"))).then(pl.lit("report_on_or_after_failure"))
                                    .when(ff.is_not_null() & (ff <= asof)).then(pl.lit("failed_before_asof"))
                                    .when(nonfail_exit & (pl.col("exit_date") <= asof)).then(pl.lit("exited_before_asof"))
                                    .when(~pl.col("BKCLASS").is_in(list(INSURED_CLASSES)).fill_null(False) | pl.col("BKCLASS").is_null())
                                    .then(pl.lit("out_of_scope_not_insured"))
                                    .otherwise(pl.lit("eligible")))
    in_win = lambda d: d.is_not_null() & (d > asof) & (d <= lend)
    a = a.with_columns(label_status=pl.when(pl.col("pop_status") != "eligible").then(pl.lit("not_in_population"))
        .when(lend > data_end).then(pl.lit("horizon_incomplete"))
        .when(in_win(ff)).then(pl.lit("positive"))
        .when((pl.col("exit_class") == "merger_or_acquisition") & in_win(pl.col("exit_date"))).then(pl.lit("negative_merged_in_window"))
        .when((pl.col("exit_class") == "assistance_exit") & in_win(pl.col("exit_date"))).then(pl.lit("negative_assistance_exit_in_window"))
        .when((pl.col("exit_class") == "closure_unverified") & in_win(pl.col("exit_date"))).then(pl.lit("censored_closure_unverified"))
        .when((pl.col("exit_class") == "exit_unknown") & (pl.col("last_rd") < lend)).then(pl.lit("censored_unknown_exit"))
        .when(pl.col("assist_in_window")).then(pl.lit("negative_assistance_in_window"))
        .otherwise(pl.lit("negative")))
    a = a.with_columns(
        y_audit=pl.when(pl.col("label_status") == "positive").then(1)
                  .when(pl.col("label_status").str.starts_with("negative")).then(0).cast(pl.Int8),
        y_broad_audit=pl.when(pl.col("label_status") == "positive").then(1)
                  .when(pl.col("label_status").is_in(["negative_assistance_in_window", "negative_assistance_exit_in_window"])).then(1)
                  .when(pl.col("label_status").str.starts_with("negative")).then(0).cast(pl.Int8),
        positive_event_cert=pl.when(pl.col("label_status") == "positive").then(pl.col("CERT")))
    return a.select("CERT", "report_period_end", "available_at_assumed", "prediction_as_of", "pq", "label_end",
                    "pop_status", "label_status", "y_audit", "y_broad_audit", "post_assistance", "assist_in_window",
                    "first_failure", "exit_class", "exit_date", "last_rd", "positive_event_cert")


class ContractCapperV4(OneToOneFeatureMixin, TransformerMixin, BaseEstimator):
    """Recipe v3 rule + sparse-tail fix: when the upper train quantile is 0 but positive train values exist, the upper bound is the same quantile OF THE
    POSITIVE VALUES (rare valid positives are kept); with no positive train value the upper bound is +inf (sign kept). Identical to v3 when q_hi > 0."""
    def __init__(self, columns, contract, lower=0.005, upper=0.995):
        self.columns = columns; self.contract = contract; self.lower = lower; self.upper = upper
    def _array(self, X):
        if isinstance(X, pd.DataFrame) and list(X.columns) != list(self.columns): raise ValueError("column order differs")
        a = np.asarray(X, dtype=np.float64)
        if a.ndim != 2 or a.shape[1] != len(self.columns): raise ValueError("feature shape differs")
        return a
    def fit(self, X, y=None):
        a = self._array(X)
        if np.isnan(a).all(axis=0).any(): raise ValueError("all-missing fit feature")
        lo, hi = np.nanquantile(a, self.lower, axis=0), np.nanquantile(a, self.upper, axis=0)
        L, H = np.minimum(lo, 0.0), np.maximum(hi, 0.0)
        for j, c in enumerate(self.columns):
            k = self.contract[c]; col = a[:, j]
            if k == "log": L[j], H[j] = -np.inf, np.inf; continue
            if not hi[j] > 0:
                pos = col[col > 0]; H[j] = float(np.quantile(pos, self.upper)) if pos.size else np.inf
            if k in ("signed", "signed_change"):
                neg = col[col < 0]; L[j] = lo[j] if lo[j] < 0 else (float(np.quantile(neg, self.lower)) if neg.size else -np.inf)
            elif k == "upper_only": L[j] = -np.inf
        self.lower_bounds_, self.upper_bounds_ = L, H; self.n_features_in_ = a.shape[1]; self.feature_names_in_ = np.asarray(self.columns, dtype=object)
        return self
    def transform(self, X):
        check_is_fitted(self, "lower_bounds_"); return np.clip(self._array(X), self.lower_bounds_, self.upper_bounds_)


def v59_block_T(raw: pl.DataFrame) -> pl.DataFrame:
    nn = lambda c: pl.when(pl.col(c) >= 0).then(pl.col(c))                      # negative stock -> null; null stays null
    num = nn("NCLNLS") + nn("ORE"); den = pl.col("EQ") - nn("INTAN") + nn("LNATRES"); a = pl.when(pl.col("ASSET") > 0).then(pl.col("ASSET"))
    return raw.select("CERT", "report_period_end",
                      texas_proxy=pl.when(den > 0).then(100 * num / den),
                      texas_den_nonpos=pl.when(num.is_not_null() & den.is_not_null()).then((den <= 0).cast(pl.Float64)),
                      buffer_gap_assets=100 * (num - den) / a, uncovered_ncl_assets=100 * (nn("NCLNLS") - nn("LNATRES")) / a)
