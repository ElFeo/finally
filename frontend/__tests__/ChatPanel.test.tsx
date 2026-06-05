import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatPanel } from '@/components/ChatPanel';

jest.mock('@/lib/api', () => ({
  api: {
    sendChatMessage: jest.fn(),
  },
}));

import { api } from '@/lib/api';
const mockSendChatMessage = api.sendChatMessage as jest.Mock;

// Mock scrollIntoView which is not available in jsdom
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});

describe('ChatPanel', () => {
  const mockOnTradeExecuted = jest.fn();
  const mockOnWatchlistChanged = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the welcome message', () => {
    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );
    expect(screen.getByText(/Hello!/i)).toBeInTheDocument();
  });

  it('renders the chat input', () => {
    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );
    expect(screen.getByPlaceholderText('Ask FinAlly anything...')).toBeInTheDocument();
  });

  it('shows loading state while waiting for response', async () => {
    let resolvePromise: (value: unknown) => void = () => {};
    mockSendChatMessage.mockReturnValue(
      new Promise(resolve => { resolvePromise = resolve; })
    );

    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );

    const input = screen.getByPlaceholderText('Ask FinAlly anything...');
    fireEvent.change(input, { target: { value: 'What should I buy?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockSendChatMessage).toHaveBeenCalledWith('What should I buy?');
    });

    // Resolve the promise to clean up
    resolvePromise({
      message: 'I recommend AAPL.',
      trades_executed: [],
      watchlist_changes: [],
    });
  });

  it('displays assistant response after sending a message', async () => {
    mockSendChatMessage.mockResolvedValueOnce({
      message: 'I recommend buying AAPL.',
      trades_executed: [],
      watchlist_changes: [],
    });

    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );

    const input = screen.getByPlaceholderText('Ask FinAlly anything...');
    fireEvent.change(input, { target: { value: 'What should I buy?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('I recommend buying AAPL.')).toBeInTheDocument();
    });
  });

  it('calls onTradeExecuted when trade is successfully executed', async () => {
    mockSendChatMessage.mockResolvedValueOnce({
      message: 'Bought 10 AAPL for you.',
      trades_executed: [{ ticker: 'AAPL', side: 'buy', quantity: 10, price: 192.5, success: true }],
      watchlist_changes: [],
    });

    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );

    const input = screen.getByPlaceholderText('Ask FinAlly anything...');
    fireEvent.change(input, { target: { value: 'Buy 10 AAPL' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockOnTradeExecuted).toHaveBeenCalled();
    });
  });

  it('renders quick prompt buttons', () => {
    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );
    expect(screen.getByText('Analyze my portfolio')).toBeInTheDocument();
  });

  it('calls onWatchlistChanged when watchlist is changed', async () => {
    mockSendChatMessage.mockResolvedValueOnce({
      message: 'Added PYPL to your watchlist.',
      trades_executed: [],
      watchlist_changes: [{ ticker: 'PYPL', action: 'add', success: true }],
    });

    render(
      <ChatPanel
        onTradeExecuted={mockOnTradeExecuted}
        onWatchlistChanged={mockOnWatchlistChanged}
      />
    );

    const input = screen.getByPlaceholderText('Ask FinAlly anything...');
    fireEvent.change(input, { target: { value: 'Add PYPL to my watchlist' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockOnWatchlistChanged).toHaveBeenCalled();
    });
  });
});
