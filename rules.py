# constraint rules + engine.
# each rule says what column types a figure needs, which goals it serves, hard constraints
# (fail -> ruled out) and soft constraints (fail -> lower score). every "why" / "why not"
# string comes straight from the constraint that passed or failed.
from dataclasses import dataclass, field
from typing import Callable, Optional

GOALS = ["comparison", "trend", "distribution", "relationship", "part_to_whole"]

GOAL_LABELS = {
    "comparison": "Comparison",
    "trend": "Trend over time",
    "distribution": "Distribution",
    "relationship": "Relationship",
    "part_to_whole": "Part-to-whole",
}

GOAL_DESCRIPTIONS = {
    "comparison": "how a number differs between groups (e.g. average gpa by major)",
    "trend": "how something changes over time (e.g. temperature by month)",
    "distribution": "how values are spread out: typical values, range, outliers",
    "relationship": "whether two measurements move together (e.g. height vs weight)",
    "part_to_whole": "how a total breaks down into pieces (e.g. share of students per major)",
}

# shown when nothing fits, so the user knows what to pick instead
GOAL_NEEDS = {
    "comparison": "comparison needs a category column (the groups), optionally plus a number column to compare, e.g. major + gpa.",
    "trend": "trend needs a date column (or an ordered number like year) plus a number column that changes over time, e.g. month + avg_temp_c.",
    "distribution": "distribution needs a number column, optionally plus a category column to split it into groups, e.g. gpa, or major + gpa.",
    "relationship": "relationship needs two number columns, e.g. height_cm + weight_kg. to see how a number differs across categories, try 'comparison' instead.",
    "part_to_whole": "part-to-whole needs a category column (the parts), optionally plus a number column to add up, e.g. major.",
}


# ---------- context about the selected columns ----------

@dataclass
class Ctx:
    cols: list
    goal: str = ""
    cats: list = field(default_factory=list)
    nums: list = field(default_factory=list)
    dates: list = field(default_factory=list)

    def __post_init__(self):
        for c in self.cols:
            {"categorical": self.cats, "numeric": self.nums, "date": self.dates}[c["type"]].append(c)

    @property
    def n_rows(self) -> int:
        return max((c["n_rows"] for c in self.cols), default=0)

    def shape(self) -> str:
        # e.g. "C", "N", "CN", "CC", "NN", "DN" (sorted so order doesn't matter)
        letters = {"categorical": "C", "numeric": "N", "date": "D"}
        return "".join(sorted(letters[c["type"]] for c in self.cols))


def _groups(ctx, roles) -> int:
    # number of groups in the column used for groups (x for bars/boxes, color for stacks)
    key = roles.get("group_col")
    return next((c["n_unique"] for c in ctx.cols if c["name"] == key), 0)


# ---------- rule definition ----------

@dataclass
class Rule:
    id: str
    figure: str  # what render.py draws
    label: str  # what the user sees
    goals: dict  # goal -> base score
    fit: Callable  # ctx -> roles dict, or a string explaining what's missing
    why: Callable  # (ctx, roles, goal) -> str
    hard: list = field(default_factory=list)  # (ctx, roles) -> reason str or None
    soft: list = field(default_factory=list)  # (ctx, roles) -> (penalty, note) or None
    wrong_for: dict = field(default_factory=dict)  # goal -> (ctx) -> reason str or None


# ---------- fit functions (which column plays which role) ----------

def fit_bar(ctx):
    s = ctx.shape()
    if s == "CN":
        cat, num = ctx.cats[0], ctx.nums[0]
        repeated = num["n_rows"] > cat["n_unique"]
        return {"x": cat["name"], "y": num["name"], "agg": "mean" if repeated else "sum", "group_col": cat["name"]}
    if s == "C":
        return {"x": ctx.cats[0]["name"], "y": None, "agg": "count", "group_col": ctx.cats[0]["name"]}
    return "bar charts need one category column (the groups), optionally with one number column."


def fit_grouped_bar(ctx):
    if ctx.shape() == "CC":
        a, b = sorted(ctx.cats, key=lambda c: -c["n_unique"])  # fewer groups go in the color
        return {"x": a["name"], "y": None, "color": b["name"], "agg": "count", "group_col": a["name"]}
    return "grouped bars need two category columns (e.g. major and year)."


def fit_line(ctx):
    s = ctx.shape()
    if s == "DN":
        d, n = ctx.dates[0], ctx.nums[0]
        return {"x": d["name"], "y": n["name"], "agg": "mean" if n["n_rows"] > d["n_unique"] else None, "group_col": d["name"]}
    if s == "NN":
        x, y = ctx.cols[0], ctx.cols[1]  # first picked column is the time axis
        return {"x": x["name"], "y": y["name"], "agg": "mean" if y["n_rows"] > x["n_unique"] else None, "group_col": x["name"]}
    if ctx.cats:
        name = ctx.cats[0]["name"]
        return (f"'{name}' is a category column, so its values have no natural order for a line to connect. "
                f"if it really is ordered (like years or months), change its type to date or numeric in step 2.")
    return "line charts need a date (or ordered number) column for the x-axis plus a number column to plot."


