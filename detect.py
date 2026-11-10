# column type detection: categorical, numeric, or date
import warnings

import pandas as pd

TYPES = ["categorical", "numeric", "date"]

# numeric columns with this many unique values or fewer are treated as categories (e.g. ratings 1-5)
MAX_NUMERIC_CATEGORIES = 10
# share of non-empty values that must parse as dates for a text column to count as a date
DATE_PARSE_THRESHOLD = 0.9


def load_csv(file) -> pd.DataFrame:
    # reads a csv (path or uploaded file) and drops fully empty rows/columns.
    # raises ValueError with a friendly message if it can't be read.
    try:
        df = pd.read_csv(file)
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)
        df = pd.read_csv(file, encoding="latin-1")
    except Exception as e:
        raise ValueError(f"we couldn't read that file as a csv ({e}).") from e
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.empty:
        raise ValueError("that file doesn't seem to have any data in it.")
    return df


def _looks_like_dates(s: pd.Series) -> bool:
    values = s.dropna().astype(str)
    if values.empty:
        return False
    # plain numbers like "2019" or "3.5" shouldn't be read as dates
    if values.str.fullmatch(r"-?\d+(\.\d+)?").mean() > 0.5:
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    return parsed.notna().mean() >= DATE_PARSE_THRESHOLD


def detect_type(s: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    if pd.api.types.is_bool_dtype(s):
        return "categorical"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric" if s.nunique(dropna=True) > MAX_NUMERIC_CATEGORIES else "categorical"
    if _looks_like_dates(s):
        return "date"
    return "categorical"


def detect_columns(df: pd.DataFrame) -> list[dict]:
    # one dict per column: {"name", "type", "n_unique", "n_rows"}, plus "min" when the
    # column holds numbers (rules use it to spot negatives, which can't be parts of a whole)
    out = []
    for col in df.columns:
        info = {
            "name": str(col),
            "type": detect_type(df[col]),
            "n_unique": int(df[col].nunique(dropna=True)),
            "n_rows": int(df[col].notna().sum()),
        }
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and s.notna().any():
            info["min"] = float(s.min())
        out.append(info)
    return out


def apply_types(df: pd.DataFrame, columns: list[dict]) -> pd.DataFrame:
    # returns a copy of df with each listed column converted to its (possibly overridden) type,
    # so charts treat it the way the user asked
    out = df.copy()
    for c in columns:
        name, t = c["name"], c["type"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if t == "date":
                out[name] = pd.to_datetime(out[name], errors="coerce", format="mixed")
            elif t == "numeric":
                out[name] = pd.to_numeric(out[name], errors="coerce")
            else:
                out[name] = out[name].astype(str).where(out[name].notna())
    return out
