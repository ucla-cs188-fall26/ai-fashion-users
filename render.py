# builds altair charts from one item in suggest()["suggested"], plus png export
import altair as alt
import pandas as pd
import vl_convert as vlc

# baseline style for every figure, from published guides:
# - colors: wong 2011 (nature methods) palette, distinguishable with red-green color blindness;
#   yellow is left out because it is hard to see on white
# - color only with a purpose; everything else gray (rougier et al. 2014, rule 6)
# - light, recessive gridlines and axes; no backgrounds or decoration (rougier rule 8)
# - fonts larger than library defaults (rougier rule 5); sentence-case titles; readable axis labels
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#000000"]
SINGLE = PALETTE[0]
INK, MUTED, GRID, AXIS = "#1a1a1a", "#555555", "#ececec", "#bdbdbd"
WIDTH, HEIGHT = 520, 320
FONT = 13


def nice(name):
    # column names as readable axis labels: study_hours_per_week -> study hours per week
    return None if name is None else str(name).replace("_", " ")


def sentence(text):
    return text[:1].upper() + text[1:] if text else text


def _vtype(df: pd.DataFrame, col: str) -> str:
    # altair encoding type from the (already type-converted) column
    s = df[col]
    if pd.api.types.is_datetime64_any_dtype(s):
        return "T"
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return "Q"
    return "N"


def _enc(df, col, title=None, **kw):
    return alt.X(f"{col}:{_vtype(df, col)}", title=title or nice(col), **kw)


def _yagg(y, agg):
    # y encoding string with aggregation, plus a readable axis title
    if y is None or agg == "count":
        return "count():Q", "number of rows"
    if agg == "mean":
        label = nice(y)
        return f"mean({y}):Q", label if label.lower().startswith(("avg", "average", "mean")) else f"average {label}"
    if agg == "median":
        return f"median({y}):Q", f"median {nice(y)}"
    if agg == "sum":
        return f"sum({y}):Q", f"total {nice(y)}"
    return f"{y}:Q", nice(y)


def _color(col, title=None):
    return alt.Color(f"{col}:N", title=title or nice(col), scale=alt.Scale(range=PALETTE))


def _configure(chart):
    return (
        chart.configure_view(stroke=None)
        .configure_axis(gridColor=GRID, domainColor=AXIS, tickColor=AXIS, labelColor=MUTED,
                        titleColor=INK, titleFontWeight="normal", labelFontSize=FONT, titleFontSize=FONT,
                        labelLimit=180)
        .configure_axisX(grid=False)  # vertical gridlines add nothing for categories or time
        .configure_legend(labelColor=INK, titleColor=INK, titleFontWeight="normal", labelFontSize=FONT,
                          titleFontSize=FONT)
        .configure_title(color=INK, fontSize=FONT + 3, anchor="start", fontWeight="normal",
                         subtitleColor=MUTED, subtitleFontSize=FONT - 1)
    )


def _style(chart: alt.Chart, title) -> alt.Chart:
    if isinstance(title, str):
        title = sentence(title)
    return _configure(chart.properties(width=WIDTH, height=HEIGHT, title=title, background="#ffffff"))


