import { useEffect, useCallback } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { Markdown } from "@tiptap/markdown";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import api from "@/lib/api-client";
import { TiptapToolbar } from "./TiptapToolbar";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface TiptapEditorProps {
  content: string;
  onChange?: (content: string) => void;
  readOnly?: boolean;
  orgId: string;
  placeholder?: string;
  className?: string;
}

export function TiptapEditor({
  content,
  onChange,
  readOnly = false,
  orgId,
  placeholder = "Start writing...",
  className,
}: TiptapEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Markdown,
      Image.configure({
        inline: false,
        allowBase64: false,
        HTMLAttributes: {
          class: "rounded-md max-w-full",
        },
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: "text-primary underline",
        },
      }),
      Table.configure({
        resizable: true,
        HTMLAttributes: {
          class: "tiptap-table",
        },
      }),
      TableRow,
      TableHeader,
      TableCell,
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
      // Get markdown directly from editor
      onChange?.(editor.getMarkdown());
    },
    editorProps: {
      attributes: {
        class: "tiptap-editor min-h-[200px] p-4 focus:outline-none",
      },
    },
  });

  // Handle image upload to S3 via presigned URL
  const handleImageUpload = useCallback(
    async (file: File) => {
      if (!editor || !orgId) return;

      // Validate file type
      if (!file.type.startsWith("image/")) {
        toast.error("Only image files are allowed");
        return;
      }

      // Validate file size (max 5MB)
      const maxSize = 5 * 1024 * 1024;
      if (file.size > maxSize) {
        toast.error("Image must be less than 5MB");
        return;
      }

      try {
        // Create document image record and get presigned URL
        const createResponse = await api.post<{
          id: string;
          upload_url: string;
          image_url: string;
        }>(`/api/organizations/${orgId}/documents/images`, {
          filename: file.name,
          content_type: file.type,
          size_bytes: file.size,
        });

        // Upload file to presigned URL
        await fetch(createResponse.data.upload_url, {
          method: "PUT",
          body: file,
          headers: {
            "Content-Type": file.type,
          },
        });

        // Insert image into editor using the image_url from the response
        editor.chain().focus().setImage({ src: createResponse.data.image_url }).run();
        toast.success("Image uploaded successfully");
      } catch (error) {
        console.error("Image upload failed:", error);
        toast.error("Failed to upload image");
      }
    },
    [editor, orgId]
  );

  // Handle paste events for image pasting
  useEffect(() => {
    if (!editor || readOnly) return;

    const handlePaste = (event: ClipboardEvent) => {
      const items = event.clipboardData?.items;
      if (!items) return;

      for (const item of items) {
        if (item.type.startsWith("image/")) {
          event.preventDefault();
          const file = item.getAsFile();
          if (file) handleImageUpload(file);
          return;
        }
      }
    };

    const dom = editor.view.dom;
    dom.addEventListener("paste", handlePaste);
    return () => dom.removeEventListener("paste", handlePaste);
  }, [editor, readOnly, handleImageUpload]);

  // Handle drop events for image dropping
  useEffect(() => {
    if (!editor || readOnly) return;

    const handleDrop = (event: DragEvent) => {
      const files = event.dataTransfer?.files;
      if (!files || files.length === 0) return;

      const file = files[0];
      if (file.type.startsWith("image/")) {
        event.preventDefault();
        handleImageUpload(file);
      }
    };

    const dom = editor.view.dom;
    dom.addEventListener("drop", handleDrop);
    return () => dom.removeEventListener("drop", handleDrop);
  }, [editor, readOnly, handleImageUpload]);

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
      <div className={cn(
        "min-h-[200px] animate-pulse bg-muted/50",
        !className?.includes("border-none") && "border rounded-md",
        className
      )} />
    );
  }

  return (
    <div className={cn(
      "overflow-hidden",
      !className?.includes("border-none") && "border rounded-md",
      className
    )}>
      {!readOnly && (
        <TiptapToolbar editor={editor} onImageUpload={handleImageUpload} />
      )}
      <EditorContent editor={editor} />
    </div>
  );
}
