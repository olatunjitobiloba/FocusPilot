import React, { useEffect, useState } from 'react';
import { blocklistAPI, suggestionsAPI } from '../api/client';
import AddSiteModal from '../components/AddSiteModal';
import SuggestionCard from '../components/SuggestionCard';
import BlockedSiteCard from '../components/BlockedSiteCard';
import Navbar from '../components/Navbar';

const BLOCKLIST_CACHE_KEY = 'focuspilot_blocklist_cache_v1';

interface BlocklistItem {
  id: string;
  domain: string;
  reason?: string | null;
  created_at?: string;
}

interface SuggestionItem {
  domain: string;
  distraction_score?: number;
  frequency?: number;
  total_time_seconds?: number;
}

function Blocklist() {
  const [blocklist, setBlocklist] = useState<BlocklistItem[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [hasLoadedSuggestions, setHasLoadedSuggestions] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'blocked' | 'suggested'>('blocked');
  const [searchQuery, setSearchQuery] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    const cached = localStorage.getItem(BLOCKLIST_CACHE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed)) {
          setBlocklist(parsed);
          setLoading(false);
          loadBlocklist(false);
          return;
        }
      } catch {
        localStorage.removeItem(BLOCKLIST_CACHE_KEY);
      }
    }

    loadBlocklist(true);
  }, []);

  useEffect(() => {
    if (activeTab === 'suggested' && !hasLoadedSuggestions) {
      loadSuggestions();
    }
  }, [activeTab, hasLoadedSuggestions]);

  useEffect(() => {
    if (loading || hasLoadedSuggestions) return;

    const schedulePreload = () => loadSuggestions();
    const runtime = globalThis as any;

    if (typeof runtime.requestIdleCallback === 'function') {
      const idleId = runtime.requestIdleCallback(schedulePreload, { timeout: 500 });
      return () => {
        runtime.cancelIdleCallback?.(idleId);
      };
    }

    const timer = setTimeout(schedulePreload, 120);
    return () => clearTimeout(timer);
  }, [loading, hasLoadedSuggestions]);

  const loadBlocklist = async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const blocklistRes = await blocklistAPI.getAll();
      const nextBlocklist = blocklistRes.data.blocklist || [];
      setBlocklist(nextBlocklist);
      localStorage.setItem(BLOCKLIST_CACHE_KEY, JSON.stringify(nextBlocklist));
    } catch (error) {
      console.error('Error loading blocklist:', error);
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  const loadSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const suggestionsRes = await suggestionsAPI.getAll();
      setSuggestions(suggestionsRes.data.suggestions || []);
      setHasLoadedSuggestions(true);
    } catch (error) {
      console.error('Error loading suggestions:', error);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const cleanDomain = (value: string) => {
    let clean = value.trim().toLowerCase();
    clean = clean.replace(/^https?:\/\//, '');
    clean = clean.replace(/^www\./, '');
    clean = clean.split('/')[0];
    return clean;
  };

  const handleAddSite = async (domain: string, reason?: string) => {
    const normalizedDomain = cleanDomain(domain);

    if (!normalizedDomain) {
      throw new Error('Domain is required');
    }

    try {
      await blocklistAPI.add(normalizedDomain, reason);
      showSuccess(`${normalizedDomain} added to blocklist`);
      await loadBlocklist(false);
      if (hasLoadedSuggestions) {
        await loadSuggestions();
      }
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to add site');
      throw error;
    }
  };

  const handleRemoveSite = async (domain: string) => {
    if (!window.confirm(`Remove ${domain} from blocklist?`)) return;
    try {
      await blocklistAPI.remove(domain);
      showSuccess(`${domain} removed`);
      await loadBlocklist(false);
    } catch (error) {
      alert('Failed to remove site');
    }
  };

  const handleAcceptSuggestion = async (domain: string) => {
    const normalizedDomain = cleanDomain(domain);
    try {
      await suggestionsAPI.accept(normalizedDomain);
      showSuccess(`${normalizedDomain} added to blocklist`);
      await Promise.all([loadBlocklist(false), loadSuggestions()]);
    } catch (error) {
      alert('Failed to accept suggestion');
    }
  };

  const handleDismissSuggestion = async (domain: string) => {
    try {
      await suggestionsAPI.dismiss(domain);
      setSuggestions((prev) => prev.filter((s) => s.domain !== domain));
    } catch (error) {
      alert('Failed to dismiss suggestion');
    }
  };

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  const filteredBlocklist = blocklist.filter((item) =>
    item.domain.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-2xl text-gray-600 animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Blocklist Manager</h1>
            <p className="text-gray-600 mt-1">Manage which sites are blocked during focus sessions</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition"
          >
            + Add Site
          </button>
        </div>

        {successMsg && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-6 flex items-center">
            {successMsg}
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-red-600">{blocklist.length}</p>
            <p className="text-gray-600 text-sm mt-1">Sites Blocked</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-yellow-600">{suggestions.length}</p>
            <p className="text-gray-600 text-sm mt-1">AI Suggestions</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-green-600">{blocklist.length + suggestions.length}</p>
            <p className="text-gray-600 text-sm mt-1">Total Identified</p>
          </div>
        </div>

        <div className="flex border-b border-gray-200 mb-6">
          <button
            onClick={() => setActiveTab('blocked')}
            className={`px-6 py-3 font-semibold text-sm transition ${
              activeTab === 'blocked'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Blocked Sites ({blocklist.length})
          </button>
          <button
            onClick={() => setActiveTab('suggested')}
            className={`px-6 py-3 font-semibold text-sm transition ${
              activeTab === 'suggested'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            AI Suggestions ({suggestions.length})
          </button>
        </div>

        {activeTab === 'blocked' && (
          <div>
            {blocklist.length > 5 && (
              <input
                type="text"
                placeholder="Search blocked sites..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            )}

            {filteredBlocklist.length === 0 && (
              <div className="text-center py-16">
                <h3 className="text-xl font-semibold text-gray-700 mb-2">No sites blocked yet</h3>
                <p className="text-gray-500 mb-6">Add sites you want to block during focus sessions</p>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700"
                >
                  + Add Your First Site
                </button>
              </div>
            )}

            <div className="space-y-3">
              {filteredBlocklist.map((item) => (
                <BlockedSiteCard key={item.id} item={item} onRemove={handleRemoveSite} />
              ))}
            </div>
          </div>
        )}

        {activeTab === 'suggested' && (
          <div>
            {loadingSuggestions && (
              <div className="text-center py-10 text-gray-500">Loading suggestions...</div>
            )}

            {!loadingSuggestions && suggestions.length === 0 ? (
              <div className="text-center py-16">
                <h3 className="text-xl font-semibold text-gray-700 mb-2">No suggestions yet</h3>
                <p className="text-gray-500">
                  Complete a few focus sessions and the AI will analyze your browsing patterns to suggest
                  sites to block.
                </p>
              </div>
            ) : (
              <>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                  <p className="text-green-800 text-sm">
                    <strong>AI Analysis:</strong> Based on your browsing patterns, these sites are hurting
                    your focus the most. Accept to block them automatically.
                  </p>
                </div>

                <div className="space-y-4">
                  {suggestions.map((suggestion) => (
                    <SuggestionCard
                      key={suggestion.domain}
                      suggestion={suggestion}
                      onAccept={handleAcceptSuggestion}
                      onDismiss={handleDismissSuggestion}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </main>

      {showAddModal && (
        <AddSiteModal onAdd={handleAddSite} onClose={() => setShowAddModal(false)} />
      )}
    </div>
  );
}

export default Blocklist;
