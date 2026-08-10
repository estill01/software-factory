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
      { path: "projects/:projectId/:tab?", lazy: () => import("@/routes/project-workspace-page") },
      { path: "runs/:targetId", lazy: () => import("@/routes/run-workspace-page") },
      { path: "runs/:targetId/supervisor", lazy: () => import("@/routes/supervisor-workspace-page") },
      { path: "tasks/:taskId", lazy: () => import("@/routes/task-workspace-page") },
      { path: "trackers", lazy: () => import("@/routes/trackers-page") },
      { path: "trackers/:trackerId/:view?", lazy: () => import("@/routes/tracker-workspace-page") },
      { path: "reports", lazy: () => import("@/routes/reports-page") },
      { path: "admin", lazy: () => import("@/routes/admin-page") },
      { path: "*", lazy: () => import("@/routes/not-found-page") },
    ],
  },
])
