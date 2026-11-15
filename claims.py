# claim check: does the data support the student's stated finding?
# v1 compares the average of one measure between two independent groups.
#
# method: welch's t confidence interval for the gap in means (one of the tests tea selects
# among; it does not assume equal variances), plus cohen's d (tea reports it and recommends
# focusing on effect size). we use a t-interval rather than a bootstrap percentile interval
# because the percentile interval is too narrow for small samples (hesterberg 2015), and
# student datasets are often small. the verdict "the 95% interval excludes zero" is exactly
# a two-sided welch t-test at the 0.05 level.
# v2 (planned): tea-style assumption checks (normality, sample size) to switch to
# mann-whitney u when a t-interval isn't appropriate.
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

LEVEL = 0.95
SMALL_N = 10  # below this many values per group, t-intervals lean on normality (tea would check it)

DIRECTIONS = ("higher", "lower", None)


@dataclass
class Finding:
    measure: str  # numeric column, e.g. gpa
    group_col: str  # category column, e.g. major
    a: str  # first group named in the finding
    b: str  # second group
    direction: Optional[str] = None  # "higher" / "lower" (a compared to b), or None if not sure


def size_label(d: float) -> str:
    # cohen's conventions (0.2 / 0.5 / 0.8). cohen himself called these rough conventions.
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


def _values(df: pd.DataFrame, group_col: str, measure: str, group) -> np.ndarray:
    s = df.loc[df[group_col].astype(str) == str(group), measure]
    return pd.to_numeric(s, errors="coerce").dropna().to_numpy(dtype=float)


def welch_interval(xa: np.ndarray, xb: np.ndarray, level: float = LEVEL) -> tuple[float, float, float]:
    # gap in means with a welch t interval (welch-satterthwaite degrees of freedom)
    va, vb = xa.var(ddof=1) / len(xa), xb.var(ddof=1) / len(xb)
    gap = xa.mean() - xb.mean()
    se = np.sqrt(va + vb)
    if se == 0:
        return float(gap), float(gap), float(gap)
    df = (va + vb) ** 2 / (va ** 2 / (len(xa) - 1) + vb ** 2 / (len(xb) - 1))
    t = stats.t.ppf(0.5 + level / 2, df)
    return float(gap), float(gap - t * se), float(gap + t * se)


def mean_interval(x: np.ndarray, level: float = LEVEL) -> tuple[float, float]:
    # t interval for one group's mean
    if len(x) < 2:
        return float(x[0]), float(x[0])
    half = stats.t.ppf(0.5 + level / 2, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return float(x.mean() - half), float(x.mean() + half)


def cohens_d(xa: np.ndarray, xb: np.ndarray) -> float:
    na, nb = len(xa), len(xb)
    pooled_var = ((na - 1) * xa.var(ddof=1) + (nb - 1) * xb.var(ddof=1)) / (na + nb - 2)
    if pooled_var <= 0:
        return float("nan")
    return float((xa.mean() - xb.mean()) / np.sqrt(pooled_var))


def group_intervals(df: pd.DataFrame, group_col: str, measure: str, groups: list) -> pd.DataFrame:
    # mean and 95% t interval of the mean for each group, used to draw dots with interval lines
    rows = []
    for g in groups:
        x = _values(df, group_col, measure, g)
        if len(x) == 0:
            continue
        lo, hi = mean_interval(x)
        rows.append({group_col: str(g), "mean": x.mean(), "low": lo, "high": hi, "n": len(x)})
    return pd.DataFrame(rows)


def check(df: pd.DataFrame, f: Finding) -> dict:
    # returns everything the ui and the figure need: numbers, a verdict, and plain-language text
    if f.direction not in DIRECTIONS:
        raise ValueError("direction must be 'higher', 'lower', or None")
    if str(f.a) == str(f.b):
        raise ValueError("pick two different groups to compare.")
    xa, xb = _values(df, f.group_col, f.measure, f.a), _values(df, f.group_col, f.measure, f.b)
    if len(xa) < 2 or len(xb) < 2:
        raise ValueError(f"each group needs at least 2 values of {f.measure} to compare "
                         f"({f.a}: {len(xa)}, {f.b}: {len(xb)}).")

    gap, low, high = welch_interval(xa, xb)
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
        text = f"no clear difference in average {f.measure} between {f.a} and {f.b}"
    else:
        text = f"{f.a} has a {data_says} average {f.measure} than {f.b} (by {abs(gap):.2f})"
    return text[0].upper() + text[1:]


def _headline(f: Finding, status: str, data_says: str) -> str:
    claimed = f"{f.a} has a {f.direction} average {f.measure} than {f.b}" if f.direction else None
    if status == "supported":
        return f"Your data supports this: {claimed}."
    if status == "contradicted":
        return (f"Your data shows the opposite: {f.a} has a {data_says} average {f.measure} than {f.b}, "
                f"not {f.direction}.")
    if status == "found":
        return f"Your data shows that {f.a} has a {data_says} average {f.measure} than {f.b}."
    # unclear: absence of evidence, not evidence of no difference
    if claimed:
        return (f"Your data can't tell these groups apart yet, so it doesn't support \"{claimed}\". "
                f"The true gap could plausibly be zero or go either way.")
    return f"Your data can't tell {f.a} and {f.b} apart on average {f.measure} yet."


def _detail(f, gap, low, high, d, na, nb) -> str:
    return (f"Average {f.measure}: {f.a} minus {f.b} = {gap:+.2f} "
            f"(95% confidence interval {low:+.2f} to {high:+.2f}). "
            f"Gap size (Cohen's d) = {d:+.2f}, {size_label(d)}. "
            f"Based on {na} values for {f.a} and {nb} for {f.b}.")


def caption(result: dict, figure: str, show_points: bool) -> str:
    # a ready-to-use figure caption: what the marks mean, the sample sizes, and the numbers.
    # captions are not optional (rougier et al. 2014), and error bars must say what they show
    # (cumming & finch 2005).
    f = result["finding"]
    if figure == "dot_ci":
        marks = (f"Each small dot is one value of {f.measure}; large dots" if show_points else "Dots")
        marks += f" show the average for each {f.group_col}, and lines show 95% confidence intervals for those averages."
    else:
        marks = f"Bars show the average {f.measure} for each {f.group_col}."
    return (f"{marks} {f.a}: n = {result['n_a']}; {f.b}: n = {result['n_b']}. "
            f"Difference in averages ({f.a} minus {f.b}) = {result['gap']:.2f}, "
            f"95% CI [{result['low']:.2f}, {result['high']:.2f}] (Welch's t), Cohen's d = {result['d']:.2f}.")