def fit_time_bar(ctx):
    if ctx.shape() == "DN":
        d, n = ctx.dates[0], ctx.nums[0]
        return {"x": d["name"], "y": n["name"], "agg": "mean", "group_col": d["name"]}
    return "bars over time need a date column plus a number column."


def fit_one_numeric_or_split(ctx):
    s = ctx.shape()
    if s == "CN":
        return {"x": ctx.cats[0]["name"], "y": ctx.nums[0]["name"], "group_col": ctx.cats[0]["name"]}
    if s == "N":
        return {"x": None, "y": ctx.nums[0]["name"], "group_col": None}
    return "this needs one number column, optionally with one category column to split it into groups."


def fit_box(ctx):
    # for comparison, a box needs groups to compare; a lone number column has nothing to compare against
    if ctx.goal == "comparison" and ctx.shape() == "N":
        return (f"to compare with box plots you need groups; add a category column (like major) "
                f"so each group gets its own box of {ctx.nums[0]['name']}.")
    return fit_one_numeric_or_split(ctx)


def fit_histogram(ctx):
    if ctx.shape() == "N":
        return {"x": ctx.nums[0]["name"], "y": None, "group_col": None}
    if ctx.shape() == "CN":
        return "a histogram shows one number column on its own; with groups, box or strip plots let you compare the groups side by side."
    return "histograms need one number column."


def fit_scatter(ctx):
    if ctx.shape() == "NN":
        return {"x": ctx.cols[0]["name"], "y": ctx.cols[1]["name"], "group_col": None}
    names = " and ".join(f"'{c['name']}'" for c in ctx.cols)
    return f"scatter plots need two number columns, but {names} {'is' if len(ctx.cols) == 1 else 'are'} not both numbers."


def fit_parts(ctx):
    s = ctx.shape()
    if s == "C":
        c = ctx.cats[0]
        return {"x": c["name"], "y": None, "agg": "count", "group_col": c["name"], "color": c["name"]}
    if s == "CN":
        c, n = ctx.cats[0], ctx.nums[0]
        return {"x": c["name"], "y": n["name"], "agg": "sum", "group_col": c["name"], "color": c["name"],
                "repeated": n["n_rows"] > c["n_unique"], "min": n.get("min")}
    return "this needs one category column (the parts), optionally with one number column to add up."


def fit_stacked(ctx):
    if ctx.shape() == "CC":
        a, b = sorted(ctx.cats, key=lambda c: -c["n_unique"])
        return {"x": a["name"], "y": None, "color": b["name"], "agg": "count", "group_col": b["name"], "normalize": True}
    roles = fit_parts(ctx)
    if isinstance(roles, dict):
        roles = {**roles, "x": None, "normalize": True}
    return roles


# ---------- shared constraint helpers ----------

def too_many_groups(limit, msg):
    def check(ctx, roles):
        k = _groups(ctx, roles)
        return msg.format(k=k) if k > limit else None
    return check


def crowded_groups(limit, penalty, msg):
    def check(ctx, roles):
        k = _groups(ctx, roles)
        return (penalty, msg.format(k=k)) if k > limit else None
    return check


def _value_phrase(roles):
    if roles.get("y") is None:
        return "how many rows fall in each"
    if roles.get("agg") == "mean":
        return f"the average {roles['y']} for each"
    return f"the {roles['y']} for each"


PIE_WRONG = ("pie charts show shares of a whole, and people are bad at comparing slice sizes. "
             "to compare groups, bar lengths are much easier to read.")


def pie_wrong_for_comparison(ctx):
    return PIE_WRONG if ctx.shape() in ("C", "CN") else None


def line_wrong_for_categories(ctx):
    if ctx.shape() == "CN":
        return (f"line charts connect points in order, which suggests a trend from one {ctx.cats[0]['name']} to the next "
                f"that doesn't exist. bars compare groups without implying an order.")
    return None


def line_wrong_for_relationship(ctx):
    if ctx.shape() == "NN":
        return ("line charts join points into one continuous path, which hides the scatter of individual rows. "
                "for two measurements on the same rows, a scatter plot shows the real pattern.")
    return None


# ---------- the rule table ----------

