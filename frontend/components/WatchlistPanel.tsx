'use client';

import React, { useState } from 'react';
import type { WatchlistTicker, PriceMap, SparklineData } from '@/types';
import { Sparkline } from './Sparkline';

interface WatchlistPanelProps {
  watchlist: WatchlistTicker[];
  prices: PriceMap;
  sparklines: SparklineData;
  flashStates: Record<string, 'up' | 'down' | null>;
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
  onAddTicker: (ticker: string) => void;
  onRemoveTicker: (ticker: string) => void;
}

export function WatchlistPanel({
  watchlist,
  prices,
  sparklines,
  flashStates,
  selectedTicker,
  onSelectTicker,
  onAddTicker,
  onRemoveTicker,
}: WatchlistPanelProps) {
  const [addInput, setAddInput] = useState('');
  const [hoveredTicker, setHoveredTicker] = useState<string | null>(null);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = addInput.trim().toUpperCase();
    if (ticker) {
      onAddTicker(ticker);
      setAddInput('');
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#0d1117' }}>
      {/* Header */}
      <div className="px-3 py-2 border-b" style={{ borderColor: '#2d333b' }}>
        <span className="text-xs font-bold tracking-widest" style={{ color: '#8b949e' }}>WATCHLIST</span>
      </div>

      {/* Tickers */}
      <div className="flex-1 overflow-y-auto">
        {watchlist.map((item) => {
          const liveData = prices[item.ticker];
          const price = liveData?.price ?? item.price ?? null;
          const changePct = liveData?.change_percent ?? item.change_percent ?? null;
          const direction = liveData?.direction ?? item.direction ?? 'flat';
          const flash = flashStates[item.ticker];
          const sparkData = sparklines[item.ticker] || [];
          const isSelected = selectedTicker === item.ticker;
          const isHovered = hoveredTicker === item.ticker;

          return (
            <div
              key={item.ticker}
              onClick={() => onSelectTicker(item.ticker)}
              onMouseEnter={() => setHoveredTicker(item.ticker)}
              onMouseLeave={() => setHoveredTicker(null)}
              className={`relative px-3 py-2 cursor-pointer border-b transition-colors ${flash === 'up' ? 'flash-up' : flash === 'down' ? 'flash-down' : ''}`}
              style={{
                borderColor: '#1a1a2e',
                backgroundColor: isSelected
                  ? 'rgba(32, 157, 215, 0.15)'
                  : isHovered
                  ? 'rgba(255,255,255,0.04)'
                  : 'transparent',
              }}
            >
              {isSelected && (
                <div
                  className="absolute left-0 top-0 bottom-0 w-0.5"
                  style={{ backgroundColor: '#209dd7' }}
                />
              )}
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-bold text-xs" style={{ color: '#e6edf3' }}>
                      {item.ticker}
                    </span>
                    <span
                      className="text-xs font-mono font-bold"
                      style={{ color: direction === 'down' ? '#f85149' : '#3fb950' }}
                    >
                      {price != null ? `$${price.toFixed(2)}` : '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span
                      className="text-xs"
                      style={{ color: direction === 'down' ? '#f85149' : '#3fb950' }}
                    >
                      {direction === 'down' ? '▼' : '▲'}{' '}
                      {changePct != null ? `${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%` : '—'}
                    </span>
                    {sparkData.length >= 2 && (
                      <Sparkline data={sparkData} width={56} height={20} />
                    )}
                  </div>
                </div>

                {/* Remove button */}
                {isHovered && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveTicker(item.ticker);
                    }}
                    className="ml-1 text-xs rounded px-1"
                    style={{ color: '#8b949e', backgroundColor: 'rgba(248,81,73,0.15)' }}
                    title="Remove from watchlist"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Add ticker form */}
      <div className="p-2 border-t" style={{ borderColor: '#2d333b' }}>
        <form onSubmit={handleAdd} className="flex gap-1">
          <input
            type="text"
            value={addInput}
            onChange={(e) => setAddInput(e.target.value.toUpperCase())}
            placeholder="Add ticker..."
            className="flex-1 text-xs py-1.5 px-2 rounded"
            style={{
              backgroundColor: '#161b22',
              border: '1px solid #2d333b',
              color: '#e6edf3',
            }}
            maxLength={10}
          />
          <button
            type="submit"
            className="text-xs px-2 py-1 rounded font-bold"
            style={{ backgroundColor: '#209dd7', color: '#0d1117' }}
          >
            +
          </button>
        </form>
      </div>
    </div>
  );
}
