'use client';

import React from 'react';
import type { ConnectionStatus, Portfolio } from '@/types';

interface HeaderProps {
  portfolio: Portfolio | null;
  connectionStatus: ConnectionStatus;
}

export function Header({ portfolio, connectionStatus }: HeaderProps) {
  const statusColors: Record<ConnectionStatus, string> = {
    connected: '#3fb950',
    reconnecting: '#ecad0a',
    disconnected: '#f85149',
  };

  const statusLabels: Record<ConnectionStatus, string> = {
    connected: 'LIVE',
    reconnecting: 'SYNC',
    disconnected: 'DISC',
  };

  const totalValue = portfolio?.total_value ?? 0;
  const cashBalance = portfolio?.cash_balance ?? 0;
  const pnl = portfolio?.unrealized_pnl ?? 0;

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: '#2d333b', backgroundColor: '#0d1117', height: '48px' }}>
      {/* Logo */}
      <div className="flex items-center gap-3">
        <span className="text-xl font-bold tracking-wider" style={{ color: '#ecad0a', fontFamily: 'monospace' }}>
          FIN<span style={{ color: '#209dd7' }}>ALLY</span>
        </span>
        <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#1a1a2e', color: '#8b949e', border: '1px solid #2d333b' }}>
          AI TRADING WORKSTATION
        </span>
      </div>

      {/* Portfolio Stats */}
      <div className="flex items-center gap-6">
        <div className="flex flex-col items-end">
          <span className="text-xs" style={{ color: '#8b949e' }}>PORTFOLIO</span>
          <span className="text-base font-bold" style={{ color: '#e6edf3' }}>
            ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>

        <div className="w-px h-8" style={{ backgroundColor: '#2d333b' }} />

        <div className="flex flex-col items-end">
          <span className="text-xs" style={{ color: '#8b949e' }}>CASH</span>
          <span className="text-base font-bold" style={{ color: '#e6edf3' }}>
            ${cashBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>

        <div className="w-px h-8" style={{ backgroundColor: '#2d333b' }} />

        <div className="flex flex-col items-end">
          <span className="text-xs" style={{ color: '#8b949e' }}>UNREALIZED P&L</span>
          <span className="text-base font-bold" style={{ color: pnl >= 0 ? '#3fb950' : '#f85149' }}>
            {pnl >= 0 ? '+' : ''}${pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>

        <div className="w-px h-8" style={{ backgroundColor: '#2d333b' }} />

        {/* Connection Status */}
        <div className="flex items-center gap-2">
          <div
            className="rounded-full"
            style={{
              width: '8px',
              height: '8px',
              backgroundColor: statusColors[connectionStatus],
              boxShadow: `0 0 6px ${statusColors[connectionStatus]}`,
              animation: connectionStatus === 'connected' ? 'none' : 'pulseDot 1.5s infinite',
            }}
          />
          <span className="text-xs font-mono" style={{ color: statusColors[connectionStatus] }}>
            {statusLabels[connectionStatus]}
          </span>
        </div>
      </div>
    </header>
  );
}
