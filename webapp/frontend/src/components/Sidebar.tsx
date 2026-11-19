import type { Project } from "../types";

interface Props {
  projects: Project[];
  activeId: string | null;
  onNew: () => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onHome: () => void;
}

export default function Sidebar({ projects, activeId, onNew, onOpen, onDelete, onHome }: Props) {
  return (
    <aside className="sidebar">
      <button className="brand" onClick={onHome}>
        <span className="brand-mark">▧</span>
        <span className="brand-name">xlcalc Studio</span>
      </button>

      <button className="new-project" onClick={onNew}>
        <span>+</span> New project
      </button>

      <div className="sidebar-section-label">Projects</div>
      <nav className="project-list">
        {projects.length === 0 && <div className="empty">No projects yet</div>}
        {projects.map((p) => (
          <div
            key={p.id}
            className={"project-row" + (p.id === activeId ? " active" : "")}
            onClick={() => onOpen(p.id)}
          >
            <div className="project-title">
              <span className="dot" data-status={p.status} />
              <span className="truncate">{p.name}</span>
            </div>
            <button
              className="row-delete"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(p.id);
              }}
              title="Delete project"
            >
              ×
            </button>
          </div>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="muted">xlcalcmodel 3.6.7 · POC</div>
      </div>
    </aside>
  );
}
