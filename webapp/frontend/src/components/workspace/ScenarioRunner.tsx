import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api";
import type { Project } from "../../types";

interface Props {
  project: Project;
}

type InputValue = string;
type OutputMap = Record<string, number | string | { error: string }>;

interface SavedScenario {
  id: number;
  name: string;
  inputs: Record<string, InputValue>;
  outputs: OutputMap;
}

function formatValue(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "object") return `error: ${(v as { error: string }).error}`;
  if (typeof v === "number") {
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (!Number.isInteger(v)) return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
    return String(v);
  }
  return String(v);
}

function coerce(raw: InputValue, type: string): unknown {
  if (raw === "") return null;
  if (type === "number") {
    const n = Number(raw);
    return Number.isNaN(n) ? raw : n;
  }
  if (type === "boolean") return raw === "true";
  return raw;
}

export default function ScenarioRunner({ project }: Props) {
  const initial = useMemo(() => {
    const o: Record<string, InputValue> = {};
    for (const i of project.inputs) o[i.ref] = i.default == null ? "" : String(i.default);
    return o;
  }, [project.id]);

  const [vals, setVals] = useState<Record<string, InputValue>>(initial);
  const [outputs, setOutputs] = useState<OutputMap>({});
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [saved, setSaved] = useState<SavedScenario[]>([]);
  const nextId = useRef(1);

  const run = async (overrideVals?: Record<string, InputValue>) => {
    const v = overrideVals ?? vals;
    setRunning(true);
    const t0 = performance.now();
    try {
      const payload: Record<string, unknown> = {};
      for (const inp of project.inputs) {
        const raw = v[inp.ref];
        if (raw === "" || raw == null) continue;
        payload[inp.ref] = coerce(raw, inp.type);
      }
      const r = await api.evaluate(project.id, payload);
      setOutputs(r.outputs);
      setElapsed(performance.now() - t0);
    } finally {
      setRunning(false);
    }
  };

  // Auto-run once on mount with defaults
  useEffect(() => {
    run(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  const save = () => {
    setSaved((prev) => [
      ...prev,
      {
        id: nextId.current++,
        name: `Scenario ${nextId.current - 1}`,
        inputs: { ...vals },
        outputs: { ...outputs },
      },
    ]);
  };

  const restore = (s: SavedScenario) => {
    setVals(s.inputs);
    run(s.inputs);
  };

  const reset = () => {
    setVals(initial);
    run(initial);
  };

  return (
    <div className="scenario">
      <section className="panel inputs-panel">
        <div className="panel-header">
          <h3>Inputs</h3>
          <button className="link" onClick={reset}>
            Reset
          </button>
        </div>
        <div className="form">
          {project.inputs.map((inp) => (
            <label key={inp.ref} className="field">
              <span className="field-label">{inp.label}</span>
              <input
                className="field-input"
                type={inp.type === "date" ? "date" : inp.type === "number" ? "number" : "text"}
                step={inp.type === "number" ? "any" : undefined}
                value={vals[inp.ref] ?? ""}
                onChange={(e) =>
                  setVals((prev) => ({ ...prev, [inp.ref]: e.target.value }))
                }
              />
              <span className="field-ref">{inp.ref}</span>
            </label>
          ))}
        </div>
        <div className="panel-footer">
          <button className="primary" onClick={() => run()} disabled={running}>
            {running ? "Calculating..." : "Recalculate"}
          </button>
          <button className="secondary" onClick={save} disabled={running || !Object.keys(outputs).length}>
            Save scenario
          </button>
        </div>
      </section>

      <section className="panel outputs-panel">
        <div className="panel-header">
          <h3>Outputs</h3>
          {elapsed != null && <span className="subtle">Computed in {elapsed.toFixed(0)} ms</span>}
        </div>
        <table className="output-table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Value</th>
              <th>Cell</th>
            </tr>
          </thead>
          <tbody>
            {project.outputs.map((o) => (
              <tr key={o.ref}>
                <td>{o.label}</td>
                <td className="num">{formatValue(outputs[o.ref])}</td>
                <td className="subtle mono">{o.ref}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {saved.length > 0 && (
        <section className="panel saved-panel">
          <div className="panel-header">
            <h3>Saved scenarios</h3>
            <button className="link" onClick={() => setSaved([])}>
              Clear
            </button>
          </div>
          <div className="scroll-x">
            <table className="output-table">
              <thead>
                <tr>
                  <th>Name</th>
                  {project.inputs.map((i) => (
                    <th key={i.ref}>{i.label}</th>
                  ))}
                  {project.outputs.map((o) => (
                    <th key={o.ref}>{o.label}</th>
                  ))}
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {saved.map((s) => (
                  <tr key={s.id}>
                    <td>{s.name}</td>
                    {project.inputs.map((i) => (
                      <td key={i.ref} className="num">
                        {s.inputs[i.ref]}
                      </td>
                    ))}
                    {project.outputs.map((o) => (
                      <td key={o.ref} className="num">
                        {formatValue(s.outputs[o.ref])}
                      </td>
                    ))}
                    <td>
                      <button className="link" onClick={() => restore(s)}>
                        Load
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
