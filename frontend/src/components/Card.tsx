import "../styles/components.css";

interface Props {
  children: React.ReactNode;
  title?: string;
  accent?: string;
}

export const Card = ({ children, title, accent = "var(--amber)" }: Props) => (
  <div className="card" style={{ borderTopColor: accent }}>
    {title && <div className="card__header">{title}</div>}
    <div className="card__body">{children}</div>
  </div>
);
