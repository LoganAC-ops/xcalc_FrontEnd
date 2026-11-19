import { useEffect, useState } from "react";
import { api } from "../../api";
import type { Project, TestResult } from "../../types";

interface Props {
  project: Project;
  onNext: () => void;
}

export default function TestStep({ project, onNext }: Props) {
  const [res, setRes] = useState<TestResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.test(project.id).then(setRes).catch((e) => setErr(String(e)));
  }, [project.id]);

  return (
    <div className="step">
      <h2>Testing model</h2>
      <p className="subtle">
        A quick audit before you wire the model into a tool. Deeper regression tests, cell-level
        Excel diffs, and golden-value checks live here in a future version.
      </p>

      {!res && !err && <div className="log-line"><span className="spinner" /> Running checks...</div>}
      {err && <div className="error">{err}</div>}

      {res && (
        <ul className="check-list">
          {res.checks.map((c, i) => (
            <li key={i} className={"check " + (c.ok ? "ok" : "warn")}>
              <span className="check-icon">{c.ok ? "✓" : "!"}</span>
              <div>
                <div className="check-name">{c.name}</div>
                <div className="subtle">{c.detail}</div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="wizard-actions">
        <button className="primary" disabled={!res} onClick={onNext}>
          Continue
        </button>
      </div>
    </div>
  );
}
