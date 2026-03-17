import React from 'react';
import ReactDOM from 'react-dom/client';
import axios from 'axios';
import './index.css';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';

if (process.env.NODE_ENV === 'development') {
  const noop = () => {};
  (window as any).__REACT_ERROR_OVERLAY_GLOBAL_HOOK__ = {
    iframeReady: noop,
    handleRuntimeError: noop,
    showCompileError: noop,
    clearCompileError: noop,
  };
}

const isAxiosLikeError = (reason: any): boolean => {
  return (
    axios.isAxiosError(reason) ||
    reason?.isAxiosError === true ||
    reason?.name === 'AxiosError' ||
    (typeof reason?.message === 'string' &&
      reason.message.includes('Request failed with status code'))
  );
};

const swallowIfAxiosLike = (reason: any, event: Event): boolean => {
  if (!isAxiosLikeError(reason)) {
    return false;
  }

  console.error('Suppressed Axios runtime error:', reason);
  event.preventDefault();
  event.stopPropagation();
  if (typeof (event as any).stopImmediatePropagation === 'function') {
    (event as any).stopImmediatePropagation();
  }
  return true;
};

// Prevent backend API failures from surfacing as uncaught runtime overlays.
window.addEventListener(
  'unhandledrejection',
  (event) => {
    swallowIfAxiosLike((event as PromiseRejectionEvent).reason, event);
  },
  { capture: true }
);

window.addEventListener(
  'error',
  (event) => {
    const err = (event as ErrorEvent).error;
    if (!swallowIfAxiosLike(err, event)) {
      const msg = (event as ErrorEvent).message;
      swallowIfAxiosLike({ message: msg }, event);
    }
  },
  { capture: true }
);

window.onunhandledrejection = (event) => {
  if (isAxiosLikeError((event as PromiseRejectionEvent).reason)) {
    (event as PromiseRejectionEvent).preventDefault();
    return true;
  }
  return false;
};

window.onerror = (_message, _source, _lineno, _colno, error) => {
  if (isAxiosLikeError(error)) {
    return true;
  }
  return false;
};

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
