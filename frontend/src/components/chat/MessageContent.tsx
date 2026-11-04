function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatInline(text: string) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong class="msg-bold">$1</strong>')
    .replace(/__(.+?)__/g, '<span class="msg-semibold">$1</span>')
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em class="msg-em">$2</em>');
}

function normalizeLine(line: string) {
  return line
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/\uFF03/g, "#")
    .trim();
}

function stripWrap(line: string) {
  const wrapped = /^(?:\*\*|__)([\s\S]+)(?:\*\*|__)$/.exec(line);
  return wrapped ? wrapped[1].trim() : line;
}

function headingFrom(line: string): { level: 1 | 2 | 3; text: string } | null {
  const match = /^(#{1,6})\s+(.+)$/.exec(stripWrap(line).replace(/^\\+/, ""));
  if (!match) return null;
  const text = match[2]
    .replace(/^(?:#+\s*)+/, "")
    .replace(/\s+#+\s*$/, "")
    .trim();
  if (!text) return null;
  return { level: Math.min(match[1].length, 3) as 1 | 2 | 3, text };
}

function isListLine(line: string) {
  const text = stripWrap(line);
  return /^\d+\.\s+/.test(text) || /^[-*•]\s+/.test(text);
}

function isSectionLabel(line: string) {
  return (
    line.length > 0 &&
    line.length <= 90 &&
    !/[.!?।]$/.test(line) &&
    !/^[-*•#\d]/.test(line)
  );
}

function splitCells(line: string) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isSeparatorRow(line: string) {
  const cells = splitCells(line);
  return (
    cells.length > 0 &&
    cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s/g, "")))
  );
}

function isTableLine(line: string) {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.includes("|", 1);
}

type Block =
  | { type: "table"; rows: string[][] }
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "ol"; items: string[] }
  | { type: "ul"; items: string[] }
  | { type: "p"; text: string };

function parseBlocks(content: string): Block[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = normalizeLine(line);

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (isTableLine(trimmed)) {
      const tableLines: string[] = [];
      while (i < lines.length && isTableLine(lines[i].trim())) {
        tableLines.push(lines[i].trim());
        i += 1;
      }
      const rows = tableLines
        .filter((row) => !isSeparatorRow(row))
        .map(splitCells);
      if (rows.length > 0) {
        blocks.push({ type: "table", rows });
      }
      continue;
    }

    const heading = headingFrom(trimmed);
    if (heading) {
      blocks.push({ type: "heading", ...heading });
      i += 1;
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i].trim();
        if (!current) {
          const next = lines[i + 1]?.trim() ?? "";
          if (/^\d+\.\s+/.test(next) || /^[-*•]\s+/.test(next)) {
            i += 1;
            continue;
          }
          break;
        }
        if (/^\d+\.\s+/.test(current)) {
          items.push(current.replace(/^\d+\.\s+/, ""));
          i += 1;
          continue;
        }
        if (/^[-*•]\s+/.test(current) && items.length > 0) {
          items[items.length - 1] +=
            "\n• " + current.replace(/^[-*•]\s+/, "");
          i += 1;
          continue;
        }
        break;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    if (/^[-*•]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i].trim();
        if (!current) {
          const next = lines[i + 1]?.trim() ?? "";
          if (/^[-*•]\s+/.test(next)) {
            i += 1;
            continue;
          }
          break;
        }
        if (/^[-*•]\s+/.test(current)) {
          items.push(current.replace(/^[-*•]\s+/, ""));
          i += 1;
          continue;
        }
        break;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    if (/^[-*_]{3,}$/.test(trimmed)) {
      i += 1;
      continue;
    }

    let next = i + 1;
    while (next < lines.length && !normalizeLine(lines[next])) next += 1;
    if (
      isSectionLabel(trimmed) &&
      next < lines.length &&
      isListLine(normalizeLine(lines[next]))
    ) {
      blocks.push({ type: "heading", level: 3, text: trimmed });
      i += 1;
      continue;
    }

    blocks.push({ type: "p", text: trimmed });
    i += 1;
  }

  return blocks;
}

function renderRichText(text: string) {
  return text.split("\n").map((part, idx) => (
    <span key={idx}>
      {idx > 0 && <br />}
      <span dangerouslySetInnerHTML={{ __html: formatInline(part) }} />
    </span>
  ));
}

function renderBlock(block: Block, idx: number) {
        if (block.type === "table") {
          const [header, ...body] = block.rows;
          return (
            <div className="msg-table-wrap" key={idx}>
              <table className="msg-table">
                {header && (
                  <thead>
                    <tr>
                      {header.map((cell, cellIdx) => (
                        <th
                          key={cellIdx}
                          dangerouslySetInnerHTML={{
                            __html: formatInline(cell),
                          }}
                        />
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {body.map((row, rowIdx) => (
                    <tr key={rowIdx}>
                      {row.map((cell, cellIdx) => (
                        <td
                          key={cellIdx}
                          dangerouslySetInnerHTML={{
                            __html: formatInline(cell),
                          }}
                        />
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        if (block.type === "heading") {
          const Tag = `h${block.level}` as "h1" | "h2" | "h3";
          return (
            <Tag
              className={`msg-h msg-h${block.level}`}
              key={idx}
              dangerouslySetInnerHTML={{ __html: formatInline(block.text) }}
            />
          );
        }

        if (block.type === "ol") {
          return (
            <ol className="msg-ol" key={idx}>
              {block.items.map((item, itemIdx) => (
                <li key={itemIdx}>{renderRichText(item)}</li>
              ))}
            </ol>
          );
        }

        if (block.type === "ul") {
          return (
            <ul className="msg-ul" key={idx}>
              {block.items.map((item, itemIdx) => (
                <li key={itemIdx}>{renderRichText(item)}</li>
              ))}
            </ul>
          );
        }

        return (
          <p className="msg-p" key={idx}>
            {renderRichText(block.text)}
          </p>
        );
}

type Section = { heading: Extract<Block, { type: "heading" }> | null; body: Block[] };

function groupSections(blocks: Block[]): Section[] {
  const sections: Section[] = [];
  let current: Section = { heading: null, body: [] };

  for (const block of blocks) {
    if (block.type === "heading" && block.level <= 2) {
      if (current.heading || current.body.length > 0) sections.push(current);
      current = { heading: block, body: [] };
      continue;
    }
    current.body.push(block);
  }
  if (current.heading || current.body.length > 0) sections.push(current);
  return sections;
}

export default function MessageContent({ content }: { content: string }) {
  const sections = groupSections(parseBlocks(content));

  return (
    <div className="msg-content">
      {sections.map((section, sectionIdx) => (
        <section className="msg-section" key={sectionIdx}>
          {section.heading ? renderBlock(section.heading, 0) : null}
          {section.body.map((block, idx) => renderBlock(block, idx + 1))}
        </section>
      ))}
    </div>
  );
}
