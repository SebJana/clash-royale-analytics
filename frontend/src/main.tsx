import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import './index.css'
import App from './App.tsx'

const day = 24 * 60 * 60 * 1000;
const min = 60 * 1000;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: day,
      staleTime: min,
      refetchOnWindowFocus: false,
    },
  },
});

// Create persister at the root (browser only)
const persister = createAsyncStoragePersister({
  storage: typeof window !== "undefined" ? window.localStorage : undefined,
  key: "rq-cache-v1",
  throttleTime: 1000,
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: day,
        buster: "v1",
      }}
    >
      <App />
    </PersistQueryClientProvider>
  </StrictMode>
);