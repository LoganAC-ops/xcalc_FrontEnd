import { useEffect, useState } from "react";
import { api } from "../../api";
import { TOOLS, type Project, type ToolKind } from "../../types";
import ScenarioRunner from "./ScenarioRunner";
import BatchProcessor from "./BatchProcessor";
import ComingSoon from "./ComingSoon";

interface Props {
  projectId: string;
  initialTool?: ToolKind;
  onChangeProject: () => void;
}

export default function ToolWorkspace({ projectId, initialTool, onChangeProject }: Props) {
  const [project, setProject] = useState<Project | null>(null);
  const [tool, setTool] = useState<ToolKind>(initialTool ?? "scenario");

  useEffect(() => {
    setProject(null);
    api.getProject(projectId).then(setProject);
    setTool(initialTool ?? "scenario");
  }, [projectId, initialTool]);

  if (!project) return <div className="loading">Loading project...</div>;

  return (
    <div className="workspace">
      <header className="workspace-header">
        <div>
          <h1>{project.name}</h1>
          <div className="subtle">
            {project.inputs.length} inputs · {project.outputs.length} outputs · status {project.status}
          </div>
        </div>
        <nav className="tool-tabs">
          {TOOLS.map((t) => (
            <button
              key={t.kind}
              className={"tool-tab" + (tool === t.kind ? " active" : "") + (t.available ? "" : " disabled")}
              onClick={() => setTool(t.kind)}
              title={t.available ? t.description : "Coming soon"}
            >
              <span className="tool-icon-sm">{t.icon}</span>
              <span>{t.name}</span>
            </button>
          ))}
        </nav>
      </header>

      <div className="workspace-body">
        {tool === "scenario" && <ScenarioRunner project={project} />}
        {tool === "batch" && <BatchProcessor project={project} />}
        {tool !== "scenario" && tool !== "batch" && (
          <ComingSoon tool={TOOLS.find((t) => t.kind === tool)!} />
        )}
      </div>
    </div>
  );
}
