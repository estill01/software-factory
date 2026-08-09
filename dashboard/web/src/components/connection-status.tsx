import * as Tooltip from "@radix-ui/react-tooltip"
import { useQuery } from "@tanstack/react-query"
import { CircleAlert, Radio } from "lucide-react"

import { fetchHealth } from "@/lib/api"

export function ConnectionStatus() {
  const health = useQuery({
    queryKey: ["runtime-health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30_000,
    retry: 1,
  })

  const state = health.isPending ? "connecting" : health.isError ? "offline" : "online"
  const label =
    state === "connecting"
      ? "Connecting to runtime"
      : state === "offline"
        ? "Runtime unavailable"
        : "Local runtime online"

  return (
    <Tooltip.Provider delayDuration={250}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <div
            className={`connection-pill connection-${state}`}
            role="status"
            aria-label={label}
            aria-live="polite"
          >
            {state === "offline" ? <CircleAlert aria-hidden="true" /> : <Radio aria-hidden="true" />}
            <span>{label}</span>
          </div>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content className="tooltip-content" sideOffset={8}>
            {health.data
              ? `Runtime ${health.data.data.service.version}; catalog ${health.data.data.integrations.project_sources.status}; trackers ${health.data.data.integrations.tracker_sources.status}; supervision ${health.data.data.integrations.supervision_sources.status}; Codex tasks ${health.data.data.integrations.codex_app_server.status}.`
              : "The shell keeps source availability separate from visual readiness."}
            <Tooltip.Arrow className="tooltip-arrow" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}
