import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ExternalLink, ListChecks, Printer } from "lucide-react"
import { useState } from "react"
import { Link, NavLink, useParams, useSearchParams } from "react-router"

import { SafeMarkdown } from "@/components/safe-markdown"
import { TrackerProgressView } from "@/components/tracker-progress-view"
import { Button } from "@/components/ui/button"
import { TrackerWorkflowActions } from "@/features/admin/factory-workflow-actions"
import {
  Breadcrumbs,
  FactGrid,
  Identity,
  QueryState,
  StatusMark,
  TimeValue,
  WorkspaceBack,
} from "@/components/workspace-ui"
import { fetchFactoryFloor, type FactoryFloorRow } from "@/lib/floor-api"
import { projectTrackerProgress } from "@/lib/tracker-progress"
import {
  fetchTracker,
  fetchTrackerDiff,
  fetchTrackerSource,
  trackerSourceUrl,
  type TrackerDetail,
} from "@/lib/trackers-api"

const views = ["overview", "blocks", "evidence"] as const
type TrackerView = typeof views[number]
type TrackerSection = TrackerDetail["document_sections"][number]
type MappedRunProjection = {
  rows: FactoryFloorRow[]
  posture: "complete" | "partial" | "unavailable"
  missing: string[]
}

const requiredBlockSections = [
  ["Capability delta", "target-product capability delta"],
  ["Inputs / dependencies", "inputs and dependencies"],
  ["Required work", "required work"],
  ["Scope / non-goals", "scope and non-goals"],
  ["Deliverables", "deliverables and recorded state"],
  ["Resource / economy", "resource and economy contract"],
  ["QA / review", "qa and independent review"],
  ["Acceptance", "acceptance"],
  ["Negative tests", "negative tests"],
  ["Completion evidence", "completion evidence"],
] as const

function isView(value: string | undefined): value is TrackerView {
  return views.includes(value as TrackerView)
}

function SectionCard({ trackerId, section }: { trackerId: string; section: TrackerSection }) {
  const [loadExact, setLoadExact] = useState(false)
  const exact = useQuery({
    queryKey: ["tracker-source", trackerId, section.line, section.end_line],
    queryFn: ({ signal }) => fetchTrackerSource(trackerId, { line: section.line, endLine: section.end_line }, signal),
    enabled: loadExact,
    retry: false,
  })
  const markdown = exact.data ?? section.markdown_preview

  return (
    <article className="tracker-section-card" id={section.anchor}>
      <div className="tracker-section-heading">
        <div><strong>{section.title}</strong><span>Lines {section.line}–{section.end_line}</span></div>
        <Identity value={section.content_sha256} />
      </div>
      {exact.isError ? <QueryState kind="error" message={exact.error.message} retry={() => void exact.refetch()} /> : (
        <SafeMarkdown markdown={markdown} />
      )}
      <div className="tracker-section-actions">
        {(section.preview_truncated || loadExact) && !exact.data && (
          <Button variant="outline" size="compact" onClick={() => setLoadExact(true)} disabled={loadExact && exact.isPending}>
            {loadExact && exact.isPending ? "Loading exact range" : "Load exact source range"}
          </Button>
        )}
        <Button variant="ghost" size="compact" asChild>
          <a href={trackerSourceUrl(trackerId, { line: section.line, endLine: section.end_line })} target="_blank" rel="noreferrer">
            Source <ExternalLink aria-hidden="true" />
          </a>
        </Button>
      </div>
    </article>
  )
}

function isActiveRun(row: FactoryFloorRow) {
  return row.implementation.status === "active" || row.supervision.status === "active"
}

function mappedRunSummary(mapping: MappedRunProjection) {
  if (mapping.posture === "unavailable") return "Unavailable from composed owner"
  if (mapping.posture === "partial") {
    return mapping.rows.length
      ? `${mapping.rows.length} observed active claim${mapping.rows.length === 1 ? "" : "s"} · total unavailable`
      : "Exact absence unavailable · partial coverage"
  }
  return mapping.rows.length
    ? `${mapping.rows.length} exact active claim${mapping.rows.length === 1 ? "" : "s"}`
    : "No exact active claim"
}

