"""
02 - Load a real .xlsx workbook, calculate it, and save the model.

Loading uses xlwings, which opens the workbook in a hidden copy of Excel to
read every cell's formula and value. So:
  - Excel must be installed for THIS step (it takes ~20-30 seconds to start)
  - once saved, the model reloads in milliseconds and needs no Excel at all
    (see 03_what_if_scenarios.py)

Run:  python make_sample_workbook.py   (once)
      python 02_load_workbook.py
"""
import os
import time

from xlc_helpers import evaluate, from_serial, load_workbook, mark_all_dirty

WORKBOOK = "loan_model.xlsx"
SAVED_MODEL = "loan_model.pkl.gz"

if not os.path.exists(WORKBOOK):
    raise SystemExit("Run make_sample_workbook.py first.")

t = time.time()
model = load_workbook(os.path.abspath(WORKBOOK))   # xlwings wants an absolute path
print(f"Loaded {WORKBOOK} in {time.time() - t:.1f}s")

# What's in the model?
for name, sheet in model.sheets.items():
    n_formulas = sum(1 for c in sheet.cells.values() if c.formula)
    print(f"  {name:<9} {len(sheet.cells):>3} cells, {n_formulas:>2} formulas")

# Each cell holds the formula AND the value Excel last calculated for it.
cell = model.get_cell_by_canonical_address("Summary!B1")
print("\nSummary!B1 formula:        ", cell.formula)
print("Summary!B1 value from Excel:", cell.value)

# Save BEFORE build_code(). build_code() attaches compiled Python functions to
# each cell, and those can't be pickled (you'd get a PicklingError).
model.persist_to_pickle_file(SAVED_MODEL)
print(f"\nSaved model to {SAVED_MODEL} ({os.path.getsize(SAVED_MODEL):,} bytes)")

# Now compile and calculate with xlcalc itself.
model.build_code()

# Without this, formulas that read other formula cells would just return the
# values Excel stored at load time instead of recalculating.
mark_all_dirty(model)

print("\nCalculated by xlcalc:")
for row in range(1, 12):
    label = model.get_cell_by_canonical_address(f"Summary!A{row}").value
    print(f"  {label:<34} {evaluate(model, f'Summary!B{row}')!r}")

# Dates come back as Excel serial numbers.
maturity = evaluate(model, "Summary!B10")
print(f"\nMaturity date {maturity} as a date: {from_serial(maturity)}")
print("(The COUNTIF #VALUE! above is an xlcalc bug - see 04_check_workbook.py)")
