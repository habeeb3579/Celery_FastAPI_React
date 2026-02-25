import "../styles/components.css";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}

export const Select = ({ label, value, onChange, options }: Props) => (
  <div className="select-wrapper">
    <label className="select-label">{label}</label>
    <select
      className="select-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  </div>
);
