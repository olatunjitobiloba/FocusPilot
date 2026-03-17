import React from 'react';

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  errorMessage: string;
};

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      errorMessage: '',
    };
  }

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error instanceof Error ? error.message : 'Unknown frontend error',
    };
  }

  componentDidCatch(error: unknown, errorInfo: React.ErrorInfo): void {
    console.error('Unhandled React render error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
          <div className="max-w-xl w-full bg-white rounded-xl border border-red-200 shadow p-6">
            <h1 className="text-xl font-bold text-red-700 mb-2">Page failed to render</h1>
            <p className="text-sm text-gray-700 mb-4">
              The app hit an unexpected frontend error. This view replaces a blank screen and helps surface the problem.
            </p>
            <div className="text-xs text-gray-600 bg-gray-50 border rounded p-3 mb-4 break-words">
              {this.state.errorMessage || 'No error details available.'}
            </div>
            <button
              onClick={this.handleReload}
              className="px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-semibold hover:bg-gray-800 transition"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
