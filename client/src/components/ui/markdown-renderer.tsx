/**
 * MarkdownRenderer Component
 *
 * Reusable markdown renderer with syntax highlighting and custom styling.
 * Uses react-markdown with remark-gfm for GitHub Flavored Markdown support.
 */

import { cn } from "@/lib/utils";
import { getEntityRoute, type EntityType } from "@/lib/entity-icons";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useNavigate } from "react-router-dom";

/**
 * Map plural route names from entity:// URLs to EntityType.
 * e.g., "documents" -> "document", "passwords" -> "password"
 */
const pluralToEntityType: Record<string, EntityType> = {
	documents: "document",
	passwords: "password",
	configurations: "configuration",
	locations: "location",
	"custom-assets": "custom_asset",
};

/**
 * Parse an entity:// URL and return the entity type, org ID, and entity ID.
 * Format: entity://type/orgId/entityId (e.g., entity://documents/org-456/abc-123)
 *
 * @param href The href to parse
 * @returns Parsed entity info or null if not an entity URL
 */
function parseEntityUrl(
	href: string
): { entityType: EntityType; orgId: string; entityId: string } | null {
	if (!href.startsWith("entity://")) {
		return null;
	}

	const path = href.replace("entity://", "");
	const [pluralType, orgId, entityId] = path.split("/");

	if (!pluralType || !orgId || !entityId) {
		return null;
	}

	const entityType = pluralToEntityType[pluralType];
	if (!entityType) {
		return null;
	}

	return { entityType, orgId, entityId };
}

/**
 * Custom URL transform that allows entity:// protocol.
 * react-markdown strips unknown protocols by default for XSS protection.
 */
function customUrlTransform(url: string): string {
	if (url.startsWith("entity://")) {
		return url;
	}
	return defaultUrlTransform(url);
}

interface MarkdownRendererProps {
	content: string;
	className?: string;
}

export function MarkdownRenderer({
	content,
	className,
}: MarkdownRendererProps) {
	const navigate = useNavigate();

	return (
		<div
			className={cn(
				"prose prose-slate dark:prose-invert max-w-none",
				// Compact spacing for dialog/card contexts
				"prose-p:my-2 prose-p:leading-7",
				"prose-headings:font-semibold prose-h1:text-xl prose-h2:text-lg prose-h3:text-base",
				"prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5",
				"prose-pre:my-2 prose-pre:p-0 prose-pre:bg-transparent",
				className,
			)}
		>
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				rehypePlugins={[rehypeRaw]}
				urlTransform={customUrlTransform}
				components={{
					// Code blocks and inline code
					code({ className, children }) {
						const match = /language-(\w+)/.exec(className || "");
						const codeContent = String(children).replace(/\n$/, "");

						// Determine if this is a code block (has newlines or language class)
						const isCodeBlock =
							codeContent.includes("\n") || className;

						if (isCodeBlock) {
							return (
								<SyntaxHighlighter
									style={oneDark}
									language={match?.[1] || "text"}
									PreTag="div"
									className="rounded-md !my-2"
								>
									{codeContent}
								</SyntaxHighlighter>
							);
						}

						// Inline code
						return (
							<code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">
								{children}
							</code>
						);
					},

					// Paragraphs
					p: ({ children }) => (
						<p className="my-2 leading-7">{children}</p>
					),

					// Headings
					h1: ({ children }) => (
						<h1 className="text-xl font-semibold mt-4 mb-2">
							{children}
						</h1>
					),
					h2: ({ children }) => (
						<h2 className="text-lg font-semibold mt-3 mb-2">
							{children}
						</h2>
					),
					h3: ({ children }) => (
						<h3 className="text-base font-semibold mt-3 mb-1">
							{children}
						</h3>
					),
					h4: ({ children }) => (
						<h4 className="text-sm font-semibold mt-2 mb-1">
							{children}
						</h4>
					),

					// Lists
					ul: ({ children }) => (
						<ul className="my-2 ml-4 list-disc space-y-1">
							{children}
						</ul>
					),
					ol: ({ children }) => (
						<ol className="my-2 ml-4 list-decimal space-y-1">
							{children}
						</ol>
					),
					li: ({ children }) => (
						<li className="leading-6">{children}</li>
					),

					// Links - handle entity:// URLs with React Router, external links in new tab
					a: ({ href, children }) => {
						if (!href) {
							return (
								<span className="text-primary">{children}</span>
							);
						}

						// Check if this is an entity:// URL
						const entityInfo = parseEntityUrl(href);
						if (entityInfo) {
							const routePath = getEntityRoute(
								entityInfo.entityType
							);
							const to = `/org/${entityInfo.orgId}/${routePath}/${entityInfo.entityId}`;

							return (
								<button
									type="button"
									onClick={() => navigate(to)}
									className="text-primary hover:underline cursor-pointer bg-transparent border-none p-0 font-inherit text-inherit"
								>
									{children}
								</button>
							);
						}

						// Regular external link - open in new tab
						return (
							<a
								href={href}
								target="_blank"
								rel="noopener noreferrer"
								className="text-primary hover:underline"
							>
								{children}
							</a>
						);
					},

					// Blockquotes
					blockquote: ({ children }) => (
						<blockquote className="border-l-2 border-muted-foreground/30 pl-4 my-2 italic text-muted-foreground">
							{children}
						</blockquote>
					),

					// Tables
					table: ({ children }) => (
						<div className="my-2 overflow-x-auto">
							<table className="min-w-full border-collapse border border-border">
								{children}
							</table>
						</div>
					),
					th: ({ children }) => (
						<th className="border border-border px-3 py-2 bg-muted font-semibold text-left">
							{children}
						</th>
					),
					td: ({ children }) => (
						<td className="border border-border px-3 py-2">
							{children}
						</td>
					),

					// Horizontal rule
					hr: () => <hr className="my-4 border-border" />,
				}}
			>
				{content}
			</ReactMarkdown>
		</div>
	);
}
