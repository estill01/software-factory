import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { SafeMarkdown } from "@/components/safe-markdown"

describe("SafeMarkdown", () => {
  it("renders bounded structure without activating source HTML or links", () => {
    const { container } = render(
      <SafeMarkdown markdown={'- Exact fact\n- [unsafe](javascript:alert(1))\n\n<script onerror="SECRET">SECRET</script>\n\n```sh\necho safe\n```'} />,
    )

    expect(screen.getByText("Exact fact")).toBeVisible()
    expect(screen.getByText("[unsafe](javascript:alert(1))")).toBeVisible()
    expect(screen.getByText(/<script onerror="SECRET">/)).toBeVisible()
    expect(screen.getByText("echo safe")).toBeVisible()
    expect(container.querySelector("script")).toBeNull()
    expect(container.querySelector("a")).toBeNull()
    expect(container.querySelector(".safe-markdown")).toHaveAttribute("tabindex", "0")
  })
})
