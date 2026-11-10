# regenerates the bundled sample csvs in data/ (fixed seed so they're reproducible)
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(188)
out = Path(__file__).resolve().parent.parent / "data"
out.mkdir(exist_ok=True)

# grades_by_major: categorical + numeric, 120 rows, 6 majors
majors = ["biology", "chemistry", "computer science", "economics", "english", "psychology"]
means = [3.3, 3.1, 3.4, 3.2, 3.5, 3.3]
rows = []
for i in range(120):
    m = i % len(majors)
    gpa = float(np.clip(rng.normal(means[m], 0.3), 2.0, 4.0))
    rows.append({
        "student_id": 1000 + i,
        "major": majors[m],
        "year": int(rng.integers(1, 5)),  # 1-4, numeric codes that are really categories
        "gpa": round(gpa, 2),
        "study_hours_per_week": round(float(np.clip(rng.normal(15, 5), 2, 40)), 1),
    })
pd.DataFrame(rows).to_csv(out / "grades_by_major.csv", index=False)

# temperature_monthly: date + numeric, 24 months
dates = pd.date_range("2023-01-01", periods=24, freq="MS")
month_idx = np.arange(24)
temp = 15 + 8 * np.sin((month_idx - 3) / 12 * 2 * np.pi) + rng.normal(0, 1, 24)
rain = np.clip(80 - 50 * np.sin((month_idx - 3) / 12 * 2 * np.pi) + rng.normal(0, 10, 24), 0, None)
pd.DataFrame({
    "month": dates.strftime("%Y-%m-%d"),
    "avg_temp_c": temp.round(1),
    "rainfall_mm": rain.round(1),
}).to_csv(out / "temperature_monthly.csv", index=False)

# height_weight: numeric + numeric, 200 rows
height = rng.normal(170, 9, 200)
weight = 0.9 * (height - 100) + rng.normal(0, 7, 200)
sex = rng.choice(["female", "male"], 200)
pd.DataFrame({
    "height_cm": height.round(1),
    "weight_kg": weight.round(1),
    "sex": sex,
}).to_csv(out / "height_weight.csv", index=False)

print("wrote samples to", out)
