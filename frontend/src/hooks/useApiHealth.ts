import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { ApiStatus } from "../types";

export type { ApiStatus };

export const useApiHealth = (): ApiStatus => {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const sub = api.health().subscribe({
      next: () => setStatus("online"),
      error: () => setStatus("offline"),
    });

    return () => sub.unsubscribe();
  }, []);

  return status;
};
