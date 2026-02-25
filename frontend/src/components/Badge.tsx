import "../styles/components.css";

interface Props {
  label: string;
  color?: string;
}

export const Badge = ({ label, color }: Props) => (
  <span
    className="badge"
    style={{ "--badge-color": color ?? "var(--amber)" } as React.CSSProperties}
  >
    {label}
  </span>
);
