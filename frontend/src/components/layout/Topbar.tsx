import React, { useState, useEffect } from 'react';
import { Activity, Clock } from 'lucide-react';
import { useLocation } from 'react-router-dom';

export const Topbar: React.FC = () => {
  const [time, setTime] = useState<Date>(new Date());
  const location = useLocation();

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const timeString = time.toLocaleTimeString('en-US');
  const dateString = time.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  const pathParts = location.pathname.split('/').filter(Boolean);
  const contextName = pathParts.length > 0 
    ? pathParts[0].charAt(0).toUpperCase() + pathParts[0].slice(1) 
    : 'Overview';

  return (
    <header className="h-[44px] bg-panel border-b border-border flex items-center justify-between px-4 flex-shrink-0 text-sm">
      <div className="flex items-center space-x-4">
        <div className="flex items-center font-bold tracking-wider text-text-primary">
          <span className="text-semantic-green mr-1.5">■</span> ReStockAI
        </div>
        <div className="text-text-muted">/</div>
        <div className="text-text-secondary uppercase tracking-widest text-xs font-semibold">
          {contextName}
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2 text-text-secondary">
          <Activity className="h-3.5 w-3.5 text-semantic-blue" />
          <span className="text-xs uppercase tracking-wider">Network Live</span>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-semantic-red opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-semantic-red"></span>
          </div>
          <span className="text-xs uppercase tracking-wider text-semantic-red font-semibold">Critical Active</span>
        </div>

        <div className="flex items-center space-x-2 text-text-secondary font-mono text-xs bg-page px-2.5 py-1 rounded border border-border">
          <Clock className="h-3.5 w-3.5" />
          <span>{dateString}</span>
          <span className="text-text-muted">|</span>
          <span className="text-text-primary">{timeString}</span>
        </div>
      </div>
    </header>
  );
};
