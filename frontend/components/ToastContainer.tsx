'use client';

import React from 'react';
import type { Toast } from '@/types';

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  const colors: Record<Toast['type'], { bg: string; border: string; icon: string }> = {
    success: { bg: 'rgba(63, 185, 80, 0.15)', border: '#3fb950', icon: '✓' },
    error: { bg: 'rgba(248, 81, 73, 0.15)', border: '#f85149', icon: '✕' },
    info: { bg: 'rgba(32, 157, 215, 0.15)', border: '#209dd7', icon: 'ℹ' },
  };

  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
      {toasts.map(toast => {
        const { bg, border, icon } = colors[toast.type];
        return (
          <div
            key={toast.id}
            className="toast-enter flex items-center gap-2 px-3 py-2 rounded text-xs max-w-xs cursor-pointer"
            style={{
              backgroundColor: bg,
              border: `1px solid ${border}`,
              color: '#e6edf3',
              backdropFilter: 'blur(4px)',
            }}
            onClick={() => onRemove(toast.id)}
          >
            <span style={{ color: border, fontWeight: 'bold' }}>{icon}</span>
            <span>{toast.message}</span>
          </div>
        );
      })}
    </div>
  );
}
