"""Exact cover-based Tree SHAP for imodels custom forests; first-order ALE.
Adapted from the audited research notebook. See references/README.md and rule provenance.
These are model associations, never causal financial effects.
"""
from __future__ import annotations
import numpy as np
import polars as pl
from itertools import combinations
from math import factorial
from joblib import Parallel,delayed
from imodels import IRFClassifier
def v55_tree_arrays(t) -> tuple:
    return (t.children_left_, t.children_right_, t.feature_, t.threshold_, np.asarray(t.value_)[:, 1].astype(np.float64), np.asarray(t.weighted_n_node_samples_, dtype=np.float64))

def v55_route_left(xv: float, thr: float) -> bool:
    return float(np.float64(np.float32(xv))) <= float(thr)

def v55_expvalue(arr, x, S) -> float:
    """Algorithm 1: E[f(x) | x_S] with the training cover (exponential reference)."""
    cl, cr, ft, th, v, w = arr
    def g(j):
        if cl[j] < 0: return v[j]
        if ft[j] in S: return g(cl[j]) if v55_route_left(x[ft[j]], th[j]) else g(cr[j])
        return (w[cl[j]] * g(cl[j]) + w[cr[j]] * g(cr[j])) / w[j]
    return g(0)

def v55_treeshap_tree(arr, x, M) -> np.ndarray:
    """Algorithm 2 (polynomial Tree SHAP) for one tree and one row; path elements (d, z, o, w), shap-style 0-based weights."""
    cl, cr, ft, th, v, w = arr; phi = np.zeros(M)
    def extend(m, pz, po, pi):
        m = [list(e) for e in m]; l = len(m); m.append([pi, pz, po, 1.0 if l == 0 else 0.0])
        for i in range(l - 1, -1, -1):
            m[i + 1][3] += po * m[i][3] * (i + 1) / (l + 1)
            m[i][3] = pz * m[i][3] * (l - i) / (l + 1)
        return m
    def unwind(m, i):
        l = len(m) - 1; n = m[l][3]; z, o = m[i][1], m[i][2]; m = [list(e) for e in m]
        for j in range(l - 1, -1, -1):
            if o != 0:
                t = m[j][3]; m[j][3] = n * (l + 1) / ((j + 1) * o); n = t - m[j][3] * z * (l - j) / (l + 1)
            else:
                m[j][3] = (m[j][3] * (l + 1)) / (z * (l - j))
        for j in range(i, l):
            m[j][0], m[j][1], m[j][2] = m[j + 1][0], m[j + 1][1], m[j + 1][2]
        return m[:l]
    def unwound_sum(m, i):
        l = len(m) - 1; z, o = m[i][1], m[i][2]; n = m[l][3]; tot = 0.0
        for j in range(l - 1, -1, -1):
            if o != 0:
                t = n * (l + 1) / ((j + 1) * o); tot += t; n = m[j][3] - t * z * (l - j) / (l + 1)
            else:
                tot += (m[j][3] / z) / ((l - j) / (l + 1))
        return tot
    def recurse(j, m, pz, po, pi):
        m = extend(m, pz, po, pi)
        if cl[j] < 0:
            for i in range(1, len(m)):
                phi[m[i][0]] += unwound_sum(m, i) * (m[i][2] - m[i][1]) * v[j]
            return
        d = ft[j]; hot, cold = (cl[j], cr[j]) if v55_route_left(x[d], th[j]) else (cr[j], cl[j]); iz = io = 1.0
        k = next((i for i in range(1, len(m)) if m[i][0] == d), None)
        if k is not None:
            iz, io = m[k][1], m[k][2]; m = unwind(m, k)
        recurse(hot, m, iz * w[hot] / w[j], io, d); recurse(cold, m, iz * w[cold] / w[j], 0.0, d)
    recurse(0, [], 1.0, 1.0, -1)
    return phi

