import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Project, ToolKind } from "./types";
import Sidebar from "./components/Sidebar";
import NewProjectWizard from "./components/NewProjectWizard";
import ToolWorkspace from "./components/workspace/ToolWorkspace";
import HomePane from "./components/HomePane";

type View =
  | { kind: "home" }
  | { kind: "wizard" }
  | { kind: "project"; id: string; tool?: ToolKind };

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [view, setView] = useState<View>({ kind: "home" });

  const refresh = useCallback(async () => {
    setProjects(await api.listProjects());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const openProject = (id: string, tool?: ToolKind) => setView({ kind: "project", id, tool });
  const openWizard = () => setView({ kind: "wizard" });
  const goHome = () => setView({ kind: "home" });

  const onProjectCreated = async (id: string) => {
    await refresh();
    openProject(id);
  };

  const onDelete = async (id: string) => {
    if (!confirm("Delete this project? This removes the compiled model file.")) return;
    await api.deleteProject(id);
    if (view.kind === "project" && view.id === id) goHome();
    refresh();
  };

  return (
    <div className="app">
      <Sidebar
        projects={projects}
        activeId={view.kind === "project" ? view.id : null}
        onNew={openWizard}
        onOpen={(id) => openProject(id)}
        onDelete={onDelete}
        onHome={goHome}
      />
      <main className="main">
        {view.kind === "home" && (
          <HomePane projects={projects} onNew={openWizard} onOpen={openProject} />
        )}
        {view.kind === "wizard" && (
          <NewProjectWizard onCancel={goHome} onDone={onProjectCreated} />
        )}
        {view.kind === "project" && (
          <ToolWorkspace
            projectId={view.id}
            initialTool={view.tool}
            onChangeProject={refresh}
          />
        )}
      </main>
    </div>
  );
}
