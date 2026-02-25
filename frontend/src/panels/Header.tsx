import "../styles/panels.css";
import { Badge } from "../components/Badge";
import { useApiHealth } from "../hooks/useApiHealth";
import { config } from "../config";

const NavLink = ({ href, label }: { href: string; label: string }) => (
  <a href={href} target="_blank" rel="noreferrer" className="header__link">
    {label} ↗
  </a>
);

export const Header = () => {
  const status = useApiHealth();

  return (
    <header className="header">
      <div>
        <div className="panel-row">
          <h1 className="header__title">ML Terminal</h1>
          <span className="header__sub">CELERY + FASTAPI + REDIS + REACT</span>
        </div>
      </div>
      <nav className="header__nav">
        <NavLink href={config.flowerUrl} label="Flower" />
        <NavLink href={config.redisUrl} label="Redis" />
        <NavLink href={`${config.apiUrl}/docs`} label="API" />
        <NavLink href={config.jupyterUrl} label="Jupyter" />
        <Badge
          label={
            status === "online"
              ? "● online"
              : status === "offline"
                ? "● offline"
                : "● checking"
          }
          color={
            status === "online"
              ? "var(--green)"
              : status === "offline"
                ? "var(--red)"
                : "var(--amber)"
          }
        />
      </nav>
    </header>
  );
};
