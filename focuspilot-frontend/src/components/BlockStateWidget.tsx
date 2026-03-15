// src/components/BlockStateWidget.tsx
import React, { useEffect, useState } from 'react';
import { executionAPI } from '../api/client';
import { BlockState } from '../types/execution';

function BlockStateWidget() {
  const [state,   setState]   = useState<BlockState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, []);

  const load = async () => {
    try {
      const res = await executionAPI.getBlockState();
      setState(res.data);
    } finally {
      setLoading(false);
    }
  };

  const handleUnblock = async () => {
    await executionAPI.manualUnblock();
    await load();
  };

  if (loading || !state) return null;

  if (!state.is_blocked) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-4
        flex items-center gap-3">
        <span className="text-2xl">🔓</span>
        <div>
          <p className="font-semibold text-green-800 text-sm">
            Sites Accessible
          </p>
          <p className="text-xs text-green-600">
            No active site blocks
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-4
      flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-2xl">🔒</span>
        <div>
          <p className="font-semibold text-red-800 text-sm">
            Focus Mode Active
          </p>
          <p className="text-xs text-red-600">
            {state.blocked_domains?.length || 0} sites blocked
            {state.unblock_at && (
              ` · Unblocks at ${new Date(state.unblock_at)
                .toLocaleTimeString()}`
            )}
          </p>
        </div>
      </div>
      <button
        onClick={handleUnblock}
        className="text-xs text-red-600 hover:underline font-medium"
      >
        Unblock
      </button>
    </div>
  );
}

export default BlockStateWidget;
