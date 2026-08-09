import { useQuery } from "@tanstack/react-query"
import { CircleAlert, FolderGit2, Settings2 } from "lucide-react"
import { Link } from "react-router"

import { Button } from "@/components/ui/button"
import { fetchProjects } from "@/lib/projects-api"

export function ProjectInventory() {
  const projects = useQuery({
    queryKey: ["projects", false],
    queryFn: ({ signal }) => fetchProjects(false, signal),
  })

  if (projects.isPending) {
    return <div className="inventory-state" role="status">Refreshing registered projects…</div>
  }
  if (projects.isError) {
    return (
      <div className="catalog-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div><strong>Project inventory unavailable</strong><p>{projects.error.message}</p></div>
        <Button variant="outline" size="compact" onClick={() => void projects.refetch()}>Retry</Button>
      </div>
    )
  }
  if (projects.data.data.projects.length === 0) {
    return (
      <div className="project-inventory-empty">
        <div className="page-state-icon"><FolderGit2 aria-hidden="true" /></div>
        <h2>No active projects are registered.</h2>
        <p>The dashboard only discovers repositories you explicitly register. It never scans the workstation.</p>
        <Button asChild><Link to="/admin"><Settings2 aria-hidden="true" /> Open project catalog</Link></Button>
      </div>
    )
  }

  return (
    <div className="project-inventory-grid">
      {projects.data.data.projects.map((project) => (
        <article className="inventory-project" key={project.id}>
          <div className="inventory-project-heading">
            <div className={`project-mark ${project.discovery.status === "unavailable" ? "project-mark-error" : ""}`}>
              {project.discovery.status === "unavailable"
                ? <CircleAlert aria-hidden="true" />
                : <FolderGit2 aria-hidden="true" />}
            </div>
            <div><h2>{project.label}</h2><span>{project.id}</span></div>
            <span className={`discovery-badge ${project.discovery.status === "unavailable" ? "discovery-unavailable" : ""}`}>
              {project.discovery.status === "unavailable" ? "Unavailable" : "Discovered"}
            </span>
          </div>
          <p>{project.description || "No display description."}</p>
          <dl className="inventory-facts">
            <div><dt>Branch</dt><dd>{project.discovery.git.branch || "Unavailable"}</dd></div>
            <div><dt>Revision</dt><dd><code>{project.discovery.git.revision?.slice(0, 10) || "Unavailable"}</code></dd></div>
            <div><dt>Tracker candidates</dt><dd>{project.discovery.trackers.candidates.length}</dd></div>
          </dl>
          {project.discovery.errors.length > 0 && (
            <div className="inventory-error">
              {project.discovery.errors.map((error) => error.message).join(" ")}
            </div>
          )}
          <footer>
            <code>{project.root}</code>
            <span>Observed {new Date(project.observed_at).toLocaleString()}</span>
          </footer>
        </article>
      ))}
    </div>
  )
}
