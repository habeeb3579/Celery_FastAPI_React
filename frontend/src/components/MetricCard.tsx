import "../styles/components.css";

interface Props {
  label: string;
  value: string;
  sub?: string;
}

export const MetricCard = ({ label, value, sub }: Props) => (
  <div className="metric-card">
    <div className="metric-card__label">{label}</div>
    <div className="metric-card__value">{value}</div>
    {sub && <div className="metric-card__sub">{sub}</div>}
  </div>
);
