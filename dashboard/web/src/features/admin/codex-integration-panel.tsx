import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CircleAlert, RefreshCw, ServerCog } from "lucide-react"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  fetchTaskIntegration,
  restartTaskIntegration,
  streamTaskEvents,
} from "@/lib/task-api"

const integrationQueryKey = ["task-integration"] as const

function message(error: unknown): string {
  return error instanceof Error ? error.message : "Codex integration is unavailable."
}

function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase())
}

export function CodexIntegrationPanel() {
  const queryClient = useQueryClient()
  const [streamError, setStreamError] = useState<string | null>(null)
  const integration = useQuery({
    queryKey: integrationQueryKey,
    queryFn: ({ signal }) => fetchTaskIntegration(signal),
    retry: 1,
    refetchInterval: 30_000,
  })
  const restart = useMutation({
    mutationFn: restartTaskIntegration,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: integrationQueryKey }),
        queryClient.invalidateQueries({ queryKey: ["runtime-health"] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
      ])
    },
  })

  useEffect(() => {
    const controller = new AbortController()
    void streamTaskEvents(
      (event) => {
        setStreamError(null)
        void queryClient.invalidateQueries({ queryKey: integrationQueryKey })
        if (event.type !== "connection") {
          void queryClient.invalidateQueries({ queryKey: ["tasks"] })
        }
      },
      controller.signal,
      0,
      (state) => {
        if (state.status === "connected") setStreamError(null)
        if (state.replay_truncated) {
          void Promise.all([
            queryClient.invalidateQueries({ queryKey: integrationQueryKey }),
            queryClient.invalidateQueries({ queryKey: ["tasks"] }),
          ])
        }
      },
    ).catch((error: unknown) => {
      if (!controller.signal.aborted) setStreamError(message(error))
    })
    return () => controller.abort()
  }, [queryClient])

  if (integration.isPending) {
    return (
      <section className="panel integration-panel" aria-busy="true">
        <div className="panel-heading"><h2>Codex integration</h2><span className="data-state-label">Checking</span></div>
        <div className="integration-loading" aria-label="Checking Codex integration" />
      </section>
    )
  }

  if (integration.isError) {
    return (
      <section className="panel integration-panel">
        <div className="panel-heading"><h2>Codex integration</h2><span className="data-state-label">Unavailable</span></div>
        <div className="catalog-error" role="alert">
          <CircleAlert aria-hidden="true" />
          <div><strong>Integration check failed</strong><p>{message(integration.error)}</p></div>
        </div>
      </section>
    )
  }

  const state = integration.data.data.integration
  const available = state.status === "available" && state.protocol_status === "compatible"
  const supported = state.features.filter((feature) => feature.status === "supported").length
  const readFeatures = state.features.filter((feature) => feature.exposure === "read")
  const ownerGatedFeatures = state.features.filter(
    (feature) => feature.exposure === "owner-gated",
  )
  const unavailableFeatures = state.features.filter(
    (feature) => feature.exposure === "unavailable",
  )

  return (
    <section className="panel integration-panel">
      <div className="panel-heading integration-heading">
        <div className="integration-title">
          <span className={`integration-mark ${available ? "integration-mark-ready" : ""}`}>
            <ServerCog aria-hidden="true" />
          </span>
          <h2>Codex integration</h2>
        </div>
        <div className="integration-actions">
          <span className={`data-state-label ${available ? "state-ready" : ""}`}>
            {available ? "Connected" : label(state.protocol_status)}
          </span>
          <Button
            variant="outline"
            size="compact"
            onClick={() => restart.mutate()}
            disabled={restart.isPending}
          >
            <RefreshCw aria-hidden="true" /> {restart.isPending ? "Restarting" : "Restart adapter"}
          </Button>
        </div>
      </div>

      <dl className="integration-facts">
        <div><dt>CLI</dt><dd><code>{state.cli.version ?? state.cli.expected_version ?? "Unavailable"}</code></dd></div>
        <div><dt>Protocol</dt><dd>{label(state.protocol_status)}</dd></div>
        <div><dt>Schema</dt><dd><code>{state.schema.semantic_manifest_sha256?.slice(0, 12) ?? "Unavailable"}</code></dd></div>
        <div><dt>Capabilities</dt><dd>{supported} / {state.features.length}</dd></div>
        <div><dt>Requests</dt><dd>{state.pending_requests}</dd></div>
        <div>
          <dt>Connection</dt>
          <dd>{state.reconnect.retry_after_ms > 0 ? `Retry ${state.reconnect.retry_after_ms} ms` : `Generation ${state.connection_generation}`}</dd>
        </div>
      </dl>

      {(state.last_error || restart.isError || streamError) && (
        <div className="catalog-inline-error" role="alert">
          <CircleAlert aria-hidden="true" />
          <span>{state.last_error?.message ?? (restart.isError ? message(restart.error) : streamError)}</span>
        </div>
      )}

      <div className="integration-capabilities" aria-label="Codex capability matrix">
        <div className="capability-group" role="group" aria-label="Read capabilities">
          <div className="capability-group-label"><span>Read</span><strong>{readFeatures.length}</strong></div>
          <div className="capability-tokens" role="list">
            {readFeatures.map((feature) => (
              <span
                role="listitem"
                className={feature.status === "supported" ? "capability-supported" : ""}
                aria-label={`${label(feature.capability)}: ${feature.status}`}
                title={feature.reason ?? undefined}
                key={feature.capability}
              >
                {label(feature.capability)}
              </span>
            ))}
          </div>
        </div>

        <div className="capability-group" role="group" aria-label="Owner-gated capabilities">
          <div className="capability-group-label"><span>Owner-gated</span><strong>{ownerGatedFeatures.length}</strong></div>
          <div className="capability-tokens" role="list">
            {ownerGatedFeatures.map((feature) => (
              <span
                role="listitem"
                className={feature.status === "supported" ? "capability-supported" : ""}
                aria-label={`${label(feature.capability)}: ${feature.status}`}
                title={feature.reason ?? undefined}
                key={feature.capability}
              >
                {label(feature.capability)}
              </span>
            ))}
          </div>
        </div>

        <div className="capability-group capability-unavailable" role="group" aria-label="Unavailable capabilities">
          <div className="capability-group-label"><span>Not exposed</span><strong>{unavailableFeatures.length}</strong></div>
          <div role="list">
            {unavailableFeatures.map((feature) => (
              <div role="listitem" key={feature.capability}>
                <span>{label(feature.capability)}</span>
                <strong>Unavailable</strong>
                {feature.reason && <small>{feature.reason}</small>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
