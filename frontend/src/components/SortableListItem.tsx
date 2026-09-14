import type { CSSProperties, ReactNode } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

export interface SortableSlotArgs {
  innerRef: (node: HTMLLIElement | null) => void;
  style: CSSProperties;
  dragHandleProps?: Record<string, unknown>;
}

// Render-prop wrapper around dnd-kit's useSortable() so callers (TaskCard
// and friends) stay decoupled from dnd-kit's own types.
export function SortableListItem({
  id,
  disabled,
  children,
}: {
  id: string;
  disabled?: boolean;
  children: (args: SortableSlotArgs) => ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled,
  });
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 1 : undefined,
  };
  return (
    <>
      {children({
        innerRef: setNodeRef,
        style,
        dragHandleProps: disabled ? undefined : { ...attributes, ...listeners },
      })}
    </>
  );
}
