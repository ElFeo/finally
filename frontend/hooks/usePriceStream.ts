'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import type { PriceMap, ConnectionStatus, SparklineData } from '@/types';

const MAX_SPARKLINE_POINTS = 50;

export function usePriceStream() {
  const [prices, setPrices] = useState<PriceMap>({});
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [sparklines, setSparklines] = useState<SparklineData>({});
  const [flashStates, setFlashStates] = useState<Record<string, 'up' | 'down' | null>>({});
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flashTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const triggerFlash = useCallback((ticker: string, direction: 'up' | 'down') => {
    // Clear existing timer
    if (flashTimersRef.current[ticker]) {
      clearTimeout(flashTimersRef.current[ticker]);
    }
    setFlashStates(prev => ({ ...prev, [ticker]: direction }));
    flashTimersRef.current[ticker] = setTimeout(() => {
      setFlashStates(prev => ({ ...prev, [ticker]: null }));
    }, 600);
  }, []);

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setConnectionStatus('reconnecting');
    const es = new EventSource('/api/stream/prices');
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionStatus('connected');
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // data format: { AAPL: { ticker, price, previous_price, change, change_percent, direction }, ... }
        setPrices(prev => {
          const next = { ...prev };
          Object.entries(data).forEach(([ticker, priceData]) => {
            const pd = priceData as typeof next[string];
            next[ticker] = pd;
            // Trigger flash if price changed
            if (prev[ticker] && prev[ticker].price !== pd.price) {
              triggerFlash(ticker, pd.direction === 'down' ? 'down' : 'up');
            }
          });
          return next;
        });

        // Update sparklines
        setSparklines(prev => {
          const next = { ...prev };
          Object.entries(data).forEach(([ticker, priceData]) => {
            const pd = priceData as { price: number };
            const existing = next[ticker] || [];
            next[ticker] = [...existing, pd.price].slice(-MAX_SPARKLINE_POINTS);
          });
          return next;
        });
      } catch {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      setConnectionStatus('reconnecting');
      es.close();
      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };
  }, [triggerFlash]);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      Object.values(flashTimersRef.current).forEach(clearTimeout);
    };
  }, [connect]);

  return { prices, connectionStatus, sparklines, flashStates };
}
