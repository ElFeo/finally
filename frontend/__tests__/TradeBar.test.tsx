import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TradeBar } from '@/components/TradeBar';

// Mock the API module
jest.mock('@/lib/api', () => ({
  api: {
    executeTrade: jest.fn(),
  },
}));

import { api } from '@/lib/api';
const mockExecuteTrade = api.executeTrade as jest.Mock;

describe('TradeBar', () => {
  const mockOnTradeComplete = jest.fn();
  const mockOnToast = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders ticker and quantity inputs', () => {
    render(
      <TradeBar
        defaultTicker={null}
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );
    expect(screen.getByTestId('trade-ticker-input')).toBeInTheDocument();
    expect(screen.getByTestId('trade-quantity-input')).toBeInTheDocument();
  });

  it('renders BUY and SELL buttons', () => {
    render(
      <TradeBar
        defaultTicker={null}
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );
    expect(screen.getByTestId('buy-button')).toBeInTheDocument();
    expect(screen.getByTestId('sell-button')).toBeInTheDocument();
  });

  it('shows error when ticker is missing on buy', async () => {
    render(
      <TradeBar
        defaultTicker={null}
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );
    fireEvent.click(screen.getByTestId('buy-button'));
    await waitFor(() => {
      expect(mockOnToast).toHaveBeenCalledWith('Please enter a ticker symbol', 'error');
    });
  });

  it('shows error when quantity is missing on buy', async () => {
    render(
      <TradeBar
        defaultTicker="AAPL"
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );
    fireEvent.click(screen.getByTestId('buy-button'));
    await waitFor(() => {
      expect(mockOnToast).toHaveBeenCalledWith('Please enter a valid quantity', 'error');
    });
  });

  it('calls executeTrade API and shows success toast on successful buy', async () => {
    mockExecuteTrade.mockResolvedValueOnce({
      success: true,
      message: 'Trade executed',
      price: 192.5,
    });

    render(
      <TradeBar
        defaultTicker="AAPL"
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );

    fireEvent.change(screen.getByTestId('trade-quantity-input'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('buy-button'));

    await waitFor(() => {
      expect(mockExecuteTrade).toHaveBeenCalledWith({ ticker: 'AAPL', quantity: 5, side: 'buy' });
      expect(mockOnToast).toHaveBeenCalledWith(expect.stringContaining('Bought'), 'success');
      expect(mockOnTradeComplete).toHaveBeenCalled();
    });
  });

  it('calls executeTrade API and shows success toast on successful sell', async () => {
    mockExecuteTrade.mockResolvedValueOnce({
      success: true,
      message: 'Trade executed',
      price: 192.5,
    });

    render(
      <TradeBar
        defaultTicker="AAPL"
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );

    fireEvent.change(screen.getByTestId('trade-quantity-input'), { target: { value: '3' } });
    fireEvent.click(screen.getByTestId('sell-button'));

    await waitFor(() => {
      expect(mockExecuteTrade).toHaveBeenCalledWith({ ticker: 'AAPL', quantity: 3, side: 'sell' });
      expect(mockOnToast).toHaveBeenCalledWith(expect.stringContaining('Sold'), 'success');
    });
  });

  it('shows error toast on failed trade', async () => {
    mockExecuteTrade.mockResolvedValueOnce({
      success: false,
      message: 'Insufficient funds',
    });

    render(
      <TradeBar
        defaultTicker="AAPL"
        onTradeComplete={mockOnTradeComplete}
        onToast={mockOnToast}
      />
    );

    fireEvent.change(screen.getByTestId('trade-quantity-input'), { target: { value: '1000' } });
    fireEvent.click(screen.getByTestId('buy-button'));

    await waitFor(() => {
      expect(mockOnToast).toHaveBeenCalledWith('Insufficient funds', 'error');
    });
  });
});
