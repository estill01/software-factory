import { describe, expect, it } from "vitest"

import {
  boundedText,
  exactProjectRunIds,
  eventsForMission,
  missionEntityIds,
  newestTimestamp,
  newestPage,
  runBelongsToProject,
  runProjectClaims,
  safeGitOrigin,
  safeReturnPath,
  safeTaskItemSummary,
} from "@/lib/workspace-data"

describe("workspace source boundaries", () => {
  it("associates a run only through its canonical binding or exact target task", () => {
    const run = {
      target_thread_id: "target-1",
      project_binding: { status: "unassigned", project_id: null },
    }
    const exact = [{
      id: "target-1",
      project_binding: { status: "bound", project_id: "alpha" },
    }]
    const sameCwdButDifferentId = [{
      id: "target-2",
      project_binding: { status: "bound", project_id: "alpha" },
    }]

    expect(runBelongsToProject(run as never, exact as never, "alpha")).toBe(true)
    expect(runBelongsToProject(run as never, sameCwdButDifferentId as never, "alpha")).toBe(false)
  })

  it("keeps conflicting run and target-task project claims separate", () => {
    const run = { target_thread_id: "target-1", project_binding: { status: "bound", project_id: "beta" } }
    const task = [{ id: "target-1", project_binding: { status: "bound", project_id: "alpha" } }]

    expect(runBelongsToProject(run as never, task as never, "alpha")).toBe(false)
    expect(runBelongsToProject(run as never, task as never, "beta")).toBe(true)
    expect(runProjectClaims(run as never, task as never, "alpha")).toEqual([
      { source: "run binding", projectId: "beta" },
      { source: "target task", projectId: "alpha" },
      { source: "Factory Floor", projectId: "alpha" },
    ])
    const claims = [{ runId: "target-1", projectId: "alpha" }]
    expect([...exactProjectRunIds([run] as never, task as never, claims, "alpha")]).toEqual([])
    expect([...exactProjectRunIds([run] as never, task as never, claims, "beta")]).toEqual(["target-1"])
  })

  it("keeps predecessor events and entities outside the current mission", () => {
    const predecessor = "a".repeat(64)
    const current = "b".repeat(64)
    const events = [
      { mission_root: predecessor, incident_id: "INC-old", decision_id: null, transition_id: null },
      { mission_root: current, incident_id: "INC-current", decision_id: "DEC-current", transition_id: null },
    ]

    const selected = eventsForMission(events, predecessor)
    expect(selected).toHaveLength(1)
    expect(missionEntityIds(selected, "incident_id")).toEqual(new Set(["INC-old"]))
    expect(missionEntityIds(selected, "decision_id")).toEqual(new Set())
  })

  it("preserves bounded text, newest source time, and local return routes", () => {
    expect(boundedText("123456", 5)).toBe("1234…")
    expect(newestTimestamp(["2026-08-09T10:00:00Z", null, "2026-08-09T11:00:00Z"]))
      .toBe("2026-08-09T11:00:00Z")
    expect(safeReturnPath("/?project=alpha&time=24h")).toBe("/?project=alpha&time=24h")
    expect(safeReturnPath("//example.com/escape")).toBe("/")
    expect(safeReturnPath("/\\example.com/escape")).toBe("/")
  })

  it("never carries command arguments or message bodies into task summaries", () => {
    expect(safeTaskItemSummary("commandExecution", "API_TOKEN=secret curl -H Bearer-secret https://example.com"))
      .toBe("Command · curl · arguments withheld")
    expect(safeTaskItemSummary("userMessage", "password=hunter2")).toBe("user message · content withheld in dashboard")
    expect(safeTaskItemSummary("mcpToolCall", "mcp__owner__read")).toBe("Tool · mcp__owner__read")
    expect(safeTaskItemSummary("mcpToolCall", "tool secret-argument")).toBe("Tool call recorded")
    expect(safeGitOrigin("https://operator:SUPERSECRET@example.com/private/repo.git"))
      .toBe("https://example.com · path and credentials withheld")
    expect(safeGitOrigin("ssh://deploy:SECRET@example.com/private/repo.git"))
      .toBe("example.com · path and credentials withheld")
    expect(safeGitOrigin("git@example.com:private/repo.git"))
      .toBe("example.com · path and credentials withheld")
  })

  it("pages bounded records from the newest window without reordering them", () => {
    expect(newestPage([1, 2, 3, 4, 5, 6, 7], 0, 3)).toMatchObject({
      items: [5, 6, 7], start: 5, end: 7, total: 7, hasOlder: true, hasNewer: false,
    })
    expect(newestPage([1, 2, 3, 4, 5, 6, 7], 1, 3)).toMatchObject({
      items: [2, 3, 4], start: 2, end: 4, total: 7, hasOlder: true, hasNewer: true,
    })
  })
})
