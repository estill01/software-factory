import type { RunSummary } from "@/lib/operations-api"
import type { TaskListEnvelope } from "@/lib/task-api"

type ListedTask = TaskListEnvelope["data"]["tasks"][number]

export function runBelongsToProject(
  run: RunSummary,
  tasks: readonly ListedTask[],
  projectId: string,
): boolean {
  if (run.project_binding.status === "bound" && run.project_binding.project_id === projectId) {
    return true
  }
  return tasks.some(
    (task) => task.id === run.target_thread_id
      && task.project_binding.status === "bound"
      && task.project_binding.project_id === projectId,
  )
}

export function taskBelongsToProject(task: ListedTask, projectId: string): boolean {
  return task.project_binding.status === "bound" && task.project_binding.project_id === projectId
}

export function newestTimestamp(values: readonly (string | null | undefined)[]): string | null {
  return values.reduce<string | null>((newest, value) => {
    if (!value) return newest
    if (!newest) return value
    const candidate = Date.parse(value)
    const current = Date.parse(newest)
    if (Number.isNaN(candidate)) return newest
    return Number.isNaN(current) || candidate > current ? value : newest
  }, null)
}

type MissionEvent = {
  mission_root: string
  incident_id?: string | null
  decision_id?: string | null
  transition_id?: string | null
}

export function eventsForMission<T extends MissionEvent>(
  events: readonly T[],
  missionRoot: string,
): T[] {
  return events.filter((event) => event.mission_root === missionRoot)
}

export function missionEntityIds(
  events: readonly MissionEvent[],
  field: "incident_id" | "decision_id" | "transition_id",
): Set<string> {
  return new Set(
    events.flatMap((event) => {
      const value = event[field]
      return value ? [value] : []
    }),
  )
}

export function boundedText(value: string | null | undefined, limit = 220): string {
  if (!value) return "Unavailable"
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value
}

export function shortIdentity(value: string | null | undefined): string {
  if (!value) return "Unavailable"
  return value.length > 22 ? `${value.slice(0, 10)}…${value.slice(-7)}` : value
}

export function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || /[\r\n]/.test(value)) return "/"
  return value
}

function commandExecutable(value: string | null | undefined): string | null {
  if (!value) return null
  let tokens: string[]
  try {
    const parsed = JSON.parse(value) as unknown
    tokens = Array.isArray(parsed) && parsed.every((item) => typeof item === "string")
      ? parsed
      : value.trim().split(/\s+/)
  } catch {
    tokens = value.trim().split(/\s+/)
  }
  const token = tokens.find((item) => !/^[A-Za-z_][A-Za-z0-9_]*=/.test(item))
  if (!token) return null
  const cleaned = token.replace(/^["']|["']$/g, "").split("/").at(-1)
  return cleaned && /^[A-Za-z0-9._+-]{1,80}$/.test(cleaned) ? cleaned : null
}

export function safeTaskItemSummary(type: string, summary: string | null | undefined): string {
  if (type === "commandExecution") {
    const executable = commandExecutable(summary)
    return executable ? `Command · ${executable} · arguments withheld` : "Command recorded · content withheld"
  }
  if (["mcpToolCall", "dynamicToolCall", "collabAgentToolCall"].includes(type)) {
    const tool = summary?.trim()
    return tool && /^[A-Za-z0-9._:/+-]{1,120}$/.test(tool) ? `Tool · ${tool}` : "Tool call recorded"
  }
  if (type === "fileChange") return summary ?? "File change recorded"
  if (["agentMessage", "userMessage", "reasoning", "plan"].includes(type)) {
    return `${type.replace(/([A-Z])/g, " $1").toLowerCase()} · content withheld in dashboard`
  }
  return "Item details withheld in dashboard"
}

export function newestPage<T>(values: readonly T[], page: number, pageSize: number) {
  const safeSize = Math.max(1, Math.floor(pageSize))
  const pageCount = Math.max(1, Math.ceil(values.length / safeSize))
  const safePage = Math.min(Math.max(0, Math.floor(page)), pageCount - 1)
  const end = Math.max(0, values.length - safePage * safeSize)
  const start = Math.max(0, end - safeSize)
  return {
    items: values.slice(start, end),
    start: values.length ? start + 1 : 0,
    end,
    total: values.length,
    page: safePage,
    hasOlder: start > 0,
    hasNewer: safePage > 0,
  }
}
