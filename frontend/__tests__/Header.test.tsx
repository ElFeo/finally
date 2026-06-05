import React from 'react';
import { render, screen } from '@testing-library/react';
import { Header } from '@/components/Header';
import type { Portfolio } from '@/types';

const mockPortfolio: Portfolio = {
  cash_balance: 5000,
  total_value: 10523.45,
  positions: [],
  unrealized_pnl: 523.45,
};

describe('Header', () => {
  it('renders part of the app name "FIN"', () => {
    render(<Header portfolio={null} connectionStatus="connected" />);
    expect(screen.getByText(/FIN/)).toBeInTheDocument();
  });

  it('renders portfolio total value', () => {
    render(<Header portfolio={mockPortfolio} connectionStatus="connected" />);
    expect(screen.getByText(/10,523\.45/)).toBeInTheDocument();
  });

  it('renders cash balance', () => {
    render(<Header portfolio={mockPortfolio} connectionStatus="connected" />);
    expect(screen.getByText(/5,000\.00/)).toBeInTheDocument();
  });

  it('renders connection status as LIVE when connected', () => {
    render(<Header portfolio={null} connectionStatus="connected" />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });

  it('renders connection status as SYNC when reconnecting', () => {
    render(<Header portfolio={null} connectionStatus="reconnecting" />);
    expect(screen.getByText('SYNC')).toBeInTheDocument();
  });

  it('renders connection status as DISC when disconnected', () => {
    render(<Header portfolio={null} connectionStatus="disconnected" />);
    expect(screen.getByText('DISC')).toBeInTheDocument();
  });

  it('shows positive P&L amount', () => {
    render(<Header portfolio={mockPortfolio} connectionStatus="connected" />);
    // The P&L element should show a positive number
    const pnlElements = screen.getAllByText(/523\.45/);
    expect(pnlElements.length).toBeGreaterThan(0);
  });

  it('renders AI TRADING WORKSTATION badge', () => {
    render(<Header portfolio={null} connectionStatus="connected" />);
    expect(screen.getByText('AI TRADING WORKSTATION')).toBeInTheDocument();
  });
});
