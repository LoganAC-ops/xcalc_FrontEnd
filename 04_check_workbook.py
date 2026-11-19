"""
04 - Can xlcalc be trusted with THIS workbook? Check before relying on it.

Two checks worth running on any workbook you load:
  1. Unsupported functions - xlcalc silently returns 0 for functions it doesn't
     implement (INDEX, TEXT, XLOOKUP, IFS, OFFSET, ...), with no error.
  2. Compare against Excel - the loader stores the value Excel calculated for
     every cell, so recalculate each formula with xlcalc and diff the two.

Run:  python 02_load_workbook.py   (once)
      python 04_check_workbook.py
"""
import os

from xlcalc import EvalContext, Model
from xlc_helpers import evaluate, formula_cells, mark_all_dirty, to_python, unsupported_functions

SAVED_MODEL = "loan_model.pkl.gz"
if not os.path.exists(SAVED_MODEL):
    raise SystemExit("Run 02_load_workbook.py first.")

# Don't build yet: we want Excel's stored values before xlcalc overwrites them.
model = Model.construct_from_pickle_file(SAVED_MODEL, build_code=False)

# --- 1. Unsupported functions -------------------------------------------------
missing = unsupported_functions(model)
print("1. Unsupported functions")
if not missing:
    print("   none - every function used is implemented")
for name, cells in missing.items():
    print(f"   {name:<10} used in {', '.join(cells)}")

# --- 2. xlcalc vs Excel -------------------------------------------------------
excel_values = {ref: cell.value for ref, cell in formula_cells(model)}

model.build_code()
# Force a genuine recalculation - otherwise formulas reading other formula
# cells would just hand back Excel's stored values and everything would "match".
mark_all_dirty(model)
ctx = EvalContext(model)


def same(a, b, tol=1e-9) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol * max(1, abs(a))
    return a == b


print("\n2. xlcalc vs Excel")
mismatches = 0
for ref, excel in excel_values.items():
    try:
        ours = evaluate(model, ref, ctx)
    except Exception as e:
        ours = f"ERROR: {type(e).__name__}: {e}"
    if not same(to_python(excel), ours):
        mismatches += 1
        print(f"   MISMATCH {ref:<12} Excel={excel!r:<24} xlcalc={ours!r}")
print(f"   {len(excel_values) - mismatches} of {len(excel_values)} formula cells match Excel")
