# textbook benchmark: can the tool express each dataset's documented finding, and does its
# check agree with the analysis in the dataset's official r documentation?
# modeled on tea's evaluation, which compared its test choices with textbook tutorials.
# run: python benchmarks/textbook.py  (writes docs/evaluation_results.md)
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from claims import Finding, check  # noqa: E402
from detect import apply_types, detect_columns  # noqa: E402
from finding import suggest_for_finding  # noqa: E402
from rules import suggest  # noqa: E402

DATA = ROOT / "data"
rows = []


def load(name):
    return pd.read_csv(DATA / f"{name}.csv")


def tool_check(df, measure, group_col, a, b, direction):
    d = df.copy()
    d[group_col] = d[group_col].astype(str)
    r = check(d, Finding(measure, group_col, str(a), str(b), direction))
    first = suggest_for_finding(r, d[group_col].nunique())["suggested"][0]["label"]
    return r, first


def record(dataset, documented, finding, tool, reference, agrees, coverage, note):
    rows.append({"dataset": dataset, "documented analysis": documented, "finding given to the tool": finding,
                 "tool says": tool, "reference result": reference, "agrees?": agrees,
                 "coverage": coverage, "what we learned": note})


# 1. plantgrowth (dobson 1983): one-way anova across ctrl, trt1, trt2
pg = load("plant_growth_dobson1983")
f, p = stats.f_oneway(*[g.weight for _, g in pg.groupby("group")])
r, fig = tool_check(pg, "weight", "group", "trt2", "trt1", "higher")
w = stats.ttest_ind(pg[pg.group == "trt2"].weight, pg[pg.group == "trt1"].weight, equal_var=False)
record("PlantGrowth (Dobson 1983)", "Boxplot + one-way ANOVA over 3 groups",
       "trt2 has a higher average weight than trt1",
       f"{r['status']}: gap {r['gap']:+.2f}, 95% CI [{r['low']:.2f}, {r['high']:.2f}]; figure: {fig}",
       f"ANOVA F = {f:.2f}, p = {p:.3f}; Welch trt2 vs trt1 p = {w.pvalue:.4f}",
       "yes" if r["status"] == "supported" and p < 0.05 else "no",
       "partial: pairwise only, no 3-group test",
       "Pairwise claim agrees. The tool can't state 'the groups differ overall', and checking several pairs needs a multiple-comparison correction it doesn't do yet.")

# 2. sleep (student 1908): paired t-test, same 10 patients under both drugs
sl = load("sleep_drug_student1908")
r, fig = tool_check(sl, "extra", "group", 2, 1, "higher")
x1 = sl[sl.group == 1].sort_values("ID").extra.to_numpy()
x2 = sl[sl.group == 2].sort_values("ID").extra.to_numpy()
pt = stats.ttest_rel(x2, x1)
ci = pt.confidence_interval()
record("sleep (Student 1908)", "Paired t-test (same 10 patients took both drugs)",
       "drug 2 gives more extra sleep than drug 1",
       f"{r['status']}: gap {r['gap']:+.2f}, 95% CI [{r['low']:.2f}, {r['high']:.2f}]",
       f"paired t p = {pt.pvalue:.4f}, 95% CI [{ci.low:.2f}, {ci.high:.2f}]",
       "no" if r["status"] != "supported" else "yes",
       "wrong design: treats paired data as separate groups",
       "Real failure. The data support the claim, but the tool says it can't tell, because it ignores that each patient appears twice. "
       "Fix: ask about study design (like Tea) and use a paired check and a paired figure.")

# 3. toothgrowth: coplot of len vs dose given supplement (two factors)
tg = load("tooth_growth_vitamin_c")
r, fig = tool_check(tg, "len", "supp", "OJ", "VC", "higher")
by_dose = []
for dose, g in tg.groupby("dose"):
    t = stats.ttest_ind(g[g.supp == "OJ"].len, g[g.supp == "VC"].len, equal_var=False)
    by_dose.append(f"dose {dose:g}: p = {t.pvalue:.3f}")
