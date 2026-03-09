import React from 'react';

interface BlockedSiteCardProps {
  item: {
    id: string;
    domain: string;
    reason?: string | null;
    added_at?: string;
    created_at?: string;
  };
  onRemove: (domain: string) => void | Promise<void>;
}

function BlockedSiteCard({ item, onRemove }: BlockedSiteCardProps) {
  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

  const addedDate = item.added_at || item.created_at;

  const faviconUrl = `https://www.google.com/s2/favicons?domain=${item.domain}&sz=32`;

  return (
    <div className="bg-white rounded-lg shadow p-4 flex items-center justify-between hover:shadow-md transition">
      <div className="flex items-center">
        <img
          src={faviconUrl}
          alt={item.domain}
          className="w-8 h-8 rounded mr-4"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />

        <div>
          <p className="font-semibold text-gray-900">{item.domain}</p>
          <div className="flex items-center gap-3 mt-1">
            {addedDate && (
              <span className="text-xs text-gray-500">
                Added {formatDate(addedDate)}
              </span>
            )}
            {item.reason && (
              <span className="text-xs text-gray-400">• {item.reason}</span>
            )}
          </div>
        </div>
      </div>

      <button
        onClick={() => onRemove(item.domain)}
        className="text-red-500 hover:text-red-700 hover:bg-red-50 p-2 rounded-lg transition"
        title="Remove from blocklist"
      >
        Remove
      </button>
    </div>
  );
}

export default BlockedSiteCard;