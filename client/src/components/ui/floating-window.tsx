import { useState, useRef, useCallback, useEffect, useId } from "react";
import { X, GripVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FloatingWindowProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
  children: React.ReactNode;
  defaultPosition?: { x: number; y: number };
  defaultSize?: { width: number; height: number };
  minSize?: { width: number; height: number };
  className?: string;
  headerExtra?: React.ReactNode;
}

interface Position {
  x: number;
  y: number;
}

interface Size {
  width: number;
  height: number;
}

// Get initial position, handling SSR
function getInitialPosition(defaultPosition?: Position): Position {
  if (typeof window === "undefined") {
    return defaultPosition ?? { x: 100, y: 100 };
  }
  return defaultPosition ?? {
    x: Math.max(0, window.innerWidth - 450),
    y: Math.max(0, window.innerHeight - 650),
  };
}

export function FloatingWindow({
  open,
  onOpenChange,
  title,
  children,
  defaultPosition,
  defaultSize = { width: 420, height: 550 },
  minSize = { width: 320, height: 400 },
  className,
  headerExtra,
}: FloatingWindowProps) {
  const titleId = useId();
  // Use lazy initializer to get position - will be called on first render only
  const [position, setPosition] = useState<Position>(() =>
    getInitialPosition(defaultPosition)
  );
  const [size, setSize] = useState<Size>(defaultSize);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const windowRef = useRef<HTMLDivElement>(null);
  const dragOffset = useRef<Position>({ x: 0, y: 0 });

  // Constrain position to viewport
  const constrainPosition = useCallback(
    (pos: Position, currentSize: Size): Position => {
      if (typeof window === "undefined") return pos;
      const maxX = window.innerWidth - currentSize.width;
      const maxY = window.innerHeight - currentSize.height;
      return {
        x: Math.max(0, Math.min(pos.x, maxX)),
        y: Math.max(0, Math.min(pos.y, maxY)),
      };
    },
    []
  );

  // Handle drag start
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest("button")) return;
    setIsDragging(true);
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  }, [position]);

  // Handle drag
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newPos = {
        x: e.clientX - dragOffset.current.x,
        y: e.clientY - dragOffset.current.y,
      };
      setPosition(constrainPosition(newPos, size));
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, size, constrainPosition]);

  // Handle resize
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const currentPosition = position;
    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = Math.max(minSize.width, e.clientX - currentPosition.x);
      const newHeight = Math.max(minSize.height, e.clientY - currentPosition.y);
      setSize({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, position, minSize]);

  // Handle escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div
      ref={windowRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className={cn(
        "fixed z-50 flex flex-col bg-card border rounded-lg shadow-2xl",
        isDragging && "cursor-grabbing select-none",
        className
      )}
      style={{
        left: position.x,
        top: position.y,
        width: size.width,
        height: size.height,
      }}
    >
      {/* Header - draggable */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b bg-muted/50 rounded-t-lg cursor-grab shrink-0"
        onMouseDown={handleDragStart}
      >
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground" />
          <span id={titleId} className="font-medium text-sm">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {headerExtra}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onOpenChange(false)}
            className="h-7 w-7"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">{children}</div>

      {/* Resize handle */}
      <div
        className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
        onMouseDown={handleResizeStart}
      >
        <svg
          className="w-4 h-4 text-muted-foreground/50"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M14 14H12V12H14V14ZM14 10H12V8H14V10ZM10 14H8V12H10V14Z" />
        </svg>
      </div>
    </div>
  );
}
