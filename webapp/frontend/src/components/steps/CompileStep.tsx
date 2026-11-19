import { useEffect, useRef, useState } from "react";
import { api, readNdjson } from "../../api";
import type { Project } from "../../types";

interface Props {
  project: Project;
  onCompiled: (project: Project) => void;
}

interface Chunk {
  stage: string;
  message: string;
  done?: boolean;
}

export default function CompileStep({ project, onCompiled }: Props) {
  const [log, setLog] = useState<Chunk[]>([]);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const resp = await api.compileStream(project.id);
        if (!resp.ok) throw new Error(await resp.text());
        await readNdjson<Chunk>(resp, (c) => {
          setLog((prev) => [...prev, c]);
          if (c.stage === "error") setErr(c.message);
          if (c.done && c.stage === "done") setDone(true);
        });
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, [project.id]);

  const next = async () => {
    const p = await api.getProject(project.id);
    onCompiled(p);
  };

  return (
    <div className="step">
      <h2>Compiling workbook</h2>
      <p className="subtle">
        Parsing formulas, building the dependency graph, and compiling to Python.
      </p>

      <div className="log">
        {log.map((c, i) => (
          <div className={"log-line stage-" + c.stage} key={i}>
            <span className="log-stage">{c.stage}</span>
            <span className="log-msg">{c.message}</span>
          </div>
        ))}
        {!done && !err && (
          <div className="log-line">
            <span className="spinner" /> Working...
          </div>
        )}
      </div>

      {err && <div className="error">{err}</div>}

      <div className="wizard-actions">
        <button className="primary" disabled={!done} onClick={next}>
          Continue to tests
        </button>
      </div>
    </div>
  );
}
