'use client';

import React from 'react';
import type { Position, PriceMap } from '@/types';

interface PositionsTableProps {
  positions: Position[];
  prices: PriceMap;
  onSelectTicker?: (ticker: string) => void;
}

export function PositionsTable({ positions, prices, onSelectTicker }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: '#8b949e' }}>
        <span className="text-xs">No positions — buy some shares to get started</span>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto h-full">
      <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #2d333b', backgroundColor: '#0d1117' }}>
            {['TICKER', 'QTY', 'AVG COST', 'PRICE', 'MKT VALUE', 'P&L', 'P&L %'].map(col => (
              <th
                key={col}
                className="px-3 py-2 text-left font-bold tracking-wider"
                style={{ color: '#8b949e', whiteSpace: 'nowrap' }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const livePrice = prices[pos.ticker]?.price ?? pos.current_price ?? pos.avg_cost;
            const marketValue = pos.quantity * livePrice;
            const pnl = (livePrice - pos.avg_cost) * pos.quantity;
            const pnlPct = pos.avg_cost > 0 ? ((livePrice - pos.avg_cost) / pos.avg_cost) * 100 : 0;
            const isPositive = pnl >= 0;

            return (
              <tr
                key={pos.ticker}
                className="border-b cursor-pointer hover:bg-opacity-50"
                style={{ borderColor: '#1a1a2e' }}
                onClick={() => onSelectTicker?.(pos.ticker)}
              >
                <td className="px-3 py-2 font-bold" style={{ color: '#209dd7' }}>
                  {pos.ticker}
                </td>
                <td className="px-3 py-2 font-mono" style={{ color: '#e6edf3' }}>
                  {pos.quantity % 1 === 0 ? pos.quantity : pos.quantity.toFixed(4)}
                </td>
                <td className="px-3 py-2 font-mono" style={{ color: '#8b949e' }}>
                  ${pos.avg_cost.toFixed(2)}
                </td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: '#e6edf3' }}>
                  ${livePrice.toFixed(2)}
                </td>
                <td className="px-3 py-2 font-mono" style={{ color: '#e6edf3' }}>
                  ${marketValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: isPositive ? '#3fb950' : '#f85149' }}>
                  {isPositive ? '+' : ''}${pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: isPositive ? '#3fb950' : '#f85149' }}>
                  {isPositive ? '+' : ''}{pnlPct.toFixed(2)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
