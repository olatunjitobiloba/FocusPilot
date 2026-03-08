// src/components/SessionHistory.tsx
import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';

function SessionHistory() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await api.get('/sessions/history/detailed?limit=10');
      setSessions(response.data.sessions);
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading sessions...</div>;
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600">
        No sessions yet. Start your first focus session!
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {sessions.map((session) => (
        <SessionCard key={session.id} session={session} />
      ))}
    </div>
  );
}

function SessionCard({ session }: { session: any }) {
  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFocusColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-100';
    if (score >= 5) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 hover:shadow-md transition">
      <div className="flex justify-between items-start mb-2">
        <div>
          <p className="text-sm text-gray-600">{formatDate(session.start_time)}</p>
          <p className="text-lg font-semibold text-gray-900">
            {session.duration_minutes} minutes
          </p>
        </div>
        
        {session.focus_score && (
          <div className={`px-3 py-1 rounded-full ${getFocusColor(session.focus_score)}`}>
            <span className="font-semibold">{session.focus_score}/10</span>
          </div>
        )}
      </div>

      {session.distraction_count > 0 && (
        <div className="flex items-center text-sm text-gray-600 mt-2">
          <span>{session.distraction_count} distractions blocked</span>
          
          {session.top_distraction && (
            <span className="ml-2 text-gray-500">
              (mostly {session.top_distraction.domain})
            </span>
          )}
        </div>
      )}

      {session.distraction_count === 0 && (
        <div className="flex items-center text-sm text-green-600 mt-2">
          <span>Perfect focus - no distractions!</span>
        </div>
      )}
    </div>
  );
}

export default SessionHistory;
