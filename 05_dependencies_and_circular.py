"""
05 - Under the hood: dependency graphs, parsed formulas, circular references.

Useful for understanding a workbook you didn't build: which inputs drive a
result, and which results change when an input changes.

Run:  python 02_load_workbook.py   (once)
      python 05_dependencies_and_circular.py
"""
import logging
import os

from xlcalc import FUNCTIONS, EvalContext, Model
from xlcalc.incremental_calculator import get_dependent_cells, get_upstream_cells
from xlc_helpers import evaluate, put

SAVED_MODEL = "loan_model.pkl.gz"
if not os.path.exists(SAVED_MODEL):
    raise SystemExit("Run 02_load_workbook.py first.")

model = Model.construct_from_pickle_file(SAVED_MODEL, build_code=True)

# --- Direct precedents: what does a formula reference? ------------------------
# model.dependency_graph maps cell -> cells it reads directly.
print("Direct precedents of Summary!B6:", model.dependency_graph["Summary!B6"])

# --- Everything upstream (transitive): all cells feeding a result ---------------
upstream = get_upstream_cells(model, "Summary!B2") - {"Summary!B2"}
inputs = sorted(c for c in upstream if not model.get_cell_by_canonical_address(c).formula)
print(f"\nSummary!B2 depends on {len(upstream)} cells; the raw inputs among them:", inputs)

# --- Everything downstream: what changes if an input changes? -----------------
affected = get_dependent_cells(model, "Inputs!B2") - {"Inputs!B2"}
print(f"\nChanging Inputs!B2 (rate) affects {len(affected)} cells, e.g.:", sorted(affected)[:6])

# --- The parsed formula (AST) ---------------------------------------------------
def show_tree(node, depth=1):
    """Print an xlcalc AST: FunctionNode/OperatorNode have children, the rest are leaves."""
    kind = type(node).__name__.removesuffix("Node")
    print("  " * depth + f"{kind}: {node.tvalue}")
    for child in getattr(node, "args", None) or []:
        show_tree(child, depth + 1)
    for side in ("left", "right"):
        if getattr(node, side, None) is not None:
            show_tree(getattr(node, side), depth + 1)


cell = model.get_cell_by_canonical_address("Summary!B7")
print("\nSummary!B7 formula:", cell.formula)
print("Parsed tree:")
show_tree(cell.parsed_ast)

# --- Supported functions ----------------------------------------------------------
print(f"\n{len(FUNCTIONS)} supported Excel functions:")
print(", ".join(sorted(FUNCTIONS)))

# --- Circular references ------------------------------------------------------------
# A2 depends on A3 and A3 depends on A2. Excel needs "Enable iterative calculation"
# for this; xlcalc needs EvalContext(iterative=True).
circ = Model()
put(circ, "Sheet1!A1", 100)
put(circ, "Sheet1!A2", formula="=A1 + A3*0.1")
put(circ, "Sheet1!A3", formula="=A2*0.5")
circ.build_code()

print("\nCircular reference A2 = A1 + 0.1*A3, A3 = 0.5*A2")
logging.getLogger("xlcalc").setLevel(logging.CRITICAL)  # it also logs the cycle as an error
try:
    evaluate(circ, "Sheet1!A2", EvalContext(circ))
except RuntimeError as e:
    print("  without iteration ->", e)

ctx = EvalContext(circ, iterative=True, max_iterations=200, max_change=1e-9)
print("  with iteration    ->", evaluate(circ, "Sheet1!A2", ctx),
      " (exact answer:", 100 / 0.95, ")")
