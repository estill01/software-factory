export function LoadingShell() {
  return (
    <div className="loading-shell" role="status" aria-label="Loading dashboard">
      <div className="loading-sidebar" />
      <div className="loading-content">
        <span className="loading-line loading-line-short" />
        <span className="loading-line loading-line-title" />
        <div className="loading-card-grid">
          {Array.from({ length: 4 }, (_, index) => (
            <span className="loading-card" key={index} />
          ))}
        </div>
      </div>
    </div>
  )
}
