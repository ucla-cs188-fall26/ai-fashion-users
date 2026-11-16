# Evaluation plan and first results

## Why
A TA asked at crit why a student wouldn't just use Gemini. Our answer is that Figure Helper only draws valid figures, checks the student's finding against the data, and explains every choice. Those are claims, so we test them, the way Tea was tested: Tea's authors compared its test choices against 12 textbook tutorials and it matched 9.

## Part 1: textbook benchmark (run Nov 14)
Six datasets that ship with R. Each one's official documentation runs a specific analysis and draws a specific figure; that is the reference answer. Full table: [evaluation_results.md](evaluation_results.md). Re-run with `python benchmarks/textbook.py`.

| Dataset | Documented analysis | Result |
|---|---|---|
| PlantGrowth (Dobson 1983) | Boxplot + one-way ANOVA | Agrees (pairwise claim) |
| chickwts (Snedecor 1948) | Boxplot + one-way ANOVA | Agrees (pairwise claim) |
| InsectSprays (Beall 1942) | ANOVA on raw and square-root counts | Agrees |
| cars (Ezekiel 1930) | Scatter plot + smooth curve + regression | Figure matches; claim not checked |
| sleep (Student 1908) | Paired t-test | **Fails**: says "can't tell" (Welch p = 0.079); paired test p = 0.003 |
| ToothGrowth (Crampton 1947) | Length vs dose, split by supplement | **Misleading**: ignoring dose hides a clear effect at doses 0.5 and 1 |

**What we learned, in priority order for the final:**
1. **Study design.** Same subjects measured twice (sleep) needs a paired check and a figure that connects each subject's values. Tea handles this by asking about the design; we should too. Highest priority because the tool gives a wrong answer, not just a missing one.
2. **A second factor.** ToothGrowth's real finding depends on dose. Supporting a third column, done as "the effect of A at each level of B", is the fix.
3. **Relationship claims.** "X increases with Y" (cars) should get a check (correlation with its interval) and a trend line.
4. **More than two groups.** PlantGrowth and chickwts are documented with an overall test across all groups; we only check one pair. Checking several pairs also needs a multiple-comparison correction.
5. **Counts.** InsectSprays agreed, but the tool doesn't warn that counts often need a transform. Tea-style assumption checks would.

Showing every value (our default figure) already helps: in ToothGrowth the clusters inside each supplement group hint at the hidden dose effect, which a bar of averages would hide entirely.

## Part 2: same tasks with Gemini and ChatGPT (to do, by hand)
For each dataset: open a new chat, upload the CSV, paste the prompt, and save the figure and answer. Do it 3 times per tool (new chat each time) to check consistency. About 5 minutes per run.

**Prompt (same for every dataset, fill in the brackets):**
> I'm a student writing a research report. My finding is: "[finding]". Using the attached data, make the best figure to show this finding, and tell me whether the data supports it.

| Dataset | File | Finding to paste |
|---|---|---|
| PlantGrowth | `plant_growth_dobson1983.csv` | trt2 plants have a higher average weight than trt1 plants |
| sleep | `sleep_drug_student1908.csv` | drug 2 gives more extra sleep than drug 1 |
| ToothGrowth | `tooth_growth_vitamin_c.csv` | orange juice (OJ) gives longer teeth than vitamin C (VC) |
| chickwts | `chick_weights_by_feed.csv` | chicks on casein weigh more than chicks on horsebean |
| InsectSprays | `insect_sprays_beall1942.csv` | spray C leaves fewer insects than spray A |
| cars | `car_stopping_distance_1920s.csv` | faster cars need longer distances to stop |

**Score each run (yes / no):**
1. Valid figure type for the data (no pie of averages, no line across separate groups, bars start at zero)
2. Shows individual values or uncertainty, not just averages
3. Correct verdict compared with the documented analysis (sleep: supported once pairing is used; ToothGrowth: depends on dose)
4. Notices the design issue on its own (sleep: pairing; ToothGrowth: dose)
5. Same answer across the 3 runs
6. Explains why it chose the figure

The interesting comparisons are items 3 to 5: an LLM may notice pairing that our v1 misses, or may give different answers each run. Either result is useful for Part E and the final.

## Part 3: papers from our users' fields (for the final)
10 to 15 published figures with open data from biology, chemical engineering, and economics. Pick figures that published guides use as good examples (Rougier et al. 2014; Weissgerber et al. 2015; Wilke, *Fundamentals of Data Visualization*), or papers with an open-data statement. Same scoring as Part 2, plus: does our figure match or improve on the published one?

## Limits of this evaluation
Six textbook datasets are a small, clean sample; real student data is messier. The reference answers come from R's documentation examples, which show one reasonable analysis, not the only one. Two of six cases were chosen knowing they test design features (pairing, a second factor), so the failure rate isn't an estimate of real-world accuracy.
