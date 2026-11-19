"""
Small helpers that smooth over xlcalc's rough edges. Imported by the examples.

xlcalc's own API is fairly low-level and has a few traps:
  - CellAddress.from_string() can't parse "Sheet!A1", so the sheet must be set separately
  - results come back as a mix of float, np.float64, and xlcalc's own Number wrapper
  - the Excel loader prints a DEBUG line for every single cell
  - the loader stores dates as Python datetimes, which date functions reject
  - STALE VALUES: a formula that reads another formula cell gets that cell's
    stored value unless it's flagged need_update. So after changing an input,
    every downstream formula must be flagged - set_value() does this.
These helpers hide that so the examples can focus on the workflow.
"""
import contextlib
import datetime as dt
import io
import re

import numpy as np

from xlcalc import FUNCTIONS, EvalContext, Model
from xlcalc.incremental_calculator import get_dependent_cells, recalc_or_iterate
from xlcalc.references import CellAddress

EXCEL_EPOCH = dt.datetime(1899, 12, 30)


def to_serial(d) -> float:
    """date/datetime -> Excel serial number (what Excel stores internally)."""
    if not isinstance(d, dt.datetime):
        d = dt.datetime(d.year, d.month, d.day)
    return (d - EXCEL_EPOCH).total_seconds() / 86400


def from_serial(n: float) -> dt.date:
    """Excel serial number -> date. Use on results of DATE/EDATE/EOMONTH etc."""
    return (EXCEL_EPOCH + dt.timedelta(days=float(n))).date()


def addr(ref: str) -> CellAddress:
    """'Inputs!B2' -> CellAddress with sheet='Inputs'. Bare 'B2' -> Sheet1."""
    sheet, _, local = ref.rpartition("!")
    a = CellAddress.from_string(local)
    a.sheet = sheet.strip("'") or "Sheet1"
    return a


def put(model: Model, ref: str, value=None, formula=None) -> None:
    """Add/replace a cell. Formulas must start with '='."""
    model.set_cell_value(addr(ref), value=value, formula=formula)


def set_value(model: Model, ref: str, value) -> None:
    """Change an input cell's value and flag everything downstream for recalculation.
    Dates are converted to Excel serial numbers. Call after model.build_code()."""
    cell = model.get_cell_by_canonical_address(ref)
    if cell is None:
        raise KeyError(f"{ref} is not in the model")
    if isinstance(value, (dt.date, dt.datetime)):
        value = to_serial(value)
    cell.value = value
    cell.formula = None   # typing a value over a cell replaces its formula, as in Excel
    for dep in get_dependent_cells(model, ref):
        c = model.get_cell_by_canonical_address(dep)
        if c is not None and c.formula:
            c.need_update = True


def mark_all_dirty(model: Model) -> None:
    """Flag every formula for recalculation, ignoring values stored from Excel."""
    for _, cell in formula_cells(model):
        cell.need_update = True


def to_python(v):
    """Convert xlcalc result types (Number, np.float64, ...) to plain Python values."""
    if isinstance(v, (bool, str)) or v is None:
        return v
    if isinstance(v, np.generic):
        return v.item()
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def evaluate(model: Model, ref: str, ctx: EvalContext = None):
    """Calculate one cell (handles circular references if ctx is iterative)."""
    ctx = ctx or EvalContext(model)
    return to_python(recalc_or_iterate(ctx, ref))


def load_workbook(path: str) -> Model:
    """Load an .xlsx through Excel (via xlwings), without the per-cell DEBUG spam.
    Date cells are converted to Excel serial numbers so date functions work.

    The loader also turns typed-in dates into pseudo-formulas like '=45306'
    (it compares str(datetime) to Excel's '45306' and sees a mismatch). Those
    are turned back into plain values so they behave as inputs."""
    from xlcalc.loader import load_workbook_to_model
    with contextlib.redirect_stdout(io.StringIO()):
        model = load_workbook_to_model(path)
    for sheet in model.sheets.values():
        for cell in sheet.cells.values():
            if isinstance(cell.value, (dt.date, dt.datetime)):
                cell.value = to_serial(cell.value)
                if cell.formula and re.fullmatch(r"=\d+(\.\d+)?", cell.formula):
                    cell.formula = None
    return model


def formula_cells(model: Model):
    """Yield (canonical_ref, cell) for every cell that has a formula."""
    for sheet_name, sheet in model.sheets.items():
        for key, cell in sheet.cells.items():
            if cell.formula:
                yield f"{sheet_name}!{key}", cell


_FUNC_RE = re.compile(r"([A-Z][A-Z0-9.]*)\s*\(")


def unsupported_functions(model: Model) -> dict:
    """{function_name: [cells using it]} for functions xlcalc doesn't implement.
    xlcalc silently returns 0.0 for these, so always check before trusting results."""
    found = {}
    for ref, cell in formula_cells(model):
        # Drop string literals so text like "SUM(" inside quotes isn't matched
        body = re.sub(r'"[^"]*"', "", cell.formula.upper())
        for name in _FUNC_RE.findall(body):
            name = name.removeprefix("_XLFN.")
            if name not in FUNCTIONS:
                found.setdefault(name, []).append(ref)
    return found
