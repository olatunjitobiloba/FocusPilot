import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders landing page brand', () => {
  render(<App />);
  const brandElement = screen.getByText('FocusPilot');
  expect(brandElement).toBeInTheDocument();
});
