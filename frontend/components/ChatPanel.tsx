'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { ChatMessage, TradeExecuted, WatchlistChange } from '@/types';
import { api } from '@/lib/api';

interface ChatPanelProps {
  onTradeExecuted: () => void;
  onWatchlistChanged: () => void;
}

function ActionChip({ trade }: { trade: TradeExecuted }) {
  return (
    <div
      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full mt-1"
      style={{
        backgroundColor: trade.success
          ? (trade.side === 'buy' ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)')
          : 'rgba(139,148,158,0.15)',
        border: `1px solid ${trade.success ? (trade.side === 'buy' ? '#3fb950' : '#f85149') : '#8b949e'}`,
        color: trade.success ? (trade.side === 'buy' ? '#3fb950' : '#f85149') : '#8b949e',
      }}
    >
      {trade.success ? '✓' : '✗'}{' '}
      {trade.side === 'buy' ? 'Bought' : 'Sold'} {trade.quantity} {trade.ticker}
      {trade.price ? ` @ $${trade.price.toFixed(2)}` : ''}
    </div>
  );
}

function WatchlistChip({ change }: { change: WatchlistChange }) {
  return (
    <div
      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full mt-1 ml-1"
      style={{
        backgroundColor: change.success ? 'rgba(32, 157, 215, 0.15)' : 'rgba(139,148,158,0.15)',
        border: `1px solid ${change.success ? '#209dd7' : '#8b949e'}`,
        color: change.success ? '#209dd7' : '#8b949e',
      }}
    >
      {change.success ? '✓' : '✗'}{' '}
      {change.action === 'add' ? 'Added' : 'Removed'} {change.ticker}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-3`}>
      <div
        className="max-w-xs px-3 py-2 rounded-lg text-xs leading-relaxed"
        style={{
          backgroundColor: isUser ? 'rgba(32, 157, 215, 0.2)' : '#1e2530',
          border: `1px solid ${isUser ? '#209dd7' : '#2d333b'}`,
          color: '#e6edf3',
        }}
      >
        {msg.content}
      </div>
      {/* Action chips */}
      {!isUser && (msg.trades_executed?.length ?? 0) > 0 && (
        <div className="flex flex-wrap gap-1 mt-1 max-w-xs">
          {msg.trades_executed!.map((trade, i) => (
            <ActionChip key={i} trade={trade} />
          ))}
        </div>
      )}
      {!isUser && (msg.watchlist_changes?.length ?? 0) > 0 && (
        <div className="flex flex-wrap gap-1 mt-0.5 max-w-xs">
          {msg.watchlist_changes!.map((change, i) => (
            <WatchlistChip key={i} change={change} />
          ))}
        </div>
      )}
      <span className="text-xs mt-1" style={{ color: '#8b949e', fontSize: '10px' }}>
        {msg.timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}
      </span>
    </div>
  );
}

export function ChatPanel({ onTradeExecuted, onWatchlistChanged }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I'm FinAlly, your AI trading assistant. I can analyze your portfolio, suggest trades, and execute them for you. What would you like to do?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.sendChatMessage(text);

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        trades_executed: response.trades_executed,
        watchlist_changes: response.watchlist_changes,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMsg]);

      // Trigger refresh if trades or watchlist changes happened
      if (response.trades_executed?.some(t => t.success)) {
        onTradeExecuted();
      }
      if (response.watchlist_changes?.some(c => c.success)) {
        onWatchlistChanged();
      }
    } catch (e) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: e instanceof Error ? `Error: ${e.message}` : 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading, onTradeExecuted, onWatchlistChanged]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#0d1117' }}>
      {/* Header */}
      <div className="px-3 py-2 border-b" style={{ borderColor: '#2d333b' }}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold tracking-widest" style={{ color: '#8b949e' }}>AI ASSISTANT</span>
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(117,57,145,0.2)', color: '#753991', border: '1px solid rgba(117,57,145,0.4)' }}>
            FinAlly
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-start mb-3">
            <div
              className="px-3 py-2 rounded-lg text-xs"
              style={{ backgroundColor: '#1e2530', border: '1px solid #2d333b', color: '#8b949e' }}
            >
              <span className="inline-flex gap-1">
                <span style={{ animation: 'pulseDot 1.2s infinite' }}>●</span>
                <span style={{ animation: 'pulseDot 1.2s infinite 0.2s' }}>●</span>
                <span style={{ animation: 'pulseDot 1.2s infinite 0.4s' }}>●</span>
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-2 border-t" style={{ borderColor: '#2d333b' }}>
        {/* Quick prompts */}
        <div className="flex gap-1 mb-2 overflow-x-auto">
          {['Analyze my portfolio', 'What should I buy?', 'Show risk exposure'].map(prompt => (
            <button
              key={prompt}
              onClick={() => setInput(prompt)}
              className="text-xs px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0"
              style={{ backgroundColor: '#1a1a2e', border: '1px solid #2d333b', color: '#8b949e' }}
            >
              {prompt}
            </button>
          ))}
        </div>

        <div className="flex gap-1">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask FinAlly anything..."
            disabled={loading}
            className="flex-1 text-xs py-1.5 px-2 rounded"
            style={{
              backgroundColor: '#161b22',
              border: '1px solid #2d333b',
              color: '#e6edf3',
            }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-3 py-1.5 rounded text-xs font-bold disabled:opacity-40 transition-opacity"
            style={{ backgroundColor: '#753991', color: 'white' }}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
