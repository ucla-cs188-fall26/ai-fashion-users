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


# ---------- step 1: data ----------

def step_data():
    left, right = st.columns(2)
    with left:
        uploaded = st.file_uploader("Upload a CSV", type=["csv"])
    with right:
        samples = [NO_SAMPLE] + sorted(p.name for p in DATA_DIR.glob("*.csv"))
        sample = st.selectbox("Or try an example dataset", samples)

    try:
        if uploaded is not None:
            df, source = load_csv(uploaded), uploaded.name
        elif sample != NO_SAMPLE:
            df, source = load_sample(sample), sample
        else:
            st.info("Upload a CSV or choose an example dataset to get started.")
            return None, None
    except ValueError as e:
        st.error(str(e))
        return None, None

    st.caption(f"**{source}**: {len(df)} rows, {len(df.columns)} columns. here are the first few rows:")
    st.dataframe(df.head(8), hide_index=True)
    return df, source


# ---------- step 2: columns + type override ----------

def step_columns(df: pd.DataFrame, source: str):
    st.subheader("Choose the variables")
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
    st.subheader("What do you want to understand?")
    labels = {
        "comparison": "Compare groups",
        "trend": "Show change over time",
        "distribution": "Understand how values are spread out",
        "relationship": "Explore a relationship between two measurements",
        "part_to_whole": "Show how a whole breaks into parts",
    }
    return st.radio(
        "Your question", GOALS, format_func=lambda g: labels[g],
        captions=[GOAL_DESCRIPTIONS[g] for g in GOALS],
        index=None, key="goal", label_visibility="collapsed",
    )


def step_results(typed, selected, goal, intent=None, summary="mean"):
    result = suggest(selected, goal, intent=intent, summary=summary)
    st.header("3. Choose your figure")
    st.caption("Suggestions use rules about your question and data. They are guidance, not a validated ranking.")
    if result["message"]:
        st.warning(result["message"])
    suggestions = result["suggested"]
    if suggestions:
        labels = [s["label"] for s in suggestions]
        # A stable key per task preserves the choice while navigating back and forth.
        choice = st.radio("Compare suitable options", labels,
                          key="figure_" + str((goal, intent, summary, [(c["name"], c["type"]) for c in selected])),
                          horizontal=True)
        chosen = suggestions[labels.index(choice)]
        with st.container(border=True):
            st.subheader(chosen["label"])
            if chosen is suggestions[0]:
                st.caption("RECOMMENDED STARTING POINT · based on your current question")
            left, right = st.columns([2, 1])
            with left:
                try:
                    chart = render(typed, chosen)
                    st.altair_chart(chart, width="stretch", theme=None)
                except Exception as e:
                    st.error(f"We couldn't draw this figure: {e}")
                    chart = None
            with right:
                st.markdown("**Why it fits your question**")
                st.write(chosen["why"])
                st.markdown("**What it emphasizes**")
                st.write(chosen["emphasis"])
                st.markdown("**Keep in mind**")
                st.write(chosen["limit"])
            used = list(dict.fromkeys(c for c in (chosen.get("x"), chosen.get("y"), chosen.get("color")) if c))
            n = len(typed[used].dropna()) if used else len(typed)
            st.caption(f"Using {n} of {len(typed)} rows. {len(typed) - n} rows excluded because a selected value is missing or could not be read.")
            if chosen.get("agg"):
                st.caption("Summary used: " + {"mean": "average", "median": "median", "sum": "sum", "count": "row count"}[chosen["agg"]] + ".")
            if chart is not None:
                try:
                    st.download_button("Download this figure as PNG", png_bytes(chart.to_json()),
                                       file_name=f"{chosen['figure']}.png", mime="image/png", type="primary")
                except Exception as e:
                    st.error(f"PNG export is unavailable: {e}")
        alternatives = [s for s in suggestions if s is not chosen]
        if alternatives:
            with st.expander("How the alternatives differ"):
                for other in alternatives:
                    st.markdown(f"**{other['label']}** — {other['emphasis']} {other['limit']}")
        else:
            st.info("Only one chart fits the supported rules for this question. We won't add an unsuitable alternative just to fill a slot.")
    if result["ruled_out"]:
        with st.expander("Why some other charts do not fit", expanded=not suggestions):
            for r in result["ruled_out"]:
                st.markdown(f"**{r['label']}:** {r['why_not']}")


def go_to(stage):
    st.session_state.stage = stage


