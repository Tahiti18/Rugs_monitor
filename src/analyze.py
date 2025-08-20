import os
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import acf

from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./rugs.db")

def load_df():
    with sqlite3.connect(DB_PATH) as c:
        df = pd.read_sql_query("SELECT round_id, timestamp, bust_multiplier FROM rounds ORDER BY id ASC", c)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df

def runs_test(series):
    # Wald–Wolfowitz runs test on above/below median
    median = np.median(series)
    signs = np.where(series >= median, 1, 0)
    n1 = signs.sum()
    n2 = len(signs) - n1
    runs = 1 + np.sum(signs[1:] != signs[:-1])
    mean_r = 1 + 2*n1*n2/(n1+n2)
    var_r = (2*n1*n2*(2*n1*n2 - n1 - n2))/(((n1+n2)**2)*(n1+n2-1))
    z = (runs - mean_r) / np.sqrt(var_r) if var_r > 0 else 0.0
    p = 2*(1-stats.norm.cdf(abs(z)))
    return dict(stat=z, pvalue=p, runs=int(runs), median=float(median))

def autocorr_check(series, lags=20):
    # Autocorrelation function on raw multipliers and log multipliers
    ac_raw = acf(series, nlags=lags, fft=True)
    ac_log = acf(np.log(series.clip(lower=1.0001)), nlags=lags, fft=True)
    return dict(ac_raw=ac_raw.tolist(), ac_log=ac_log.tolist())

def tail_exceedance(df, thresholds=(2.0, 10.0, 50.0)):
    out = {}
    n = len(df)
    for t in thresholds:
        out[str(t)] = {
            "count": int((df['bust_multiplier'] >= t).sum()),
            "freq": float((df['bust_multiplier'] >= t).mean()),
            "n": int(n)
        }
    return out

def ks_against_empirical(df):
    # Compare to exponential-like tail via log-transformed linearity (sanity only).
    # We avoid assuming a specific theoretical distribution; we test uniformity after applying PIT by rank.
    x = df['bust_multiplier'].values
    ranks = stats.rankdata(x, method='average')
    u = ranks / (len(x)+1.0)  # pseudo-uniform
    d, p = stats.kstest(u, 'uniform')
    return dict(ks_stat=float(d), pvalue=float(p))

if __name__ == "__main__":
    df = load_df()
    if df.empty:
        print("No data yet. Run the scraper first.")
        raise SystemExit(0)

    print(f"Loaded {len(df)} rounds. Time span: {df['timestamp'].min()} -> {df['timestamp'].max()}")

    rt = runs_test(df['bust_multiplier'].values)
    print("\nRuns test (independence above/below median):", rt)

    ac = autocorr_check(df['bust_multiplier'].values, lags=20)
    print("\nAutocorrelation (first 10 lags, raw):", [round(v,4) for v in ac['ac_raw'][:11]])
    print("Autocorrelation (first 10 lags, log):", [round(v,4) for v in ac['ac_log'][:11]])

    te = tail_exceedance(df, thresholds=(2.0, 10.0, 50.0))
    print("\nTail exceedance frequencies:", te)

    ks = ks_against_empirical(df)
    print("\nK-S test vs. pseudo-uniform (rank-based):", ks)

    # Simple anomaly heuristics (flag if looks suspicious, purely indicative):
    flags = []
    if abs(rt['stat']) > 2 and rt['pvalue'] < 0.05:
        flags.append("Non-random runs pattern (p<0.05)")
    if any(abs(v) > 0.2 for v in ac['ac_raw'][1:6]):
        flags.append("Strong lag-ACF on raw multipliers")
    if any(abs(v) > 0.2 for v in ac['ac_log'][1:6]):
        flags.append("Strong lag-ACF on log multipliers")
    if ks['pvalue'] < 0.01:
        flags.append("Distribution anomaly vs. rank-uniform (p<0.01)")

    print("\nHeuristic anomaly flags:", flags or ["none"])
