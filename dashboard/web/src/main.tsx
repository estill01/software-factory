import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { StrictMode, Suspense } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router"

import { AppErrorBoundary } from "@/components/app-error-boundary"
import { LoadingShell } from "@/components/loading-shell"
import { router } from "@/router"
import "@/index.css"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
    },
  },
})

const root = document.getElementById("root")
if (!root) throw new Error("Dashboard root element is missing")

createRoot(root).render(
  <StrictMode>
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Suspense fallback={<LoadingShell />}>
          <RouterProvider router={router} />
        </Suspense>
      </QueryClientProvider>
    </AppErrorBoundary>
  </StrictMode>,
)
