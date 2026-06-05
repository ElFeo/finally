'use client';

import { useState, useEffect, useCallback } from 'react';
import type { WatchlistTicker } from '@/types';
import { api } from '@/lib/api';

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistTicker[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const data = await api.getWatchlist();
      setWatchlist(data);
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  const addTicker = useCallback(async (ticker: string) => {
    try {
      await api.addToWatchlist(ticker.toUpperCase());
      await fetch();
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof Error ? e.message : 'Failed to add ticker' };
    }
  }, [fetch]);

  const removeTicker = useCallback(async (ticker: string) => {
    try {
      await api.removeFromWatchlist(ticker);
      setWatchlist(prev => prev.filter(t => t.ticker !== ticker));
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof Error ? e.message : 'Failed to remove ticker' };
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { watchlist, loading, addTicker, removeTicker, refresh: fetch };
}
