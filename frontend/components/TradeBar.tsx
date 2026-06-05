'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';

interface TradeBarProps {
  defaultTicker?: string | null;
  onTradeComplete: () => void;
  onToast: (message: string, type: 'success' | 'error' | 'info') => void;
}

export function TradeBar({ defaultTicker, onTradeComplete, onToast }: TradeBarProps) {
  const [ticker, setTicker] = useState(defaultTicker || '');
  const [quantity, setQuantity] = useState('');
  const [loading, setLoading] = useState(false);

  // Update ticker when defaultTicker changes
  React.useEffect(() => {
    if (defaultTicker) setTicker(defaultTicker);
  }, [defaultTicker]);

  const executeTrade = async (side: 'buy' | 'sell') => {
    const t = ticker.trim().toUpperCase();
    const q = parseFloat(quantity);

    if (!t) {
      onToast('Please enter a ticker symbol', 'error');
      return;
    }
    if (!q || q <= 0) {
      onToast('Please enter a valid quantity', 'error');
      return;
    }

    setLoading(true);
    try {
      const result = await api.executeTrade({ ticker: t, quantity: q, side });
      if (result.success) {
        onToast(
          `${side === 'buy' ? '▲ Bought' : '▼ Sold'} ${q} ${t} @ $${result.price?.toFixed(2) ?? '—'}`,
          'success'
        );
        setQuantity('');
        onTradeComplete();
      } else {
        onToast(result.message || 'Trade failed', 'error');
      }
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Trade failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2" style={{ backgroundColor: '#0d1117', borderTop: '1px solid #2d333b' }}>
      <span className="text-xs font-bold tracking-widest" style={{ color: '#8b949e' }}>TRADE</span>

      <div className="flex items-center gap-2 flex-1">
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
            className="w-20 text-xs py-1.5 px-2 rounded font-mono font-bold"
            style={{
              backgroundColor: '#161b22',
              border: '1px solid #2d333b',
              color: '#ecad0a',
            }}
            maxLength={10}
            data-testid="trade-ticker-input"
          />
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="Qty"
            min="0.01"
            step="1"
            className="w-20 text-xs py-1.5 px-2 rounded font-mono"
            style={{
              backgroundColor: '#161b22',
              border: '1px solid #2d333b',
              color: '#e6edf3',
            }}
            data-testid="trade-quantity-input"
          />
        </div>

        <button
          onClick={() => executeTrade('buy')}
          disabled={loading}
          className="px-4 py-1.5 rounded text-xs font-bold tracking-wider transition-opacity disabled:opacity-50"
          style={{ backgroundColor: '#753991', color: 'white' }}
          data-testid="buy-button"
        >
          {loading ? '...' : '▲ BUY'}
        </button>

        <button
          onClick={() => executeTrade('sell')}
          disabled={loading}
          className="px-4 py-1.5 rounded text-xs font-bold tracking-wider transition-opacity disabled:opacity-50"
          style={{ backgroundColor: '#f85149', color: 'white' }}
          data-testid="sell-button"
        >
          {loading ? '...' : '▼ SELL'}
        </button>

        <span className="text-xs" style={{ color: '#8b949e' }}>
          Market Order · Instant Fill
        </span>
      </div>
    </div>
  );
}
