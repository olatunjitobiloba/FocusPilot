import React, { useState } from 'react';

interface AddSiteModalProps {
  onAdd: (domain: string, reason?: string) => Promise<void> | void;
  onClose: () => void;
  title?: string;
  submitLabel?: string;
}

const COMMON_SITES = [
  { domain: 'youtube.com', label: 'YouTube' },
  { domain: 'twitter.com', label: 'Twitter' },
  { domain: 'instagram.com', label: 'Instagram' },
  { domain: 'tiktok.com', label: 'TikTok' },
  { domain: 'reddit.com', label: 'Reddit' },
  { domain: 'facebook.com', label: 'Facebook' },
  { domain: 'netflix.com', label: 'Netflix' },
  { domain: 'twitch.tv', label: 'Twitch' },
];

function AddSiteModal({
  onAdd,
  onClose,
  title = 'Add Site to Block',
  submitLabel = 'Block Site',
}: AddSiteModalProps) {
  const [domain, setDomain] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const validateDomain = (value: string): boolean => {
    const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$/;
    return domainRegex.test(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const cleanDomain = domain.toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .split('/')[0]
      .trim();

    if (!validateDomain(cleanDomain)) {
      setError('Please enter a valid domain (e.g. youtube.com)');
      return;
    }

    setLoading(true);
    try {
      await onAdd(cleanDomain, reason || undefined);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to add site. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAdd = async (quickDomain: string) => {
    setError('');
    setLoading(true);
    try {
      await onAdd(quickDomain);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to add site. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
          >
            X
          </button>
        </div>

        <div className="mb-6">
          <p className="text-sm font-semibold text-gray-600 mb-3">
            Quick Add Common Sites:
          </p>
          <div className="grid grid-cols-4 gap-2">
            {COMMON_SITES.map((site) => (
              <button
                key={site.domain}
                onClick={() => handleQuickAdd(site.domain)}
                disabled={loading}
                className="flex flex-col items-center p-2 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-green-300 transition text-xs"
              >
                <span className="text-gray-600 truncate w-full text-center">
                  {site.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center mb-6">
          <div className="flex-1 border-t border-gray-200" />
          <span className="px-3 text-sm text-gray-500">or enter manually</span>
          <div className="flex-1 border-t border-gray-200" />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Domain *
            </label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. youtube.com"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              No need for https:// or www
            </p>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Reason (optional)
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Too addictive during study time"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400 transition"
            >
              {loading ? 'Adding...' : submitLabel}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddSiteModal;