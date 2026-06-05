'use client';

import React, { useMemo } from 'react';
import type { Position, PriceMap } from '@/types';

interface PortfolioHeatmapProps {
  positions: Position[];
  prices: PriceMap;
}

interface TreemapInputNode {
  ticker: string;
  value: number;
  pnlPct: number;
  pnl: number;
}

interface TreemapNode extends TreemapInputNode {
  width: number;
  height: number;
  x: number;
  y: number;
}

function getPnlColor(pct: number): string {
  if (pct > 5) return '#1a6b2e';
  if (pct > 2) return '#28a745';
  if (pct > 0) return '#3fb950';
  if (pct > -2) return '#f85149';
  if (pct > -5) return '#c0392b';
  return '#8b0000';
}

// Simple recursive binary split treemap
function computeTreemap(nodes: TreemapInputNode[], width: number, height: number): TreemapNode[] {
  if (nodes.length === 0) return [];

  const total = nodes.reduce((s, n) => s + n.value, 0);
  if (total === 0) return [];

  const sorted = [...nodes].sort((a, b) => b.value - a.value);
  const result: TreemapNode[] = [];

  function layout(items: TreemapInputNode[], x: number, y: number, w: number, h: number) {
    if (items.length === 0) return;
    if (items.length === 1) {
      result.push({ ...items[0], x, y, width: w, height: h });
      return;
    }

    const itemTotal = items.reduce((s, n) => s + n.value, 0);
    let halfValue = 0;
    let splitIdx = 0;
    for (let i = 0; i < items.length; i++) {
      halfValue += items[i].value;
      if (halfValue >= itemTotal / 2) {
        splitIdx = i + 1;
        break;
      }
    }
    if (splitIdx === 0) splitIdx = 1;

    const firstHalf = items.slice(0, splitIdx);
    const secondHalf = items.slice(splitIdx);
    const firstRatio = halfValue / itemTotal;

    if (w >= h) {
      const splitX = x + w * firstRatio;
      layout(firstHalf, x, y, w * firstRatio, h);
      layout(secondHalf, splitX, y, w * (1 - firstRatio), h);
    } else {
      const splitY = y + h * firstRatio;
      layout(firstHalf, x, y, w, h * firstRatio);
      layout(secondHalf, x, splitY, w, h * (1 - firstRatio));
    }
  }

  layout(sorted, 0, 0, width, height);
  return result;
}

export function PortfolioHeatmap({ positions, prices }: PortfolioHeatmapProps) {
  const nodes = useMemo<TreemapInputNode[]>(() => {
    return positions
      .map(pos => {
        const livePrice = prices[pos.ticker]?.price ?? pos.current_price ?? pos.avg_cost;
        const marketValue = pos.quantity * livePrice;
        const pnlPct = pos.avg_cost > 0 ? ((livePrice - pos.avg_cost) / pos.avg_cost) * 100 : 0;
        const pnl = (livePrice - pos.avg_cost) * pos.quantity;
        return {
          ticker: pos.ticker,
          value: Math.abs(marketValue),
          pnlPct,
          pnl,
        };
      })
      .filter(n => n.value > 0);
  }, [positions, prices]);

  const tiles = useMemo<TreemapNode[]>(() => computeTreemap(nodes, 100, 100), [nodes]);

  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full" style={{ backgroundColor: '#161b22' }}>
        <div className="text-center">
          <div className="text-2xl mb-1" style={{ color: '#2d333b' }}>▦</div>
          <p className="text-xs" style={{ color: '#8b949e' }}>No positions yet</p>
          <p className="text-xs" style={{ color: '#8b949e' }}>Buy shares to see the heatmap</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full" style={{ backgroundColor: '#161b22' }}>
      {tiles.map((tile) => (
        <div
          key={tile.ticker}
          className="heatmap-tile"
          style={{
            left: `${tile.x}%`,
            top: `${tile.y}%`,
            width: `${tile.width}%`,
            height: `${tile.height}%`,
            backgroundColor: getPnlColor(tile.pnlPct),
          }}
          title={`${tile.ticker}: ${tile.pnlPct >= 0 ? '+' : ''}${tile.pnlPct.toFixed(2)}%`}
        >
          <span
            className="font-bold text-white"
            style={{
              fontSize: Math.min(tile.width * 0.3, 14) + 'px',
              textShadow: '0 1px 2px rgba(0,0,0,0.8)',
            }}
          >
            {tile.ticker}
          </span>
          <span
            className="text-white font-mono"
            style={{
              fontSize: Math.min(tile.width * 0.22, 11) + 'px',
              textShadow: '0 1px 2px rgba(0,0,0,0.8)',
            }}
          >
            {tile.pnlPct >= 0 ? '+' : ''}{tile.pnlPct.toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}
