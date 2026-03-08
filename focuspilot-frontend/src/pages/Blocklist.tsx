// focuspilot-frontend/src/pages/Blocklist.tsx
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

interface BlocklistItem {
  id: string;
  domain: string;
  created_at: string;
}

function Blocklist() {
  const [blocklist, setBlocklist] = useState<BlocklistItem[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load blocklist on mount
  useEffect(() => {
    loadBlocklist();
  }, []);

  const loadBlocklist = async () => {
    try {
      const response = await api.get('/blocklist/');
      setBlocklist(response.data.blocklist);
    } catch (err: any) {
      console.error('Error loading blocklist:', err);
      setError('Failed to load blocklist');
    }
  };

  const addDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Clean domain (remove http://, www., etc.)
      let cleanDomain = newDomain.trim().toLowerCase();
      cleanDomain = cleanDomain.replace(/^https?:\/\//, '');
      cleanDomain = cleanDomain.replace(/^www\./, '');
      cleanDomain = cleanDomain.split('/')[0]; // Remove path

      const response = await api.post('/blocklist/', { domain: cleanDomain });
      
      // Add to list
      setBlocklist([...blocklist, response.data]);
      setNewDomain('');
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add domain');
    } finally {
      setLoading(false);
    }
  };

  const removeDomain = async (id: string) => {
    try {
      await api.delete(`/blocklist/${id}`);
      setBlocklist(blocklist.filter(item => item.id !== id));
    } catch (err: any) {
      setError('Failed to remove domain');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Blocklist</h1>
            <a 
              href="/dashboard" 
              className="text-green-600 hover:text-green-800"
            >
              ← Back to Dashboard
            </a>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Add Domain Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Add Website to Block</h2>
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <form onSubmit={addDomain} className="flex gap-4">
            <input
              type="text"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              placeholder="youtube.com, twitter.com, facebook.com"
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
            >
              {loading ? 'Adding...' : 'Add'}
            </button>
          </form>

          <p className="text-sm text-gray-600 mt-2">
            Tip: Just enter the domain (e.g., "youtube.com"). No need for http:// or www.
          </p>
        </div>

        {/* Blocklist */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-xl font-semibold">
              Blocked Websites ({blocklist.length})
            </h2>
          </div>

          {blocklist.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p className="text-lg mb-2">No blocked websites yet</p>
              <p className="text-sm">Add websites above to block them during focus sessions</p>
            </div>
          ) : (
            <ul className="divide-y">
              {blocklist.map((item) => (
                <li key={item.id} className="p-4 flex justify-between items-center hover:bg-gray-50">
                  <div>
                    <p className="font-medium text-gray-900">{item.domain}</p>
                    <p className="text-sm text-gray-500">
                      Added {
                        item.created_at 
                          ? new Date(item.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric'
                            })
                          : 'Recently'
                      }
                    </p>
                  </div>
                  <button
                    onClick={() => removeDomain(item.id)}
                    className="text-red-600 hover:text-red-800 font-medium"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Popular Sites */}
        <div className="mt-6 bg-green-50 rounded-lg p-6">
          <h3 className="font-semibold mb-3">Popular Sites to Block:</h3>
          <div className="flex flex-wrap gap-2">
            {['youtube.com', 'twitter.com', 'facebook.com', 'instagram.com', 'reddit.com', 'tiktok.com', 'netflix.com'].map(domain => (
              <button
                key={domain}
                onClick={() => setNewDomain(domain)}
                className="bg-white px-3 py-1 rounded-full text-sm hover:bg-green-100"
              >
                + {domain}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Blocklist;
