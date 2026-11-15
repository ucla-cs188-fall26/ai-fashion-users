# claim check: does the data support the student's stated finding?
# v1 compares the average of one measure between two groups.
# method: bootstrap 95% interval for the gap in means (tea's own fallback when no
# standard test fits) plus cohen's d (tea reports it and recommends focusing on effect size).
# v2 (planned): tea-style assumption checks to pick student's t, welch's t, or mann-whitney u.
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

N_BOOT = 10_000
SEED = 188  # fixed so the same data always gives the same interval
SMALL_N = 10  # below this many values per group, intervals are rough

DIRECTIONS = ("higher", "lower", None)


@dataclass
class Finding:
    measure: str  # numeric column, e.g. gpa
    group_col: str  # category column, e.g. major
    a: str  # first group named in the finding
    b: str  # second group
    direction: Optional[str] = None  # "higher" / "lower" (a compared to b), or None if not sure


def size_label(d: float) -> str:
    # cohen's conventions (0.2 / 0.5 / 0.8). conventions, not findings.
    if np.isnan(d):
        return "unknown"
    d = abs(d)
    if d < 0.2:
        return "negligible"
    if d < 0.5:
        return "small"
    if d < 0.8:
        return "medium"
    return "large"


def _values(df: pd.DataFrame, f: Finding, group: str) -> np.ndarray:
    s = df.loc[df[f.group_col].astype(str) == str(group), f.measure]
    return pd.to_numeric(s, errors="coerce").dropna().to_numpy(dtype=float)


def _boot_means(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    # resample with replacement N_BOOT times and return the mean of each resample
    idx = rng.integers(0, len(x), size=(N_BOOT, len(x)))
    return x[idx].mean(axis=1)


def cohens_d(xa: np.ndarray, xb: np.ndarray) -> float:
    na, nb = len(xa), len(xb)
    pooled_var = ((na - 1) * xa.var(ddof=1) + (nb - 1) * xb.var(ddof=1)) / (na + nb - 2)
    if pooled_var <= 0:
        return float("nan")
    return float((xa.mean() - xb.mean()) / np.sqrt(pooled_var))


def group_intervals(df: pd.DataFrame, group_col: str, measure: str, groups: list) -> pd.DataFrame:
    # mean and bootstrap 95% interval of the mean for each group, used to draw dots with whiskers
    rng = np.random.default_rng(SEED)
    rows = []
    for g in groups:
        x = pd.to_numeric(df.loc[df[group_col].astype(str) == str(g), measure], errors="coerce").dropna().to_numpy(float)
        if len(x) == 0:
            continue
        if len(x) > 1:
            lo, hi = np.percentile(_boot_means(x, rng), [2.5, 97.5])
        else:
            lo = hi = x[0]
        rows.append({group_col: str(g), "mean": x.mean(), "low": lo, "high": hi, "n": len(x)})
    return pd.DataFrame(rows)


def check(df: pd.DataFrame, f: Finding) -> dict:
    # returns everything the ui and the figure need: numbers, a verdict, and plain-language text
    if f.direction not in DIRECTIONS:
        raise ValueError("direction must be 'higher', 'lower', or None")
    if str(f.a) == str(f.b):
        raise ValueError("pick two different groups to compare.")
    xa, xb = _values(df, f, f.a), _values(df, f, f.b)
    if len(xa) < 2 or len(xb) < 2:
        raise ValueError(f"each group needs at least 2 values of {f.measure} to compare "
                         f"({f.a}: {len(xa)}, {f.b}: {len(xb)}).")

    rng = np.random.default_rng(SEED)
    gaps = _boot_means(xa, rng) - _boot_means(xb, rng)
    gap = float(xa.mean() - xb.mean())
    low, high = (float(v) for v in np.percentile(gaps, [2.5, 97.5]))
    d = cohens_d(xa, xb)

    # what the data says on its own, regardless of the claim
    if low > 0:
        data_says = "higher"
    elif high < 0:
        data_says = "lower"
    else:
        data_says = "unclear"

    if data_says == "unclear":
        status = "unclear"
    elif f.direction is None:
        status = "found"
    elif f.direction == data_says:
        status = "supported"
    else:
        status = "contradicted"

    return {
        "finding": f,
        "mean_a": float(xa.mean()), "mean_b": float(xb.mean()),
        "n_a": len(xa), "n_b": len(xb),
        "gap": gap, "low": low, "high": high,
        "d": d, "size": size_label(d),
        "data_says": data_says, "status": status,
        "small_n": min(len(xa), len(xb)) < SMALL_N,
        "headline": _headline(f, status, data_says),
        "message": message(f, data_says, gap),
        "detail": _detail(f, gap, low, high, d, len(xa), len(xb)),
    }


def message(f: Finding, data_says: str, gap: float) -> str:
    # the one-sentence finding, used as the figure title (titles drive what readers remember)
    if data_says == "unclear":
        return f"No clear difference in average {f.measure} between {f.a} and {f.b}"
    return f"{f.a} has a {data_says} average {f.measure} than {f.b} (by {abs(gap):.2f})"


def _headline(f: Finding, status: str, data_says: str) -> str:
    claimed = f"{f.a} has a {f.direction} average {f.measure} than {f.b}" if f.direction else None
    if status == "supported":
        return f"Your data supports this: {claimed}."
    if status == "contradicted":
        return (f"Your data shows the opposite: {f.a} has a {data_says} average {f.measure} than {f.b}, "
                f"not {f.direction}.")
    if status == "found":
        return f"Your data shows that {f.a} has a {data_says} average {f.measure} than {f.b}."
    # unclear
    if claimed:
        return (f"Your data can't tell these groups apart yet, so it doesn't support \"{claimed}\". "
                f"The gap could plausibly be zero or go either way.")
    return f"Your data can't tell {f.a} and {f.b} apart on average {f.measure} yet."


def _detail(f, gap, low, high, d, na, nb) -> str:
    return (f"Average {f.measure}: {f.a} minus {f.b} = {gap:+.2f} "
            f"(95% interval {low:+.2f} to {high:+.2f}). "
            f"Gap size (Cohen's d) = {d:+.2f}, {size_label(d)}. "
            f"Based on {na} values for {f.a} and {nb} for {f.b}.")
