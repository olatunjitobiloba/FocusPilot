// src/tests/Login.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../pages/Login';
import { authAPI } from '../api/client';

jest.mock('../api/client', () => ({
  authAPI: {
    login: jest.fn(),
  },
}));

const mockedLogin = authAPI.login as jest.Mock;

// Wrap component in router (Login uses useNavigate)
const renderLogin = () => render(
  <BrowserRouter>
    <Login />
  </BrowserRouter>
);

describe('Login Page', () => {

  beforeEach(() => {
    mockedLogin.mockReset();
    mockedLogin.mockResolvedValue({
      data: {
        access_token: 'mock-token',
        user: {
          id: 'user-123',
          email: 'test@test.com',
          full_name: 'Test User',
        },
      },
    });
  });

  test('renders login form', () => {
    renderLogin();

    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
  });

  test('shows error on empty form submit', async () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    // HTML5 validation prevents submit — email field should be focused
    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toBeRequired();
  });

  test('shows error on invalid credentials', async () => {
    mockedLogin.mockRejectedValueOnce({
      response: {
        data: {
          detail: 'Invalid credentials',
        },
      },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText('Email'),    { target: { value: 'wrong@test.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrongpass' } });
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  test('shows loading state during login', async () => {
    mockedLogin.mockImplementationOnce(
      () => new Promise(() => {})
    );

    renderLogin();

    fireEvent.change(screen.getByLabelText('Email'),    { target: { value: 'test@test.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    // Should show loading text immediately
    expect(screen.getByText('Logging In...')).toBeInTheDocument();
  });

  test('link to signup page exists', () => {
    renderLogin();

    const signupLink = screen.getByRole('link', { name: /sign up/i });
    expect(signupLink).toHaveAttribute('href', '/signup');
  });
});
