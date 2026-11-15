import numpy as np
import pandas as pd
import pytest
from scipy import stats

from claims import Finding, check, cohens_d, size_label
from finding import suggest_for_finding
from render import render_finding


def two_groups(mean_a, mean_b, n=30, sd=0.3, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "g": ["a"] * n + ["b"] * n,
        "y": np.r_[rng.normal(mean_a, sd, n), rng.normal(mean_b, sd, n)],
    })


def test_supported_when_data_agrees():
    r = check(two_groups(3.0, 3.5), Finding("y", "g", "a", "b", "lower"))
    assert r["status"] == "supported" and r["data_says"] == "lower"
    assert r["high"] < 0


def test_contradicted_when_data_disagrees():
    r = check(two_groups(3.0, 3.5), Finding("y", "g", "a", "b", "higher"))
    assert r["status"] == "contradicted"
    assert "opposite" in r["headline"]


def test_unclear_when_groups_overlap():
    r = check(two_groups(3.0, 3.02), Finding("y", "g", "a", "b", "higher"))
    assert r["status"] == "unclear"
    assert r["low"] < 0 < r["high"]
    assert r["message"].startswith("No clear difference")


def test_not_sure_lets_data_decide():
    r = check(two_groups(3.5, 3.0), Finding("y", "g", "a", "b", None))
    assert r["status"] == "found" and r["data_says"] == "higher"


def test_interval_matches_scipy_welch_and_verdict_matches_test():
    for mb in (3.05, 3.15, 3.3):
        df = two_groups(3.0, mb, n=15)
        r = check(df, Finding("y", "g", "a", "b", None))
        res = stats.ttest_ind(df[df.g == "a"].y, df[df.g == "b"].y, equal_var=False)
        ci = res.confidence_interval()
        assert r["low"] == pytest.approx(ci.low) and r["high"] == pytest.approx(ci.high)
        assert (r["status"] != "unclear") == (res.pvalue < 0.05)


def test_group_interval_matches_t_interval():
    from claims import group_intervals
    df = two_groups(3.0, 3.3, n=12)
    gi = group_intervals(df, "g", "y", ["a"]).iloc[0]
    x = df[df.g == "a"].y
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    assert gi["low"] == pytest.approx(lo) and gi["high"] == pytest.approx(hi)


def test_same_data_same_answer():
    df = two_groups(3.0, 3.1)
    f = Finding("y", "g", "a", "b", None)
    assert check(df, f)["low"] == check(df, f)["low"]


def test_cohens_d_and_labels():
    xa, xb = np.array([1.0, 2, 3, 4]), np.array([2.0, 3, 4, 5])
    assert cohens_d(xa, xb) == pytest.approx(-1 / np.std([1, 2, 3, 4], ddof=1))
    assert [size_label(v) for v in (0.1, 0.3, 0.6, 1.2)] == ["negligible", "small", "medium", "large"]


def test_rejects_bad_input():
    df = two_groups(3.0, 3.5)
    with pytest.raises(ValueError):
        check(df, Finding("y", "g", "a", "a", None))
    with pytest.raises(ValueError):
        check(df.head(31), Finding("y", "g", "a", "b", None))  # only 1 value in b


def test_showing_the_data_comes_first_bars_stay_available():
    for gap in (0.05, 1.5):
        plan = suggest_for_finding(check(two_groups(2.0, 2.0 + gap), Finding("y", "g", "a", "b", None)), 2)
        assert [s["figure"] for s in plan["suggested"]] == ["dot_ci", "bar_focus"]


def test_large_groups_hide_individual_points():
    big = suggest_for_finding(check(two_groups(2.0, 2.5, n=300), Finding("y", "g", "a", "b", None)), 2)
    assert big["show_points"] is False


def test_caption_states_marks_n_and_interval():
    from claims import caption
    r = check(two_groups(2.0, 3.5, n=20), Finding("y", "g", "a", "b", "lower"))
    text = caption(r, "dot_ci", True)
    assert "n = 20" in text and "95% CI" in text and "confidence intervals" in text


def test_every_suggestion_and_exclusion_names_a_source():
    plan = suggest_for_finding(check(two_groups(2.0, 3.5), Finding("y", "g", "a", "b", None)), 5)
    assert all(s["sources"] for s in plan["suggested"] + plan["ruled_out"])


@pytest.mark.parametrize("figure", ["bar_focus", "dot_ci"])
def test_finding_figures_render_with_message_title(figure):
    df = two_groups(2.0, 3.5)
    r = check(df, Finding("y", "g", "a", "b", "lower"))
    spec = render_finding(df, r, figure).to_dict()
    assert spec["title"]["text"] == r["message"]
    assert r["message"].startswith("a has a lower")  # data labels keep their own spelling
