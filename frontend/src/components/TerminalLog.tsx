import "../styles/components.css";

interface Props {
  lines: string[];
}

export const TerminalLog = ({ lines }: Props) => (
  <div className="terminal-log">
    {lines.length === 0 ? (
      <span className="terminal-log__empty">$ waiting...</span>
    ) : (
      lines.map((line, i) => (
        <div
          key={i}
          className="terminal-log__line"
          style={{
            color: i === 0 ? "var(--green)" : "var(--text-lo)",
            opacity: i === 0 ? 1 : 0.6 + (lines.length - i) * 0.015,
          }}
        >
          <span className="terminal-log__prompt">›</span> {line}
        </div>
      ))
    )}
  </div>
);
