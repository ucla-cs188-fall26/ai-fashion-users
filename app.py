# streamlit ui: wires detect -> rules -> render together.
# each step is its own function so teammates can edit different steps without collisions.
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import vl_convert as vlc

from claims import Finding, caption, check
from detect import TYPES, apply_types, detect_columns, load_csv
from finding import suggest_for_finding
from render import render, render_finding, sentence
from rules import GOAL_DESCRIPTIONS, GOAL_LABELS, GOALS, suggest
from sources import cite

DATA_DIR = Path(__file__).resolve().parent / "data"
NO_SAMPLE = "(choose a sample)"

TYPE_HELP = {
    "categorical": "Categorical: labels or groups (e.g. major, yes/no, ratings 1-5)",
    "numeric": "Numeric: measured amounts you can average (e.g. GPA, height)",
    "date": "Date: points in time (e.g. 2024-03-01)",
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

    st.caption(f"**{source}**: {len(df)} rows, {len(df.columns)} columns. Here are the first few rows:")
    st.dataframe(df.head(8), hide_index=True)
    return df, source


# ---------- step 2: columns + type override ----------

def step_columns(df: pd.DataFrame, source: str):
    detected = {c["name"]: c for c in detect_columns(df)}

    with st.expander("What we detected for every column", expanded=False):
        st.dataframe(
            pd.DataFrame([{"column": c["name"], "type": c["type"], "unique values": c["n_unique"]}
                          for c in detected.values()]),
            hide_index=True,
        )

    picked = st.multiselect(
        "Which columns hold the finding you want to show?",
        list(detected), max_selections=2, key=f"cols_{source}",
        placeholder="Pick one or two columns",
    )
    if not picked:
        st.info("Pick at least one column, for example a group column (like major) and a number column (like GPA).")
        return None, None

    st.caption("We guessed each column's type. If a guess is wrong, change it: the suggestions depend on it.")
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
            st.warning(f"None of the values in '{o['name']}' could be read as {o['type']}. Try a different type.")
            return None, None
        if info["n_rows"] < len(df):
            st.caption(f"Note: {len(df) - info['n_rows']} rows in '{o['name']}' are empty or couldn't be read as "
                       f"{o['type']}, so they're skipped.")
        selected.append(info)
    return selected, typed


# ---------- step 3: goal ----------

def step_goal():
    labels = {
        "comparison": "Compare groups",
        "trend": "Show change over time",
        "distribution": "Understand how values are spread out",
        "relationship": "Explore a relationship between two measurements",
        "part_to_whole": "Show how a whole breaks into parts",
    }
    return st.radio(
        "Your question", GOALS, format_func=lambda g: labels[g],
        captions=[sentence(GOAL_DESCRIPTIONS[g]) for g in GOALS],
        index=None, key="goal", label_visibility="collapsed",
    )


def sentences(text):
    # the rule table's explanations are written in lowercase; show them as proper sentences.
    # capitalizes the first letter and each letter after ". " except after "e.g." / "i.e."
    text = sentence(text.replace("_", " "))  # column names read as words: study_hours_per_week
    return re.sub(r"(?<!e\.g)(?<!i\.e)([.!?] )([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def redirect_goal(goal, selected):
    # some goal + column combinations are really a different question. instead of a dead end,
    # explain the mismatch and answer the question the columns can actually support.
    names = lambda t: [c["name"].replace("_", " ") for c in selected if c["type"] == t]
    cats, nums, dates = names("categorical"), names("numeric"), names("date")
    to, why = None, None
    if goal == "comparison" and len(nums) == 2:
        to, why = "relationship", (f"Your two columns, {nums[0]} and {nums[1]}, are both measurements of the same rows, so "
                                   f"comparing them means asking whether one goes up or down with the other. That's a relationship.")
    elif goal == "relationship" and len(cats) == 1 and len(nums) == 1:
        to, why = "comparison", (f"{cats[0].capitalize()} is a set of groups, so a relationship between it and {nums[0]} means "
                                 f"comparing {nums[0]} across those groups. That's a comparison.")
    elif goal in ("comparison", "relationship") and len(dates) == 1 and len(nums) == 1:
        to, why = "trend", (f"{dates[0].capitalize()} is time, so comparing {nums[0]} across it means asking how {nums[0]} "
                            f"changes over time. That's a trend.")
    elif goal == "distribution" and len(nums) == 2:
        to, why = "relationship", (f"A spread is about one measurement at a time. To see how {nums[0]} and {nums[1]} are spread "
                                   f"together, a relationship figure shows both; to see one on its own, pick just that column.")
    if to:
        st.info(why + " Here are figures for that question instead.")
        return to
    return goal


def show_sources(sources):
    # one line per source; links open the paper
    lines = [f"- [{x['text']}]({x['url']})" if x["url"] else f"- {x['text']}" for x in sources]
    st.markdown("\n".join(lines))


# ---------- finding: the student states what they want to show ----------

NOT_SURE = "not sure"


def step_finding(typed, cat, num, source):
    st.subheader("State your finding (optional)")
    st.caption("Pick the two groups your finding is about. Not sure which is higher? Leave it as "
               "\"not sure\" and the data will tell you.")
    groups = sorted(typed[cat].dropna().astype(str).unique())
    left, mid, right = st.columns([2, 2, 2])
    a = left.selectbox("Group", [None] + groups, key=f"find_a_{source}", placeholder="Choose a group",
                       format_func=lambda g: "Choose a group" if g is None else g)
    direction = mid.selectbox(
        "Compared with", ["higher", "lower", NOT_SURE], index=2, key=f"find_dir_{source}",
        format_func=lambda d: {"higher": f"has a higher average {num} than",
                               "lower": f"has a lower average {num} than",
                               NOT_SURE: f"(not sure how its average {num} compares to)"}[d])
    b = right.selectbox("Other group", [None] + [g for g in groups if g != a], key=f"find_b_{source}",
                        format_func=lambda g: "Choose a group" if g is None else g)
    if a is None or b is None:
        st.caption("Or skip this and browse suitable charts below.")
        return None
    return Finding(measure=num, group_col=cat, a=a, b=b, direction=None if direction == NOT_SURE else direction)


def step_finding_results(typed, finding, source):
    st.header("4. Your finding and figure")
    try:
        result = check(typed, finding)
    except ValueError as e:
        st.error(str(e))
        return
    box = {"supported": st.success, "found": st.success, "contradicted": st.error, "unclear": st.warning}[result["status"]]
    box(result["headline"])
    st.caption(result["detail"])
    if result["small_n"]:
        st.caption("Heads up: with fewer than 10 values in a group, the interval is rough. Treat it as a first look.")
    with st.expander("How we checked this"):
        st.markdown(
            f"We compared the average {finding.measure} of {finding.a} and {finding.b} and computed a 95% confidence "
            "interval for the gap using Welch's t, a standard method that doesn't assume both groups vary equally. "
            "If the whole interval is on one side of zero, the data supports a difference in that direction "
            "(the same as a two-sided Welch's t-test at the 0.05 level). We also report Cohen's d, the gap measured "
            "in units of how spread out the values are (0.2 small, 0.5 medium, 0.8 large, by convention).\n\n"
            "This is a first check, not a full analysis: it compares two averages, assumes the values are "
            "independent, and doesn't adjust for other variables. Checking many pairs one after another raises the "
            "chance of a fluke, so decide on your finding before you check it.")
        show_sources(cite("tea", "hesterberg"))

    n_groups = typed[finding.group_col].nunique()
    plan = suggest_for_finding(result, n_groups)
    labels = [s["label"] for s in plan["suggested"]]
    choice = st.radio("Figures that show this finding", labels, horizontal=True,
                      key=f"find_fig_{source}_{finding.a}_{finding.b}")
    chosen = plan["suggested"][labels.index(choice)]
    show_others = n_groups > 2 and st.checkbox(f"Also show the other {n_groups - 2} groups (in gray)",
                                               key=f"find_others_{source}")
    with st.container(border=True):
        st.subheader(chosen["label"])
        if chosen is plan["suggested"][0]:
            st.caption("RECOMMENDED · built around your finding")
        if result["status"] == "contradicted":
            st.caption("The title states what your data shows, not your original claim.")
        left = right = st.container()  # stacked: chart, then explanation
        with left:
            chart = render_finding(typed, result, chosen["figure"], show_others, plan["show_points"])
            st.altair_chart(chart, theme=None)
        with right:
            st.markdown("**Why it fits your finding**")
            st.write(chosen["why"])
            st.markdown("**What it emphasizes**")
            st.write(chosen["emphasis"])
            st.markdown("**Keep in mind**")
            st.write(chosen["limit"])
        st.markdown("**Suggested caption** (every figure needs one)")
        st.code(caption(result, chosen["figure"], plan["show_points"]), language=None, wrap_lines=True)
        with st.expander("Where these rules come from"):
            show_sources(chosen["sources"] + cite("kong", "rougier", "wong"))
        try:
            st.download_button("Download this figure as PNG", png_bytes(chart.to_json()),
                               file_name=f"{chosen['figure']}.png", mime="image/png", type="primary")
        except Exception as e:
            st.error(f"PNG export is unavailable: {e}")
    with st.expander("Why some other charts do not fit"):
        for r in plan["ruled_out"]:
            st.markdown(f"**{r['label']}:** {sentences(r['why_not'])}")
            st.caption("Source: " + "; ".join(x["text"] for x in r["sources"]))


def step_results(typed, selected, goal, intent=None, summary="mean"):
    result = suggest(selected, goal, intent=intent, summary=summary)
    st.header("4. Figures that fit")
    st.caption("Suggestions use rules about your question and data. They are guidance, not a validated ranking.")
    if result["message"]:
        st.warning(sentences(result["message"]))
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
            left = right = st.container()  # stacked: chart, then explanation
            with left:
                try:
                    chart = render(typed, chosen)
                    st.altair_chart(chart, width="stretch", theme=None)
                except Exception as e:
                    st.error(f"We couldn't draw this figure: {e}")
                    chart = None
            with right:
                st.markdown("**Why it fits your question**")
                st.write(sentences(chosen["why"]))
                st.markdown("**What it emphasizes**")
                st.write(chosen["emphasis"])
                st.markdown("**Keep in mind**")
                st.write(chosen["limit"])
            with st.expander("Where this rule comes from"):
                show_sources(chosen["sources"])
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
                    st.markdown(f"**{other['label']}:** {other['emphasis']} {other['limit']}")
        else:
            st.info("Only one chart fits the supported rules for this question. We won't add an unsuitable alternative just to fill a slot.")
    if result["ruled_out"]:
        with st.expander("Why some other charts do not fit", expanded=not suggestions):
            for r in result["ruled_out"]:
                st.markdown(f"**{r['label']}:** {sentences(r['why_not'])}")


def main():
    # one scrolling page with numbered steps and streamlit's default look (anusha's layout);
    # every feature from the later versions is kept.
    st.set_page_config(page_title="Figure Helper", page_icon="📊", layout="centered")
    st.title("Figure Helper")
    st.write("Tell us about your data and the finding you want to show. We'll check it against your data, "
             "suggest figures that fit, explain why, and explain why the others don't.")
    st.caption("Your data is processed by the app host, with no external AI service.")

    st.header("1. Your data")
    df, source = step_data()
    if df is None:
        return

    st.header("2. What do you want to show?")
    goal = step_goal()
    st.header("3. Pick 1 or 2 columns")
    selected, typed = step_columns(df, source)
    if not selected or goal is None:
        st.info("Choose what you want to show and your columns to see suitable figures.")
        return

    intent, summary, finding = None, "mean", None
    cats = [c for c in selected if c["type"] == "categorical"]
    nums = [c for c in selected if c["type"] == "numeric"]
    goal = redirect_goal(goal, selected)
    if goal == "comparison" and cats and nums:
        finding = step_finding(typed, cats[0]["name"], nums[0]["name"], source)
    if goal == "comparison" and cats and nums and finding is None:
        intent = st.radio("What matters most in this comparison?", ["typical", "variation", "individual"],
            format_func=lambda v: {"typical": "Typical values in each group", "variation": "How much values vary within each group", "individual": "Every individual observation"}[v],
            key=f"intent_{source}")
    if finding is None and nums and (goal == "trend" or (goal == "comparison" and cats)):
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

    if finding is not None:
        step_finding_results(typed, finding, source)
    else:
        step_results(typed, selected, goal, intent, summary)


if __name__ == "__main__":
    main()
