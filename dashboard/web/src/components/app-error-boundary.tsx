import { Component, type ErrorInfo, type ReactNode } from "react"

type Props = { children: ReactNode }
type State = { error: Error | null }

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Dashboard render failure", error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="fatal-state">
          <p className="eyebrow">Interface error</p>
          <h1>The dashboard shell could not render.</h1>
          <p>Reload the local page. No Factory operation was attempted.</p>
          <button className="button button-primary" onClick={() => window.location.reload()}>
            Reload dashboard
          </button>
        </main>
      )
    }
    return this.props.children
  }
}
