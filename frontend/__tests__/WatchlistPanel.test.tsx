import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { WatchlistPanel } from '@/components/WatchlistPanel';
import type { WatchlistTicker } from '@/types';

// Mock Sparkline to avoid canvas issues in tests
jest.mock('@/components/Sparkline', () => ({
  Sparkline: () => <div data-testid="sparkline" />,
}));

const mockWatchlist: WatchlistTicker[] = [
  {
    ticker: 'AAPL',
    price: 192.5,
    previous_price: 191.0,
    change: 1.5,
    change_percent: 0.79,
    direction: 'up',
    added_at: '2024-01-01T00:00:00Z',
  },
  {
    ticker: 'GOOGL',
    price: 175.2,
    previous_price: 176.0,
    change: -0.8,
    change_percent: -0.45,
    direction: 'down',
    added_at: '2024-01-01T00:00:00Z',
  },
];

describe('WatchlistPanel', () => {
  const defaultProps = {
    watchlist: mockWatchlist,
    prices: {},
    sparklines: {},
    flashStates: {},
    selectedTicker: null,
    onSelectTicker: jest.fn(),
    onAddTicker: jest.fn(),
    onRemoveTicker: jest.fn(),
  };

  it('renders all watchlist tickers', () => {
    render(<WatchlistPanel {...defaultProps} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('GOOGL')).toBeInTheDocument();
  });

  it('renders prices', () => {
    render(<WatchlistPanel {...defaultProps} />);
    expect(screen.getByText('$192.50')).toBeInTheDocument();
    expect(screen.getByText('$175.20')).toBeInTheDocument();
  });

  it('calls onSelectTicker when a ticker is clicked', () => {
    const onSelectTicker = jest.fn();
    render(<WatchlistPanel {...defaultProps} onSelectTicker={onSelectTicker} />);
    fireEvent.click(screen.getByText('AAPL').closest('div')!.parentElement!);
    expect(onSelectTicker).toHaveBeenCalledWith('AAPL');
  });

  it('renders an add ticker input and button', () => {
    render(<WatchlistPanel {...defaultProps} />);
    expect(screen.getByPlaceholderText('Add ticker...')).toBeInTheDocument();
  });

  it('calls onAddTicker when add form is submitted', () => {
    const onAddTicker = jest.fn();
    render(<WatchlistPanel {...defaultProps} onAddTicker={onAddTicker} />);
    const input = screen.getByPlaceholderText('Add ticker...');
    fireEvent.change(input, { target: { value: 'TSLA' } });
    fireEvent.submit(input.closest('form')!);
    expect(onAddTicker).toHaveBeenCalledWith('TSLA');
  });

  it('applies flash-up class when ticker flashes up', () => {
    const { container } = render(
      <WatchlistPanel {...defaultProps} flashStates={{ AAPL: 'up' }} />
    );
    const aaplRow = screen.getByText('AAPL').closest('[class*="flash"]');
    expect(aaplRow?.className).toContain('flash-up');
  });

  it('applies flash-down class when ticker flashes down', () => {
    render(
      <WatchlistPanel {...defaultProps} flashStates={{ AAPL: 'down' }} />
    );
    const aaplRow = screen.getByText('AAPL').closest('[class*="flash"]');
    expect(aaplRow?.className).toContain('flash-down');
  });
});
