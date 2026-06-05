// Market data types
export interface PriceData {
  ticker: string;
  price: number;
  previous_price: number;
  change: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
  timestamp?: number;
}

export type PriceMap = Record<string, PriceData>;

// Watchlist types
export interface WatchlistTicker {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: 'up' | 'down' | 'flat';
  added_at: string;
}

// Portfolio types
export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  positions: Position[];
  unrealized_pnl: number;
}

// Portfolio history
export interface PortfolioSnapshot {
  recorded_at: string;
  total_value: number;
}

// Trade types
export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: 'buy' | 'sell';
}

export interface TradeResult {
  success: boolean;
  message: string;
  ticker?: string;
  side?: string;
  quantity?: number;
  price?: number;
}

// Chat types
export interface TradeExecuted {
  ticker: string;
  side: string;
  quantity: number;
  price: number;
  success: boolean;
}

export interface WatchlistChange {
  ticker: string;
  action: string;
  success: boolean;
}

export interface ChatResponse {
  message: string;
  trades_executed: TradeExecuted[];
  watchlist_changes: WatchlistChange[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  trades_executed?: TradeExecuted[];
  watchlist_changes?: WatchlistChange[];
  timestamp: Date;
}

// Connection status
export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

// Toast notification
export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

// Sparkline data
export type SparklineData = Record<string, number[]>;
