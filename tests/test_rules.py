from pathlib import Path

import pytest

from detect import detect_columns, load_csv
from rules import GOALS, suggest

DATA = Path(__file__).resolve().parent.parent / "data"


def cols(filename, *names):
    info = {c["name"]: c for c in detect_columns(load_csv(DATA / filename))}
    return [info[n] for n in names]


def col(name, type_, n_unique, n_rows, **extra):
    return {"name": name, "type": type_, "n_unique": n_unique, "n_rows": n_rows, **extra}


def figures(result, key="suggested"):
    return [s["label"] for s in result[key]]


# ---------- core scenario on the sample datasets ----------

def test_grades_comparison_suggests_bar_first_and_rules_out_pie():
    r = suggest(cols("grades_by_major.csv", "major", "gpa"), "comparison")
    assert r["suggested"][0]["label"] == "Bar chart"
    assert r["suggested"][0]["agg"] == "mean"
    assert "Box plot" in figures(r)
    assert "Pie chart" in figures(r, "ruled_out")
    assert "Line chart" in figures(r, "ruled_out")


def test_grades_distribution():
    r = suggest(cols("grades_by_major.csv", "major", "gpa"), "distribution")
    assert figures(r)[:2] == ["Box plot", "Strip (dot) plot"]
    assert "Histogram" in figures(r, "ruled_out")


def test_temperature_trend_suggests_line():
    r = suggest(cols("temperature_monthly.csv", "month", "avg_temp_c"), "trend")
    top = r["suggested"][0]
    assert top["label"] == "Line chart"
    assert (top["x"], top["y"]) == ("month", "avg_temp_c")


def test_height_weight_relationship_suggests_scatter():
    r = suggest(cols("height_weight.csv", "height_cm", "weight_kg"), "relationship")
    assert figures(r) == ["Scatter plot"]
    assert "Line chart" in figures(r, "ruled_out")


# ---------- hard constraints ----------

def test_bar_ruled_out_past_20_groups():
    r = suggest([col("county", "categorical", 25, 500), col("pop", "numeric", 400, 500)], "comparison")
    assert "Bar chart" in figures(r, "ruled_out")


def test_pie_ruled_out_with_too_many_slices():
    r = suggest([col("state", "categorical", 14, 200)], "part_to_whole")
    why = next(x["why_not"] for x in r["ruled_out"] if x["label"] == "Pie chart")
    assert "14 slices" in why
    assert "Stacked bar (100%)" in figures(r, "ruled_out")  # 14 > 10 segments
    assert r["message"]


def test_pie_ruled_out_with_negative_values():
    r = suggest([col("dept", "categorical", 3, 3), col("profit", "numeric", 3, 3, min=-5.0)], "part_to_whole")
    assert "Pie chart" in figures(r, "ruled_out")


def test_line_ruled_out_for_categorical_x_mentions_override():
    r = suggest([col("year", "categorical", 4, 120), col("gpa", "numeric", 87, 120)], "trend")
    why = next(x["why_not"] for x in r["ruled_out"] if x["label"] == "Line chart")
    assert "change its type" in why


def test_histogram_ruled_out_under_20_rows():
    r = suggest([col("score", "numeric", 15, 15)], "distribution")
    assert "Histogram" in figures(r, "ruled_out")
    assert "Strip (dot) plot" in figures(r)


def test_box_ruled_out_with_few_rows_per_group():
    r = suggest([col("lab", "categorical", 6, 12), col("yield", "numeric", 12, 12)], "distribution")
    assert "Box plot" in figures(r, "ruled_out")


def test_strip_ruled_out_past_500_rows():
    r = suggest([col("x", "numeric", 900, 1000)], "distribution")
    assert "Strip (dot) plot" in figures(r, "ruled_out")


def test_grouped_bar_ruled_out_past_8_categories():
    r = suggest([col("a", "categorical", 9, 100), col("b", "categorical", 3, 100)], "comparison")
    assert "Grouped bar chart" in figures(r, "ruled_out")


# ---------- soft constraints ----------

def test_bar_score_lowered_past_10_groups():
    few = suggest([col("g", "categorical", 5, 100)], "comparison")["suggested"][0]
    many = suggest([col("g", "categorical", 15, 100)], "comparison")["suggested"][0]
    assert many["score"] < few["score"]
    assert "crowded" in many["why"]


def test_line_score_lowered_with_few_time_points():
    r = suggest([col("d", "date", 3, 3), col("v", "numeric", 3, 3)], "trend")
    line = next(s for s in r["suggested"] if s["label"] == "Line chart")
    assert line["score"] < 0.95


# ---------- edge cases + invariants ----------

def test_relationship_with_two_categories_explains_what_is_needed():
    r = suggest([col("a", "categorical", 3, 50), col("b", "categorical", 4, 50)], "relationship")
    assert r["suggested"] == []
    assert "two number columns" in r["message"]
    assert "Scatter plot" in figures(r, "ruled_out")


def test_box_not_suggested_for_comparison_without_groups():
    r = suggest([col("gpa", "numeric", 87, 120)], "comparison")
    assert "Box plot" not in figures(r)
    assert "Box plot" in figures(r, "ruled_out")


def test_no_columns():
    assert suggest([], "comparison")["message"]


@pytest.mark.parametrize("goal", GOALS)
@pytest.mark.parametrize("selection", [
    ("grades_by_major.csv", "major", "gpa"),
    ("grades_by_major.csv", "gpa"),
    ("grades_by_major.csv", "major", "year"),
    ("temperature_monthly.csv", "month", "avg_temp_c"),
    ("height_weight.csv", "height_cm", "weight_kg"),
])
def test_every_result_has_explanations(goal, selection):
    r = suggest(cols(*selection), goal)
    assert all(s["why"] for s in r["suggested"])
    assert all(s["why_not"] for s in r["ruled_out"])
    assert r["suggested"] or r["message"]
    scores = [s["score"] for s in r["suggested"]]
    assert scores == sorted(scores, reverse=True)
