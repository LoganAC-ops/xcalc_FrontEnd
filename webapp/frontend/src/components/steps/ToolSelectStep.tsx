import { TOOLS, type ToolKind } from "../../types";

interface Props {
  onPick: (tool: ToolKind) => void;
  onSkip: () => void;
}

export default function ToolSelectStep({ onPick, onSkip }: Props) {
  return (
    <div className="step">
      <h2>Choose a tool</h2>
      <p className="subtle">
        What should this model become? Pick a starting point — you can switch at any time.
      </p>

      <div className="card-grid">
        {TOOLS.map((t) => (
          <button
            key={t.kind}
            className={"card tool-card" + (t.available ? "" : " disabled")}
            disabled={!t.available}
            onClick={() => t.available && onPick(t.kind)}
          >
            <div className="tool-icon">{t.icon}</div>
            <div className="card-title">{t.name}</div>
            <div className="card-sub">{t.description}</div>
            {!t.available && <div className="pill soon">Coming soon</div>}
          </button>
        ))}
      </div>

      <div className="wizard-actions">
        <button className="link" onClick={onSkip}>
          Skip — open project
        </button>
      </div>
    </div>
  );
}
