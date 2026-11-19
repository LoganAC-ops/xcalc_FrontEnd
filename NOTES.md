# xlcalc — evaluation notes

Working notes on `xlcalcmodel` 3.6.7 (imported as `xlcalc`, author Derek Pierson,
<https://github.com/mustseetv314/xlcalcmodel>). Covers what's broken, what we'd want
improved, and where the library is worth building on.

**Verified against:** Python 3.14.0, numpy 2.4.4, pandas 3.0.2, scipy 1.18.1,
openpyxl 3.1.5, xlwings 0.37.4, Windows 11. Every claim below was reproduced on
this machine on 2026-09-22 — findings are not copied from upstream docs.

**Bottom line:** the engine is sound for arithmetic, logic, lookups and the
dependency graph — 57 of 61 formula cells in our sample workbook match Excel to
1e-9. The problems are all at the edges: a narrow function library, two
silent-wrong-answer failure modes, and a hard Excel dependency on load. It is
usable today behind a validation gate; it is not yet something to point at an
arbitrary workbook unattended.

---

## 1. Issues

Ranked by how much damage each can do, not how often it fires. The first two are
the dangerous ones because **they produce wrong numbers without raising**.

### 1.1 Unsupported functions silently return `0.0` — SEVERITY: CRITICAL

No exception, no warning, no `#NAME?`. The cell just evaluates to zero and
everything downstream quietly absorbs it.

```
=IPMT(0.05/12,1,360,-250000)   -> 0.0      (should be ~-1041.67)
=FV(0.05/12,360,-1500)         -> 0.0      (should be ~1,248,000)
=SUBSTITUTE("a-b","-","+")     -> 0.0      (should be "a+b")
```

This is the single biggest risk in adopting the library. A model can be 95%
correct and confidently hand back a total that's wrong by the size of whatever
landed in an unsupported cell. Nothing in the library's own API flags it —
`unsupported_functions()` in [xlc_helpers.py](xlc_helpers.py) is ours, not theirs.

**Mitigation in place:** run `unsupported_functions(model)` before trusting any
result. [04_check_workbook.py](04_check_workbook.py) does this.

### 1.2 `COUNTIF` / `SUMIF` / `COUNTIFS` / `SUMIFS` are entirely broken — SEVERITY: CRITICAL

These are registered as supported, so the unsupported-function check does **not**
catch them. They raise `ValueExcelError` on every call:

```
=COUNTIF(A1:A4,">1300")  -> ValueExcelError("Cannot cast type <class 'numpy.int64'> => 1200")
=SUMIF(A1:A4,">1300")    -> ValueExcelError(...)
=COUNTIF(A1:A4,1400)     -> ValueExcelError(...)
```

Worth correcting the README's diagnosis here: this is **not** a criteria-parsing
problem. The numeric-literal criteria `1400` fails identically to the string
criteria `">1300"`, and the error names the *source data* (`1200`), not the
criteria.

**Root cause, traced in the source.** `ExcelType.cast_from_native` at
[xlcalc_source/funcs/func_xltypes.py:75](xlcalc_source/funcs/func_xltypes.py#L75)
does an **exact-type** dictionary lookup:

```python
cast_cls = NATIVE_TO_XLTYPE.get(type(value))     # type(), not isinstance()
if cast_cls:
    return cast_cls(value)
raise xlerrors.ValueExcelError(f"Cannot cast type {type(value)} => {value}")
```

`NATIVE_TO_XLTYPE` is keyed on `int`, `float` and `bool`. Ranges arrive as numpy
arrays, so their elements are `np.int64` / `np.float64` — which are *not* `int`
or `float` by exact type, miss the lookup, and raise. A second guard at
[func_xltypes.py:41](xlcalc_source/funcs/func_xltypes.py#L41)
(`assert isinstance(value, cls.native_types)`) rejects them again, and the
comparison operators then return `np.bool_`, which fails the same way a third time.

Nothing here is specific to criteria handling — `xlcriteria.py` is correct. This
is a numpy 2 compatibility gap in the type system, and these functions would have
worked under numpy 1.x where `np.float64` subclassed `float`.

**A working fix — confirmed, ~5 lines.** Registering the numpy scalar types
against the existing classes repairs the family:

```python
import numpy as np
from xlcalc.funcs import func_xltypes as fx
Number, Boolean = fx.NATIVE_TO_XLTYPE[float], fx.NATIVE_TO_XLTYPE[bool]
Number.native_types  = tuple(Number.native_types)  + (np.integer, np.floating)
Boolean.native_types = tuple(Boolean.native_types) + (np.bool_,)
for t, c in [(np.int64, Number), (np.float64, Number), (np.bool_, Boolean)]:
    fx.NATIVE_TO_XLTYPE[t] = c
```

Results after patching: `COUNTIF(...,">1300")` → `2.0` ✓, `SUMIF` → `2900.0` ✓,
`COUNTIF(...,1400)` → `1.0` ✓, `SUMIFS` → `4100.0` ✓. Against the real workbook,
`Summary!B9` now returns `12.0`, **matching Excel exactly** — that mismatch in §1
disappears.

`COUNTIFS` is **not** fixed by this and fails separately with
`"COUNTIFS expects each 'range' argument to be an XlArray"` — a distinct
argument-marshalling bug that still needs tracing.

**Workaround if not patching, confirmed working:**

| Broken | Replacement | Verified |
|---|---|---|
| `=COUNTIF(A1:A4,">1300")` | `=SUMPRODUCT((A1:A4>1300)*1)` | → `2.0` ✓ |
| `=SUMIF(A1:A4,">1300")` | `=SUMPRODUCT((A1:A4>1300)*A1:A4)` | → `2900.0` ✓ |

### 1.3 Function coverage is thin — 116 functions — SEVERITY: HIGH

That's roughly 20% of Excel's surface, and the gaps are not in exotic corners.
The financial gap is the one that stings, because financial modeling is the
obvious use case for a headless Excel engine:

- **Financial:** `IPMT`, `PPMT`, `FV`, `NPER`, `RATE`, `MIRR`, `DB`, `DDB` — all
  missing. `PMT`, `PV`, `NPV`, `IRR`, `XIRR`, `XNPV`, `SLN`, `VDB` are present.
  So you can compute a payment but not split it into interest and principal, and
  you can't solve for term or rate. Our own sample workbook has to hand-roll the
  amortization split in [make_sample_workbook.py](make_sample_workbook.py) for
  exactly this reason.
- **Lookup/reference:** `INDEX`, `OFFSET`, `INDIRECT`, `XLOOKUP` missing —
  though `MATCH`, `VLOOKUP`, `HLOOKUP`, `CHOOSE` are present. No `INDEX` means no
  `INDEX/MATCH`, which is the idiom most real workbooks reach for.
- **Logic:** `IFS`, `SWITCH` missing. `IF`, `IFERROR` present.
- **Text:** `TEXT`, `TEXTJOIN`, `SUBSTITUTE` missing.
- **Aggregation:** `AVERAGEIF(S)`, `MAXIFS`, `MINIFS`, `SUBTOTAL`, `AGGREGATE` missing.
- **Date:** `NETWORKDAYS`, `WORKDAY`, `DAYS360` missing.
- **Modern:** `LET`, `LAMBDA`, `FILTER`, `SORT`, `UNIQUE` missing — i.e. no dynamic
  arrays at all.

### 1.4 Stale values: formulas return Excel's old numbers — SEVERITY: HIGH

A formula that reads another formula cell hands back that cell's *stored* value
unless the cell is flagged `need_update`. After loading a workbook, change an
input and the change may silently fail to propagate — you get Excel's numbers
from whenever the file was last saved, which look perfectly plausible.

This is arguably a design choice (it's an incremental calculator), but the
default is backwards: correctness should be the default and staleness the opt-in.

**Mitigation in place:** `set_value()` walks `get_dependent_cells()` and flags
everything downstream; `mark_all_dirty()` flags every formula. Both in
[xlc_helpers.py](xlc_helpers.py). Note that 04's Excel-comparison would report a
false 100% match without `mark_all_dirty()` — it would be comparing Excel's
stored values against themselves.

### 1.5 `YEARFRAC` basis 1 disagrees with Excel — SEVERITY: MEDIUM

Over a 30-year term: xlcalc `30.000104798263344` vs Excel `30.000706526538902`.
xlcalc uses Actual/Actual AFB; Excel uses its own averaging method. Small, but
it compounds in day-count-sensitive work (accrued interest, bond math), and it's
a *wrong answer*, not an error.

### 1.6 Loading requires a real, installed Excel — SEVERITY: MEDIUM

`xlcalc.loader` drives Excel through xlwings, despite upstream docs implying
Excel isn't needed. ~20–30s per load, Windows/macOS only, and a non-starter in
CI, Docker or Linux.

Mitigated but not solved by the load-once-then-pickle pattern: someone with Excel
has to produce the `.pkl.gz` in the first place. **Untested idea worth pursuing:**
openpyxl can read formulas without Excel — a pure-openpyxl loader may be viable,
losing only Excel's cached values (which we currently rely on for the 04 diff).

### 1.7 Smaller sharp edges — SEVERITY: LOW

| Issue | Detail |
|---|---|
| `persist_to_pickle_file` after `build_code()` | Raises `PicklingError` — compiled functions aren't picklable. Save first, or reload with `build_code=True` |
| `to_json()` / `from_json()` round trip | Fails: `Invalid cell reference: Inputs!$A$1` |
| `CellAddress.from_string("Inputs!B1")` | Raises. Sheet must be assigned separately — hence `addr()` |
| Inconsistent result types | `float`, `np.float64`, and xlcalc's own `Number` come back from the same API — hence `to_python()` |
| Dates | Loader stores Python datetimes, which xlcalc's own date functions reject; typed-in dates become pseudo-formulas like `=45306` |
| Per-cell DEBUG spam | Loader prints a line per cell; we suppress with `redirect_stdout` |
| Install is fragile | Needs `--no-deps` + manual deps. Plain `pip install` backtracks on `yearfrac`/numpy 2 and fails to build |
| Untrusted model files | `construct_from_pickle_file` / `construct_from_json_file` execute code from the file — pickle deserialization. Only load files we generated |

### 1.8 What works well — worth recording

Not everything is a caveat. These were solid:

- **Numerics match Excel** to 1e-9 across PMT, SUM, VLOOKUP, IF, EDATE, string
  concat and a 12-row chained amortization table.
- **The dependency graph is genuinely good.** `get_upstream_cells` /
  `get_dependent_cells` / `model.dependency_graph` all behave, transitively and
  across sheets. This is the most under-sold part of the library.
- **Circular references converge correctly.** `EvalContext(iterative=True)` gives
  `105.26315789472656` against an exact `105.26315789473685` — 1e-11, tunable via
  `max_change`.
- **It's fast.** 12 full scenario recalcs in 0.03s; model reload from pickle in
  0.02s. Roughly 400 recalcs/sec on this workbook, against ~20–30s to boot Excel
  once. That ratio is the whole argument for the library.
- **The AST is inspectable**, which makes formula linting and translation
  realistic (see §3.5).

---

## 2. Areas for improvement

### 2.1 In our code (ours to do)

1. **Fold the safety checks into the load path.** Right now `unsupported_functions()`
   is something you have to remember to call. `load_workbook()` should run it and
   raise — or at minimum warn loudly — unless the caller passes something like
   `allow_unsupported=True`. Silent zeros are too dangerous to leave opt-in.
2. **Apply the `*IF` family fix.** §1.2 has a confirmed ~5-line shim that repairs
   `COUNTIF`/`SUMIF`/`SUMIFS` and makes `Summary!B9` match Excel. Ship it as an
   importable `xlc_patches.py` applied at import time, and have the checker treat
   `COUNTIFS` as unsupported until its separate array-marshalling bug is traced.
3. **Add a formula rewriter** for the known workarounds: `COUNTIF`→`SUMPRODUCT`,
   and potentially `INDEX/MATCH`→`VLOOKUP` where the shape allows. Applied at
   load time, this quietly widens compatibility.
4. **Package `xlc_helpers.py` properly.** It's the genuinely reusable asset here
   and it's currently a loose module next to five scripts. Make it a small
   installable package with tests.
5. **No tests.** The examples are demos that print, not assertions. The gotchas
   catalogued here are exactly what a regression suite should pin — especially
   since a future numpy or xlcalc release may fix `COUNTIF` and we'd want to know.
6. **No `requirements.txt` / lockfile.** Given how fragile the install is (§1.7),
   the exact working dependency set should be committed, with the `--no-deps`
   sequence scripted.
7. **Not under version control.** No git repo. Everything above argues for one.
8. **Machine-readable check output.** `04_check_workbook.py` prints. It should
   also emit JSON/CSV and exit non-zero on mismatch, so it can gate a pipeline.

### 2.2 Upstream (worth filing / contributing)

1. Raise `#NAME?` instead of returning `0.0` for unimplemented functions. This is
   a small change with an outsized correctness payoff.
2. Fix the numpy 2 cast in the type system — make `cast_from_native` use
   `isinstance` rather than an exact `type()` lookup, or register the numpy
   scalar types. §1.2 has the traced cause, line numbers and a working patch;
   this is the most valuable thing we could contribute back.
3. Relax the `yearfrac` pin so a plain `pip install` works under numpy 2.
4. Add an openpyxl-based loader so Excel isn't required.
5. Fill the financial gap — `IPMT`, `PPMT`, `FV`, `NPER`, `RATE` are the obvious
   first five, and numpy-financial (already a dependency) implements all of them.
6. Fix `to_json`/`from_json` round-tripping — it's the safe alternative to pickle.
7. Demote the per-cell loader `print` to `logging.debug`.

---

## 3. Use cases to develop

Ordered by ratio of value to effort. The theme: xlcalc is most valuable where a
spreadsheet holds business logic that needs to run **many times** or **under
test** — not where it's used as a file format.

### 3.1 Spreadsheet regression testing — highest value, build first

Point [04_check_workbook.py](04_check_workbook.py) at real workbooks in CI. Every
formula recalculated and diffed against Excel's stored value, so a broken
workbook fails a build instead of a quarter-end. Needs the JSON output and exit
code from §2.1.8, and it is genuinely novel — there is no good off-the-shelf tool
for "did someone break this spreadsheet?"

### 3.2 Monte Carlo / scenario engines over existing models

[03_what_if_scenarios.py](03_what_if_scenarios.py) runs 12 scenarios in 0.03s.
That extrapolates to ~400/sec, i.e. 10k+ iterations in well under a minute — with
no Excel, no Data Tables, no copy-paste. Takes a model a business team already
owns and trusts, and wraps it in real statistics. This is the most
immediately sellable use of the library.

### 3.3 Spreadsheet → API

Load once, pickle, serve behind FastAPI: inputs in as JSON, outputs out. The
business keeps authoring pricing/quoting logic in Excel; downstream systems call
an endpoint. The pickle reloads in 0.02s, so it can sit in a warm process or even
load per-request. Gated on §1.1/§1.2 validation — this is precisely the context
where a silent `0.0` becomes a wrong customer-facing number.

### 3.4 Workbook auditing and documentation

§1.8's dependency graph is the asset. From `get_upstream_cells` /
`get_dependent_cells` you can generate, for a workbook nobody understands:
impact analysis ("what breaks if I change this input?" — our rate cell touches 59
cells), input/output inventories, orphaned-cell detection, cross-sheet dependency
diagrams, and hardcoded-constant hunting. Read-only, so none of the calculation
bugs apply — **this works reliably today**, which makes it the safest thing on
this list.

### 3.5 Formula linting and migration

The parsed AST (§1.8) makes it practical to flag deprecated patterns, find
volatile functions, detect inconsistent formulas across a row, or mechanically
translate workbook logic into Python/SQL. The AST walker in
[05_dependencies_and_circular.py](05_dependencies_and_circular.py) is the seed.

### 3.6 Goal seek and optimization at scale

The bisection in `03` is ~15 lines. Generalize it: multi-variable solving via
scipy (already a dependency), constraint satisfaction, batch goal-seek across
hundreds of rows — all things Excel's own Goal Seek does one cell at a time,
manually.

### 3.7 Speculative — needs the Excel dependency solved first

Server-side recalculation for a web app, spreadsheet diffing that compares
*logic* rather than values, and using workbooks as versionable test fixtures. All
blocked on §1.6 until a pure-openpyxl loader exists.

---

## 4. Recommendation

**Adopt for read-only analysis (§3.4) now** — the dependency graph is reliable
and none of the calculation bugs touch it.

**Adopt for calculation behind a mandatory validation gate** — every workbook
passes `04_check_workbook.py` before anything trusts its numbers, and that gate
becomes a hard CI requirement rather than a convention. The §1.1 and §1.2 silent
failures are survivable when checked and unacceptable when not.

**Don't yet** put it anywhere the workbook can change without re-validation, or
anywhere Excel can't be installed to do the initial load.

The highest-leverage next step is §2.1.1 — make the load path refuse to hand back
a model containing unsupported functions unless explicitly overridden. That single
change converts the library's worst failure mode from silent to loud.
