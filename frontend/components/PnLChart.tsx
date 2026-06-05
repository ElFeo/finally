'use client';

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PortfolioSnapshot } from '@/types';

interface PnLChartProps {
  history: PortfolioSnapshot[];
}

interface ChartDataPoint {
  time: string;
  value: number;
  displayTime: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="px-2 py-1.5 rounded text-xs" style={{ backgroundColor: '#1a1a2e', border: '1px solid #2d333b', color: '#e6edf3' }}>
      <p style={{ color: '#8b949e' }}>{label}</p>
      <p className="font-bold" style={{ color: '#209dd7' }}>
        ${payload[0].value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
    </div>
  );
}

export function PnLChart({ history }: PnLChartProps) {
  const data: ChartDataPoint[] = useMemo(() => {
    return history.map(snap => {
      const date = new Date(snap.recorded_at);
      return {
        time: snap.recorded_at,
        value: snap.total_value,
        displayTime: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
      };
    });
  }, [history]);

  const minValue = data.length > 0 ? Math.min(...data.map(d => d.value)) * 0.999 : 9000;
  const maxValue = data.length > 0 ? Math.max(...data.map(d => d.value)) * 1.001 : 11000;

  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center h-full" style={{ backgroundColor: '#0d1117' }}>
        <p className="text-xs" style={{ color: '#8b949e' }}>
          Portfolio value history will appear here once data is collected...
        </p>
      </div>
    );
  }

  return (
    <div className="w-full h-full" style={{ backgroundColor: '#0d1117' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2530" vertical={false} />
          <XAxis
            dataKey="displayTime"
            tick={{ fill: '#8b949e', fontSize: 10 }}
            axisLine={{ stroke: '#2d333b' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minValue, maxValue]}
            tick={{ fill: '#8b949e', fontSize: 10 }}
            axisLine={{ stroke: '#2d333b' }}
            tickLine={false}
            width={72}
            tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#209dd7"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#ecad0a' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
