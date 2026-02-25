import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/ change port to 3000 and host to 0.0.0.0 for docker compatibility instead of default 5173 and localhost
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
  },
});
