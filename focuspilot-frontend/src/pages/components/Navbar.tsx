import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { agentAPI } from '../../api/client';

export { default } from '../../components/Navbar';

function NotificationBell() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    loadCount();
    const interval = setInterval(loadCount, 30_000);
    return () => clearInterval(interval);
  }, []);

  const loadCount = async () => {
    try {
      const res = await agentAPI.getNotifications();
      setCount(res.data.unread_count || 0);
    } catch {}
  };

  return (
    <Link to="/agent" className="relative">
      <span className="text-sm font-medium text-gray-700">Alerts</span>
      {count > 0 && (
        <span className="absolute -top-1 -right-1 bg-red-500 text-white
          text-xs rounded-full w-4 h-4 flex items-center justify-center
          font-bold">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </Link>
  );
}

// Add to Navbar JSX:
// <NotificationBell />
