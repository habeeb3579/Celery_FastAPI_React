// ── Service URLs ───────────────────────────────────────────────
// All configurable via .env — defaults match docker-compose ports

export const config = {
  apiUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8090",
  flowerUrl: import.meta.env.VITE_FLOWER_URL ?? "http://localhost:5555",
  redisUrl: import.meta.env.VITE_REDIS_COMMANDER_URL ?? "http://localhost:8081",
  jupyterUrl:
    import.meta.env.VITE_JUPYTER_URL ?? "http://localhost:8888?token=mlproject",
} as const;
