import { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { Markdown } from "@tiptap/markdown";
import { TiptapToolbarAssetField } from "./TiptapToolbarAssetField";
import { cn } from "@/lib/utils";

interface TiptapEditorAssetFieldProps {
  content: string;
  onChange?: (content: string) => void;
  readOnly?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Simplified Tiptap editor for custom asset textbox fields.
 * Does not include image upload functionality (that's document-specific).
 */
export function TiptapEditorAssetField({
  content,
  onChange,
  readOnly = false,
  placeholder = "Start writing...",
  className,
}: TiptapEditorAssetFieldProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [2, 3], // No h1 in asset fields
        },
      }),
      Markdown,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: "text-primary underline",
        },
      }),
      Placeholder.configure({
        placeholder,
        emptyEditorClass:
          "before:content-[attr(data-placeholder)] before:text-muted-foreground before:float-left before:h-0 before:pointer-events-none",
      }),
    ],
    content,
    contentType: "markdown",
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getMarkdown());
    },
    editorProps: {
      attributes: {
        class: "tiptap-editor min-h-[120px] max-h-[400px] overflow-y-auto p-3 focus:outline-none prose prose-sm dark:prose-invert max-w-none",
      },
    },
  });

  // Sync editable state when readOnly changes
  useEffect(() => {
    if (editor) {
      editor.setEditable(!readOnly);
    }
  }, [editor, readOnly]);

  // Sync content when it changes externally
  useEffect(() => {
    if (editor && content !== editor.getMarkdown()) {
      editor.commands.setContent(content, { contentType: "markdown" });
    }
  }, [content, editor]);

  if (!editor) {
    return (
      <div className="border rounded-md min-h-[120px] animate-pulse bg-muted/50" />
    );
  }

  return (
    <div className={cn("border rounded-md overflow-hidden", className)}>
      {!readOnly && <TiptapToolbarAssetField editor={editor} />}
      <EditorContent editor={editor} />
    </div>
  );
}
