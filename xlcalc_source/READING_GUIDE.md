# Reading guide — xlcalc source

A read-only copy of `xlcalcmodel` 3.6.7's source, taken 2026-09-22 from
`C:\Users\logan.mckeown\AppData\Roaming\Python\Python314\site-packages\xlcalc`.
27 files, ~5,800 lines, `__pycache__` excluded.

**This is a copy for reading. Editing it changes nothing** — Python still imports
the installed package in site-packages.

## Follow one formula through the system

The clearest way in. `=PMT(Inputs!B2/12, ...)` becomes a number like this:

| Step | File | Lines | What happens |
|---|---|---|---|
| 1. Text → tokens → AST | [parser.py](parser.py) | 672 | The biggest file. Shunting-yard tokenizer plus AST node classes |
| 2. AST → Python source | [compiler.py](compiler.py) | 154 | Each formula becomes a compiled Python function attached to the cell |
| 3. Who-depends-on-whom | [dependency.py](dependency.py) | 255 | Builds the precedent/dependent graph |
| 4. Run it | [evaluator.py](evaluator.py) | 221 | `EvalContext` — resolves references, calls the compiled function |
| 5. Recalc only what's stale | [incremental_calculator.py](incremental_calculator.py) | 196 | `recalc_or_iterate`, the `need_update` flag, circular-reference iteration |

## The rest

| File | Lines | Why you'd open it |
|---|---|---|
| [model.py](model.py) | 350 | `Model`, `Sheet`, `Cell`; pickle/JSON persistence. Start here for the public API |
| [funcs/func_xltypes.py](funcs/func_xltypes.py) | 454 | Excel's type system — `Number`, `Text`, `Boolean`, `Array`, and the coercion rules. **Where the `COUNTIF` bug lives** (see NOTES.md §1.2) |
| [xltypes.py](xltypes.py) | 189 | Cell/range value wrappers, distinct from the above |
| [references.py](references.py) | 140 | `CellAddress`, range parsing. The `"Sheet!A1"` parsing limitation is here |
| [loader.py](loader.py) | 102 | Short, worth reading. The whole xlwings/Excel dependency is these 100 lines |
| [funcs/xlerrors.py](funcs/xlerrors.py) | 78 | `#VALUE!`, `#REF!` etc. as Python exceptions |
| [funcs/xlcriteria.py](funcs/xlcriteria.py) | 84 | `COUNTIF`-style criteria parsing. Correct as written — the bug is upstream of it |

## Function implementations

One file per category under [funcs/](.). This is where to check how any specific
Excel function actually behaves, and to confirm whether one exists at all:

- [math_funcs.py](funcs/math_funcs.py) — 645 lines, the largest
- [financial_funcs.py](funcs/financial_funcs.py) — `PMT`, `PV`, `NPV`, `IRR`, `XIRR`. Note what is *absent*: `IPMT`, `PPMT`, `FV`, `NPER`, `RATE`
- [lookup.py](funcs/lookup.py) — `VLOOKUP`, `HLOOKUP`, `MATCH`. No `INDEX`
- [date_funcs.py](funcs/date_funcs.py) — includes the `YEARFRAC` basis-1 discrepancy
- [statistics.py](funcs/statistics.py), [logical_funcs.py](funcs/logical_funcs.py),
  [text.py](funcs/text.py), [information_funcs.py](funcs/information_funcs.py),
  [engineering_funcs.py](funcs/engineering_funcs.py)
- [xl.py](funcs/xl.py) — the registration decorator that populates `FUNCTIONS`

To list what exists without reading files:

```python
from xlcalc import FUNCTIONS
print(len(FUNCTIONS))              # 116
print("INDEX" in FUNCTIONS)        # False
```

## Refreshing this copy

It will drift if the package is upgraded. Regenerate with:

```powershell
$src = "$env:APPDATA\Python\Python314\site-packages\xlcalc"
Remove-Item -Recurse -Force xlcalc_source\* -Exclude READING_GUIDE.md
Copy-Item -Recurse "$src\*" xlcalc_source\ -Exclude __pycache__
```
