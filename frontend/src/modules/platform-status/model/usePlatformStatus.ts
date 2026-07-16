import { useEffect, useState } from "react";

import { getReadiness } from "../api/getReadiness";

export type PlatformState = "loading" | "ready" | "error";

export function usePlatformStatus(): PlatformState {
  const [state, setState] = useState<PlatformState>("loading");

  useEffect(() => {
    const controller = new AbortController();
    getReadiness(controller.signal)
      .then(() => {
        setState("ready");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setState("error");
      });
    return () => {
      controller.abort();
    };
  }, []);

  return state;
}
