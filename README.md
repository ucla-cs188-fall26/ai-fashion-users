# Figure Helper

A CS 188 prototype that helps undergrad and early grad students pick the right figure for a research finding.

You give it a csv, choose one or two columns, and say what you want to show (comparison, trend, distribution, relationship, or part-to-whole). It suggests figures drawn with your own data, explains **why each one fits**, and explains **why the other figures were ruled out**.

Figure choice is treated as a constraint satisfaction problem (an idea borrowed from Tea). Column types and the goal act as constraints, and each figure is a rule with hard constraints (which rule it out) and soft constraints (which lower its score). Every explanation comes from the specific constraint that passed or failed.

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
1. pick "grades_by_major.csv" from the sample dropdown
2. select columns "major" and "gpa"
3. choose "comparison"
4. look at the suggested figures and their explanations, then open "figures we ruled out and why"
5. click "download as png" under a figure

Other scenarios to try:
- `temperature_monthly.csv`, columns `month` + `avg_temp_c`, goal **trend over time**: suggests a line chart
- `height_weight.csv`, columns `height_cm` + `weight_kg`, goal **relationship**: suggests a scatter plot
- `grades_by_major.csv`, columns `year` + `gpa`, goal **trend over time**: nothing fits, because `year` is detected as a category. change its type to **numeric** and a line chart appears

## tests
```
pytest
```

## project layout
| file | what it does |
|---|---|
| `app.py` | streamlit ui, one function per step |
| `detect.py` | loads csvs, detects column types (categorical / numeric / date), applies type overrides |
| `rules.py` | the rule table and the `suggest()` engine |
| `render.py` | turns a suggestion into an altair chart, plus png export |
| `data/` | sample datasets (regenerate with `python scripts/make_samples.py`) |
| `tests/` | unit tests for detection and rules, plus a render smoke test |
| `docs/design_decisions.md` | design decisions log |

## Updated selection workflow
- Use the sidebar or Continue buttons to move between data, question, and figure stages. Earlier choices remain available in their expandable sections.
- For group comparisons with a measurement, choose typical values, variation, or individual observations. This changes the preferred chart, subject to sample-size and crowding rules.
- Choose mean or median for group/time summaries. For two numeric variables used as a time trend, identify and confirm the time variable first.
- Select a suitable chart to inspect its fit, emphasis, and limitations. Other suitable charts are alternatives, not necessarily inferior choices. Numeric ranking weights are implementation heuristics, not validated confidence scores.
- PNG export uses the selected chart. Chart label editing is not implemented yet.
- CSVs are processed by the Python app host, with no external AI service. A local run processes data on your computer; a hosted run processes it on that server.
