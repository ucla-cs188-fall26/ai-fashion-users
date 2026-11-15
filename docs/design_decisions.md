# Design decisions

## 1. Goal is a fixed list of 5 options, not free text
- **Decision:** students choose comparison, trend, distribution, relationship, or part-to-whole with radio buttons. Each option has a one-line plain-language description.
- **Alternative rejected:** a free-text "describe your finding" box parsed by an LLM.
- **Why:** each goal maps straight to constraints in `rules.py`, so suggestions and explanations stay predictable and testable. Students we interviewed already knew what they wanted to show, so naming it from a short list is easy, and the list removes any risk of the system misreading their intent. (Free text is still a possible stretch feature, with the list as a fallback.)

## 2. Show ruled-out figures with reasons
- **Decision:** every result includes an expander called "figures we ruled out and why". It lists common figures that don't fit, each with a reason tied to the student's data (for example, "14 slices is too many...").
- **Alternative rejected:** showing only the top suggestion.
- **Why:** this serves design goal 2 (explain the choice so students build intuition). Interviewees made several figures and compared them by eye; seeing why the alternatives fail replaces that trial and error. To avoid clutter, a figure from an unrelated goal appears only when it is a *common wrong choice* for the data, such as a pie chart for comparison or a line chart across categories.

## 3. Rules are written by hand in Python
- **Decision:** each figure is a `Rule` in `rules.py` with a fit function, hard constraints, and soft constraints. The engine loops over the rules and sorts the suggestions by score.
- **Alternative rejected:** a constraint solver such as Draco's answer set programming approach.
- **Why:** the rule set is small, so plain Python is faster to build and easier for the whole team to read in one quarter. Each explanation string sits right next to the constraint that produces it, so the "why" can't drift from the logic.

## 4. Users can override detected column types
- **Decision:** step 2 shows the detected type for each selected column, and the student can change it from a dropdown.
- **Alternative rejected:** fully automatic detection.
- **Why:** numeric codes such as year 1-4 or ratings 1-5 are often really categories, and the reverse also happens. A wrong type produces wrong suggestions. The rules also point students to this control: a line chart ruled out for a category column says "change its type to date or numeric in step 2".

## 5. Ask what a group comparison should emphasize
- **Decision:** ask whether the user wants typical values, variation, or individual observations. Prioritize bars, boxes, or dots respectively, subject to the existing data constraints. Offer mean or median explicitly for summaries.
- **Alternative:** always rank average bars first.
- **Reason:** the same variables can support different messages. This implements the goal-plus-data matching insight without an external AI service. The precise ranking weights are implementation judgments, not validated research findings.

## 6. Guide the task and explain tradeoffs
- **Decision:** provide three named stages, persistent controls, one selected chart preview, and separate explanations for fit, emphasis, and limitations. Keep alternatives and exclusions available without rendering every chart at once.
- **Alternative:** a long page containing every chart and download button.
- **Reason:** support independent walkthroughs and design goal 2 while reducing competing actions. Whether this improves usability remains to be evaluated with real participants.

## 7. The student states their finding, not just a goal category
- **Decision:** for comparisons, the student picks group A, a direction (higher / lower / not sure), and group B. The figure is built around that finding.
- **Alternative rejected:** asking only for the goal category (comparison, trend, ...), as in decision 1.
- **Why:** one participant said "I did know what I wanted to show. I just didn't know how to make it show it though." Our expert's first question was "what are you comparing?" Tea works the same way: it takes a hypothesis, not a test name. Pickers instead of free text keep it predictable (same reasoning as decision 1). "Not sure" lets students who don't know the direction still get an answer.

