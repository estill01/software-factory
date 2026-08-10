import type { ReactNode } from "react"

function isBlockStart(line: string): boolean {
  return /^\s*(?:```|~~~|#{1,6}\s|[-*+]\s|\d+[.)]\s|\|)/.test(line)
}

export function SafeMarkdown({ markdown }: { markdown: string }) {
  const lines = markdown.split("\n")
  const blocks: ReactNode[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index] ?? ""
    if (!line.trim()) {
      index += 1
      continue
    }

    if (/^\s*(?:```|~~~)/.test(line)) {
      const fence = line.trim().slice(0, 3)
      const code: string[] = []
      index += 1
      while (index < lines.length && !(lines[index] ?? "").trim().startsWith(fence)) {
        code.push(lines[index] ?? "")
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push(<pre className="safe-markdown-code" key={`code:${index}`}><code>{code.join("\n")}</code></pre>)
      continue
    }

    const heading = line.match(/^\s*#{1,6}\s+(.+)$/)
    if (heading) {
      blocks.push(<strong className="safe-markdown-heading" key={`heading:${index}`}>{heading[1]}</strong>)
      index += 1
      continue
    }

    if (/^\s*[-*+]\s+/.test(line)) {
      const items: string[] = []
      while (index < lines.length && /^\s*[-*+]\s+/.test(lines[index] ?? "")) {
        items.push((lines[index] ?? "").replace(/^\s*[-*+]\s+/, ""))
        index += 1
      }
      blocks.push(<ul key={`ul:${index}`}>{items.map((item, itemIndex) => <li key={`${itemIndex}:${item}`}>{item}</li>)}</ul>)
      continue
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: string[] = []
      while (index < lines.length && /^\s*\d+[.)]\s+/.test(lines[index] ?? "")) {
        items.push((lines[index] ?? "").replace(/^\s*\d+[.)]\s+/, ""))
        index += 1
      }
      blocks.push(<ol key={`ol:${index}`}>{items.map((item, itemIndex) => <li key={`${itemIndex}:${item}`}>{item}</li>)}</ol>)
      continue
    }

    if (line.trim().startsWith("|")) {
      const table: string[] = []
      while (index < lines.length && (lines[index] ?? "").trim().startsWith("|")) {
        table.push(lines[index] ?? "")
        index += 1
      }
      blocks.push(<pre className="safe-markdown-table" key={`table:${index}`}>{table.join("\n")}</pre>)
      continue
    }

    const paragraph = [line.trim()]
    index += 1
    while (index < lines.length && (lines[index] ?? "").trim() && !isBlockStart(lines[index] ?? "")) {
      paragraph.push((lines[index] ?? "").trim())
      index += 1
    }
    blocks.push(<p key={`paragraph:${index}`}>{paragraph.join(" ")}</p>)
  }

  return <div className="safe-markdown" tabIndex={0}>{blocks}</div>
}