def main():
    st.set_page_config(page_title="MAD Scientists · Figure Helper", page_icon="📊", layout="wide")
    st.markdown("""<style>
    html, body, [data-testid="stApp"], [data-testid="stApp"] input,
    [data-testid="stApp"] button, [data-testid="stApp"] select,
    [data-testid="stApp"] textarea, [data-testid="stApp"] p,
    [data-testid="stApp"] h1, [data-testid="stApp"] h2,
    [data-testid="stApp"] h3 {font-family: Arial, Helvetica, sans-serif;}
    [data-testid="stHeader"] {display: none;}
    .block-container {max-width: 1200px; padding: 0 2.5rem 3rem;}
    .site-masthead {background: #24569b; color: white; width: 100vw;
        margin-left: calc(50% - 50vw); padding: 26px max(40px, calc((100vw - 1120px) / 2));
        display: flex; align-items: center; gap: 30px; box-sizing: border-box;}
    .site-brand {font-size: 19px; font-weight: 700; line-height: 1.25; letter-spacing: .01em;}
    .site-name {font-size: 30px; font-weight: 400; border-left: 2px solid #d9e3f2;
        padding-left: 30px; line-height: 1.4;}
    .st-key-stage {width: 100%; border-bottom: 5px solid #b5bec1; padding: 8px 0 18px; margin-bottom: 20px;}
    .st-key-stage [role="radiogroup"] {gap: 32px; flex-wrap: wrap;}
    .st-key-stage [role="radiogroup"] label {padding: 12px 0; margin: 0;}
    .st-key-stage [data-testid="stRadioOption"] > div > div:first-child {display: none;}
    .st-key-stage [role="radiogroup"] label p {font-size: 14px; letter-spacing: .09em;
        text-transform: uppercase; font-weight: 400; color: #42494e;}
    .st-key-stage label:has(input:checked) {box-shadow: 0 3px 0 #24569b;}
    .st-key-stage label:has(input:checked) p {color: #24569b; font-weight: 700;}
    .st-key-stage label:focus-within {outline: 2px solid #24569b; outline-offset: 4px;}
    h1 {font-size: 30px !important; font-weight: 400 !important; letter-spacing: 0 !important;}
    h2 {font-size: 23px !important; font-weight: 400 !important; letter-spacing: 0 !important;}
    h3 {font-size: 19px !important; font-weight: 600 !important;}
    [data-testid="stApp"] button {border-radius: 0 !important; min-height: 42px; box-shadow: none;}
    [data-testid="stExpander"], [data-testid="stExpander"] details,
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stAlertContainer"],
    [data-testid="stFileUploaderDropzone"], [data-testid="stDataFrame"],
    [data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="tag"] {
        border-radius: 0 !important; box-shadow: none !important;}
    [data-testid="stExpander"] {border-color: #c8cdd2;}
    [data-testid="stExpander"] summary {background: #f5f6f7; padding: 14px 18px;}
    [data-testid="stFileUploaderDropzone"] {background: #f5f6f7; border: 1px solid #c8cdd2;}
    [data-testid="stCaptionContainer"] {color: #596168;}
    @media (max-width: 640px) {
        .block-container {padding-left: 20px; padding-right: 20px;}
        .site-masthead {padding: 22px 20px; gap: 18px;}
        .site-brand {font-size: 15px;} .site-name {font-size: 23px; padding-left: 18px;}
        .st-key-stage [role="radiogroup"] {gap: 18px;}
        .st-key-stage [role="radiogroup"] label p {font-size: 12px; letter-spacing: .04em;}
    }
    </style>
<div class="site-masthead"><div class="site-brand">MAD<br>Scientists</div>
<div class="site-name">Figure Helper</div></div>
    """, unsafe_allow_html=True)
    stage = st.radio("Workflow navigation", ["1 · Your data", "2 · Your question", "3 · Your figure"],
                     key="stage", horizontal=True, label_visibility="collapsed")
    st.title("Choose a figure for your research")
    st.write("Explore suitable figures for your data and question, understand the tradeoffs, and download your choice.")
    st.caption("Revisit any step to revise your choices. Data is processed by the app host, with no external AI service.")
    # Keep widgets mounted in containers so Streamlit preserves choices between stages.
    data_panel = st.container()
    question_panel = st.container()
    figure_panel = st.container()
    with data_panel:
        if stage != "1 · Your data":
            st.caption("DATA · Select “Your data” above to change the dataset.")
        with st.expander("1. Your data", expanded=stage == "1 · Your data"):
            df, source = step_data()
    if df is None:
        return
    if stage == "1 · Your data":
        st.button("Continue to your question →", on_click=go_to, args=("2 · Your question",), type="primary")
    with question_panel:
        with st.expander("2. Your question", expanded=stage == "2 · Your question"):
            goal = step_goal()
            selected, typed = step_columns(df, source)
            if not selected or goal is None:
                st.info("Choose your question and variables to see suitable figures.")
                return
            intent, summary = None, "mean"
            cats = [c for c in selected if c["type"] == "categorical"]
            nums = [c for c in selected if c["type"] == "numeric"]
            if goal == "comparison" and cats and nums:
                intent = st.radio("What matters most in this comparison?", ["typical", "variation", "individual"],
                    format_func=lambda v: {"typical": "Typical values in each group", "variation": "How much values vary within each group", "individual": "Every individual observation"}[v],
                    key=f"intent_{source}")
            if nums and (goal == "trend" or (goal == "comparison" and cats)):
                summary = st.selectbox("If several rows share a group or time point, summarize them using", ["mean", "median"],
                    format_func=lambda v: "Average (mean)" if v == "mean" else "Median (middle value)", key=f"summary_{source}")
                st.caption("This choice affects summary charts. Dot and box plots still use the individual observations.")
            if goal == "trend" and len(nums) == 2:
                time = st.selectbox("Which variable represents ordered time?", [c["name"] for c in selected], key=f"time_{source}")
                confirmed = st.checkbox("I confirm this variable represents time, not an ID or an unrelated measurement.", key=f"time_confirm_{source}_{time}")
                if not confirmed:
                    st.info("Confirm the time variable before drawing a connected line.")
                    return
                selected = sorted(selected, key=lambda c: c["name"] != time)
            if stage != "3 · Your figure":
                st.button("See suitable figures →", on_click=go_to, args=("3 · Your figure",), type="primary")
    with figure_panel:
        step_results(typed, selected, goal, intent, summary)


if __name__ == "__main__":
    main()
