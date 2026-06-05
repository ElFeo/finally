'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { PriceMap } from '@/types';

interface MainChartProps {
  ticker: string | null;
  prices: PriceMap;
  sparklines: Record<string, number[]>;
}

interface ChartPoint {
  time: number;
  value: number;
}

export function MainChart({ ticker, prices, sparklines }: MainChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const seriesRef = useRef<any>(null);
  const chartPointsRef = useRef<ChartPoint[]>([]);
  const [chartReady, setChartReady] = useState(false);

  // Initialize chart
  useEffect(() => {
    let mounted = true;
    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (!mounted || !containerRef.current) return;

      const chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: '#161b22' },
          textColor: '#8b949e',
        },
        grid: {
          vertLines: { color: '#1e2530' },
          horzLines: { color: '#1e2530' },
        },
        crosshair: {
          vertLine: { color: '#209dd7', width: 1, style: 2 },
          horzLine: { color: '#209dd7', width: 1, style: 2 },
        },
        rightPriceScale: {
          borderColor: '#2d333b',
          textColor: '#8b949e',
        },
        timeScale: {
          borderColor: '#2d333b',
          timeVisible: true,
          secondsVisible: true,
        },
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });

      const series = chart.addLineSeries({
        color: '#209dd7',
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineColor: '#ecad0a',
        priceLineWidth: 1,
        priceLineStyle: 2,
      });

      chartRef.current = chart;
      seriesRef.current = series;
      setChartReady(true);

      // Handle resize
      const resizeObserver = new ResizeObserver(() => {
        if (containerRef.current) {
          chart.applyOptions({
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight,
          });
        }
      });
      if (containerRef.current) {
        resizeObserver.observe(containerRef.current);
      }

      return () => {
        resizeObserver.disconnect();
        chart.remove();
      };
    });

    return () => { mounted = false; };
  }, []);

  // Reset chart data when ticker changes
  useEffect(() => {
    if (!seriesRef.current || !ticker) return;
    chartPointsRef.current = [];
    seriesRef.current.setData([]);
  }, [ticker]);

  // Update chart with new price
  useEffect(() => {
    if (!seriesRef.current || !ticker || !chartReady) return;
    const priceData = prices[ticker];
    if (!priceData) return;

    const now = Math.floor(Date.now() / 1000);
    const point: ChartPoint = { time: now, value: priceData.price };

    // Avoid duplicate timestamps
    const last = chartPointsRef.current[chartPointsRef.current.length - 1];
    if (last && last.time === now) {
      // Update existing point
      chartPointsRef.current[chartPointsRef.current.length - 1] = point;
    } else {
      chartPointsRef.current.push(point);
    }

    try {
      seriesRef.current.setData(chartPointsRef.current);
    } catch {
      // Chart might not be ready
    }
  }, [ticker, prices, chartReady]);

  const currentPrice = ticker ? (prices[ticker]?.price ?? null) : null;
  const direction = ticker ? (prices[ticker]?.direction ?? null) : null;
  const changePct = ticker ? (prices[ticker]?.change_percent ?? null) : null;

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#161b22' }}>
      {/* Chart header */}
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: '#2d333b' }}>
        {ticker ? (
          <>
            <div className="flex items-center gap-3">
              <span className="font-bold text-sm" style={{ color: '#e6edf3' }}>{ticker}</span>
              <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: '#1a1a2e', color: '#8b949e' }}>
                PRICE CHART
              </span>
            </div>
            <div className="flex items-center gap-3">
              {currentPrice && (
                <span className="text-lg font-bold font-mono" style={{ color: '#e6edf3' }}>
                  ${currentPrice.toFixed(2)}
                </span>
              )}
              {changePct !== null && (
                <span
                  className="text-sm font-bold"
                  style={{ color: direction === 'down' ? '#f85149' : '#3fb950' }}
                >
                  {direction === 'down' ? '▼' : '▲'} {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                </span>
              )}
            </div>
          </>
        ) : (
          <span className="text-xs" style={{ color: '#8b949e' }}>Select a ticker to view chart</span>
        )}
      </div>

      {/* Chart container */}
      <div className="flex-1 relative">
        {!ticker ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2" style={{ color: '#2d333b' }}>📈</div>
              <p className="text-sm" style={{ color: '#8b949e' }}>Click a ticker in the watchlist</p>
            </div>
          </div>
        ) : (
          <div ref={containerRef} className="absolute inset-0" />
        )}
      </div>
    </div>
  );
}
