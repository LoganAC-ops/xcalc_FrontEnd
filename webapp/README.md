# xlcalc Studio (POC)

A Claude-style frontend over the `xlcalcmodel` backend. Compile an Excel workbook
once, then drive it from a web form (Scenario Runner), a CSV (Batch Processor), or
one of four more tools on the roadmap (REST, Sensitivity, Goal Seek, Chat).

## Architecture

```
webapp/
├── backend/        FastAPI, wraps xlc_helpers from the parent project
├── frontend/       React + TypeScript (Vite)
├── projects/       On-disk project store: one .pkl.gz + one .meta.json each
└── start-dev.ps1   Launcher
```

The backend lives on port **8000**, the frontend on **5173**. Vite proxies
`/api/*` through to the backend so the browser sees a single origin.

## First run

Requirements: Python 3.14 with FastAPI, Node 22+, the parent project's `xlc_helpers.py`
importable, and `loan_model.pkl.gz` in the parent directory (the backend seeds it as
the first project automatically on startup).

```powershell
# From the project root (one-time install if you haven't already)
pip install fastapi "uvicorn[standard]" python-multipart

# Launch both dev servers
cd webapp
.\start-dev.ps1
```

Then open <http://localhost:5173>.

## What's wired

| Area                | Status                                                                 |
|---------------------|------------------------------------------------------------------------|
| Sidebar + routing   | Real                                                                   |
| Upload (.xlsx)      | Real — triggers full xlwings compile (needs Excel)                     |
| Upload (.pkl.gz)    | Real — instant, no Excel needed                                        |
| Compile step        | Real — streams progress from the backend                               |
| Test step           | Real audit (unsupported-function scan, formula count), simple pass/fail |
| Tool: Scenario      | **Fully wired** — form → `/api/.../evaluate` → outputs table           |
| Tool: Batch         | **Fully wired** — CSV in → CSV out, with preview + template download   |
| Tool: REST          | Placeholder card ("Coming soon")                                       |
| Tool: Sensitivity   | Placeholder card                                                       |
| Tool: Goal Seek     | Placeholder card                                                       |
| Tool: Chat          | Placeholder card                                                       |

## What's not wired (deliberately, for POC scope)

- No auth, no multi-user, no deploy config — localhost only
- Test step is one API call, not a cell-level diff against Excel's cached values
- COUNTIF / SUMIF bug fix not applied — the sample workbook uses one COUNTIF
  (`Summary!B9`) which will return `0` instead of the correct count. The Test
  step would flag this via `unsupported_functions`, but that bug is about
  numpy types, not unsupported functions. See `../NOTES.md` for the shim.
- Auto-detect assumes convention: input cells on a sheet called "Inputs"
  (col A label, col B value), output cells on a sheet called "Summary" /
  "Outputs" / "Results". Workbooks that break this convention will come up
  with empty input/output lists and will need manual metadata editing (not
  yet exposed in the UI — edit the `.meta.json` by hand).

## Project store

Each uploaded project lives as two or three files in `webapp/projects/`:

- `<id>.pkl.gz` — the compiled xlcalc model
- `<id>.xlsx` — the original workbook (only if uploaded as .xlsx)
- `<id>.meta.json` — name, inputs, outputs, status

Deleting a project in the UI removes all three.

The seeded project (`loan_model`) is copied from the parent directory on first
start. Delete its meta file to re-seed from fresh.
