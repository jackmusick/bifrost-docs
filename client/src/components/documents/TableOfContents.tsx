import { useMemo, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface TocHeading {
  id: string;
  text: string;
  level: number;
}

interface TableOfContentsProps {
  content: string;
  className?: string;
}

/**
 * Parses HTML content and extracts h1, h2, h3 headings for table of contents.
 * Creates IDs for headings if they don't exist.
 */
function parseHeadings(html: string): TocHeading[] {
  if (!html) return [];

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const headings: TocHeading[] = [];

  doc.querySelectorAll("h1, h2, h3").forEach((heading, index) => {
    const text = heading.textContent?.trim() || "";
    if (!text) return;

    // Generate ID from text if not present
    const id =
      heading.id ||
      `heading-${index}-${text.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    const level = parseInt(heading.tagName[1], 10);

    headings.push({ id, text, level });
  });

  return headings;
}

export function TableOfContents({ content, className }: TableOfContentsProps) {
  const headings = useMemo(() => parseHeadings(content), [content]);
  const [activeId, setActiveId] = useState<string>("");

  // Track active heading on scroll
  useEffect(() => {
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: "-80px 0px -80% 0px" }
    );

    // Observe all headings
    headings.forEach(({ id }) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, [headings]);

  const handleClick = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
    }
  };

  if (headings.length === 0) {
    return null;
  }

  return (
    <nav className={cn("space-y-1", className)}>
      <h3 className="text-sm font-semibold text-foreground mb-3">
        On this page
      </h3>
      {headings.map((heading) => (
        <button
          key={heading.id}
          onClick={() => handleClick(heading.id)}
          className={cn(
            "block w-full text-left text-sm py-1 transition-colors hover:text-foreground",
            heading.level === 1 && "font-medium",
            heading.level === 2 && "pl-3",
            heading.level === 3 && "pl-6 text-xs",
            activeId === heading.id
              ? "text-primary font-medium"
              : "text-muted-foreground"
          )}
        >
          {heading.text}
        </button>
      ))}
    </nav>
  );
}
