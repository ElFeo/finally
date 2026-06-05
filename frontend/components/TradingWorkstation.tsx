'use client';

import React, { useState, useCallback } from 'react';
import { Header } from '@/components/Header';
import { WatchlistPanel } from '@/components/WatchlistPanel';
import { MainChart } from '@/components/MainChart';
import { PortfolioHeatmap } from '@/components/PortfolioHeatmap';
import { PnLChart } from '@/components/PnLChart';
import { PositionsTable } from '@/components/PositionsTable';
import { TradeBar } from '@/components/TradeBar';
import { ChatPanel } from '@/components/ChatPanel';
import { ToastContainer } from '@/components/ToastContainer';
import { usePriceStream } from '@/hooks/usePriceStream';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useWatchlist } from '@/hooks/useWatchlist';
import { useToast } from '@/hooks/useToast';

export default function TradingWorkstation() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>('AAPL');
  const { prices, connectionStatus, sparklines, flashStates } = usePriceStream();
  const { portfolio, history, refresh: refreshPortfolio } = usePortfolio();
  const { watchlist, addTicker, removeTicker, refresh: refreshWatchlist } = useWatchlist();
  const { toasts, addToast, removeToast } = useToast();

  const handleTradeComplete = useCallback(async () => {
    await refreshPortfolio();
  }, [refreshPortfolio]);

  const handleWatchlistChanged = useCallback(async () => {
    await refreshWatchlist();
  }, [refreshWatchlist]);

  const handleAddTicker = useCallback(async (ticker: string) => {
    const result = await addTicker(ticker);
    if (result.success) {
      addToast(`Added ${ticker} to watchlist`, 'success');
    } else {
      addToast(result.error || 'Failed to add ticker', 'error');
    }
  }, [addTicker, addToast]);

  const handleRemoveTicker = useCallback(async (ticker: string) => {
    const result = await removeTicker(ticker);
    if (result.success) {
      addToast(`Removed ${ticker} from watchlist`, 'info');
      if (selectedTicker === ticker) setSelectedTicker(null);
    } else {
      addToast(result.error || 'Failed to remove ticker', 'error');
    }
  }, [removeTicker, addToast, selectedTicker]);

  return (
    <div
      className="flex flex-col"
      style={{
        height: '100vh',
        backgroundColor: '#0d1117',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Header portfolio={portfolio} connectionStatus={connectionStatus} />

      {/* Main Content Area */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Watchlist */}
        <div
          className="flex-shrink-0 border-r overflow-hidden"
          style={{ width: '200px', borderColor: '#2d333b' }}
        >
          <WatchlistPanel
            watchlist={watchlist}
            prices={prices}
            sparklines={sparklines}
            flashStates={flashStates}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
            onAddTicker={handleAddTicker}
            onRemoveTicker={handleRemoveTicker}
          />
        </div>

        {/* Center: Charts + Heatmap */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {/* Top: Main Chart + Portfolio Heatmap */}
          <div className="flex border-b" style={{ height: '55%', borderColor: '#2d333b' }}>
            {/* Main Chart */}
            <div className="flex-1 border-r" style={{ borderColor: '#2d333b' }}>
              <MainChart
                ticker={selectedTicker}
                prices={prices}
                sparklines={sparklines}
              />
            </div>

            {/* Portfolio Heatmap */}
            <div className="flex-shrink-0" style={{ width: '280px' }}>
              <div className="px-3 py-2 border-b" style={{ borderColor: '#2d333b', backgroundColor: '#161b22' }}>
                <span className="text-xs font-bold tracking-widest" style={{ color: '#8b949e' }}>PORTFOLIO HEATMAP</span>
              </div>
              <div style={{ height: 'calc(100% - 33px)' }}>
                <PortfolioHeatmap
                  positions={portfolio?.positions ?? []}
                  prices={prices}
                />
              </div>
            </div>
          </div>

          {/* Bottom: P&L Chart */}
          <div style={{ height: '45%' }}>
            <div className="px-3 py-2 border-b" style={{ borderColor: '#2d333b' }}>
              <span className="text-xs font-bold tracking-widest" style={{ color: '#8b949e' }}>PORTFOLIO VALUE HISTORY</span>
            </div>
            <div style={{ height: 'calc(100% - 33px)' }}>
              <PnLChart history={history} />
            </div>
          </div>
        </div>

        {/* Right: AI Chat Panel */}
        <div
          className="flex-shrink-0 border-l overflow-hidden"
          style={{ width: '280px', borderColor: '#2d333b' }}
        >
          <ChatPanel
            onTradeExecuted={handleTradeComplete}
            onWatchlistChanged={handleWatchlistChanged}
          />
        </div>
      </div>

      {/* Positions Table */}
      <div
        className="flex-shrink-0 border-t"
        style={{ height: '160px', borderColor: '#2d333b', backgroundColor: '#0d1117' }}
      >
        <div className="px-3 py-1.5 border-b" style={{ borderColor: '#2d333b' }}>
          <span className="text-xs font-bold tracking-widest" style={{ color: '#8b949e' }}>POSITIONS</span>
        </div>
        <div style={{ height: 'calc(100% - 28px)', overflowY: 'auto' }}>
          <PositionsTable
            positions={portfolio?.positions ?? []}
            prices={prices}
            onSelectTicker={setSelectedTicker}
          />
        </div>
      </div>

      {/* Trade Bar */}
      <TradeBar
        defaultTicker={selectedTicker}
        onTradeComplete={handleTradeComplete}
        onToast={addToast}
      />

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
