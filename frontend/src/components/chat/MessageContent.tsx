function formatLine(line: string) {
  return line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

export default function MessageContent({ content }: { content: string }) {
  const blocks = content.split(/\n\n+/);

  return (
    <div className="space-y-3">
      {blocks.map((block, blockIdx) => {
        const lines = block.split("\n").filter((l) => l.trim());
        const isList = lines.every((l) => /^\d+\.\s/.test(l.trim()));

        if (isList) {
          return (
            <ol key={blockIdx} className="ml-1 space-y-2">
              {lines.map((line, i) => {
                const text = line.replace(/^\d+\.\s*/, "");
                return (
                  <li
                    key={i}
                    className="flex gap-3 text-[15px] leading-relaxed text-[var(--chat-text)]"
                  >
                    <span
                      className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
                      style={{
                        background:
                          "color-mix(in srgb, var(--accent) 15%, transparent)",
                        color: "var(--accent)",
                      }}
                    >
                      {i + 1}
                    </span>
                    <span
                      dangerouslySetInnerHTML={{ __html: formatLine(text) }}
                    />
                  </li>
                );
              })}
            </ol>
          );
        }

        return (
          <div key={blockIdx} className="space-y-2">
            {lines.map((line, i) => (
              <p
                key={i}
                className="text-[15px] leading-relaxed text-[var(--chat-text)]"
                dangerouslySetInnerHTML={{ __html: formatLine(line) }}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