def render(df: pd.DataFrame, suggestion: dict) -> alt.Chart:
    # takes one item from suggest()["suggested"] and returns an altair chart.
    # df should already have column types applied (see detect.apply_types).
    fig = suggestion["figure"]
    x, y, color, agg = suggestion.get("x"), suggestion.get("y"), suggestion.get("color"), suggestion.get("agg")
    cols = list(dict.fromkeys(c for c in (x, y, color) if c))  # unique, keeps order
    data = df[cols].dropna() if cols else df
    base = alt.Chart(data)

    if fig == "bar":
        y_field, y_title = _yagg(y, agg)
        tip = [alt.Tooltip(f"{x}:{_vtype(data, x)}"), alt.Tooltip(y_field, title=y_title, format=",.2f")]
        if _vtype(data, x) == "T":
            # temporal bars default to hairlines; size them to the number of periods
            width = max(4, int(WIDTH / max(data[x].nunique(), 1) * 0.7))
            chart = base.mark_bar(color=SINGLE, width=width).encode(
                x=_enc(data, x), y=alt.Y(y_field, title=y_title), tooltip=tip)
        elif data[x].nunique() > 4:
            # many groups: horizontal bars keep category labels horizontal and readable (rougier rule 3)
            chart = base.mark_bar(color=SINGLE).encode(
                y=alt.Y(f"{x}:N", title=nice(x), sort="-x"), x=alt.X(y_field, title=y_title, axis=alt.Axis(tickCount=6)), tooltip=tip)
        else:
            chart = base.mark_bar(color=SINGLE).encode(
                x=alt.X(f"{x}:N", title=nice(x), sort="-y", axis=alt.Axis(labelAngle=0)),
                y=alt.Y(y_field, title=y_title), tooltip=tip)
        title = f"{y_title} by {nice(x)}"

    elif fig == "grouped_bar":
        chart = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X(f"{x}:N", title=nice(x), axis=alt.Axis(labelAngle=-30)),
            xOffset=alt.XOffset(f"{color}:N"),
            y=alt.Y("count():Q", title="number of rows"),
            color=_color(color),
            tooltip=[f"{x}:N", f"{color}:N", alt.Tooltip("count():Q", title="rows")],
        )
        title = f"rows by {nice(x)} and {nice(color)}"

    elif fig == "line":
        y_field, y_title = _yagg(y, agg or "none")
        chart = base.mark_line(color=SINGLE, strokeWidth=2, point=alt.OverlayMarkDef(size=60, color=SINGLE)).encode(
            x=_enc(data, x), y=alt.Y(y_field, title=y_title, scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip(f"{x}:{_vtype(data, x)}"), alt.Tooltip(y_field, title=y_title, format=",.2f")],
        )
        title = f"{y_title} over {nice(x)}"

    elif fig == "histogram":
        chart = base.mark_bar(color=SINGLE, cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=alt.X(f"{x}:Q", bin=alt.Bin(maxbins=20), title=nice(x)),
            y=alt.Y("count():Q", title="number of rows"),
            tooltip=[alt.Tooltip(f"{x}:Q", bin=alt.Bin(maxbins=20), title=f"{x} range"), alt.Tooltip("count():Q", title="rows")],
        )
        title = f"how {nice(x)} is spread out"

    elif fig == "box":
        enc = {"y": alt.Y(f"{y}:Q", title=nice(y), scale=alt.Scale(zero=False))}
        if x:
            enc["x"] = alt.X(f"{x}:N", title=nice(x), axis=alt.Axis(labelAngle=-30))
        chart = base.mark_boxplot(color=SINGLE, size=36, median=alt.MarkConfig(color="#ffffff"),
                                  outliers=alt.MarkConfig(color=SINGLE)).encode(**enc)
        title = f"spread of {nice(y)}" + (f" by {nice(x)}" if x else "")

    elif fig == "strip":
        enc = {
            "y": alt.Y(f"{y}:Q", title=nice(y), scale=alt.Scale(zero=False)),
            "xOffset": alt.XOffset("jitter:Q", scale=alt.Scale(domain=[-1, 1]), title=None),
            "tooltip": [f"{c}:{_vtype(data, c)}" for c in (x, y) if c],
        }
        if x:
            enc["x"] = alt.X(f"{x}:N", title=nice(x), axis=alt.Axis(labelAngle=-30))
        chart = (base.transform_calculate(jitter="sqrt(-2*log(random()))*cos(2*PI*random()) / 3")
                 .mark_circle(size=60, color=SINGLE, opacity=0.6, stroke="#ffffff", strokeWidth=1)
                 .encode(**enc))
        title = f"every value of {nice(y)}" + (f" by {nice(x)}" if x else "")

    elif fig == "scatter":
        opacity = 0.7 if len(data) < 1000 else 0.25
        chart = base.mark_circle(size=60, color=SINGLE, opacity=opacity, stroke="#ffffff", strokeWidth=1).encode(
            x=alt.X(f"{x}:Q", title=nice(x), scale=alt.Scale(zero=False)),
            y=alt.Y(f"{y}:Q", title=nice(y), scale=alt.Scale(zero=False)),
            tooltip=[f"{x}:Q", f"{y}:Q"],
        )
        title = f"{nice(y)} vs {nice(x)}"

    elif fig == "pie":
        theta, t_title = _yagg(y, agg)
        chart = base.mark_arc(stroke="#ffffff", strokeWidth=2).encode(
            theta=alt.Theta(theta, stack=True),
            color=_color(color),
            order=alt.Order(theta, sort="descending"),
            tooltip=[f"{color}:N", alt.Tooltip(theta, title=t_title, format=",.2f")],
        )
        title = f"share of {'rows' if t_title == 'number of rows' else t_title} by {nice(color)}"

    elif fig == "stacked_bar":
        v_field, v_title = _yagg(y, agg)
        v_title = "rows" if v_title == "number of rows" else v_title
        enc = {
            "x": alt.X(v_field, stack="normalize", title=f"share of {v_title}", axis=alt.Axis(format="%")),
            "color": _color(color),
            # same segment order in every bar so the eye can track one color across bars
            "order": alt.Order(f"{color}:N", sort="ascending"),
            "tooltip": [c for c in (f"{x}:N" if x else None, f"{color}:N") if c]
                       + [alt.Tooltip(v_field, title=v_title, format=",.2f")],
        }
        if x:
            enc["y"] = alt.Y(f"{x}:N", title=nice(x))
        chart = base.mark_bar(stroke="#ffffff", strokeWidth=2).encode(**enc)
        title = f"share of {v_title} by {nice(color)}" + (f" within each {nice(x)}" if x else "")

    else:
        raise ValueError(f"don't know how to draw figure type: {fig}")

    chart = _style(chart, title)
    if fig == "stacked_bar" and not x:
        chart = chart.properties(height=80)
    return chart


