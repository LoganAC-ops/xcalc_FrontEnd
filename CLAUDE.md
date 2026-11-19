# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A Python evaluation and example suite for `xlcalcmodel` 3.6.7 (imported as `xlcalc`): a headless Excel formula engine that parses, compiles, and evaluates Excel formulas in pure Python without opening Excel at runtime. This project demonstrates the library's workflow and documents its limitations for production use (Accenture / Mondelez APO engagement).

## Running Scripts

No build step. Run scripts in this order — each depends on outputs from earlier steps:

```powershell
python make_sample_workbook.py        # Creates loan_model.xlsx (fast, no deps)
python 01_build_model_in_code.py      # Pure Python, no Excel
python 02_load_workbook.py            # Requires Excel installed; ~20-30s; saves loan_model.pkl.gz
python 03_what_if_scenarios.py        # Requires loan_model.pkl.gz
python 04_check_workbook.py           # Requires loan_model.pkl.gz
python 05_dependencies_and_circular.py # Requires loan_model.pkl.gz
```

Only `02_load_workbook.py` requires Excel to be installed (uses xlwings). Once `loan_model.pkl.gz` exists, all other scripts run without Excel.

## Key Files

- **[xlc_helpers.py](xlc_helpers.py)** — import this in any new script. Papers over library rough edges:
  - `addr("Sheet!A1")` — parses sheet-qualified refs (the library's own `CellAddress.from_string` cannot)
  - `set_value(model, ref, value)` — sets an input and marks downstream formulas dirty
  - `mark_all_dirty(model)` — forces full recalculation
  - `evaluate(model, ref)` — calculates a cell and returns a plain Python scalar
  - `load_workbook(path)` — wraps xlwings loader, suppresses spam, converts datetimes to Excel serials
  - `unsupported_functions(model)` — returns `{func_name: [cells]}` for silently-broken functions

- **[xlcalc_source/](xlcalc_source/)** — read-only copy of xlcalcmodel 3.6.7 source for debugging. `READING_GUIDE.md` inside traces one formula through all five processing stages.

## Architecture: xlcalc Formula Lifecycle

A formula like `=PMT(Inputs!B2/12, ...)` passes through five stages:

| Stage | File | Role |
|---|---|---|
| Text → AST | `xlcalc_source/parser.py` | Shunting-yard tokenizer |
| AST → Python | `xlcalc_source/compiler.py` | Compiles formula to a Python function on the `Cell` |
| Dependency graph | `xlcalc_source/dependency.py` | Builds who-reads-whom for incremental recalc |
| Evaluation | `xlcalc_source/evaluator.py` | `EvalContext` resolves refs, calls compiled function |
| Incremental recalc | `xlcalc_source/incremental_calculator.py` | `recalc_or_iterate`, circular-ref convergence |

## Critical Known Bugs

Two bugs silently produce wrong numbers — always check before trusting output:

1. **Unsupported functions return `0.0` without any warning.** Affects: `INDEX`, `TEXT`, `XLOOKUP`, `IFS`, `OFFSET`, `INDIRECT`, `TEXTJOIN`, and ~15 others. Use `unsupported_functions(model)` from `xlc_helpers.py` to audit.

2. **`COUNTIF` / `SUMIF` / `SUMIFS` are broken.** Root cause: `xlcalc_source/funcs/func_xltypes.py` line 75 — `cast_from_native` uses `type()` keyed on `int`/`float`, but numpy 2 range elements arrive as `np.int64`/`np.float64`. A 5-line shim in `func_xltypes.py` fixes `COUNTIF`/`SUMIF`/`SUMIFS` (not `COUNTIFS`, which has a separate bug). See `NOTES.md` for the exact fix.

## Environment Notes

- Python 3.14 (CPython 3.14.0)
- Key packages installed with `--no-deps` due to a `yearfrac`/numpy-2 pip conflict: `xlcalcmodel`, `numpy`, `pandas`, `scipy`, `openpyxl`, `xlwings`
- No `requirements.txt` or lockfile exists — see `NOTES.md` §2.1.6
- No git history — see `NOTES.md` §2.1.7
- After calling `model.build_code()`, do **not** pickle the model — it causes a `PicklingError`. Load from `loan_model.pkl.gz` instead (reloads in ~0.02s)
