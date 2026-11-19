"""
03 - What-if scenarios: reload a saved model and run it with different inputs.

This is the main reason to use xlcalc: take the logic in a spreadsheet and run
it thousands of times from Python - no Excel, no copy-pasting inputs.

Run:  python 02_load_workbook.py   (once, to create loan_model.pkl.gz)
      python 03_what_if_scenarios.py
"""
import os
import time

import pandas as pd

from xlcalc import EvalContext, Model
from xlc_helpers import evaluate, set_value

SAVED_MODEL = "loan_model.pkl.gz"
if not os.path.exists(SAVED_MODEL):
    raise SystemExit("Run 02_load_workbook.py first.")

t = time.time()
model = Model.construct_from_pickle_file(SAVED_MODEL, build_code=True)
print(f"Reloaded model in {time.time() - t:.2f}s (no Excel involved)\n")

ctx = EvalContext(model)

INPUTS = {"principal": "Inputs!B1", "rate": "Inputs!B2", "years": "Inputs!B3"}
OUTPUTS = {
    "payment": "Summary!B1",
    "yr1_interest": "Summary!B2",
    "total_interest": "Summary!B6",
    "interest>principal": "Summary!B7",
}


def run(**inputs) -> dict:
    """Set the given inputs, calculate every output, return one result row."""
    for name, value in inputs.items():
        set_value(model, INPUTS[name], value)
    return {**inputs, **{name: evaluate(model, ref, ctx) for name, ref in OUTPUTS.items()}}


# --- A grid of scenarios -----------------------------------------------------
t = time.time()
results = [
    run(principal=p, rate=r, years=y)
    for p in (200_000, 350_000)
    for r in (0.04, 0.055, 0.07)
    for y in (15, 30)
]
elapsed = time.time() - t

df = pd.DataFrame(results)
pd.set_option("display.width", 140)
pd.set_option("display.float_format", "{:,.2f}".format)
print(df.to_string(index=False))
print(f"\n{len(df)} scenarios in {elapsed:.2f}s")

# --- Goal seek: what rate gives a $1,500 payment on $250k / 30y? -------------
# Simple bisection - the same idea as Excel's Goal Seek, driven from Python.
set_value(model, INPUTS["principal"], 250_000)
set_value(model, INPUTS["years"], 30)
lo, hi, target = 0.0001, 0.20, 1500
for _ in range(50):
    mid = (lo + hi) / 2
    set_value(model, INPUTS["rate"], mid)
    if evaluate(model, OUTPUTS["payment"], ctx) < target:
        lo = mid
    else:
        hi = mid
print(f"\nGoal seek: a {mid:.4%} rate gives a ${target:,} payment")
