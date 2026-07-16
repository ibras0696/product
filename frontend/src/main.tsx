import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import "@/app/styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element is missing");
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: 60_000 },
    mutations: { retry: false },
  },
});

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
