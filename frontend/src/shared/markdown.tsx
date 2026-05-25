import type { ReactNode } from "react";

export function renderAssistantMarkdown(text: string): ReactNode[] {
  const blocks = text
    .split(/\n{2,}/)
    .map((block) => block.replace(/\s+$/g, ""))
    .filter(Boolean);

  return blocks.map((block, index) => {
    const lines = block.split("\n").filter((line) => line.trim());
    if (lines.every((line) => parseBulletLine(line) !== null)) {
      return (
        <ul key={index} className="assistant-list">
          {lines.map((line, lineIndex) => {
            const bullet = parseBulletLine(line);
            return (
              <li
                key={lineIndex}
                className={bullet?.level === 0 ? "primary" : "secondary"}
              >
                {renderInline(bullet?.text ?? line.trim())}
              </li>
            );
          })}
        </ul>
      );
    }

    return <p key={index}>{renderInline(block)}</p>;
  });
}

function parseBulletLine(line: string): { level: number; text: string } | null {
  const match = line.match(/^(\s*)\*\s+(.*)$/);
  if (!match) {
    return null;
  }
  return {
    level: match[1].length > 0 ? 1 : 0,
    text: match[2].trim()
  };
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const regex = /\*\*(.*?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    nodes.push(<strong key={`${match.index}-${match[1]}`}>{match[1]}</strong>);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}
