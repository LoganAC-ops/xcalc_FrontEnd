import { useState } from "react";
import type { Project, ToolKind } from "../types";
import UploadStep from "./steps/UploadStep";
import CompileStep from "./steps/CompileStep";
import TestStep from "./steps/TestStep";
import ToolSelectStep from "./steps/ToolSelectStep";

interface Props {
  onCancel: () => void;
  onDone: (projectId: string, tool?: ToolKind) => void;
}

type StepKey = "upload" | "compile" | "test" | "tool";

const STEPS: { key: StepKey; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "compile", label: "Compile" },
  { key: "test", label: "Test" },
  { key: "tool", label: "Choose a tool" },
];

export default function NewProjectWizard({ onCancel, onDone }: Props) {
  const [step, setStep] = useState<StepKey>("upload");
  const [project, setProject] = useState<Project | null>(null);

  const stepIndex = STEPS.findIndex((s) => s.key === step);

  const advance = (next: StepKey) => setStep(next);

  return (
    <div className="wizard">
      <div className="wizard-header">
        <h1>New project</h1>
        <button className="link" onClick={onCancel}>
          Cancel
        </button>
      </div>

      <ol className="step-indicator">
        {STEPS.map((s, i) => {
          const state = i < stepIndex ? "done" : i === stepIndex ? "active" : "pending";
          return (
            <li key={s.key} data-state={state}>
              <span className="step-num">{i + 1}</span>
              <span className="step-label">{s.label}</span>
            </li>
          );
        })}
      </ol>

      <div className="wizard-body">
        {step === "upload" && (
          <UploadStep
            onUploaded={(p) => {
              setProject(p);
              advance(p.status === "ready" ? "test" : "compile");
            }}
          />
        )}
        {step === "compile" && project && (
          <CompileStep
            project={project}
            onCompiled={(p) => {
              setProject(p);
              advance("test");
            }}
          />
        )}
        {step === "test" && project && (
          <TestStep project={project} onNext={() => advance("tool")} />
        )}
        {step === "tool" && project && (
          <ToolSelectStep
            onPick={(tool) => onDone(project.id, tool)}
            onSkip={() => onDone(project.id)}
          />
        )}
      </div>
    </div>
  );
}
