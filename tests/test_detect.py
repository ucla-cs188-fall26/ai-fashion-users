from pathlib import Path

import pandas as pd
import pytest

from detect import apply_types, detect_columns, load_csv

DATA = Path(__file__).resolve().parent.parent / "data"


def types_of(df):
    return {c["name"]: c["type"] for c in detect_columns(df)}


def test_grades_sample():
    t = types_of(load_csv(DATA / "grades_by_major.csv"))
    assert t["major"] == "categorical"
    assert t["gpa"] == "numeric"
    assert t["year"] == "categorical"  # 4 unique numeric codes


def test_temperature_sample_has_date():
    t = types_of(load_csv(DATA / "temperature_monthly.csv"))
    assert t["month"] == "date"
    assert t["avg_temp_c"] == "numeric"


def test_height_weight_sample():
    t = types_of(load_csv(DATA / "height_weight.csv"))
    assert t == {"height_cm": "numeric", "weight_kg": "numeric", "sex": "categorical"}


def test_small_integer_range_is_categorical():
    df = pd.DataFrame({"rating": [1, 2, 3, 4, 5] * 10})
    assert types_of(df)["rating"] == "categorical"


def test_bool_is_categorical():
    df = pd.DataFrame({"passed": [True, False] * 20})
    assert types_of(df)["passed"] == "categorical"


def test_year_numbers_are_not_dates():
    df = pd.DataFrame({"year": [str(y) for y in range(1990, 2020)]})
    assert types_of(df)["year"] == "categorical"


def test_mostly_unparseable_text_is_not_date():
    df = pd.DataFrame({"x": ["2020-01-01", "hello", "world", "foo", "bar"]})
    assert types_of(df)["x"] == "categorical"


def test_counts_and_rows():
    df = pd.DataFrame({"a": ["x", "y", None, "x"]})
    info = detect_columns(df)[0]
    assert info["n_unique"] == 2
    assert info["n_rows"] == 3


def test_apply_types_override():
    df = pd.DataFrame({"rating": [1, 2, 3], "when": ["2020-01-01", "2020-02-01", "2020-03-01"]})
    out = apply_types(df, [{"name": "rating", "type": "categorical"}, {"name": "when", "type": "date"}])
    assert out["rating"].tolist() == ["1", "2", "3"]
    assert pd.api.types.is_datetime64_any_dtype(out["when"])


def test_load_csv_bad_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("")
    with pytest.raises(ValueError):
        load_csv(p)
