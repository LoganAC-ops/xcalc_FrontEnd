"""
01 - Build a model in pure Python (no Excel needed) and calculate it.

The core workflow, in four steps:
    1. Model()                  - an empty workbook
    2. set_cell_value(...)      - add values and formulas
    3. model.build_code()       - parse + compile formulas, build the dependency graph
    4. recalc_or_iterate(ctx, "Sheet!A1")  - calculate a cell

Run:  python 01_build_model_in_code.py
"""
from xlcalc import EvalContext, Model
from xlcalc.incremental_calculator import recalc_or_iterate
from xlcalc.references import CellAddress

# --- 1 & 2: build a model the "raw" way ------------------------------------
model = Model()

# CellAddress.from_string only understands "B1", not "Inputs!B1",
# so the sheet is set as a separate attribute.
a = CellAddress.from_string("B1")
a.sheet = "Inputs"
model.set_cell_value(a, value=250000)

# The rest use the helper, which does exactly the above for you.
from xlc_helpers import evaluate, put, set_value

put(model, "Inputs!B2", 0.065)   # annual rate
put(model, "Inputs!B3", 30)      # years

# Formulas are written exactly as in Excel, including the leading '='.
# References without a sheet name point at the formula's own sheet.
put(model, "Calc!B1", formula="=PMT(Inputs!B2/12, Inputs!B3*12, -Inputs!B1)")
put(model, "Calc!B2", formula="=B1*Inputs!B3*12")
put(model, "Calc!B3", formula="=B2-Inputs!B1")
put(model, "Calc!B4", formula='=IF(B3>Inputs!B1, "interest > principal", "ok")')
put(model, "Calc!B5", formula='=ROUND(B1, 2) & " per month"')

# --- 3: compile ------------------------------------------------------------
# Call this after adding/changing FORMULAS. Changing plain values doesn't need it.
model.build_code()

# --- 4: calculate ------------------------------------------------------------
ctx = EvalContext(model)

# Raw results come back as assorted types (xlcalc Number, np.float64, float, str)...
raw = recalc_or_iterate(ctx, "Calc!B1")
print("raw result:", repr(raw), type(raw).__name__)
print("as float:  ", float(raw))

# ...so the helper converts them to plain Python values.
print()
for ref in ["Calc!B1", "Calc!B2", "Calc!B3", "Calc!B4", "Calc!B5"]:
    cell = model.get_cell_by_canonical_address(ref)
    print(f"{ref:<8} {cell.formula:<48} -> {evaluate(model, ref, ctx)!r}")

# --- Change an input and recalculate ---------------------------------------
set_value(model, "Inputs!B2", 0.05)
print("\nAfter changing the rate to 5%:")
for ref in ["Calc!B1", "Calc!B4", "Calc!B5"]:
    print(f"  {ref:<8} -> {evaluate(model, ref, ctx)!r}")
