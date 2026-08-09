import { createBrowserRouter } from "react-router"

import { AppShell } from "@/components/app-shell"
import { LoadingShell } from "@/components/loading-shell"
import { RouteErrorPage } from "@/routes/route-error-page"

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteErrorPage />,
    hydrateFallbackElement: <LoadingShell />,
    children: [
      { index: true, lazy: () => import("@/routes/floor-page") },
      { path: "projects", lazy: () => import("@/routes/projects-page") },
      { path: "trackers", lazy: () => import("@/routes/trackers-page") },
      { path: "reports", lazy: () => import("@/routes/reports-page") },
      { path: "admin", lazy: () => import("@/routes/admin-page") },
      { path: "*", lazy: () => import("@/routes/not-found-page") },
    ],
  },
])
