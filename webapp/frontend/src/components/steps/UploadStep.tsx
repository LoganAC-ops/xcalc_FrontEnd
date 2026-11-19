import { useRef, useState } from "react";
import { api } from "../../api";
import type { Project } from "../../types";

interface Props {
  onUploaded: (project: Project) => void;
}

export default function UploadStep({ onUploaded }: Props) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    setBusy(true);
    setErr(null);
    try {
      const p = await api.upload(file);
      onUploaded(p);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="step">
      <h2>Upload a workbook</h2>
      <p className="subtle">
        Drop an <code>.xlsx</code> file to compile from scratch, or a pre-compiled{" "}
        <code>.pkl.gz</code> for an instant project.
      </p>

      <div
        className={"dropzone" + (dragOver ? " drag" : "")}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) upload(f);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <div className="dropzone-icon">⬆</div>
        <div className="dropzone-headline">
          {busy ? "Uploading..." : "Drop a file here or click to browse"}
        </div>
        <div className="subtle">Accepted: .xlsx, .pkl.gz</div>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.pkl.gz,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload(f);
          }}
        />
      </div>

      {err && <div className="error">{err}</div>}

      <div className="step-tip subtle">
        <strong>Tip:</strong> compiling an .xlsx needs Excel installed (uses xlwings, ~20–30s). A
        pre-compiled .pkl.gz loads in milliseconds.
      </div>
    </div>
  );
}
