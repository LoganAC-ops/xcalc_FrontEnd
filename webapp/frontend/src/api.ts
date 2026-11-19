import type { EvaluateResponse, Project, TestResult } from "./types";

const BASE = "/api";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export const api = {
  listProjects: () => fetch(`${BASE}/projects`).then(j<Project[]>),
  getProject: (id: string) => fetch(`${BASE}/projects/${id}`).then(j<Project>),
  deleteProject: (id: string) =>
    fetch(`${BASE}/projects/${id}`, { method: "DELETE" }).then(j<{ ok: boolean }>),
  updateProject: (id: string, patch: Partial<Project>) =>
    fetch(`${BASE}/projects/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then(j<Project>),

  upload: async (file: File): Promise<Project> => {
    const fd = new FormData();
    fd.append("file", file);
    return j<Project>(await fetch(`${BASE}/projects/upload`, { method: "POST", body: fd }));
  },

  compileStream: (id: string) =>
    fetch(`${BASE}/projects/${id}/compile`, { method: "POST" }),

  autodetect: (id: string) =>
    fetch(`${BASE}/projects/${id}/autodetect`, { method: "POST" }).then(j<Project>),

  test: (id: string) => fetch(`${BASE}/projects/${id}/test`).then(j<TestResult>),

  evaluate: (id: string, inputs: Record<string, unknown>, outputs?: string[]) =>
    fetch(`${BASE}/projects/${id}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inputs, outputs }),
    }).then(j<EvaluateResponse>),

  batch: async (id: string, file: File): Promise<Blob> => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${BASE}/projects/${id}/batch`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.blob();
  },
};

/** Read an ndjson stream and dispatch each parsed line. */
export async function readNdjson<T = unknown>(
  resp: Response,
  onChunk: (chunk: T) => void,
): Promise<void> {
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() || "";
    for (const line of lines) {
      if (line.trim()) onChunk(JSON.parse(line) as T);
    }
  }
  if (buf.trim()) onChunk(JSON.parse(buf) as T);
}
