'use client';

import { useState, useEffect, useCallback } from 'react';
import type { Portfolio, PortfolioSnapshot } from '@/types';
import { api } from '@/lib/api';

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [history, setHistory] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPortfolio = useCallback(async () => {
    try {
      const data = await api.getPortfolio();
      setPortfolio(data);
    } catch {
      // Silently handle error
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await api.getPortfolioHistory();
      setHistory(data);
    } catch {
      // Silently handle error
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([fetchPortfolio(), fetchHistory()]);
  }, [fetchPortfolio, fetchHistory]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      await refresh();
      if (mounted) setLoading(false);
    };
    load();

    // Poll every 5 seconds
    const interval = setInterval(() => {
      if (mounted) fetchPortfolio();
    }, 5000);

    // Poll history every 30 seconds
    const historyInterval = setInterval(() => {
      if (mounted) fetchHistory();
    }, 30000);

    return () => {
      mounted = false;
      clearInterval(interval);
      clearInterval(historyInterval);
    };
  }, [refresh, fetchPortfolio, fetchHistory]);

  return { portfolio, history, loading, refresh };
}