function workingSourceSummary(tracker: TrackerDetail) {
  if (tracker.git.status !== "available" || tracker.git.diff.status !== "available" || tracker.git.diff.changed === null) {
    return "Unavailable from Git owner"
  }
  return tracker.git.diff.changed ? "Working tree differs from HEAD" : "No working-tree changes after HEAD"
}

function runBoundSourceSummary(tracker: TrackerDetail) {
  if (tracker.git.binding_status === "current") return "Matches run-bound content hash"
  if (tracker.git.binding_status === "stale") return "Run-bound content hash is stale"
  return "Unavailable from run owner"
}

function ReadinessFacts({ tracker, mapping }: { tracker: TrackerDetail; mapping: MappedRunProjection }) {
  const missingAcceptedEvidence = tracker.blocks.filter((block) => block.status === "accepted" && block.completion_evidence.posture === "missing").length
  return (
    <FactGrid facts={[
      ["Maintained verifier", tracker.verifier.valid ? "Valid" : `${tracker.verifier.errors.length} errors`],
      ["Source currentness", `${tracker.progress_posture} · Git ${tracker.git.durability}`],
      ["Dependency eligibility", tracker.eligible_blocks.length ? `Blocks ${tracker.eligible_blocks.join(", ")}` : "No eligible Block"],
      ["Current execution", tracker.current_blocks.length ? `Blocks ${tracker.current_blocks.join(", ")}` : "No Block in progress"],
      ["Accepted evidence", missingAcceptedEvidence ? `${missingAcceptedEvidence} accepted Blocks missing evidence` : "No accepted evidence gap"],
      ["Mapped active run", mappedRunSummary(mapping)],
    ]} />
  )
}

function WorkingTreeDiff({ tracker }: { tracker: TrackerDetail }) {
  const [requested, setRequested] = useState(false)
  const diffQuery = useQuery({
    queryKey: ["tracker-diff", tracker.id, tracker.raw_file.content_sha256, tracker.git.repository_head],
    queryFn: ({ signal }) => fetchTrackerDiff(tracker.id, signal),
    enabled: requested,
    retry: false,
  })
  const loaded = diffQuery.data?.data
  const snapshotMatches = loaded
    ? loaded.content_sha256 === tracker.raw_file.content_sha256
      && loaded.repository_head === tracker.git.repository_head
    : true

  return (
    <section className="workspace-panel">
      <div className="workspace-panel-heading"><h2>Working tree comparison</h2><StatusMark status={tracker.git.diff.status === "available" ? tracker.git.diff.changed ? "dirty" : "current" : "unavailable"} /></div>
      <FactGrid facts={[
        ["Base", tracker.git.diff.base ?? "Unavailable"],
        ["Changed", tracker.git.diff.changed === null ? "Unavailable" : tracker.git.diff.changed ? "Yes" : "No"],
        ["Added lines", tracker.git.diff.added_lines ?? "Unavailable"],
        ["Removed lines", tracker.git.diff.removed_lines ?? "Unavailable"],
        ["Text", tracker.git.diff.changed ? "Deferred until requested" : tracker.git.diff.status === "available" ? "No diff" : "Unavailable"],
      ]} />
      {diffQuery.isError ? (
        <QueryState kind="error" message={diffQuery.error.message} retry={() => void diffQuery.refetch()} />
      ) : !snapshotMatches ? (
        <QueryState kind="error" message="Tracker content or repository HEAD changed; refresh before reviewing the diff." />
      ) : loaded?.diff.preview ? (
        <>
          {loaded.diff.truncated && <div className="workspace-bound">Diff preview is bounded.</div>}
          <pre className="tracker-diff-preview" tabIndex={0} aria-label="Tracker textual diff"><code>{loaded.diff.preview}</code></pre>
        </>
      ) : tracker.git.diff.changed ? (
        <Button variant="outline" size="compact" onClick={() => setRequested(true)} disabled={requested && diffQuery.isPending}>
          {requested && diffQuery.isPending ? "Loading textual diff" : "Load textual diff"}
        </Button>
      ) : (
        <span className="workspace-muted">{tracker.git.diff.error?.message ?? "No working-tree changes."}</span>
      )}
    </section>
  )
}