## 8. Check the finding against the data before drawing it
- **Decision:** a 95% Welch's t confidence interval for the gap in averages plus Cohen's d, reported as a plain-language verdict (supported / opposite / can't tell apart yet) with the numbers underneath.
- **Alternatives rejected:** (a) a bootstrap percentile interval, our first version; (b) full Tea-style test selection for this prototype.
- **Why:** Welch's t is one of the tests Tea selects among and doesn't assume equal variances. "The interval excludes zero" is exactly a two-sided Welch test at 0.05. We dropped the bootstrap because the percentile interval is too narrow for small samples (Hesterberg 2015, The American Statistician), and student datasets are often small. Tea reports effect sizes and recommends focusing on them, so we show d. We report the gap and its uncertainty rather than a pass/fail stamp so the tool doesn't encourage fishing for significance. Tea-style assumption checks (normality, then Mann-Whitney when needed) are planned for the final.

## 9. Show every value, with averages and 95% intervals, before bars
- **Decision:** for a finding about a continuous measure, the first figure shows each individual value as a small dot, plus each group's average and 95% confidence interval. A bar chart of averages stays available as a familiar alternative, with its limits stated.
- **Alternative rejected:** bars of averages first (our first version picked bars when the gap was large).
- **Why:** bar graphs of averages hide the distribution of continuous data, and many different datasets produce the same bars; research guides recommend showing individual values, especially for small samples (Weissgerber et al. 2015, PLOS Biology). Position on a common scale is the most accurately read encoding (Cleveland & McGill 1984), and unlike bars it doesn't need a zero baseline (Correll et al. 2020). The two groups sit side by side because arrangement steers which comparison people make (Xiong et al. 2021), and only they are colored (color with purpose: Rougier et al. 2014).

## 10. A baseline style for every figure, from published guides
- **Decision:** color-blind-safe palette (Wong 2011), color used only for the groups that matter and everything else gray, light gridlines and no decoration, fonts larger than library defaults, sentence-case titles, readable axis labels, and a ready-to-use caption that says what the marks and error bars show and gives n per group.
- **Alternative rejected:** charting-library defaults.
- **Why:** "Ten Simple Rules for Better Figures" (Rougier et al. 2014): identify the message, don't trust defaults, use color effectively, avoid chartjunk, and captions are not optional. Error bars must say what they show (Cumming & Finch 2005).

## 11. Removed an unsupported rule
- **Decision:** removed the rule "no bars when one average is negative and the other positive".
- **Why:** bars measured from zero encode negative and positive values correctly; no source supports that rule. Every rule left in the code cites a paper, our expert interview, or is labeled as a team heuristic.

## 12. One scrolling page with numbered steps
- **Decision:** go back to Anusha's original layout: steps 1-4 on one scrolling page, Streamlit's default look, a narrower centered page, and each figure's explanation below it. This replaces the stage tabs, collapsible step sections, and custom banner from decision 6; everything else from decision 6 stays (one selected figure at a time, alternatives and exclusions in expanders).
- **Alternative rejected:** keeping both the stage tabs and scrolling.
- **Why:** having two ways to move through the same page was redundant and confusing. The plain layout keeps attention on the data, the finding, and the figure.

## 13. Redirect mismatched questions instead of dead ends
- **Decision:** when the goal and columns don't fit together, explain the mismatch and answer the question the columns can support (two measurements + "compare" becomes a relationship; a category + a number + "relationship" becomes a comparison; a date + a number + "compare" becomes a trend). Also added: two categories + "relationship" (100% stacked bars), one category + "spread" (counts), one date + "trend" (counts over time).
- **Alternative rejected:** "nothing fits" messages.
- **Why:** a student asked to compare GPA with study hours, which is a valid question in everyday words. The old message was a dead end; the new one teaches the distinction and still gives a figure (design goal 2).

## 14. Test against textbook datasets, like Tea did
- **Decision:** benchmark the tool on six R datasets whose documentation runs a known analysis (`benchmarks/textbook.py`, `docs/evaluation.md`).
- **Alternative rejected:** demoing only on our synthetic GPA data.
- **Why:** Tea was validated against textbook tutorials. Our first run found two real gaps (paired data and a second factor) that now set the priorities for the final.
