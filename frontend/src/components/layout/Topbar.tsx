import React, { useState, useEffect } from 'react';
import { Activity, Clock, LogOut, ShieldCheck } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const Topbar: React.FC = () => {
  const [time, setTime] = useState<Date>(new Date());
  const location = useLocation();
  const navigate = useNavigate();
  const { session, logout } = useAuth();

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

        <div className="flex items-center space-x-2 pl-2 border-l border-border">
          {session && (
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold uppercase tracking-wider">
              <ShieldCheck className="h-3 w-3" />
              {session.role}
            </span>
          )}
          <button
            type="button"
            onClick={async () => {
              await logout();
              navigate('/login', { replace: true });
            }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
            title="Sign out of demo session"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};
