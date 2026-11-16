# Figure Helper

A CS 188 prototype that helps undergrad and early grad students pick the right figure for a research finding.

You give it a csv and **state your finding**, for example "chemistry majors have a lower average gpa than english majors". It checks whether your data supports that finding, then builds a figure around it: your two groups side by side and highlighted, the finding as the title. It explains **why the figure fits**, **why other figures were ruled out**, and **where each rule comes from**.

Not sure which group is higher? Leave the direction as "not sure" and the data will tell you. You can also skip the finding and browse suitable figures for a goal (comparison, trend, distribution, relationship, or part-to-whole).

Figure choice is treated as a constraint satisfaction problem (an idea borrowed from Tea). Like Tea, which takes a hypothesis instead of a test name, the student's finding plus the column types act as constraints. Hard constraints rule figures out (a line implies an order that majors don't have); soft constraints rank the rest by how visible they make the finding. Every explanation comes from the specific constraint that passed or failed, and every rule cites its source (a paper, our expert interview, or a team heuristic) in `sources.py`.

**Team:** _add names here_
**Video:** _add link here_
**Python:** 3.10 or newer (tested on 3.14)

## setup
```
git clone <repo-url>
cd <repo>
python -m venv venv
source venv/bin/activate        # windows: venv\Scripts\activate
pip install -r requirements.txt
```

## run
```
streamlit run app.py
```
The app opens at http://localhost:8501.

## try the core scenario
1. pick "grades_by_major.csv" from the example dropdown, then click **Continue to your question**
2. choose **Compare groups**, then select the columns `major` and `gpa`
3. under **State your finding**, pick `chemistry`, `has a lower average gpa than`, `english`
4. click **See suitable figures**: the data supports the finding (gap -0.40, 95% CI -0.60 to -0.19), and you get every value plus each group's average and 95% interval, both groups highlighted, the finding as the title, and a suggested caption
5. open "How we checked this", "Where these rules come from", and "Why some other charts do not fit"
6. click **Download this figure as PNG**

Two more findings to try with the same data:
- `computer science` / `not sure` / `english`: the data can't tell them apart (the interval for the gap crosses zero), and the title says so
- `english` / `has a lower average gpa than` / `chemistry`: the data shows the opposite, and the figure is titled with what the data actually shows

Other scenarios to try:
- `temperature_monthly.csv`, columns `month` + `avg_temp_c`, goal **trend over time**: suggests a line chart
- `height_weight.csv`, columns `height_cm` + `weight_kg`, goal **relationship**: suggests a scatter plot
- `grades_by_major.csv`, columns `year` + `gpa`, goal **trend over time**: nothing fits, because `year` is detected as a category. change its type to **numeric** and a line chart appears

## real datasets to try
The `data/` folder also has six classic datasets from published studies (they ship with R, and their documentation describes the original analysis):
- `plant_growth_dobson1983.csv`: compare `trt2` vs `trt1` on `weight`
- `chick_weights_by_feed.csv`: compare `casein` vs `horsebean` on `weight`
- `insect_sprays_beall1942.csv`: compare spray `C` vs `A` on `count`
- `car_stopping_distance_1920s.csv`: relationship between `speed` and `dist`
- `sleep_drug_student1908.csv` and `tooth_growth_vitamin_c.csv`: known limits of v1 (paired data, a second factor); see `docs/evaluation.md`

## evaluation
`python benchmarks/textbook.py` checks the tool against the documented analysis of each dataset. Results and the plan for comparing with Gemini and ChatGPT are in `docs/evaluation.md`.

## tests
```
pytest
```

## project layout
| file | what it does |
|---|---|
| `app.py` | streamlit ui, one function per step |
| `detect.py` | loads csvs, detects column types (categorical / numeric / date), applies type overrides |
| `claims.py` | checks a stated finding against the data: Welch's t 95% interval for the gap + Cohen's d |
| `finding.py` | picks figures for a stated finding (hard + soft constraints) and the charts ruled out |
| `sources.py` | where every rule comes from |
| `rules.py` | the rule table and the `suggest()` engine for browsing by goal |
| `render.py` | turns a suggestion or a finding into an altair chart, plus png export |
| `data/` | sample datasets (regenerate with `python scripts/make_samples.py`) |
| `tests/` | unit tests for detection, rules, claims, figures, and the app flow |
| `benchmarks/` | textbook benchmark (see `docs/evaluation.md`) |
| `docs/design_decisions.md` | design decisions log |

## Updated selection workflow
- Use the sidebar or Continue buttons to move between data, question, and figure stages. Earlier choices remain available in their expandable sections.
- For group comparisons with a measurement, choose typical values, variation, or individual observations. This changes the preferred chart, subject to sample-size and crowding rules.
- Choose mean or median for group/time summaries. For two numeric variables used as a time trend, identify and confirm the time variable first.
- Select a suitable chart to inspect its fit, emphasis, and limitations. Other suitable charts are alternatives, not necessarily inferior choices. Numeric ranking weights are implementation heuristics, not validated confidence scores.
- PNG export uses the selected chart. Chart label editing is not implemented yet.
- CSVs are processed by the Python app host, with no external AI service. A local run processes data on your computer; a hosted run processes it on that server.