RULES = [
    Rule(
        id="bar", figure="bar", label="Bar chart",
        goals={"comparison": 0.95},
        fit=fit_bar,
        hard=[too_many_groups(20, "with {k} groups the bars get too thin to read. try filtering to the groups you care about most.")],
        soft=[crowded_groups(10, 0.2, "with {k} groups it's getting crowded; sorting the bars or keeping the top 10 helps.")],
        why=lambda ctx, r, g: (f"bar charts are the clearest way to compare groups because bar lengths are easy to line up by eye. "
                               f"each bar shows {_value_phrase(r)} {r['x']}; you have {_groups(ctx, r)} groups."),
    ),
    Rule(
        id="grouped_bar", figure="grouped_bar", label="Grouped bar chart",
        goals={"comparison": 0.85},
        fit=fit_grouped_bar,
        hard=[lambda ctx, r: (f"one of your columns has {max(c['n_unique'] for c in ctx.cols)} categories; grouped bars get unreadable past 8 per side."
                              if max(c["n_unique"] for c in ctx.cols) > 8 else None)],
        why=lambda ctx, r, g: (f"grouped bars compare two sets of groups at once: each {r['x']} gets a cluster of bars, "
                               f"one per {r['color']}, showing how many rows fall in each combination."),
    ),
    Rule(
        id="line", figure="line", label="Line chart",
        goals={"trend": 0.95},
        fit=fit_line,
        soft=[lambda ctx, r: ((0.3, f"there are only {_groups(ctx, r)} time points, so there's barely a trend to show.")
                              if _groups(ctx, r) < 4 else None)],
        why=lambda ctx, r, g: (f"line charts show how {r['y']} changes across {r['x']}: the slope makes rises and drops easy to spot"
                               + (f" (each point is the average {r['y']} for that {r['x']})." if r.get("agg") == "mean" else ".")),
        wrong_for={"comparison": line_wrong_for_categories, "relationship": line_wrong_for_relationship},
    ),
    Rule(
        id="time_bar", figure="bar", label="Bar chart over time",
        goals={"trend": 0.7},
        fit=fit_time_bar,
        hard=[too_many_groups(40, "with {k} time points the bars become a dense wall; a line chart shows the same trend more cleanly.")],
        why=lambda ctx, r, g: (f"bars over time work when you have a handful of distinct periods and want each period's {r['y']} "
                               f"to stand on its own; the line chart is usually better for showing the overall trend."),
    ),
    Rule(
        id="histogram", figure="histogram", label="Histogram",
        goals={"distribution": 0.95},
        fit=fit_histogram,
        hard=[lambda ctx, r: (f"with only {ctx.n_rows} values, a histogram's bars are mostly noise. a strip plot that shows every value is more honest."
                              if ctx.n_rows < 20 else None)],
        why=lambda ctx, r, g: (f"histograms group {r['x']} into ranges and show how many values fall in each, so you can see "
                               f"where most values sit, how wide the spread is, and whether there are outliers ({ctx.n_rows} values)."),
    ),
    Rule(
        id="box", figure="box", label="Box plot",
        goals={"distribution": 0.85, "comparison": 0.75},
        fit=fit_box,
        hard=[lambda ctx, r: (
            (f"you have about {ctx.n_rows / _groups(ctx, r):.1f} values per {r['x']}; a box summarizes many values, so with this few "
             f"it hides more than it shows. a strip plot is better here.")
            if r["x"] and ctx.n_rows / max(_groups(ctx, r), 1) < 5 else
            (f"with only {ctx.n_rows} values there's too little to summarize in a box." if not r["x"] and ctx.n_rows < 5 else None))],
        soft=[crowded_groups(15, 0.2, "with {k} groups the boxes get narrow and hard to compare.")],
        why=lambda ctx, r, g: (
            (f"box plots summarize the spread of {r['y']} for each {r['x']}: the middle line is the median, the box covers the "
             f"middle half of values, and dots mark outliers. " +
             ("good for comparing whole spreads, not just averages, between groups." if g == "comparison"
              else "good for comparing spreads side by side."))
            if r["x"] else
            (f"a box plot summarizes {r['y']} in one glance: the middle line is the median, the box covers the middle half of "
             f"values, and dots mark outliers.")),
    ),
    Rule(
        id="strip", figure="strip", label="Strip (dot) plot",
        goals={"distribution": 0.8},
        fit=fit_one_numeric_or_split,
        hard=[lambda ctx, r: (f"with {ctx.n_rows} points the dots pile on top of each other and become a smear; a box plot or histogram summarizes them better."
                              if ctx.n_rows > 500 else None)],
        soft=[lambda ctx, r: ((0.15, f"{ctx.n_rows} dots is a lot, so some will overlap.") if ctx.n_rows > 200 else None)],
        why=lambda ctx, r, g: (f"strip plots draw every single value as a dot, so nothing is hidden by summarizing; "
                               f"this works well with a modest number of points like your {ctx.n_rows}."
                               + (f" each column of dots is one {r['x']}." if r["x"] else "")),
    ),
    Rule(
        id="scatter", figure="scatter", label="Scatter plot",
        goals={"relationship": 0.95},
        fit=fit_scatter,
        soft=[lambda ctx, r: ((0.3, f"with {ctx.n_rows} points, dots will overlap heavily (we make them see-through to help).")
                              if ctx.n_rows > 5000 else None)],
        why=lambda ctx, r, g: (f"scatter plots put {r['x']} on one axis and {r['y']} on the other, so each dot is one row. "
                               f"if the dots form an upward or downward band, the two move together; a shapeless cloud means they don't."),
    ),
    Rule(
        id="pie", figure="pie", label="Pie chart",
        goals={"part_to_whole": 0.8},
        fit=fit_parts,
        hard=[
            too_many_groups(6, "{k} slices is too many; people can't judge small differences in angle. a stacked bar or bar chart is easier to read."),
            lambda ctx, r: (f"'{r['y']}' has negative values, which can't be slices of a whole." if r.get("min") is not None and r["min"] < 0 else None),
        ],
        soft=[
            crowded_groups(4, 0.2, "with {k} slices, similar-sized ones get hard to tell apart."),
            lambda ctx, r: ((0.3, f"this adds up {r['y']} within each {r['x']}; only use it if {r['y']} values add up to a meaningful "
                                  f"total (like counts or money), not averages or scores.") if r.get("repeated") else None),
        ],
        why=lambda ctx, r, g: (f"pie charts show how a whole splits into parts; each slice is "
                               + (f"one {r['x']}'s share of all rows." if r["y"] is None else f"one {r['x']}'s share of total {r['y']}.")
                               + f" with {_groups(ctx, r)} slices it stays readable."),
        wrong_for={"comparison": pie_wrong_for_comparison},
    ),
    Rule(
        id="stacked_bar", figure="stacked_bar", label="Stacked bar (100%)",
        goals={"part_to_whole": 0.85},
        fit=fit_stacked,
        hard=[too_many_groups(8, "{k} segments is too many to tell apart by color; a regular bar chart works better.")],
        soft=[lambda ctx, r: ((0.3, f"this adds up {r['y']} within each {r['color']}; only meaningful if {r['y']} values add up to a real total.")
                              if r.get("repeated") else None)],
        why=lambda ctx, r, g: (
            (f"each {r['x']} gets a bar split into {r['color']} segments that add up to 100%, so you can see how the mix differs between groups.")
            if r.get("x") else
            (f"one bar split into segments shows each {r['color']}'s share of the total; segments of a straight bar are easier to compare than pie slices.")),
    ),
]


