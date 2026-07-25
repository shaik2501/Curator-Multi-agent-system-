"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, listLLMConfigs } from "@/lib/api";
import type { LLMConfig } from "@/lib/types";

/** Shared fetch of the user's saved LLM configs — used by the dashboard
 * selector and the settings page's saved-configs list. */
export function useLLMConfigs() {
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [notDeployed, setNotDeployed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    setNotDeployed(false);
    listLLMConfigs()
      .then((data) => setConfigs(data))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setNotDeployed(true);
        } else {
          setError(
            err instanceof ApiError
              ? err.message
              : "Could not reach the backend to load LLM configs.",
          );
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { configs, setConfigs, loading, error, notDeployed, refresh };
}
