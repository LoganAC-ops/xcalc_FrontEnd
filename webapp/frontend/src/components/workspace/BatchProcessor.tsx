import { useRef, useState } from "react";
import { api } from "../../api";
import type { Project } from "../../types";

interface Props {
  project: Project;
}

export default function BatchProcessor({ project }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string[][] | null>(null);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [resultText, setResultText] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const templateHeader = project.inputs.map((i) => i.label).join(",");
  const templateRow = project.inputs
    .map((i) => (i.default == null ? "" : String(i.default)))
    .join(",");

  const sampleCsv = `${templateHeader}\n${templateRow}\n`;

  const pickFile = async (f: File) => {
    setFile(f);
    setResultBlob(null);
    setResultText(null);
    setErr(null);
    const text = await f.text();
    const rows = text
      .trim()
      .split(/\r?\n/)
      .slice(0, 6)
      .map((r) => r.split(","));
    setPreview(rows);
  };

  const run = async () => {
    if (!file) return;
    setRunning(true);
    setErr(null);
    try {
      const blob = await api.batch(project.id, file);
      setResultBlob(blob);
      setResultText(await blob.text());
    } catch (e) {
      setErr(String(e));
    } finally {
      setRunning(false);
    }
  };

  const download = () => {
    if (!resultBlob) return;
    const url = URL.createObjectURL(resultBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${project.name}_batch_results.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadTemplate = () => {
    const blob = new Blob([sampleCsv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${project.name}_template.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const resultRows = resultText
    ? resultText.trim().split(/\r?\n/).slice(0, 20).map((r) => r.split(","))
    : null;

  return (
    <div className="batch">
      <section className="panel">
        <div className="panel-header">
          <h3>1. Prepare your CSV</h3>
          <button className="link" onClick={downloadTemplate}>
            Download template
          </button>
        </div>
        <p className="subtle">
          One row per scenario. Column headers must match the input labels below.
        </p>
        <ul className="chip-list">
          {project.inputs.map((i) => (
            <li className="chip" key={i.ref}>
              <strong>{i.label}</strong>
              <span className="subtle"> · {i.type}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>2. Upload</h3>
          {file && <span className="subtle">{file.name}</span>}
        </div>
        <div
          className="dropzone small"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) pickFile(f);
          }}
        >
          <div>{file ? "Replace file" : "Click or drop a .csv file"}</div>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) pickFile(f);
            }}
          />
        </div>
        {preview && (
          <>
            <div className="subtle" style={{ margin: "0.75rem 0 0.25rem" }}>
              Preview (first {preview.length} rows):
            </div>
            <div className="scroll-x">
              <table className="output-table">
                <tbody>
                  {preview.map((row, i) => (
                    <tr key={i}>
                      {row.map((c, j) => (
                        <td key={j} className={i === 0 ? "th-like" : ""}>{c}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>3. Run</h3>
        </div>
        <div className="panel-footer" style={{ borderTop: "none", padding: 0 }}>
          <button className="primary" disabled={!file || running} onClick={run}>
            {running ? "Processing..." : "Process batch"}
          </button>
          {resultBlob && (
            <button className="secondary" onClick={download}>
              Download results CSV
            </button>
          )}
        </div>
        {err && <div className="error">{err}</div>}
      </section>

      {resultRows && (
        <section className="panel">
          <div className="panel-header">
            <h3>Results preview</h3>
            <span className="subtle">first {resultRows.length - 1} rows</span>
          </div>
          <div className="scroll-x">
            <table className="output-table">
              <tbody>
                {resultRows.map((row, i) => (
                  <tr key={i}>
                    {row.map((c, j) => (
                      <td key={j} className={i === 0 ? "th-like" : "num"}>{c}</td>
                    ))}
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