# ---------- engine ----------

def suggest(columns: list[dict], goal: str) -> dict:
    # columns = the 1-2 columns the user selected (types possibly overridden).
    # returns {"suggested": [...], "ruled_out": [...], "message": str or None}
    if goal not in GOALS:
        raise ValueError(f"unknown goal: {goal}")
    if not columns:
        return {"suggested": [], "ruled_out": [], "message": "pick at least one column to get suggestions."}

    ctx = Ctx(columns, goal)
    suggested, ruled_out, seen = [], [], set()

    def rule_out(rule, reason):
        if rule.label not in seen:
            seen.add(rule.label)
            ruled_out.append({"figure": rule.figure, "label": rule.label, "why_not": reason})

    for rule in RULES:
        # goal doesn't match: only mention it if it's a common wrong choice for this data
        if goal not in rule.goals:
            check = rule.wrong_for.get(goal)
            reason = check(ctx) if check else None
            if reason:
                rule_out(rule, reason)
            continue

        roles = rule.fit(ctx)
        if isinstance(roles, str):
            rule_out(rule, roles)
            continue

        failed = next((msg for h in rule.hard if (msg := h(ctx, roles))), None)
        if failed:
            rule_out(rule, failed)
            continue

        score, notes = rule.goals[goal], []
        for s in rule.soft:
            hit = s(ctx, roles)
            if hit:
                score -= hit[0]
                notes.append(hit[1])

        why = rule.why(ctx, roles, goal)
        if notes:
            why += " heads up: " + " ".join(notes)

        suggested.append({
            "figure": rule.figure,
            "label": rule.label,
            "x": roles.get("x"),
            "y": roles.get("y"),
            "color": roles.get("color"),
            "agg": roles.get("agg"),
            "normalize": roles.get("normalize", False),
            "score": round(max(score, 0.0), 2),
            "why": why,
        })

    suggested.sort(key=lambda s: -s["score"])
    message = None if suggested else "nothing fits this combination yet. " + GOAL_NEEDS[goal]
    return {"suggested": suggested, "ruled_out": ruled_out, "message": message}