OTHER = "#b8b8b8"  # gray for groups outside the stated finding (color only with a purpose)


def render_finding(df: pd.DataFrame, result: dict, figure: str, show_others: bool = False,
                   show_points: bool = True) -> alt.Chart:
    # draws a figure built around a stated finding: the two groups sit first and side by side
    # (arrangement steers the comparison, xiong et al. 2021), are the only colored marks
    # (color with purpose, rougier et al. 2014), and the title states the finding
    # (titles drive recall, kong et al. 2019).
    from claims import group_intervals  # local import keeps render usable without the claims module

    f = result["finding"]
    a, b = str(f.a), str(f.b)
    groups = [a, b]
    if show_others:
        groups += sorted(str(g) for g in df[f.group_col].dropna().astype(str).unique() if str(g) not in (a, b))
    summary = group_intervals(df, f.group_col, f.measure, groups)
    role = lambda g: g if g in (a, b) else "other groups"
    summary["role"] = summary[f.group_col].map(role)
    order = list(summary[f.group_col])
    measure_label = f"average {nice(f.measure)}"
    color = alt.Color("role:N", title=None, legend=None,
                      scale=alt.Scale(domain=[a, b, "other groups"], range=[PALETTE[0], PALETTE[1], OTHER]))
    x = alt.X(f"{f.group_col}:N", title=nice(f.group_col), sort=order,
              axis=alt.Axis(labelAngle=0 if len(order) <= 4 else -30, labelFontSize=FONT))
    tip = [alt.Tooltip(f"{f.group_col}:N"), alt.Tooltip("mean:Q", title=measure_label, format=".2f"),
           alt.Tooltip("low:Q", title="95% CI low", format=".2f"),
           alt.Tooltip("high:Q", title="95% CI high", format=".2f"), alt.Tooltip("n:Q", title="values")]
    base = alt.Chart(summary)
    highlighted = alt.FieldOneOfPredicate(field=f.group_col, oneOf=[a, b])

    if figure == "bar_focus":
        bars = base.mark_bar(width={"band": 0.6}).encode(
            x=x, y=alt.Y("mean:Q", title=measure_label, scale=alt.Scale(zero=True)), color=color, tooltip=tip)
        labels = base.transform_filter(highlighted).mark_text(dy=-8, color=INK, fontSize=FONT).encode(
            x=x, y="mean:Q", text=alt.Text("mean:Q", format=".2f"))
        chart = bars + labels if len(order) <= 4 else bars
        subtitle = f"Bars show the {measure_label}."
    elif figure == "dot_ci":
        layers = []
        y = alt.Y("mean:Q", title=nice(f.measure), scale=alt.Scale(zero=False))
        if show_points:
            raw = df[df[f.group_col].astype(str).isin(groups)][[f.group_col, f.measure]].dropna().copy()
            raw[f.group_col] = raw[f.group_col].astype(str)
            raw["role"] = raw[f.group_col].map(role)
            # deterministic jitter so the png matches what's on screen
            raw["jitter"] = (raw.groupby(f.group_col).cumcount() * 0.618034) % 1 - 0.5
            layers.append(alt.Chart(raw).mark_circle(size=28, opacity=0.35).encode(
                x=x, xOffset=alt.XOffset("jitter:Q", scale=alt.Scale(domain=[-1.6, 1.6])),
                y=alt.Y(f"{f.measure}:Q", title=nice(f.measure), scale=alt.Scale(zero=False)),
                color=color, tooltip=[alt.Tooltip(f"{f.group_col}:N"), alt.Tooltip(f"{f.measure}:Q", title=nice(f.measure))]))
        layers.append(base.mark_rule(strokeWidth=3).encode(x=x, y=alt.Y("low:Q", title=nice(f.measure),
                      scale=alt.Scale(zero=False)), y2="high:Q", color=color, tooltip=tip))
        layers.append(base.mark_circle(size=150, opacity=1, stroke="#ffffff", strokeWidth=1.5).encode(
            x=x, y=y, color=color, tooltip=tip))
        if len(order) <= 4:  # with many groups, value labels collide with neighbors; tooltips carry them
            layers.append(base.transform_filter(highlighted).mark_text(dx=34, color=INK, fontSize=FONT, align="left").encode(
                x=x, y="mean:Q", text=alt.Text("mean:Q", format=".2f")))
        chart = alt.layer(*layers)
        subtitle = ("Small dots: each value. Large dots: averages. Lines: 95% confidence intervals."
                    if show_points else "Dots: averages. Lines: 95% confidence intervals.")
    else:
        raise ValueError(f"don't know how to draw finding figure: {figure}")

    title = alt.TitleParams(result["message"], subtitle=subtitle)
    width = max(300, min(WIDTH, 120 * len(order)))
    return _configure(chart.properties(width=width, height=HEIGHT, title=title, background="#ffffff"))


def to_png(chart: alt.Chart, scale: float = 2.0) -> bytes:
    # png bytes for the download button
    return vlc.vegalite_to_png(chart.to_json(), scale=scale)