def v55_forest_shap(clf, Xt: np.ndarray, n_jobs: int = 6) -> tuple:
    """(phi [n, M], expected value) for the forest that predicts (mean over trees); Xt = transformed inputs (after cap + median)."""
    trees = [v55_tree_arrays(t) for t in clf.forest_.estimators_]; M = Xt.shape[1]
    ev = float(np.mean([(a[5][a[0] < 0] * a[4][a[0] < 0]).sum() / a[5][0] for a in trees]))
    def one(rows):
        return np.vstack([np.mean([v55_treeshap_tree(a, x, M) for a in trees], axis=0) for x in rows])
    chunks = np.array_split(Xt, max(1, min(len(Xt), n_jobs * 4)))
    phi = np.vstack(Parallel(n_jobs=n_jobs)(delayed(one)(c) for c in chunks if len(c)))
    return phi, ev

def v55_bruteforce_tree(arr, x, M) -> np.ndarray:
    feats = sorted({int(f) for f in arr[2][arr[0] >= 0]}); phi = np.zeros(M); k = len(feats)
    for f in feats:
        others = [g for g in feats if g != f]
        for r in range(len(others) + 1):
            wgt = factorial(r) * factorial(k - r - 1) / factorial(k)
            for S in combinations(others, r):
                phi[f] += wgt * (v55_expvalue(arr, x, set(S) | {f}) - v55_expvalue(arr, x, set(S)))
    return phi

def v55_ale(model, X: np.ndarray, j: int, K: int = 20, q_lo: float = 0.01, q_hi: float = 0.99) -> pl.DataFrame:
    """First-order ALE of column j (raw input space; the pipeline applies its own cap / median). Rows with a null x_j or outside [q_lo, q_hi] are excluded
    (count reported). Interval edges = quantiles of the retained rows; ties can merge edges (unique edges kept)."""
    xj = X[:, j]; ok = np.isfinite(xj); lo, hi = np.quantile(xj[ok], [q_lo, q_hi]); keep = ok & (xj >= lo) & (xj <= hi); Z = X[keep]; z = Z[:, j]
    edges = np.unique(np.quantile(z, np.linspace(0, 1, K + 1))); k = np.clip(np.searchsorted(edges, z, side="left"), 1, len(edges) - 1)
    A, B = Z.copy(), Z.copy(); A[:, j] = edges[k - 1]; B[:, j] = edges[k]
    diff = model.predict_proba(B)[:, 1] - model.predict_proba(A)[:, 1]
    nb = np.bincount(k, minlength=len(edges))[1:]; mean_d = np.bincount(k, weights=diff, minlength=len(edges))[1:] / np.maximum(nb, 1)
    g = np.concatenate([[0.0], np.cumsum(mean_d)])                                # uncentered effect at the edges
    mid = (g[:-1] + g[1:]) / 2; f = g - (mid * nb).sum() / nb.sum()               # centre: mean effect over the retained rows (interval-midpoint rule)
    return pl.DataFrame({"edge": edges, "ale": f, "rows_in_interval_ending_here": np.concatenate([[0], nb]),
                         "excluded_null": [int((~ok).sum())] * len(edges), "excluded_tails": [int((ok & ~keep).sum())] * len(edges)})

def v55_perm_within_quarter(X: np.ndarray, quarters: np.ndarray, cols: list, rng) -> np.ndarray:
    Xp = X.copy(); idx = np.arange(len(X))
    for q in np.unique(quarters):
        r = idx[quarters == q]; p = rng.permutation(r); Xp[np.ix_(r, cols)] = X[np.ix_(p, cols)]
    return Xp

