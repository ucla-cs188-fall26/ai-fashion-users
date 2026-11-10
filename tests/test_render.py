# smoke test: every suggestion for the sample datasets renders and exports to png
from pathlib import Path

import pytest

from detect import apply_types, detect_columns, load_csv
from render import render, to_png
from rules import GOALS, suggest

DATA = Path(__file__).resolve().parent.parent / "data"

SELECTIONS = [
    ("grades_by_major.csv", ["major", "gpa"]),
    ("grades_by_major.csv", ["gpa"]),
    ("grades_by_major.csv", ["major"]),
    ("grades_by_major.csv", ["major", "year"]),
    ("temperature_monthly.csv", ["month", "avg_temp_c"]),
    ("height_weight.csv", ["height_cm", "weight_kg"]),
]


def all_cases():
    for filename, names in SELECTIONS:
        df = load_csv(DATA / filename)
        info = {c["name"]: c for c in detect_columns(df)}
        sel = [info[n] for n in names]
        for goal in GOALS:
            for s in suggest(sel, goal)["suggested"]:
                yield pytest.param(apply_types(df, sel), s, id=f"{filename}-{'+'.join(names)}-{goal}-{s['figure']}")


def test_all_figure_types_are_covered():
    figs = {case.values[1]["figure"] for case in all_cases()}
    assert figs == {"bar", "grouped_bar", "line", "histogram", "box", "strip", "scatter", "pie", "stacked_bar"}


@pytest.mark.parametrize("df,suggestion", list(all_cases()))
def test_renders_and_exports(df, suggestion):
    png = to_png(render(df, suggestion), scale=1)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_median_export_uses_requested_aggregation():
    df = load_csv(DATA / 'grades_by_major.csv')
    info = {c['name']: c for c in detect_columns(df)}
    sel = [info['major'], info['gpa']]
    suggestion = suggest(sel, 'comparison', summary='median')['suggested'][0]
    chart = render(apply_types(df, sel), suggestion)
    assert chart.to_dict()['encoding']['y']['aggregate'] == 'median'
    assert to_png(chart, scale=1).startswith(b'\x89PNG')
