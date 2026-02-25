import "../styles/components.css";

type Variant = "primary" | "ghost" | "danger";

interface Props {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: Variant;
  fullWidth?: boolean;
}

export const Button = ({
  children,
  onClick,
  disabled,
  variant = "primary",
  fullWidth,
}: Props) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={["btn", `btn--${variant}`, fullWidth ? "btn--full" : ""]
      .filter(Boolean)
      .join(" ")}
  >
    {children}
  </button>
);
