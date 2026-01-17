interface HighlightedTextProps {
  text: string;
  highlight?: string;
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function HighlightedText({ text, highlight }: HighlightedTextProps) {
  if (!highlight || highlight.length < 2) {
    return <>{text}</>;
  }

  const parts = text.split(new RegExp(`(${escapeRegExp(highlight)})`, "gi"));

  return (
    <>
      {parts.map((part, index) => {
        const isMatch = part.toLowerCase() === highlight.toLowerCase();
        return isMatch ? (
          <mark
            key={index}
            className="bg-yellow-200 dark:bg-yellow-900 rounded-sm px-0.5"
          >
            {part}
          </mark>
        ) : (
          <span key={index}>{part}</span>
        );
      })}
    </>
  );
}
