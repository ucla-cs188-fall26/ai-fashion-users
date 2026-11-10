# streamlit ui: wires detect -> rules -> render together.
# each step is its own function so teammates can edit different steps without collisions.
from pathlib import Path

import pandas as pd
import streamlit as st
import vl_convert as vlc

from detect import TYPES, apply_types, detect_columns, load_csv
from render import render
from rules import GOAL_DESCRIPTIONS, GOAL_LABELS, GOALS, suggest

DATA_DIR = Path(__file__).resolve().parent / "data"
NO_SAMPLE = "(choose a sample)"

TYPE_HELP = {
    "categorical": "categorical: labels or groups (e.g. major, yes/no, ratings 1-5)",
    "numeric": "numeric: measured amounts you can average (e.g. gpa, height)",
    "date": "date: points in time (e.g. 2024-03-01)",
}


@st.cache_data(show_spinner=False)
def png_bytes(chart_json: str) -> bytes:
    # cached on the chart spec so reruns don't re-export every chart
    return vlc.vegalite_to_png(chart_json, scale=2)


@st.cache_data(show_spinner=False)
def load_sample(name: str) -> pd.DataFrame:
    return load_csv(DATA_DIR / name)


def match_label(score: float) -> str:
    if score >= 0.85:
        return "strong match"
    if score >= 0.65:
        return "good match"
    return "okay match"


# ---------- step 1: data ----------

def step_data():
    st.header("1. Your data")
    left, right = st.columns(2)
    with left:
        uploaded = st.file_uploader("upload a csv", type=["csv"])
    with right:
        samples = [NO_SAMPLE] + sorted(p.name for p in DATA_DIR.glob("*.csv"))
        sample = st.selectbox("or try a sample dataset", samples)

    try:
        if uploaded is not None:
            df, source = load_csv(uploaded), uploaded.name
        elif sample != NO_SAMPLE:
            df, source = load_sample(sample), sample
        else:
            st.info("upload a csv or pick a sample dataset to get started.")
            return None, None
    except ValueError as e:
        st.error(str(e))
        return None, None

    st.caption(f"**{source}**: {len(df)} rows, {len(df.columns)} columns. here are the first few rows:")
    st.dataframe(df.head(8), hide_index=True)
    return df, source


# ---------- step 2: columns + type override ----------

def step_columns(df: pd.DataFrame, source: str):
    st.header("2. Pick 1 or 2 columns")
    detected = {c["name"]: c for c in detect_columns(df)}

    with st.expander("what we detected for every column", expanded=False):
        st.dataframe(
            pd.DataFrame([{"column": c["name"], "type": c["type"], "unique values": c["n_unique"]}
                          for c in detected.values()]),
            hide_index=True,
        )

    picked = st.multiselect(
        "which columns hold the finding you want to show?",
        list(detected), max_selections=2, key=f"cols_{source}",
        placeholder="pick one or two columns",
    )
    if not picked:
        st.info("pick at least one column. for example, a group column (like major) and a number column (like gpa).")
        return None, None

    st.caption("we guessed each column's type. if a guess is wrong, change it: the suggestions depend on it.")
    overrides = []
    for name in picked:
        c1, c2 = st.columns([1, 2])
        c1.markdown(f"**{name}**")
        t = c2.selectbox(
            f"type of {name}", TYPES, index=TYPES.index(detected[name]["type"]),
            format_func=lambda t: TYPE_HELP[t], key=f"type_{source}_{name}", label_visibility="collapsed",
        )
        overrides.append({"name": name, "type": t})

    typed = apply_types(df, overrides)
    # recompute counts on the converted data, but keep the user's chosen type
    stats = {c["name"]: c for c in detect_columns(typed[picked])}
    selected = []
    for o in overrides:
        info = {**stats[o["name"]], "type": o["type"]}
        if info["n_rows"] == 0:
            st.warning(f"none of the values in '{o['name']}' could be read as {o['type']}. try a different type.")
            return None, None
        if info["n_rows"] < len(df):
            st.caption(f"note: {len(df) - info['n_rows']} rows in '{o['name']}' are empty or couldn't be read as "
                       f"{o['type']}, so they're skipped.")
        selected.append(info)
    return selected, typed


# ---------- step 3: goal ----------

def step_goal():
    st.header("3. What do you want to show?")
    return st.radio(
        "pick the kind of finding",
        GOALS, format_func=lambda g: GOAL_LABELS[g],
        captions=[GOAL_DESCRIPTIONS[g] for g in GOALS],
        index=None, label_visibility="collapsed",
    )


# ---------- step 4: results ----------

def step_results(typed: pd.DataFrame, selected: list[dict], goal: str):
    st.header("4. Figures that fit")
    result = suggest(selected, goal)

    if result["message"]:
        st.warning(result["message"])

    for i, s in enumerate(result["suggested"], start=1):
        with st.container(border=True):
            badge = " · our top pick" if i == 1 else ""
            st.subheader(f"{i}. {s['label']}")
            st.caption(f"{match_label(s['score'])}{badge}")
            try:
                chart = render(typed, s)
            except Exception as e:  # keep the explanation visible even if drawing fails
                st.error(f"we couldn't draw this one ({e}).")
                chart = None
            if chart is not None:
                st.altair_chart(chart)
            st.markdown(f"**Why this fits:** {s['why']}")
            if chart is not None:
                try:
                    st.download_button(
                        "download as png", data=png_bytes(chart.to_json()),
                        file_name=f"{s['figure']}_{'_'.join(c['name'] for c in selected)}.png",
                        mime="image/png", key=f"dl_{i}_{s['label']}",
                    )
                except Exception as e:
                    st.caption(f"png export isn't available right now ({e}).")

    if result["ruled_out"]:
        with st.expander(f"Figures we ruled out and why ({len(result['ruled_out'])})",
                         expanded=not result["suggested"]):
            for r in result["ruled_out"]:
                st.markdown(f"**{r['label']}:** {r['why_not']}")


def main():
    st.set_page_config(page_title="Figure Helper", page_icon="📊", layout="centered")
    st.title("Figure Helper")
    st.write("tell us about your data and the finding you want to show, and we'll suggest figures "
             "that fit, explain why, and explain why the others don't.")

    df, source = step_data()
    if df is None:
        return
    selected, typed = step_columns(df, source)
    if not selected:
        return
    goal = step_goal()
    if goal is None:
        st.info("pick what you want to show to see suggestions.")
        return
    step_results(typed, selected, goal)


if __name__ == "__main__":
    main()