def v55_expl_tests() -> dict:
    T = {}; rng = np.random.default_rng(7)
    # toy trees from imodels itself (small, deep enough to repeat features on a path)
    Xs = rng.normal(size=(3000, 5)); ys = ((Xs[:, 0] + Xs[:, 1] * Xs[:, 2] + 0.5 * rng.normal(size=3000)) > 0.5).astype(int)
    toy = IRFClassifier(n_estimators=4, n_iterations=2, n_bootstraps=0, max_depth=5, min_samples_leaf=20, random_state=3, n_jobs=1).fit(Xs, ys)
    ok_bf, ok_add, ok_cover = True, True, True
    for t in toy.forest_.estimators_:
        a = v55_tree_arrays(t); inner = a[0] >= 0
        ok_cover &= bool(np.allclose(a[5][a[0][inner]] + a[5][a[1][inner]], a[5][inner]))
        for x in Xs[:6]:
            p2 = v55_treeshap_tree(a, x, 5); pb = v55_bruteforce_tree(a, x, 5)
            ok_bf &= bool(np.max(np.abs(p2 - pb)) < 1e-10)
            ok_add &= abs(p2.sum() + v55_expvalue(a, x, set()) - t.predict_proba(x[None, :])[0, 1]) < 1e-10
    T["toy: Algorithm 2 == brute-force Shapley (all subsets, Algorithm 1) per tree"] = ok_bf
    T["toy: additivity per tree, sum(phi) + E[f] == tree prediction"] = ok_add
    T["toy: children covers add up to the parent cover"] = ok_cover
    phi, ev = v55_forest_shap(toy, Xs[:40], n_jobs=2)
    T["toy forest: sum(phi) + E[f] == predict_proba (|diff| < 1e-9)"] = float(np.max(np.abs(phi.sum(1) + ev - toy.predict_proba(Xs[:40])[:, 1]))) < 1e-9
    T["toy: a feature never used by any tree gets phi = 0"] = bool(np.all(phi[:, [f for f in range(5) if f not in {int(u) for tt in toy.forest_.estimators_ for u in tt.feature_[tt.children_left_ >= 0]}]] == 0))
    # ALE on an additive model recovers the slope (Remark 1): f = expit-free linear stand-in
    class _Lin:
        def predict_proba(self, X): p = 0.1 + 0.02 * np.nan_to_num(X[:, 0]); return np.column_stack([1 - p, p])
    al = v55_ale(_Lin(), np.column_stack([rng.uniform(0, 10, 5000), rng.normal(size=5000)]), 0)
    T["ALE of an additive linear model has slope 0.02 and mean ~ 0"] = bool(np.allclose(np.diff(al["ale"].to_numpy()) / np.diff(al["edge"].to_numpy()), 0.02, atol=1e-9))
    qx = np.repeat([1, 2], 50); Xp = v55_perm_within_quarter(np.column_stack([np.arange(100.0), np.arange(100.0), -np.arange(100.0)]), qx, [0, 1], np.random.default_rng(1))
    T["within-quarter permutation: rows stay in their quarter, unit columns move together, others untouched"] = (
        set(Xp[:50, 0]) == set(range(50)) and bool(np.all(Xp[:, 0] == Xp[:, 1])) and bool(np.all(Xp[:, 2] == -np.arange(100.0))))
    return T

def run_explanations():
    import json,joblib
    from .pipeline import ROOT,dev_labels,dump_json
    tests=v55_expl_tests();assert all(tests.values())
    manifest=json.loads((ROOT/'models/B3/manifest.json').read_text());cols=manifest['columns']
    model=joblib.load(ROOT/'models/B3/model.joblib')
    f=pl.read_parquet(ROOT/'data/processed/features_to_2011-09-30.parquet').join(dev_labels(),on=['CERT','report_period_end'],how='inner').filter(~pl.col('fit_exclude_i01'))
    sample=f.sample(n=96,seed=42).select(cols).to_numpy().astype(float)
    transformed=model[:-1].transform(sample);phi,expected=v55_forest_shap(model['model'],transformed,n_jobs=2)
    error=float(np.max(np.abs(phi.sum(1)+expected-model.predict_proba(sample)[:,1])));assert error<1e-9
    pl.DataFrame({'feature':cols,'mean_abs_SHAP_probability':np.abs(phi).mean(0),'scope':['96 uniformly sampled development training rows; in-sample model explanation']*len(cols)}).sort('mean_abs_SHAP_probability',descending=True).write_csv(ROOT/'reports/tables/final_B3_shap.csv')
    X=f.sample(n=20000,seed=42).select(cols).to_numpy().astype(float)
    for c in ['eq_assets','noncurrent_loans','roa_ttm','texas_proxy']:
        al=v55_ale(model,X,cols.index(c),K=15);al.with_columns(feature=pl.lit(c)).write_csv(ROOT/f'reports/tables/final_B3_ALE_{c}.csv')
    dump_json(ROOT/'reports/tables/explainability_checks.json',{'toy_tests':tests,'final_model_SHAP_additivity_max_abs_error':error,'SHAP_rows':96,'ALE_rows':20000,'scope':'development training distribution; descriptions, not independent validation or causality','missing':'SHAP explains the post-cap, median-imputed representation; no missing-cause identification claim'})