record("ToothGrowth (Crampton 1947)", "Conditioning plot: length vs dose, split by supplement",
       "OJ gives longer teeth than VC",
       f"{r['status']}: gap {r['gap']:+.2f}, 95% CI [{r['low']:.2f}, {r['high']:.2f}]",
       "Welch OJ vs VC within each dose: " + "; ".join(by_dose),
       "misleading",
       "partial: can't hold dose fixed",
       "Ignoring dose, the tool says it can't tell. Within doses 0.5 and 1, OJ is clearly higher; at dose 2 they're equal. "
       "The real finding needs a third column (dose), which the tool doesn't support yet.")

# 4. chickwts: boxplot + one-way anova over 6 feeds
ck = load("chick_weights_by_feed")
f, p = stats.f_oneway(*[g.weight for _, g in ck.groupby("feed")])
r, fig = tool_check(ck, "weight", "feed", "casein", "horsebean", "higher")
record("chickwts (Snedecor 1948)", "Boxplot + one-way ANOVA over 6 feeds",
       "casein gives higher weight than horsebean",
       f"{r['status']}: gap {r['gap']:+.1f}, 95% CI [{r['low']:.1f}, {r['high']:.1f}]; figure: {fig}",
       f"ANOVA F = {f:.2f}, p = {p:.2g}",
       "yes" if r["status"] == "supported" else "no",
       "partial: pairwise only",
       "Agrees. With 6 groups the 'show others in gray' option matters: the claim is one comparison among 15 possible pairs.")

# 5. insectsprays (beall 1942): aov on counts and on sqrt(counts), because count variance grows with the mean
ins = load("insect_sprays_beall1942")
r, fig = tool_check(ins, "count", "spray", "C", "A", "lower")
sq = stats.ttest_ind(ins[ins.spray == "C"]["count"] ** 0.5, ins[ins.spray == "A"]["count"] ** 0.5, equal_var=False)
lev = stats.levene(*[g["count"] for _, g in ins.groupby("spray")])
record("InsectSprays (Beall 1942)", "ANOVA on counts, then on square-root counts (unequal spread)",
       "spray C leaves fewer insects than spray A",
       f"{r['status']}: gap {r['gap']:+.1f}, 95% CI [{r['low']:.1f}, {r['high']:.1f}]",
       f"Welch on sqrt(counts) p = {sq.pvalue:.2g}; Levene test for equal spread across sprays p = {lev.pvalue:.2g}",
       "yes" if r["status"] == "supported" and sq.pvalue < 0.05 else "no",
       "full for this claim",
       "Agrees, partly because Welch's t doesn't assume equal spread. The tool doesn't yet warn that counts often need a transform; Tea-style assumption checks would.")

# 6. cars (ezekiel 1930): scatter plot + smooth curve + regression
cr = load("car_stopping_distance_1920s")
det = {c["name"]: c for c in detect_columns(cr)}
res = suggest([det["speed"], det["dist"]], "relationship")
rr = stats.pearsonr(cr.speed, cr.dist)
record("cars (Ezekiel 1930)", "Scatter plot with a smooth curve, then regression",
       "faster cars need longer to stop (relationship)",
       "figure: " + ", ".join(s["label"] for s in res["suggested"]) + "; no claim check for relationships",
       f"Pearson r = {rr.statistic:.2f}, p = {rr.pvalue:.2g}",
       "figure yes; claim not checked",
       "partial: figure only",
       "The figure matches the documentation's first plot. The tool can't yet check 'X increases with Y' or draw a trend curve; that's the next finding type to add.")

# write results
out = ROOT / "docs" / "evaluation_results.md"
df = pd.DataFrame(rows)
lines = ["# Textbook benchmark results", "",
         "Generated by `benchmarks/textbook.py`. Each dataset ships with R and its official documentation runs a specific "
         "analysis; that analysis is the reference. Modeled on Tea's evaluation against textbook tutorials.", ""]
lines.append("| " + " | ".join(df.columns) + " |")
lines.append("|" + "---|" * len(df.columns))
for _, row in df.iterrows():
    lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row.values) + " |")
out.write_text("\n".join(lines) + "\n")
print(df[["dataset", "tool says", "reference result", "agrees?"]].to_string())
