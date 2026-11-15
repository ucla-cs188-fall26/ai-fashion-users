# figures built around a stated finding (comparison of one measure between two groups).
# hard constraints decide which figures are allowed; soft constraints decide which one makes
# the finding most visible. every explanation carries the source of the rule behind it.
from claims import Finding
from sources import cite

# bars start at zero (length encoding). if the gap is under this share of the taller bar,
# the difference is hard to see in bars and dots with intervals show it better.
VISIBLE_GAP = 0.10  # team heuristic


def visible_share(result: dict) -> float:
    top = max(abs(result["mean_a"]), abs(result["mean_b"]))
    return abs(result["gap"]) / top if top else 0.0


def suggest_for_finding(result: dict, n_groups: int) -> dict:
    # result = claims.check(...) output; n_groups = how many groups the category column has
    f: Finding = result["finding"]
    share = visible_share(result)
    unclear = result["status"] == "unclear"
    has_negative = min(result["mean_a"], result["mean_b"]) < 0 < max(result["mean_a"], result["mean_b"])

    dots = {
        "figure": "dot_ci", "label": "Dots with 95% intervals",
        "why": (f"Each dot is a group's average {f.measure} and the line through it shows the range the true "
                f"average plausibly falls in. Dots use position on a shared axis, the most accurately read encoding, "
                f"and unlike bars they don't need to start at zero, so a gap of {abs(result['gap']):.2f} stays visible."
                + (" Overlapping intervals show honestly that the data can't separate these groups yet." if unclear else "")),
        "emphasis": "The size of the gap and how certain it is.",
        "limit": "Readers less used to error bars may need the caption to explain what the lines mean.",
        "sources": cite("cleveland", "kim"),
    }
    bars = {
        "figure": "bar_focus", "label": "Bar chart, your groups highlighted",
        "why": (f"Bars make a discrete comparison between groups easy to read, and most readers know them. "
                f"{f.a} and {f.b} sit side by side and are highlighted, so the comparison you care about is the one "
                f"the eye makes first."),
        "emphasis": "Which group is higher, at a glance.",
        "limit": "Bars must start at zero, so small gaps look flat, and bars hide the uncertainty in each average.",
        "sources": cite("zacks", "xiong", "kim"),
    }
    ruled_out = []

    # hard constraint: a bar's length must mean something, so mixed signs break it
    if has_negative:
        ruled_out.append({"label": bars["label"], "why_not": (
            "One average is negative and the other positive, so bar lengths from zero would exaggerate the gap. "
            "Dots on a shared axis show it accurately."), "sources": cite("mackinlay")})
        suggested = [dots]
    elif unclear or share < VISIBLE_GAP:
        reason = (f"Here the gap is only {share:.0%} of the taller bar's height, so it would be hard to see."
                  if not unclear else "Bars would also hide that the data can't separate these groups yet.")
        bars = {**bars, "limit": bars["limit"] + " " + reason, "sources": bars["sources"] + cite("team")}
        suggested = [dots, bars]
    else:
        suggested = [bars, dots]

    # common wrong choices for a two-group comparison, with reasons tied to this finding
    ruled_out += [
        {"label": "Pie chart", "why_not": (
            f"Pies show shares of a whole, but average {f.measure} values don't add up to a whole, and angles are "
            f"read less accurately than lengths or positions."), "sources": cite("mackinlay", "cleveland")},
        {"label": "Line chart", "why_not": (
            f"A line between {f.a} and {f.b} suggests a trend from one group to the next that doesn't exist; "
            f"these are separate groups, not points in time."), "sources": cite("zacks")},
        {"label": "3D bars", "why_not": "Depth effects make bar heights harder to read accurately; stay in 2D.",
         "sources": cite("expert")},
    ]
    if n_groups > 2:
        ruled_out.append({"label": "All groups at full strength", "why_not": (
            f"Your column has {n_groups} groups. Showing them all equally competes with the one comparison you're "
            f"making; other groups are hidden by default or shown muted."), "sources": cite("expert", "bao", "kim")})

    return {"suggested": suggested, "ruled_out": ruled_out, "visible_share": share}