export function Component() {
  const { trackerId = "", view } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeView: TrackerView = isView(view) ? view : "overview"
  const trackerQuery = useQuery({
    queryKey: ["tracker", trackerId],
    queryFn: ({ signal }) => fetchTracker(trackerId, signal),
    retry: false,
  })
  const floor = useQuery({ queryKey: ["factory-floor"], queryFn: ({ signal }) => fetchFactoryFloor(signal) })

  if (trackerQuery.isPending) return <QueryState kind="loading" message="Loading tracker" />
  if (trackerQuery.isError) return <QueryState kind="error" message={trackerQuery.error.message} retry={() => void trackerQuery.refetch()} />

  const tracker = trackerQuery.data.data.tracker
  const progress = projectTrackerProgress(tracker, floor.data)
  const mappedRows = progress.exactMappedRows
  const activeMappedRows = mappedRows.filter(isActiveRun)
  const selectedValue = searchParams.get("block")
  const selectedNumber = selectedValue === null ? null : Number(selectedValue)
  const explicitlySelectedBlock = selectedNumber !== null && Number.isSafeInteger(selectedNumber)
    ? tracker.blocks.find((block) => block.number === selectedNumber)
    : undefined
  const selectedBlock = explicitlySelectedBlock
    ?? tracker.blocks.find((block) => tracker.current_blocks.includes(block.number))
    ?? tracker.blocks.find((block) => tracker.eligible_blocks.includes(block.number))
    ?? tracker.blocks[0]
  const selectBlock = (number: number) => {
    const next = new URLSearchParams(searchParams)
    next.set("block", String(number))
    setSearchParams(next)
  }
  const children = new Map<number, number[]>()
  tracker.blocks.forEach((block) => block.dependencies.forEach((dependency) => {
    children.set(dependency, [...(children.get(dependency) ?? []), block.number])
  }))
  const branching = tracker.blocks.some((block) => block.dependencies.length > 1)
    || [...children.values()].some((items) => items.length > 1)
  const overviewSections = tracker.document_sections.filter((section) =>
    /(mission frame|scope|execution contract|definition of done|final integrated acceptance|final acceptance)/.test(section.normalized_title),
  )
  const acceptedOutcomes = floor.data
    ? floor.data.data.accepted_outcomes.filter((outcome) => outcome.tracker_id === tracker.id)
    : null
  const mapping: MappedRunProjection = {
    rows: activeMappedRows,
    posture: floor.isPending || floor.isError
      ? "unavailable"
      : floor.data.coverage.status === "complete" && !floor.data.data.rows_truncated
        ? "complete"
        : "partial",
    missing: floor.data
      ? [...floor.data.coverage.missing, ...(floor.data.data.rows_truncated ? ["bounded factory-floor rows"] : [])]
      : [],
  }
  const missingSelectedSections = selectedBlock
    ? requiredBlockSections.filter(([, normalized]) =>
      !selectedBlock.sections.some((section) => section.normalized_title === normalized),
    )
    : []
  const recordedEvidenceBlocks = tracker.blocks.filter((block) => block.completion_evidence.present)
  const basePath = `/trackers/${tracker.id}`

  return (
    <div className="page-stack workspace-page tracker-workspace">
      <div className="workspace-context-bar">
        <Breadcrumbs><Link to="/trackers">Trackers</Link><span>/</span><strong>{tracker.title}</strong></Breadcrumbs>
        <WorkspaceBack to="/trackers" label="Trackers" />
      </div>

      <section className="workspace-identity-strip">
        <span className="tracker-index-mark"><ListChecks aria-hidden="true" /></span>
        <div><strong>{tracker.title}</strong><span>{tracker.project_label} · {tracker.relative_path}</span></div>
        <StatusMark status={tracker.verifier.valid ? tracker.tracker_status ?? "available" : "invalid"} />
        <Identity value={tracker.raw_file.content_sha256} />
      </section>

      <TrackerProgressView progress={progress} accepted={tracker.counts.accepted} />

      <TrackerWorkflowActions tracker={tracker} selectedBlock={selectedBlock} />

      <nav className="workspace-tabs" aria-label="Tracker views">
        {views.map((name) => <NavLink key={name} end={name === "overview"} to={name === "overview" ? basePath : `${basePath}/${name}`}>{name[0].toUpperCase() + name.slice(1)}</NavLink>)}
      </nav>

      {activeView === "overview" && (
        <>
          <section className="workspace-summary-grid" aria-label="Tracker summary">
            <div><span>Blocks</span><strong>{progress.total.value ?? "—"}</strong><small>{progress.total.posture === "exact" ? "Maintained verifier" : "Unavailable"}</small></div>
            <div><span>Accepted</span><strong>{tracker.counts.accepted}</strong><small>Only `accepted`</small></div>
            <div><span>Open</span><strong>{tracker.counts.open}</strong><small>Includes open-item postures</small></div>
            <div><span>Eligible</span><strong>{tracker.eligible_blocks.length}</strong><small>{tracker.eligible_blocks.length ? `Blocks ${tracker.eligible_blocks.join(", ")}` : "None"}</small></div>
          </section>

          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Review readiness</h2><span>Deterministic facts</span></div>
              <ReadinessFacts tracker={tracker} mapping={mapping} />
            </section>
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Contract identity</h2><StatusMark status={tracker.profile} /></div>
              <FactGrid facts={[
                ["Governing objective", tracker.metadata["governing objective"] ?? "Unavailable"],
                ["Sequence", tracker.tracker_sequence ?? "Unavailable"],
                ["Profile", `${tracker.profile} · ${tracker.profile_reason}`],
                ["Tracker status", tracker.tracker_status ?? "Unavailable"],
                ["Content hash", <Identity value={tracker.raw_file.content_sha256} />],
                ["Raw source", <a href={trackerSourceUrl(tracker.id)} target="_blank" rel="noreferrer">Open read-only Markdown</a>],
              ]} />
            </section>
          </div>

          {tracker.frames.map((frame) => (
            <section className="workspace-panel" key={`${frame.line}:${frame.title}`}>
              <div className="workspace-panel-heading"><h2>{frame.title}</h2><a href={trackerSourceUrl(tracker.id, { line: frame.line, endLine: frame.end_line })} target="_blank" rel="noreferrer">Lines {frame.line}–{frame.end_line}</a></div>
              <FactGrid facts={Object.entries(frame.fields).map(([label, value]) => [label, value])} />
              {frame.duplicate_fields.length > 0 && <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />Duplicate fields: {frame.duplicate_fields.join(", ")}</div>}
            </section>
          ))}

          {tracker.owner_source_maps.map((map) => (
            <section className="workspace-panel" key={`${map.line}:${map.title}`}>
              <div className="workspace-panel-heading"><h2>{map.title}</h2><span>Lines {map.line}–{map.end_line}</span></div>
              {map.tables.map((table) => (
                <div className="table-scroll" key={table.line}>
                  <table className="tracker-contract-table"><thead><tr>{table.headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={`${cellIndex}:${cell}`}>{cell}</td>)}</tr>)}</tbody></table>
                  {table.truncated && <span className="workspace-bound">Table projection is bounded.</span>}
                </div>
              ))}
            </section>
          ))}

          {overviewSections.map((section) => <SectionCard trackerId={tracker.id} section={section} key={`${section.line}:${section.title}`} />)}
        </>
      )}

      {activeView === "blocks" && selectedBlock && (
        <div className="tracker-block-layout">
          <aside className="tracker-block-nav" aria-label="Tracker Blocks">
            <div><strong>Blocks</strong><span>{tracker.blocks.length}</span></div>
            {tracker.blocks.map((block) => (
              <button type="button" key={block.number} className={selectedBlock.number === block.number ? "tracker-block-selected" : ""} onClick={() => selectBlock(block.number)}>
                <span>Block {block.number}</span><StatusMark status={block.status} /><small>{block.title}{block.blocked_ancestors.length ? ` · descendant-blocked by ${block.blocked_ancestors.join(", ")}` : ""}</small>
              </button>
            ))}
          </aside>
          <div className="tracker-block-detail">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Block {selectedBlock.number} · {selectedBlock.title}</h2><StatusMark status={selectedBlock.status} /></div>
              <FactGrid facts={[
                ["Dependencies", selectedBlock.dependency_expression || "None"],
                ["Dependency states", selectedBlock.dependency_statuses.length ? selectedBlock.dependency_statuses.map((item) => `${item.number}: ${item.status ?? "unknown"}`).join(" · ") : "None"],
                ["Blocked ancestors", selectedBlock.blocked_ancestors.length ? `Blocks ${selectedBlock.blocked_ancestors.join(", ")}` : "None"],
                ["Eligible", selectedBlock.eligible ? "Yes — maintained verifier valid and dependencies accepted" : "No"],
                ["Objective", selectedBlock.objective ?? "Unavailable"],
                ["Completion evidence", `${selectedBlock.completion_evidence.posture} · ${selectedBlock.completion_evidence.present ? "present" : "absent"}`],
                ["Stop", selectedBlock.stop ?? "Unavailable"],
              ]} />
            </section>
            {missingSelectedSections.length > 0 && (
              <div className="workspace-partial" role="status">
                <AlertTriangle aria-hidden="true" />Unavailable in source: {missingSelectedSections.map(([label]) => label).join(", ")}.
              </div>
            )}
            {selectedBlock.sections.map((section) => <SectionCard trackerId={tracker.id} section={section} key={`${selectedBlock.number}:${section.line}`} />)}
          </div>
          <section className="workspace-panel tracker-dependency-panel">
            <div className="workspace-panel-heading"><h2>Required order</h2><span>{branching ? "Branching graph" : "Linear dependency list"}</span></div>
            <ol className={`tracker-dependency-list ${branching ? "tracker-dependency-branching" : ""}`}>
              {tracker.blocks.map((block) => <li key={block.number}><StatusMark status={block.status} /><strong>Block {block.number}</strong><span>{block.dependencies.length ? `after ${block.dependencies.join(", ")}` : "root"}</span>{block.eligible && <span className="workspace-badge">Eligible</span>}{block.blocked_ancestors.length > 0 && <span className="workspace-badge">Descendant-blocked · Blocks {block.blocked_ancestors.join(", ")}</span>}</li>)}
            </ol>
          </section>
        </div>
      )}

      {activeView === "blocks" && !selectedBlock && (
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Block projection</h2><StatusMark status="invalid" /></div>
          <QueryState kind="error" message="No Blocks could be projected. Review verifier diagnostics or the read-only source." />
          <div className="workspace-toolbar">
            <Button variant="outline" size="compact" asChild><Link to={`${basePath}/evidence`}>Verifier diagnostics</Link></Button>
            <Button variant="ghost" size="compact" asChild><a href={trackerSourceUrl(tracker.id)} target="_blank" rel="noreferrer">Raw source</a></Button>
          </div>
        </section>
      )}

      {activeView === "evidence" && (
        <>
          <div className="workspace-toolbar print-hide">
            <span>Read-only review packet</span>
            <Button variant="outline" size="compact" onClick={() => window.print()}><Printer aria-hidden="true" />Print</Button>
            <Button variant="ghost" size="compact" asChild><a href={trackerSourceUrl(tracker.id)} target="_blank" rel="noreferrer"><ExternalLink aria-hidden="true" />Raw source</a></Button>
          </div>
          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Git &amp; currentness</h2><StatusMark status={tracker.progress_posture} /></div>
              <FactGrid facts={[
                ["Repository HEAD", <Identity value={tracker.git.repository_head} />],
                ["Branch", tracker.git.branch ?? "Unavailable"],
                ["Tracker blob", <Identity value={tracker.git.git_blob} />],
                ["Working content", <Identity value={tracker.raw_file.content_sha256} />],
                ["Bound content", <Identity value={tracker.git.bound_content_sha256} />],
                ["Binding", tracker.git.binding_status],
                ["Durability", `${tracker.git.durability} · ahead ${tracker.git.ahead ?? "?"} · behind ${tracker.git.behind ?? "?"}`],
                ["Last change", tracker.git.last_commit ? <><TimeValue value={tracker.git.last_commit.committed_at} /> · {tracker.git.last_commit.subject}</> : "Unavailable"],
              ]} />
            </section>
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Verifier</h2><StatusMark status={tracker.verifier.valid ? "valid" : "invalid"} /></div>
              <FactGrid facts={[
                ["Profile", tracker.verifier.profile],
                ["Exit status", tracker.verifier.exit_status],
                ["Owner", tracker.verifier.owner.identity],
                ["Owner revision", <Identity value={tracker.verifier.owner.owning_revision} />],
                ["Owner hash", <Identity value={tracker.verifier.owner.sha256} />],
                ["Blocks", tracker.verifier.blocks.join(", ")],
              ]} />
              {[...tracker.verifier.errors, ...tracker.verifier.warnings].length ? <ul className="tracker-diagnostics">{tracker.verifier.errors.map((item) => <li key={`error:${item}`}><AlertTriangle aria-hidden="true" />{item}</li>)}{tracker.verifier.warnings.map((item) => <li key={`warning:${item}`}>{item}</li>)}</ul> : <span className="workspace-muted">No verifier diagnostics.</span>}
            </section>
          </div>

          <WorkingTreeDiff tracker={tracker} />

          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Mapped execution</h2><span>{floor.isPending ? "Loading" : floor.isError ? "Unavailable" : mapping.posture === "partial" ? `${activeMappedRows.length} observed · partial` : activeMappedRows.length}</span></div>
              {floor.isPending ? <QueryState kind="loading" message="Loading mapped run claims" /> : floor.isError ? <QueryState kind="error" message={floor.error.message} /> : activeMappedRows.length ? <><div className="workspace-record-list">{activeMappedRows.map((row) => <Link to={row.supervision.run_id ? `/runs/${encodeURIComponent(row.supervision.run_id)}` : `/tasks/${encodeURIComponent(row.implementation.task_id)}`} className="workspace-record" key={row.id}><div><strong>{row.implementation.name ?? "Unnamed work"}</strong><Identity value={row.supervision.run_id ?? row.implementation.task_id} /></div><StatusMark status={row.work.tracker.status} /><span>{row.work.tracker.relative_path} · bound hash unavailable from run owner</span><TimeValue value={row.freshness.observed_at} /></Link>)}</div>{mapping.posture === "partial" && <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />Observed active claims are a lower bound. Missing: {mapping.missing.join(", ") || "unreported composed-owner coverage"}.</div>}</> : mapping.posture === "partial" ? <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />No active claim was observed, but exact absence is unavailable. Missing: {mapping.missing.join(", ") || "unreported composed-owner coverage"}.</div> : <QueryState kind="empty" message="No exact active tracker/run claim" />}
            </section>
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Outcome reconciliation</h2><span>{floor.isPending ? "Loading" : floor.isError ? "Unavailable" : acceptedOutcomes?.length ?? 0}</span></div>
              <FactGrid facts={[
                ["Retained open Blocks", tracker.counts.open],
                ["Current Blocks", tracker.current_blocks.length ? tracker.current_blocks.join(", ") : "None"],
                ["Recorded accepted outcomes", floor.isPending || floor.isError ? "Unavailable from composed owner" : acceptedOutcomes?.length ?? 0],
                ["Header/status conflict", tracker.header_block_status_conflict ? "Yes" : "No"],
                ["Working source after HEAD", workingSourceSummary(tracker)],
                ["Run-bound source comparison", runBoundSourceSummary(tracker)],
              ]} />
            </section>
          </div>

          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Recorded Block evidence</h2><span>{recordedEvidenceBlocks.length}</span></div>
            {recordedEvidenceBlocks.length ? (
              <div className="workspace-record-list">
                {recordedEvidenceBlocks.map((block) => (
                  <Link className="workspace-record" key={block.number} to={`${basePath}/blocks?block=${block.number}`}>
                    <div><strong>Block {block.number}</strong><span>{block.title}</span></div>
                    <StatusMark status={block.completion_evidence.posture} />
                    <span>{block.completion_evidence.preview ?? "Recorded; preview unavailable."}</span>
                    <span>{block.completion_evidence.line ? `Line ${block.completion_evidence.line}` : "Line unavailable"}</span>
                  </Link>
                ))}
              </div>
            ) : <QueryState kind="empty" message="No recorded Block completion evidence" />}
          </section>

          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Review readiness</h2><span>Derived display only</span></div>
            <ReadinessFacts tracker={tracker} mapping={mapping} />
            <div className="workspace-bound">These facts do not accept, edit, validate, or start the tracker.</div>
          </section>
        </>
      )}
    </div>
  )
}
