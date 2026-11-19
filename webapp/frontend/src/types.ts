export type ProjectStatus = "uploaded" | "needs_compile" | "ready";

export interface InputSpec {
  ref: string;
  label: string;
  type: "number" | "date" | "text" | "boolean";
  default?: number | string | boolean | null;
}

export interface OutputSpec {
  ref: string;
  label: string;
  formula?: string;
}

export interface Project {
  id: string;
  name: string;
  created_at: string;
  pkl_file: string | null;
  xlsx_file: string | null;
  status: ProjectStatus;
  inputs: InputSpec[];
  outputs: OutputSpec[];
}

export interface TestResult {
  checks: { name: string; ok: boolean; detail: string }[];
  unsupported: Record<string, string[]>;
}

export type EvaluateResponse = { outputs: Record<string, number | string | { error: string }> };

export type ToolKind =
  | "scenario"
  | "batch"
  | "rest"
  | "sensitivity"
  | "goalseek"
  | "chat";

export interface ToolDef {
  kind: ToolKind;
  name: string;
  description: string;
  available: boolean;
  icon: string;
}

export const TOOLS: ToolDef[] = [
  {
    kind: "scenario",
    name: "Scenario Runner",
    description: "Interactive form: set inputs, see outputs recalculate instantly. Save scenarios for comparison.",
    available: true,
    icon: "⚡",
  },
  {
    kind: "batch",
    name: "Batch Processor",
    description: "Upload a CSV of input rows, download a CSV with every scenario's outputs appended.",
    available: true,
    icon: "📊",
  },
  {
    kind: "rest",
    name: "REST Endpoint",
    description: "Expose the model as an HTTP API. POST inputs → JSON outputs. Shareable with other services.",
    available: false,
    icon: "🔌",
  },
  {
    kind: "sensitivity",
    name: "Sensitivity Analysis",
    description: "Vary one input across a range, chart the output as a tornado or line plot.",
    available: false,
    icon: "📈",
  },
  {
    kind: "goalseek",
    name: "Goal Seek",
    description: 'Reverse-solve: "what input gives output X?" Bisection or Newton on any formula cell.',
    available: false,
    icon: "🎯",
  },
  {
    kind: "chat",
    name: "Chat Interface",
    description: "Natural-language queries against the model. Ask questions, get calculations and explanations.",
    available: false,
    icon: "💬",
  },
];
