# Changelog

## 2026-10-20

- Added `webapp/`, a Claude-style POC frontend over xlcalc. React (Vite + TypeScript) client at `webapp/frontend/` talks to a FastAPI backend at `webapp/backend/` via a Vite dev proxy. Lives alongside the example scripts and reuses `xlc_helpers.py` directly
- Added `webapp/backend/main.py` with endpoints for project list/get/delete/patch, .xlsx or .pkl.gz upload, streaming .xlsx compile (NDJSON progress), input/output auto-detection, cosmetic test audit (wraps `unsupported_functions`), single-shot evaluate, and CSV batch processing. Each project persists as `<id>.pkl.gz` + `<id>.meta.json` under `webapp/projects/`
- Seeded the sidebar with the existing `loan_model.pkl.gz` by auto-copying it into `webapp/projects/` on backend startup with a hand-authored metadata block (4 inputs, 7 Summary outputs) so the first-run demo has no prerequisites
- Added React components for the shell (`App.tsx`, `Sidebar.tsx`, `HomePane.tsx`), a 4-step New Project wizard (`UploadStep`, `CompileStep`, `TestStep`, `ToolSelectStep`), and a tool workspace that tabs between 6 tool cards
- Wired two of the six tools end-to-end against the real backend: Scenario Runner (form → evaluate → outputs table, with save-scenario comparison) and Batch Processor (CSV template download → upload → preview → download results). The remaining four (REST, Sensitivity, Goal Seek, Chat) render as "Coming soon" placeholders
- Added `webapp/frontend/src/styles.css` — a Claude-inspired dark theme (orange accent, muted neutrals, panel cards)
- Added `webapp/start-dev.ps1` to spawn both dev servers in separate PowerShell windows and `npm install` on first run, plus `webapp/README.md` documenting the architecture, what's wired vs. deliberately mocked, and the known Vite 5 / esbuild localhost-dev-server advisories

## 2026-09-22

- Added `NOTES.md`, an evaluation of xlcalc covering issues, improvements, and use cases to develop. Every claim was reproduced by re-running the examples rather than carried over from `README.md`
- Corrected the `COUNTIF`/`SUMIF` diagnosis recorded on 2026-09-18: the failure is a numpy 2 casting bug in range coercion, not criteria parsing. Numeric criteria (`=COUNTIF(A1:A4,1400)`) fail identically to string criteria, and the error names the source data rather than the criteria — so the whole `*IF` family likely shares one upstream fix
- Documented a function inventory taken from `FUNCTIONS`: 116 supported. `IPMT`, `PPMT`, `FV`, `NPER`, `RATE`, `MIRR`, `DB`, `DDB` are all missing while `PMT`/`PV`/`IRR`/`XIRR`/`NPV` are present, which is why `make_sample_workbook.py` hand-rolls the amortization split. `SUBSTITUTE`, `SUBTOTAL` and `AGGREGATE` are also missing and were not previously noted
- Verified the `SUMPRODUCT` workarounds return correct values (2.0 and 2900.0) instead of assuming they work
- Copied the xlcalc 3.6.7 source into `xlcalc_source/` (27 files, ~5,800 lines, bytecode excluded) as a read-only reference, with `READING_GUIDE.md` tracing one formula through parse → compile → dependency graph → evaluate → incremental recalc
- Traced the `COUNTIF`/`SUMIF` root cause to `func_xltypes.py:75`, where `cast_from_native` does an exact `type()` lookup against a table keyed on `int`/`float`/`bool`. Range elements arrive as `np.int64`/`np.float64` and miss it; two further guards reject them at `func_xltypes.py:41` and on the `np.bool_` comparison result. `xlcriteria.py` is not at fault. This supersedes the vaguer "casting bug in range coercion" noted earlier today
- Confirmed a ~5-line shim registering the numpy scalar types repairs `COUNTIF`, `SUMIF` and `SUMIFS`, and makes `Summary!B9` match Excel at 12.0. `COUNTIFS` fails separately with an XlArray marshalling error and remains untraced. Recorded in `NOTES.md` §1.2; not yet applied as code
- Established that `loan_model.xlsx` holds 61 formulas across Schedule, Summary and Checks — the `Inputs` sheet's 0 formulas is by design, as it holds typed-in values. Also found that openpyxl reads every formula cell as `None` under `data_only=True` because it never calculates, which is why the loader needs real Excel and why a pure-openpyxl loader would silently disable the Excel-comparison check in `04_check_workbook.py`

## 2026-09-18

- Installed `xlcalcmodel` 3.6.7 with `--no-deps`, then its dependencies (jsonpickle, numpy-financial, mock, scipy, xlwings, tqdm) separately. A normal install fails because pip sees the installed `yearfrac` 0.4.8 as conflicting with numpy 2 (it declares `numpy<2`), backtracks to `yearfrac` 0.4.7, and that version's `setup.py` won't build
- Added `xlc_helpers.py` with wrappers for cell addressing, result conversion, quiet workbook loading, and unsupported-function detection
- Added a stale-value workaround in `set_value()`: it flags every downstream formula for recalculation. Without it, formulas reading other formula cells return values stored at load time, so changed inputs silently don't propagate
- Added date handling in `load_workbook()`. The xlwings loader stores dates as datetimes, which xlcalc's date functions reject, and it turns typed-in dates into pseudo-formulas like `=45306`
- Added `make_sample_workbook.py`, which builds `loan_model.xlsx` (inputs, 12-month amortization, summary, and a `Checks` sheet using unsupported `INDEX`/`TEXT` on purpose)
- Added examples `01`–`05`: building a model in code, loading and saving a workbook, what-if scenarios with goal seek, checking a workbook against Excel, and dependency graphs with circular references
- Added `README.md` covering the workflow and the library issues found during testing: broken `COUNTIF`/`SUMIF` family, non-Excel `YEARFRAC` basis 1, `PicklingError` when saving after `build_code()`, and broken `to_json`/`from_json` round trip
