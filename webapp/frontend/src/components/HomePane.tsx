import type { Project, ToolKind } from "../types";

interface Props {
  projects: Project[];
  onNew: () => void;
  onOpen: (id: string, tool?: ToolKind) => void;
}

export default function HomePane({ projects, onNew, onOpen }: Props) {
  return (
    <div className="home">
      <div className="home-hero">
        <h1>xlcalc Studio</h1>
        <p className="subtle">
          Compile an Excel workbook into a Python rules-engine. Drive it from a form, a CSV, an API,
          or a chat — without opening Excel.
        </p>
        <div className="hero-actions">
          <button className="primary" onClick={onNew}>
            + New project
          </button>
        </div>
      </div>

      <div className="home-section">
        <h2>Recent projects</h2>
        {projects.length === 0 ? (
          <p className="subtle">
            Nothing yet. Click <strong>New project</strong> to upload a workbook.
          </p>
        ) : (
          <div className="card-grid">
            {projects.map((p) => (
              <div className="card project-card" key={p.id} onClick={() => onOpen(p.id)}>
                <div className="card-title">{p.name}</div>
                <div className="card-sub">
                  {p.inputs.length} inputs · {p.outputs.length} outputs
                </div>
                <div className="card-meta">
                  <span className="pill" data-status={p.status}>
                    {p.status.replace("_", " ")}
                  </span>
                  <span className="muted">{p.created_at.slice(0, 10)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
