// src/tests/BlockedSiteCard.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BlockedSiteCard from '../components/BlockedSiteCard';

const mockItem = {
  id:       'block-1',
  domain:   'youtube.com',
  reason:   'Too distracting',
  added_at: '2024-01-10T10:00:00Z'
};

describe('BlockedSiteCard', () => {

  test('renders domain name', () => {
    render(<BlockedSiteCard item={mockItem} onRemove={jest.fn()} />);
    expect(screen.getByText('youtube.com')).toBeInTheDocument();
  });

  test('renders reason when provided', () => {
    render(<BlockedSiteCard item={mockItem} onRemove={jest.fn()} />);
    expect(screen.getByText(/Too distracting/)).toBeInTheDocument();
  });

  test('calls onRemove when delete button clicked', () => {
    const mockOnRemove = jest.fn();
    render(<BlockedSiteCard item={mockItem} onRemove={mockOnRemove} />);

    fireEvent.click(screen.getByTitle('Remove from blocklist'));

    expect(mockOnRemove).toHaveBeenCalledWith('youtube.com');
    expect(mockOnRemove).toHaveBeenCalledTimes(1);
  });

  test('renders added date', () => {
    render(<BlockedSiteCard item={mockItem} onRemove={jest.fn()} />);
    expect(screen.getByText(/jan 10/i)).toBeInTheDocument();
  });
});
