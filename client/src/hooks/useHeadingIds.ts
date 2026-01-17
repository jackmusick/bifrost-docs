import { useEffect } from "react";

/**
 * Hook to inject IDs into headings in rendered content.
 * Call this effect in the document detail page after content renders.
 */
export function useHeadingIds(content: string) {
  useEffect(() => {
    if (!content) return;

    // Find all headings in the document content area
    const container = document.querySelector("[data-document-content]");
    if (!container) return;

    container.querySelectorAll("h1, h2, h3").forEach((heading, index) => {
      if (!heading.id) {
        const text = heading.textContent?.trim() || "";
        heading.id = `heading-${index}-${text.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
      }
    });
  }, [content]);
}
