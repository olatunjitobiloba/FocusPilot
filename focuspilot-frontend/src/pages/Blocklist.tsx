import React, { useEffect, useState } from 'react';
import { blocklistAPI, suggestionsAPI, whitelistAPI } from '../api/client';
import AddSiteModal from '../components/AddSiteModal';
import SuggestionCard from '../components/SuggestionCard';
import BlockedSiteCard from '../components/BlockedSiteCard';
import Navbar from '../components/Navbar';
import { useLocation } from 'react-router-dom';

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

interface WhitelistItem {
  domain: string;
  created_at?: string;
}

function Blocklist() {
  const location = useLocation();
  const [blocklist, setBlocklist] = useState<BlocklistItem[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [hasLoadedSuggestions, setHasLoadedSuggestions] = useState(false);
  const [whitelist, setWhitelist] = useState<WhitelistItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAddProductiveModal, setShowAddProductiveModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'blocked' | 'suggested' | 'productive'>('blocked');
  const [searchQuery, setSearchQuery] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    const tab = new URLSearchParams(location.search).get('tab');
    if (tab === 'suggested' || tab === 'productive' || tab === 'blocked') {
      setActiveTab(tab);
    }
  }, [location.search]);

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

  const loadWhitelist = async () => {
    try {
      const whitelistRes = await whitelistAPI.getAll();
      setWhitelist(whitelistRes.data.whitelist || []);
    } catch (error) {
      console.error('Error loading whitelist:', error);
    }
  };

  const cleanDomain = (value: string) => {
    let clean = value.trim().toLowerCase();
    clean = clean.replace(/^https?:\/\//, '');
    clean = clean.replace(/^www\./, '');
    clean = clean.split('/')[0];
    return clean;
  };

  const notifyExtensionBlocklistChanged = () => {
    const token = localStorage.getItem('token');
    window.postMessage(
      {
        source: 'focuspilot-web',
        action: 'refreshBlocklist',
        token,
      },
      '*'
    );
  };

  useEffect(() => {
    loadWhitelist();
  }, []);

  const handleAddSite = async (domain: string, reason?: string) => {
    const normalizedDomain = cleanDomain(domain);

    if (!normalizedDomain) {
      throw new Error('Domain is required');
    }

    const alreadyExistsLocally = blocklist.some(
      (item) => cleanDomain(item.domain) === normalizedDomain
    );

    if (alreadyExistsLocally) {
      showSuccess(`${normalizedDomain} is already in your blocklist`);
      if (hasLoadedSuggestions) {
        setSuggestions((prev) => prev.filter((s) => cleanDomain(s.domain) !== normalizedDomain));
      }
      return;
    }

    try {
      await blocklistAPI.add(normalizedDomain, reason);
      notifyExtensionBlocklistChanged();
      showSuccess(`${normalizedDomain} added to blocklist`);
      await Promise.all([loadBlocklist(false), loadWhitelist()]);
      if (hasLoadedSuggestions) {
        await loadSuggestions();
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail || 'Failed to add site';
      const isAlreadyBlocked = typeof detail === 'string' && detail.toLowerCase().includes('already in blocklist');

      if (isAlreadyBlocked) {
        showSuccess(detail);
        await loadBlocklist(false);
        if (hasLoadedSuggestions) {
          await loadSuggestions();
        }
        return;
      }

      throw new Error(detail);
    }
  };

  const handleRemoveSite = async (domain: string) => {
    if (!window.confirm(`Remove ${domain} from blocklist?`)) return;
    try {
      await blocklistAPI.remove(domain);
      notifyExtensionBlocklistChanged();
      showSuccess(`${domain} removed`);
      await Promise.all([loadBlocklist(false), loadWhitelist()]);
    } catch (error) {
      alert('Failed to remove site');
    }
  };

  const handleAcceptSuggestion = async (domain: string) => {
    const normalizedDomain = cleanDomain(domain);
    try {
      const response = await suggestionsAPI.accept(normalizedDomain);
      notifyExtensionBlocklistChanged();
      const message = response?.data?.message || `${normalizedDomain} added to blocklist`;
      showSuccess(message);
      await Promise.all([loadBlocklist(false), loadSuggestions(), loadWhitelist()]);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to accept suggestion');
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

  const handleMarkProductive = async (domain: string) => {
    const normalizedDomain = cleanDomain(domain);

    const alreadyProductive = whitelist.some(
      (item) => cleanDomain(item.domain) === normalizedDomain
    );

    if (alreadyProductive) {
      showSuccess(`${normalizedDomain} is already marked as productive`);
      return;
    }

    try {
      await whitelistAPI.add(normalizedDomain);
      notifyExtensionBlocklistChanged();
      showSuccess(`${normalizedDomain} marked as productive`);
      await Promise.all([loadWhitelist(), loadBlocklist(false), loadSuggestions()]);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to mark as productive');
    }
  };

  const handleRemoveFromWhitelist = async (domain: string) => {
    const normalizedDomain = cleanDomain(domain);
    try {
      await whitelistAPI.remove(normalizedDomain);
      showSuccess(`${normalizedDomain} removed from productive list`);
      await Promise.all([loadWhitelist(), loadSuggestions()]);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to remove productive site');
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
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddProductiveModal(true)}
              className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition"
            >
              + Mark Productive
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition"
            >
              + Add Site
            </button>
          </div>
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
            <p className="text-3xl font-bold text-green-600">{blocklist.length + suggestions.length + whitelist.length}</p>
            <p className="text-gray-600 text-sm mt-1">Total Identified</p>
          </div>
        </div>

        {whitelist.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <p className="text-green-800 text-sm">
              <strong>Productive Whitelist:</strong> {whitelist.map((item) => item.domain).join(', ')}
            </p>
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-gray-700">
            If a site helps your work but never appears under AI Suggestions, click <strong>Mark Productive</strong> and add it manually.
          </p>
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
          <button
            onClick={() => setActiveTab('productive')}
            className={`px-6 py-3 font-semibold text-sm transition ${
              activeTab === 'productive'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Productive Sites ({whitelist.length})
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
                <BlockedSiteCard
                  key={item.id}
                  item={item}
                  onRemove={handleRemoveSite}
                  onMarkProductive={handleMarkProductive}
                />
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
                      onMarkProductive={handleMarkProductive}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'productive' && (
          <div>
            {whitelist.length === 0 ? (
              <div className="text-center py-16">
                <h3 className="text-xl font-semibold text-gray-700 mb-2">No productive sites yet</h3>
                <p className="text-gray-500">
                  Mark sites as productive to keep them out of distraction suggestions.
                </p>
                <button
                  onClick={() => setShowAddProductiveModal(true)}
                  className="mt-6 bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition"
                >
                  + Add Productive Site
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex justify-end">
                  <button
                    onClick={() => setShowAddProductiveModal(true)}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-green-700 transition"
                  >
                    + Add Productive Site
                  </button>
                </div>
                {whitelist.map((item) => (
                  <div key={item.domain} className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img
                        src={`https://www.google.com/s2/favicons?domain=${item.domain}&sz=32`}
                        alt={item.domain}
                        className="w-8 h-8 rounded"
                      />
                      <div>
                        <p className="font-semibold text-gray-900">{item.domain}</p>
                        <p className="text-xs text-gray-500">Marked productive</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveFromWhitelist(item.domain)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50 p-2 rounded-lg transition"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {showAddModal && (
        <AddSiteModal onAdd={handleAddSite} onClose={() => setShowAddModal(false)} />
      )}

      {showAddProductiveModal && (
        <AddSiteModal
          onAdd={handleMarkProductive}
          onClose={() => setShowAddProductiveModal(false)}
          title="Add Productive Site"
          submitLabel="Mark Productive"
        />
      )}
    </div>
  );
}

export default Blocklist;
