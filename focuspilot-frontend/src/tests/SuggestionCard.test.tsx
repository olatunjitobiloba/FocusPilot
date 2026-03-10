// src/tests/SuggestionCard.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import SuggestionCard from '../components/SuggestionCard';

const mockSuggestion = {
  domain:            'instagram.com',
  distraction_score: 72.5,
  confidence:        'high' as const,
  reason:            'You visit instagram.com during 80% of low-focus sessions.',
  total_visits:      15,
  total_minutes:     45.2,
  factors: {
    low_focus_ratio:   0.8,
    time_score:        0.6,
    abandonment_ratio: 0.4,
    timing_score:      0.5
  }
};

describe('SuggestionCard', () => {
  const onMarkProductive = jest.fn();

  test('renders domain name', () => {
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={jest.fn()} onDismiss={jest.fn()} onMarkProductive={onMarkProductive} />);
    expect(screen.getByText('instagram.com')).toBeInTheDocument();
  });

  test('renders distraction score', () => {
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={jest.fn()} onDismiss={jest.fn()} onMarkProductive={onMarkProductive} />);
    expect(screen.getByText('72.5')).toBeInTheDocument();
  });

  test('renders reason text', () => {
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={jest.fn()} onDismiss={jest.fn()} onMarkProductive={onMarkProductive} />);
    expect(screen.getByText(/80% of low-focus sessions/i)).toBeInTheDocument();
  });

  test('calls onAccept when block button clicked', () => {
    const mockOnAccept = jest.fn();
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={mockOnAccept} onDismiss={jest.fn()} onMarkProductive={onMarkProductive} />);

    fireEvent.click(screen.getByText(/Block This Site/));

    expect(mockOnAccept).toHaveBeenCalledWith('instagram.com');
  });

  test('calls onDismiss when dismiss button clicked', () => {
    const mockOnDismiss = jest.fn();
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={jest.fn()} onDismiss={mockOnDismiss} onMarkProductive={onMarkProductive} />);

    fireEvent.click(screen.getByText('Dismiss'));

    expect(mockOnDismiss).toHaveBeenCalledWith('instagram.com');
  });

  test('shows factor breakdown when details clicked', () => {
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={jest.fn()} onDismiss={jest.fn()} onMarkProductive={onMarkProductive} />);

    fireEvent.click(screen.getByText(/show factor breakdown/i));

    expect(screen.getByText('Low-focus visits')).toBeInTheDocument();
    expect(screen.getByText('Time spent')).toBeInTheDocument();
  });

  test('high confidence badge is red', () => {
    render(<SuggestionCard suggestion={mockSuggestion} onAccept={jest.fn()} onDismiss={jest.fn()} onMarkProductive={onMarkProductive} />);

    const badge = screen.getByText('high confidence');
    expect(badge).toHaveClass('text-red-700');
  });
});
