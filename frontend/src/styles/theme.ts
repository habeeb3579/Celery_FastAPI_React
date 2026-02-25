export const theme = {
  bg: "#080b0f",
  bgPanel: "#0d1117",
  bgInset: "#060809",
  border: "#1a2030",
  borderHi: "#2a3550",
  amber: "#f59e0b",
  amberDim: "#92400e",
  green: "#10b981",
  greenDim: "#065f46",
  blue: "#38bdf8",
  red: "#ef4444",
  text: "#cbd5e1",
  textHi: "#f1f5f9",
  textLo: "#475569",
  fontMono: "'IBM Plex Mono', 'Fira Code', 'Cascadia Code', monospace",
  fontDisp: "'DM Serif Display', 'Playfair Display', Georgia, serif",
} as const;

export type Theme = typeof theme;
