# builds altair charts from one item in suggest()["suggested"], plus png export
import altair as alt
import pandas as pd
import vl_convert as vlc

# validated categorical palette (fixed order, never cycled) and recessive chart chrome
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SINGLE = PALETTE[0]
INK, MUTED, GRID, AXIS = "#0b0b0b", "#58616b", "#e1e0d9", "#c3c2b7"
WIDTH, HEIGHT = 520, 320


def _vtype(df: pd.DataFrame, col: str) -> str:
    # altair encoding type from the (already type-converted) column
    s = df[col]
    if pd.api.types.is_datetime64_any_dtype(s):
        return "T"
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return "Q"
    return "N"


def _enc(df, col, title=None, **kw):
    return alt.X(f"{col}:{_vtype(df, col)}", title=title or col, **kw)


def _yagg(y, agg):
    # y encoding string with aggregation, plus a readable axis title
    if y is None or agg == "count":
        return "count():Q", "number of rows"
    if agg == "mean":
        return f"mean({y}):Q", f"average {y}"
    if agg == "median":
        return f"median({y}):Q", f"median {y}"
    if agg == "sum":
        return f"sum({y}):Q", f"total {y}"
    return f"{y}:Q", y


def _color(col, title=None):
    return alt.Color(f"{col}:N", title=title or col, scale=alt.Scale(range=PALETTE))


def _style(chart: alt.Chart, title: str) -> alt.Chart:
    return (
        chart.properties(width=WIDTH, height=HEIGHT, title=title, background="#ffffff")
        .configure_view(stroke=None)
        .configure_axis(gridColor=GRID, domainColor=AXIS, tickColor=AXIS, labelColor=MUTED,
                        titleColor=INK, titleFontWeight="normal", labelFontSize=12, titleFontSize=12)
        .configure_legend(labelColor=INK, titleColor=INK, titleFontWeight="normal")
        .configure_title(color=INK, fontSize=15, anchor="start", fontWeight="normal")
    )


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
        if _vtype(data, x) == "T":
            x_enc = _enc(data, x)
        else:
            x_enc = alt.X(f"{x}:N", title=x, sort="-y", axis=alt.Axis(labelAngle=-30))
        chart = base.mark_bar(color=SINGLE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=x_enc, y=alt.Y(y_field, title=y_title),
            tooltip=[alt.Tooltip(f"{x}:{_vtype(data, x)}"), alt.Tooltip(y_field, title=y_title, format=",.2f")],
        )
        title = f"{y_title} by {x}"

    elif fig == "grouped_bar":
        chart = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X(f"{x}:N", title=x, axis=alt.Axis(labelAngle=-30)),
            xOffset=alt.XOffset(f"{color}:N"),
            y=alt.Y("count():Q", title="number of rows"),
            color=_color(color),
            tooltip=[f"{x}:N", f"{color}:N", alt.Tooltip("count():Q", title="rows")],
        )
        title = f"rows by {x} and {color}"

    elif fig == "line":
        y_field, y_title = _yagg(y, agg or "none")
        chart = base.mark_line(color=SINGLE, strokeWidth=2, point=alt.OverlayMarkDef(size=60, color=SINGLE)).encode(
            x=_enc(data, x), y=alt.Y(y_field, title=y_title, scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip(f"{x}:{_vtype(data, x)}"), alt.Tooltip(y_field, title=y_title, format=",.2f")],
        )
        title = f"{y_title} over {x}"

    elif fig == "histogram":
        chart = base.mark_bar(color=SINGLE, cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=alt.X(f"{x}:Q", bin=alt.Bin(maxbins=20), title=x),
            y=alt.Y("count():Q", title="number of rows"),
            tooltip=[alt.Tooltip(f"{x}:Q", bin=alt.Bin(maxbins=20), title=f"{x} range"), alt.Tooltip("count():Q", title="rows")],
        )
        title = f"how {x} is spread out"

    elif fig == "box":
        enc = {"y": alt.Y(f"{y}:Q", title=y, scale=alt.Scale(zero=False))}
        if x:
            enc["x"] = alt.X(f"{x}:N", title=x, axis=alt.Axis(labelAngle=-30))
        chart = base.mark_boxplot(color=SINGLE, size=36, median=alt.MarkConfig(color="#ffffff"),
                                  outliers=alt.MarkConfig(color=SINGLE)).encode(**enc)
        title = f"spread of {y}" + (f" by {x}" if x else "")

    elif fig == "strip":
        enc = {
            "y": alt.Y(f"{y}:Q", title=y, scale=alt.Scale(zero=False)),
            "xOffset": alt.XOffset("jitter:Q", scale=alt.Scale(domain=[-1, 1]), title=None),
            "tooltip": [f"{c}:{_vtype(data, c)}" for c in (x, y) if c],
        }
        if x:
            enc["x"] = alt.X(f"{x}:N", title=x, axis=alt.Axis(labelAngle=-30))
        chart = (base.transform_calculate(jitter="sqrt(-2*log(random()))*cos(2*PI*random()) / 3")
                 .mark_circle(size=60, color=SINGLE, opacity=0.6, stroke="#ffffff", strokeWidth=1)
                 .encode(**enc))
        title = f"every value of {y}" + (f" by {x}" if x else "")

    elif fig == "scatter":
        opacity = 0.7 if len(data) < 1000 else 0.25
        chart = base.mark_circle(size=60, color=SINGLE, opacity=opacity, stroke="#ffffff", strokeWidth=1).encode(
            x=alt.X(f"{x}:Q", title=x, scale=alt.Scale(zero=False)),
            y=alt.Y(f"{y}:Q", title=y, scale=alt.Scale(zero=False)),
            tooltip=[f"{x}:Q", f"{y}:Q"],
        )
        title = f"{y} vs {x}"

    elif fig == "pie":
        theta, t_title = _yagg(y, agg)
        chart = base.mark_arc(stroke="#ffffff", strokeWidth=2).encode(
            theta=alt.Theta(theta, stack=True),
            color=_color(color),
            order=alt.Order(theta, sort="descending"),
            tooltip=[f"{color}:N", alt.Tooltip(theta, title=t_title, format=",.2f")],
        )
        title = f"share of {'rows' if t_title == 'number of rows' else t_title} by {color}"

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
            enc["y"] = alt.Y(f"{x}:N", title=x)
        chart = base.mark_bar(stroke="#ffffff", strokeWidth=2).encode(**enc)
        title = f"share of {v_title} by {color}" + (f" within each {x}" if x else "")

    else:
        raise ValueError(f"don't know how to draw figure type: {fig}")

    chart = _style(chart, title)
    if fig == "stacked_bar" and not x:
        chart = chart.properties(height=80)
    return chart


def to_png(chart: alt.Chart, scale: float = 2.0) -> bytes:
    # png bytes for the download button
    return vlc.vegalite_to_png(chart.to_json(), scale=scale)
