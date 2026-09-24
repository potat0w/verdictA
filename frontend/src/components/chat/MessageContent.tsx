function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatInline(text: string) {
  return escapeHtml(text).replace(
    /\*\*(.+?)\*\*/g,
    "<strong>$1</strong>"
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
    const trimmed = line.trim();

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

    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (heading) {
      blocks.push({
        type: "heading",
        level: heading[1].length as 1 | 2 | 3,
        text: heading[2],
      });
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

export default function MessageContent({ content }: { content: string }) {
  const blocks = parseBlocks(content);

  return (
    <div className="msg-content">
      {blocks.map((block, idx) => {
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
      })}
    </div>
  );
}
