// Virtualized table — TanStack Virtual + a11y-correct semantics.
// Adapt to your data shape; do not copy verbatim.

import React, { useRef, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

type Column<T> = { key: keyof T; header: string };

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  rowHeight?: number;
  emptyMessage?: string;
}

export function DataTable<T extends { id: string | number }>({
  data,
  columns,
  onRowClick,
  rowHeight = 48,
  emptyMessage = 'No rows to display',
}: DataTableProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 5,
  });

  const onActivate = useCallback(
    (row: T) => (e: React.KeyboardEvent | React.MouseEvent) => {
      if ('key' in e && e.key !== 'Enter' && e.key !== ' ') return;
      e.preventDefault();
      onRowClick?.(row);
    },
    [onRowClick],
  );

  if (data.length === 0) {
    return (
      <div role="status" className="p-4 text-center text-gray-500">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      role="table"
      aria-rowcount={data.length}
      aria-colcount={columns.length}
      className="h-96 overflow-auto"
    >
      <div role="row" className="flex sticky top-0 bg-white border-b font-medium">
        {columns.map((c) => (
          <div key={String(c.key)} role="columnheader" className="px-4 py-2 flex-1">
            {c.header}
          </div>
        ))}
      </div>

      <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {virtualizer.getVirtualItems().map((vi) => {
          const row = data[vi.index];
          return (
            <div
              key={row.id}
              role="row"
              aria-rowindex={vi.index + 1}
              tabIndex={0}
              onClick={onActivate(row)}
              onKeyDown={onActivate(row)}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: vi.size,
                transform: `translateY(${vi.start}px)`,
              }}
              className="flex items-center border-b hover:bg-gray-50 focus:outline focus:outline-2"
            >
              {columns.map((c) => (
                <div key={String(c.key)} role="cell" className="px-4 py-2 flex-1">
                  {String(row[c.key])}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
