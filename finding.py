# figures built around a stated finding (comparison of one measure between two groups).
# hard constraints decide which figures are allowed; soft constraints decide which one makes
# the finding most visible and honest. every explanation carries the source of the rule behind it.
from claims import Finding
from sources import cite

# above this many values in a group, individual dots pile up; show averages and intervals only.
# same threshold as the strip plot rule in rules.py (team heuristic).
MAX_POINTS_PER_GROUP = 200


def show_points(result: dict) -> bool:
    return max(result["n_a"], result["n_b"]) <= MAX_POINTS_PER_GROUP


def suggest_for_finding(result: dict, n_groups: int) -> dict:
    # result = claims.check(...) output; n_groups = how many groups the category column has
    f: Finding = result["finding"]
    unclear = result["status"] == "unclear"
    points = show_points(result)
    top = max(abs(result["mean_a"]), abs(result["mean_b"]))
    share = abs(result["gap"]) / top if top else 0.0

    dots = {
        "figure": "dot_ci",
        "label": "Every value, with averages and 95% intervals" if points else "Averages with 95% intervals",
        "why": ((f"Each small dot is one value of {f.measure}, so readers see the real data, not just a summary. " if points else "")
                + f"The large dot is each group's average and the line shows its 95% confidence interval. "
                  f"Dots use position on a shared axis, the most accurately read encoding, and they don't need "
                  f"to start at zero, so a gap of {abs(result['gap']):.2f} stays visible."
                + (" The verdict comes from the interval for the gap itself, which is more reliable than "
                   "eyeballing whether the two lines overlap." if unclear else "")),
        "emphasis": "The gap between your two groups, how certain it is, and the data behind it.",
        "limit": ("Lines can overlap a little even when the difference is real, so readers should go by the "
                  "caption's interval for the gap, not by overlap. Readers less used to error bars need the caption."),
        "sources": cite("weissgerber", "cleveland", "correll", "cumming"),
    }
    bars = {
        "figure": "bar_focus", "label": "Bar chart of averages",
        "why": (f"Bars are familiar and make it easy to see which group is higher. {f.a} and {f.b} sit side by "
                f"side and are the only colored bars, so the comparison you care about is the one the eye makes first."),
        "emphasis": "Which group is higher, at a glance.",
        "limit": (f"A bar of averages hides how the individual values are spread and how certain each average is; "
                  f"research guides warn against it for continuous measures like {f.measure}. Bars must also start "
                  f"at zero, so here the gap is only {share:.0%} of the taller bar's height."),
        "sources": cite("zacks", "xiong", "weissgerber", "correll"),
    }
    # showing the data is preferred for continuous measures (weissgerber et al. 2015);
    # bars stay available as a familiar alternative with their limits spelled out
    suggested = [dots, bars]

    # common wrong choices for a two-group comparison, with reasons tied to this finding
    ruled_out = [
        {"label": "Pie chart", "why_not": (
            f"Pies show shares of a whole, but average {f.measure} values don't add up to a whole, and angles are "
            f"read less accurately than lengths or positions."), "sources": cite("mackinlay", "cleveland")},
        {"label": "Line chart", "why_not": (
            f"A line between {f.a} and {f.b} suggests a trend from one group to the next that doesn't exist; "
            f"these are separate groups, not points in time."), "sources": cite("zacks")},
        {"label": "Bar chart with the axis starting above zero", "why_not": (
            "Cutting off the bottom of bars makes small gaps look large, because bar length no longer matches the "
            "value."), "sources": cite("correll")},
        {"label": "3D bars", "why_not": "Depth effects distort how tall bars look; stay in 2D.",
         "sources": cite("rougier", "expert")},
    ]
    if n_groups > 2:
        ruled_out.append({"label": "All groups at full strength", "why_not": (
            f"Your column has {n_groups} groups. Showing them all equally competes with the one comparison you're "
            f"making; other groups are hidden by default or shown in gray."), "sources": cite("expert", "rougier", "bao")})

    return {"suggested": suggested, "ruled_out": ruled_out, "visible_share": share, "show_points": points}
