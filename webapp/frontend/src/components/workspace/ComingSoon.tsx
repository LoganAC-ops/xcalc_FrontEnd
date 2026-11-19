import type { ToolDef } from "../../types";

export default function ComingSoon({ tool }: { tool: ToolDef }) {
  return (
    <div className="coming-soon">
      <div className="tool-icon big">{tool.icon}</div>
      <h2>{tool.name}</h2>
      <p className="subtle">{tool.description}</p>
      <div className="pill soon">Coming soon</div>
      <p className="subtle muted" style={{ marginTop: "2rem", maxWidth: 480 }}>
        This tool is on the roadmap. In the POC, Scenario Runner and Batch Processor are the two
        fully-wired tools — they share the same evaluation backend that the others will plug into.
      </p>
    </div>
  );
}
