import {
  Factory,
  FileChartColumn,
  FolderKanban,
  ListChecks,
  Moon,
  Settings2,
  Sun,
} from "lucide-react"
import { NavLink, Outlet, useLocation } from "react-router"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/cn"
import { useTheme } from "@/lib/theme"
import { ConnectionStatus } from "@/components/connection-status"

type NavigationItem = {
  to: string
  label: string
  icon: typeof Factory
  end?: boolean
}

const navigation: readonly NavigationItem[] = [
  { to: "/", label: "Factory Floor", icon: Factory, end: true },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/trackers", label: "Trackers", icon: ListChecks },
  { to: "/reports", label: "Reports", icon: FileChartColumn },
  { to: "/admin", label: "Admin", icon: Settings2 },
] as const

function NavigationLinks() {
  return navigation.map(({ to, label, icon: Icon, end }) => (
    <NavLink
      key={to}
      to={to}
      end={end}
      className={({ isActive }) => cn("nav-link", isActive && "nav-link-active")}
    >
      <Icon aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  ))
}

export function AppShell() {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const current = navigation.find(({ to }) =>
    to === "/" ? location.pathname === "/" : location.pathname.startsWith(to),
  )

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>

      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true"><Factory /></div>
          <div>
            <strong>Software Factory</strong>
            <span>Operations</span>
          </div>
        </div>

        <div className="sidebar-section-label">Control room</div>
        <nav className="sidebar-nav"><NavigationLinks /></nav>

        <div className="sidebar-readiness">
          <div className="sidebar-readiness-heading">
            <span className="status-dot status-green" />
            Shell ready
          </div>
          <p>Operational sources remain disconnected until their owning Blocks are accepted.</p>
        </div>

        <div className="sidebar-footer">
          <span>Local only</span>
          <span>Block 1</span>
        </div>
      </aside>

      <div className="shell-body">
        <header className="topbar">
          <div className="topbar-title">
            <span className="mobile-brand-mark" aria-hidden="true"><Factory /></span>
            <div>
              <span className="topbar-kicker">Factory workspace</span>
              <strong>{current?.label ?? "Workspace"}</strong>
            </div>
          </div>
          <div className="topbar-actions">
            <ConnectionStatus />
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
            </Button>
          </div>
        </header>

        <nav className="mobile-nav" aria-label="Primary navigation">
          <NavigationLinks />
        </nav>

        <main id="main-content" className="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
