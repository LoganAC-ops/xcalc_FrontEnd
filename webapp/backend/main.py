"""
FastAPI backend for the xlcalc webapp POC.

Wraps xlc_helpers so the React UI can:
  - list/create/delete projects (each project = one compiled .pkl.gz + sidecar metadata)
  - compile .xlsx -> .pkl.gz (slow, needs Excel) or accept a pre-compiled .pkl.gz (fast)
  - run scenarios (set inputs, read outputs)
  - batch-process a CSV of input rows

Run with:  python -m uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import shutil
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Make the project root importable so we can reuse xlc_helpers
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from xlcalc import EvalContext, Model  # noqa: E402
from xlc_helpers import evaluate, set_value, unsupported_functions  # noqa: E402

PROJECTS_DIR = ROOT / "webapp" / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="xlcalc webapp backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# In-memory model cache. Loading a pkl.gz is cheap (~20ms) but we still want to
# avoid re-reading on every evaluate call during a session.
# -----------------------------------------------------------------------------
_MODELS: dict[str, tuple[Model, EvalContext]] = {}


def _load_model(project_id: str) -> tuple[Model, EvalContext]:
    if project_id in _MODELS:
        return _MODELS[project_id]
    meta = _read_meta(project_id)
    pkl = PROJECTS_DIR / meta["pkl_file"]
    if not pkl.exists():
        raise HTTPException(400, f"Project {project_id} has no compiled .pkl.gz yet")
    model = Model.construct_from_pickle_file(str(pkl), build_code=True)
    ctx = EvalContext(model)
    _MODELS[project_id] = (model, ctx)
    return model, ctx


def _evict(project_id: str) -> None:
    _MODELS.pop(project_id, None)


# -----------------------------------------------------------------------------
# Project metadata lives in a sidecar JSON next to each .pkl.gz.
# Shape:
#   {id, name, created_at, pkl_file, xlsx_file?, inputs: [...], outputs: [...]}
# -----------------------------------------------------------------------------
def _meta_path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.meta.json"


def _read_meta(project_id: str) -> dict:
    path = _meta_path(project_id)
    if not path.exists():
        raise HTTPException(404, f"Project {project_id} not found")
    return json.loads(path.read_text())


def _write_meta(meta: dict) -> None:
    _meta_path(meta["id"]).write_text(json.dumps(meta, indent=2, default=str))


def _list_projects() -> list[dict]:
    projects = []
    for p in sorted(PROJECTS_DIR.glob("*.meta.json")):
        try:
            projects.append(json.loads(p.read_text()))
        except Exception:
            pass
    return projects


# -----------------------------------------------------------------------------
# Auto-detect inputs/outputs from a freshly-loaded model.
#   - Inputs: non-formula cells on a sheet called "Inputs" (col A = label, col B = value)
#   - Outputs: formula cells on sheets called "Summary" / "Outputs" / "Results"
#     (col A = label, col B = formula)
# -----------------------------------------------------------------------------
def _guess_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (dt.date, dt.datetime)):
        return "date"
    return "text"


def _detect_io(model: Model) -> tuple[list[dict], list[dict]]:
    inputs: list[dict] = []
    outputs: list[dict] = []
    for sheet_name, sheet in model.sheets.items():
        is_input_sheet = sheet_name.lower() in {"inputs", "input", "assumptions"}
        is_output_sheet = sheet_name.lower() in {"summary", "outputs", "output", "results"}
        if not (is_input_sheet or is_output_sheet):
            continue
        for key, cell in sheet.cells.items():
            m = re.fullmatch(r"([A-Z]+)(\d+)", key)
            if not m:
                continue
            col, row = m.group(1), int(m.group(2))
            if col != "B":
                continue
            label_cell = sheet.cells.get(f"A{row}")
            label = str(label_cell.value) if label_cell and label_cell.value is not None else key
            ref = f"{sheet_name}!{key}"
            if is_input_sheet and not cell.formula:
                inputs.append({
                    "ref": ref,
                    "label": label,
                    "type": _guess_type(cell.value),
                    "default": cell.value,
                })
            elif is_output_sheet and cell.formula:
                outputs.append({"ref": ref, "label": label, "formula": cell.formula})
    return inputs, outputs


# -----------------------------------------------------------------------------
# Request / response models
# -----------------------------------------------------------------------------
class EvaluateRequest(BaseModel):
    inputs: dict[str, Any] = {}
    outputs: list[str] | None = None  # if None, evaluate all declared outputs


class UpdateMetaRequest(BaseModel):
    name: str | None = None
    inputs: list[dict] | None = None
    outputs: list[dict] | None = None


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/projects")
def list_projects() -> list[dict]:
    return _list_projects()


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    return _read_meta(project_id)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> dict:
    meta = _read_meta(project_id)
    for key in ("pkl_file", "xlsx_file"):
        f = meta.get(key)
        if f and (PROJECTS_DIR / f).exists():
            (PROJECTS_DIR / f).unlink()
    _meta_path(project_id).unlink()
    _evict(project_id)
    return {"ok": True}


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, body: UpdateMetaRequest) -> dict:
    meta = _read_meta(project_id)
    if body.name is not None:
        meta["name"] = body.name
    if body.inputs is not None:
        meta["inputs"] = body.inputs
    if body.outputs is not None:
        meta["outputs"] = body.outputs
    _write_meta(meta)
    return meta


@app.post("/api/projects/upload")
async def upload_project(file: UploadFile = File(...)) -> dict:
    """Accept either .xlsx (will need compile) or .pkl.gz (ready to use)."""
    name = (file.filename or "project").strip()
    suffix = "".join(Path(name).suffixes).lower()
    if not (suffix.endswith(".xlsx") or suffix.endswith(".pkl.gz")):
        raise HTTPException(400, "Only .xlsx or .pkl.gz files are supported")

    project_id = uuid.uuid4().hex[:12]
    stem = Path(name).name.replace(".pkl.gz", "").replace(".xlsx", "")
    data = await file.read()

    meta: dict = {
        "id": project_id,
        "name": stem,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "pkl_file": None,
        "xlsx_file": None,
        "inputs": [],
        "outputs": [],
        "status": "uploaded",
    }

    if suffix.endswith(".pkl.gz"):
        pkl_name = f"{project_id}.pkl.gz"
        (PROJECTS_DIR / pkl_name).write_bytes(data)
        meta["pkl_file"] = pkl_name
        meta["status"] = "ready"
    else:
        xlsx_name = f"{project_id}.xlsx"
        (PROJECTS_DIR / xlsx_name).write_bytes(data)
        meta["xlsx_file"] = xlsx_name
        meta["status"] = "needs_compile"

    _write_meta(meta)
    return meta


@app.post("/api/projects/{project_id}/compile")
def compile_project(project_id: str):
    """Compile the uploaded .xlsx into a .pkl.gz. Streams progress as SSE-ish newline chunks."""
    meta = _read_meta(project_id)
    if not meta.get("xlsx_file"):
        raise HTTPException(400, "No .xlsx uploaded for this project")
    xlsx_path = PROJECTS_DIR / meta["xlsx_file"]

    def gen():
        def emit(stage: str, msg: str, done: bool = False):
            return json.dumps({"stage": stage, "message": msg, "done": done}) + "\n"

        try:
            yield emit("start", f"Compiling {meta['name']}...")
            t0 = time.time()

            yield emit("load", "Loading workbook through Excel (xlwings)...")
            from xlc_helpers import load_workbook
            model = load_workbook(str(xlsx_path))
            yield emit("load", f"Parsed {sum(len(s.cells) for s in model.sheets.values())} cells in {time.time() - t0:.1f}s")

            yield emit("build", "Compiling formulas to Python...")
            t1 = time.time()
            model.build_code()
            yield emit("build", f"Built {time.time() - t1:.1f}s")

            yield emit("detect", "Auto-detecting inputs and outputs...")
            inputs, outputs = _detect_io(model)
            yield emit("detect", f"Found {len(inputs)} inputs, {len(outputs)} outputs")

            yield emit("save", "Saving compiled model...")
            pkl_name = f"{project_id}.pkl.gz"
            # Must save BEFORE build_code to allow pickle, but we already built - reload fresh
            fresh = load_workbook(str(xlsx_path))
            fresh.save_to_pickle_file(str(PROJECTS_DIR / pkl_name))

            meta["pkl_file"] = pkl_name
            meta["inputs"] = inputs
            meta["outputs"] = outputs
            meta["status"] = "ready"
            _write_meta(meta)

            yield emit("done", f"Compiled in {time.time() - t0:.1f}s total", done=True)
        except Exception as e:
            yield emit("error", f"{type(e).__name__}: {e}\n{traceback.format_exc()}", done=True)

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/api/projects/{project_id}/autodetect")
def autodetect_io(project_id: str) -> dict:
    """Re-run input/output detection against a pkl-only project (used for seeded projects)."""
    model, _ = _load_model(project_id)
    inputs, outputs = _detect_io(model)
    meta = _read_meta(project_id)
    meta["inputs"] = inputs
    meta["outputs"] = outputs
    _write_meta(meta)
    return meta


@app.get("/api/projects/{project_id}/test")
def test_project(project_id: str) -> dict:
    """Lightweight audit used by the Test wizard step. Cosmetic for POC but uses real data."""
    model, _ = _load_model(project_id)
    unsupported = unsupported_functions(model)
    formula_count = sum(1 for s in model.sheets.values() for c in s.cells.values() if c.formula)
    return {
        "checks": [
            {"name": "Workbook loaded", "ok": True, "detail": f"{len(model.sheets)} sheets"},
            {"name": "Formulas compiled", "ok": True, "detail": f"{formula_count} formulas"},
            {"name": "No unsupported functions", "ok": len(unsupported) == 0,
             "detail": "All formulas supported" if not unsupported
             else f"{len(unsupported)} unsupported: {', '.join(unsupported)}"},
            {"name": "Inputs detected", "ok": len(_read_meta(project_id)["inputs"]) > 0,
             "detail": f"{len(_read_meta(project_id)['inputs'])} inputs"},
            {"name": "Outputs detected", "ok": len(_read_meta(project_id)["outputs"]) > 0,
             "detail": f"{len(_read_meta(project_id)['outputs'])} outputs"},
        ],
        "unsupported": unsupported,
    }


@app.post("/api/projects/{project_id}/evaluate")
def evaluate_project(project_id: str, req: EvaluateRequest) -> dict:
    model, ctx = _load_model(project_id)
    meta = _read_meta(project_id)

    for ref, value in (req.inputs or {}).items():
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            value = dt.date.fromisoformat(value)
        try:
            set_value(model, ref, value)
        except KeyError as e:
            raise HTTPException(400, str(e))

    out_refs = req.outputs or [o["ref"] for o in meta.get("outputs", [])]
    results: dict[str, Any] = {}
    for ref in out_refs:
        try:
            v = evaluate(model, ref, ctx)
            if isinstance(v, dt.date):
                v = v.isoformat()
            results[ref] = v
        except Exception as e:
            results[ref] = {"error": f"{type(e).__name__}: {e}"}
    return {"outputs": results}


@app.post("/api/projects/{project_id}/batch")
async def batch_project(project_id: str, file: UploadFile = File(...)) -> StreamingResponse:
    """CSV in, CSV out. Header row maps column name -> input ref via meta['inputs'] labels."""
    model, ctx = _load_model(project_id)
    meta = _read_meta(project_id)

    label_to_ref = {i["label"]: i["ref"] for i in meta["inputs"]}
    out_cols = [(o["label"], o["ref"]) for o in meta["outputs"]]

    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(reader.fieldnames or []) + [label for label, _ in out_cols])

    for row in reader:
        for col, val in row.items():
            ref = label_to_ref.get(col)
            if ref is None or val == "":
                continue
            parsed: Any = val
            try:
                parsed = float(val)
                if parsed.is_integer():
                    parsed = int(parsed)
            except ValueError:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
                    parsed = dt.date.fromisoformat(val)
            set_value(model, ref, parsed)
        out_vals = []
        for _, ref in out_cols:
            v = evaluate(model, ref, ctx)
            if isinstance(v, dt.date):
                v = v.isoformat()
            out_vals.append(v)
        writer.writerow(list(row.values()) + out_vals)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{meta["name"]}_batch_results.csv"'},
    )


# -----------------------------------------------------------------------------
# One-shot seeder: copies loan_model.{pkl.gz,xlsx} from project root into the
# projects directory with a hand-written meta.json. Called on startup so the
# sidebar is never empty.
# -----------------------------------------------------------------------------
def _seed_loan_model() -> None:
    seed_id = "loan_model"
    if _meta_path(seed_id).exists():
        return
    src_pkl = ROOT / "loan_model.pkl.gz"
    src_xlsx = ROOT / "loan_model.xlsx"
    if not src_pkl.exists():
        return
    shutil.copy(src_pkl, PROJECTS_DIR / f"{seed_id}.pkl.gz")
    if src_xlsx.exists():
        shutil.copy(src_xlsx, PROJECTS_DIR / f"{seed_id}.xlsx")

    meta = {
        "id": seed_id,
        "name": "Loan Model (sample)",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "pkl_file": f"{seed_id}.pkl.gz",
        "xlsx_file": f"{seed_id}.xlsx" if src_xlsx.exists() else None,
        "status": "ready",
        "inputs": [
            {"ref": "Inputs!B1", "label": "Principal", "type": "number", "default": 250000},
            {"ref": "Inputs!B2", "label": "Annual rate", "type": "number", "default": 0.065},
            {"ref": "Inputs!B3", "label": "Term (years)", "type": "number", "default": 30},
            {"ref": "Inputs!B4", "label": "Start date", "type": "date", "default": "2024-01-15"},
        ],
        "outputs": [
            {"ref": "Summary!B1", "label": "Monthly payment", "formula": "=Schedule!B2"},
            {"ref": "Summary!B2", "label": "Year-1 interest", "formula": "=SUM(Schedule!C2:C13)"},
            {"ref": "Summary!B3", "label": "Year-1 principal", "formula": "=SUM(Schedule!D2:D13)"},
            {"ref": "Summary!B4", "label": "Balance after 1 year", "formula": "=Schedule!E13"},
            {"ref": "Summary!B5", "label": "Total paid over term", "formula": "=B1*Inputs!B3*12"},
            {"ref": "Summary!B6", "label": "Total interest", "formula": "=B5-Inputs!B1"},
            {"ref": "Summary!B7", "label": "Interest > principal?", "formula": '=IF(B6>Inputs!B1,"Yes","No")'},
        ],
    }
    _write_meta(meta)


_seed_loan_model()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "projects": len(_list_projects())}
