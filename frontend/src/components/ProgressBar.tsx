import "../styles/components.css";

interface Props {
  value: number;
  label?: string;
  color?: string;
}

export const ProgressBar = ({
  value,
  label,
  color = "var(--amber)",
}: Props) => (
  <div className="progress">
    {label && (
      <div className="progress__labels">
        <span className="progress__label">{label}</span>
        <span className="progress__value" style={{ color }}>
          {value}%
        </span>
      </div>
    )}
    <div className="progress__track">
      <div
        className="progress__fill"
        style={{
          width: `${value}%`,
          background: `linear-gradient(90deg, #92400e, ${color})`,
          boxShadow: `0 0 8px ${color}80`,
        }}
      />
    </div>
  </div>
);
