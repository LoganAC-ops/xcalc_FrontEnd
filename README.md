# xlcalcmodel examples

Runnable examples for [`xlcalcmodel`](https://github.com/mustseetv314/xlcalcmodel) 3.6.7, a Python engine that
calculates Excel formulas. **Import it as `xlcalc`**, not `xlcalcmodel`.

## Run order

```powershell
python make_sample_workbook.py          # creates loan_model.xlsx
python 01_build_model_in_code.py        # no Excel needed
python 02_load_workbook.py              # opens Excel in the background (~20s), saves loan_model.pkl.gz
python 03_what_if_scenarios.py          # reloads the saved model, no Excel
python 04_check_workbook.py
python 05_dependencies_and_circular.py
```

| File | Shows |
|---|---|
| `01_build_model_in_code.py` | The core workflow: `Model()` → add cells → `build_code()` → calculate. Change an input, recalculate |
| `02_load_workbook.py` | Load an .xlsx through Excel, save the model so later runs don't need Excel |
| `03_what_if_scenarios.py` | Run the workbook's logic across a grid of inputs, plus a goal seek |
| `04_check_workbook.py` | **Run this on any real workbook.** Finds unsupported functions and diffs every formula against Excel's own result |
| `05_dependencies_and_circular.py` | Precedents/dependents, parsed formulas, the list of supported functions, circular references |
| `xlc_helpers.py` | Helpers the examples import. They work around the gotchas below |

## The workflow

```python
from xlcalc import Model, EvalContext
from xlc_helpers import load_workbook, set_value, evaluate

model = load_workbook(r"C:\full\path\book.xlsx")    # needs Excel, slow
model.persist_to_pickle_file("book.pkl.gz")         # save BEFORE build_code()

model = Model.construct_from_pickle_file("book.pkl.gz", build_code=True)  # fast, no Excel
set_value(model, "Inputs!B2", 0.05)                 # change an input
evaluate(model, "Summary!B1")                       # calculate an output
```

## Gotchas found while testing

| Problem | What happens | Workaround |
|---|---|---|
| **Stale values** | A formula reading another formula cell returns that cell's stored value unless it's flagged for recalculation. After loading a workbook, results can silently be Excel's old numbers | `set_value()` flags everything downstream. `mark_all_dirty()` flags every formula |
| **Unsupported functions return 0** | No error. `INDEX`, `TEXT`, `XLOOKUP`, `IFS`, `SWITCH`, `OFFSET`, `INDIRECT`, `TEXTJOIN`, `AVERAGEIF(S)`, `MAXIFS`, `NETWORKDAYS`, `WORKDAY`, `DAYS360`, `LET`, `FILTER`, `SORT`, `UNIQUE` are all missing | `unsupported_functions(model)` lists them. See example 04 |
| **`COUNTIF`, `SUMIF`, `COUNTIFS`, `SUMIFS` are broken** | Always return `#VALUE!` (on this Python 3.14 / numpy 2 setup) | Rewrite as `SUMPRODUCT`, e.g. `=SUMPRODUCT((C2:C13>1300)*1)` |
| **`YEARFRAC(...,1)` differs from Excel** | Uses Actual/Actual AFB rather than Excel's averaging method. 30.000105 vs Excel's 30.000707 over 30 years | Check with example 04 if you rely on it |
| **Dates** | The loader stores dates as Python datetimes, which date functions reject | `load_workbook()` converts them to Excel serial numbers. `from_serial()` turns results back into dates |
| **Saving after `build_code()`** | `persist_to_pickle_file` raises `PicklingError` | Save first, or reload with `build_code=True` |
| **`to_json()` / `from_json()`** | Round trip fails (`Invalid cell reference: Inputs!$A$1`) | Use `persist_to_pickle_file` / `persist_to_json_file` instead |
| **Cell addresses** | `CellAddress.from_string("Inputs!B1")` raises. Sheet must be set separately | `xlc_helpers.addr("Inputs!B1")` |
| **Result types** | Mix of `float`, `np.float64` and xlcalc's `Number` | `evaluate()` returns plain Python values |
| **Excel required to load** | Loading uses xlwings, which drives a real copy of Excel, despite the README saying Excel isn't needed | Load once, save the model, reuse the saved file |
| **Untrusted files** | `construct_from_json_file` / `construct_from_pickle_file` can execute code stored in the file | Only load model files you created |

## Where to read the source

`C:\Users\logan.mckeown\AppData\Roaming\Python\Python314\site-packages\xlcalc`

- `model.py`: `Model`, `Sheet`, `Cell`, saving/loading
- `loader.py`: reading .xlsx through Excel
- `evaluator.py`: `EvalContext`, how a cell gets calculated
- `incremental_calculator.py`: `recalc_or_iterate`, upstream/downstream lookups, circular-reference iteration
- `compiler.py`, `parser.py`: formula → AST → Python function
- `funcs/`: every Excel function, one file per category. Good for checking how a specific function behaves
