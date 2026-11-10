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
