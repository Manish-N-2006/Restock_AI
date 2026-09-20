import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertTriangle,
  GitBranch,
  Package,
  Activity,
  History,
  Bot,
  Workflow,
  Store,
} from 'lucide-react';
import { api } from '../../api';
import { RiskItem } from '../../types';

const navItems = [
  { name: 'Overview', to: '/', icon: LayoutDashboard },
  { name: 'Risk Network', to: '/risk', icon: AlertTriangle },
  { name: 'Recovery Decisions', to: '/decisions', icon: GitBranch },
  { name: 'Transfers', to: '/transfers', icon: Package },
  { name: 'Outcomes', to: '/outcomes', icon: Activity },
  { name: 'Historical Intelligence', to: '/history', icon: History },
  { name: 'AI Assistant', to: '/agent', icon: Bot },
  { name: 'Recovery Workflow', to: '/workflow', icon: Workflow },
];

export const Sidebar: React.FC = () => {
  const [riskItems, setRiskItems] = useState<RiskItem[]>([]);

  useEffect(() => {
    let mounted = true;
    api
      .getRiskItems()
      .then((items) => {
        if (mounted) setRiskItems(items);
      })
      .catch(console.error);
    return () => {
      mounted = false;
    };
  }, []);

  const storeMap = new Map<
    string,
    { count: number; maxScore: number; critical: boolean }
  >();

  riskItems.forEach((item) => {
    const current = storeMap.get(item.store_id) || {
      count: 0,
      maxScore: 0,
      critical: false,
    };
    current.count += item.at_risk_quantity;
    current.maxScore = Math.max(current.maxScore, item.risk_score);
    if (item.risk_level === 'CRITICAL') {
      current.critical = true;
    }
    storeMap.set(item.store_id, current);
  });

  const stores = Array.from(storeMap.entries()).map(([name, data]) => ({
    name,
    ...data,
  }));

  return (
    <aside className="w-60 bg-white border-r border-slate-200/80 h-screen flex flex-col flex-shrink-0 shadow-xs selection:bg-emerald-100">
      {/* Brand Header */}
      <div className="px-5 py-5 border-b border-slate-100 flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-emerald-500 flex items-center justify-center shadow-md shadow-emerald-200">
          <span className="text-white font-black text-lg">⚡</span>
        </div>
        <div>
          <h1 className="text-base font-extrabold tracking-tight text-slate-900 leading-tight">
            ReStock<span className="text-emerald-600">AI</span>
          </h1>
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">
            Recovery Ops
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-5 px-3 space-y-6">
        {/* Navigation Section */}
        <div>
          <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-3 px-2">
            Navigation
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2.5 text-xs font-semibold rounded-xl transition-all duration-150 ${
                    isActive
                      ? 'bg-emerald-50/90 text-emerald-800 border-l-4 border-emerald-500 shadow-xs font-bold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-emerald-700 border-l-4 border-transparent'
                  }`
                }
              >
                <item.icon
                  className="mr-3 h-4 w-4 flex-shrink-0 transition-colors"
                  aria-hidden="true"
                />
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Store Network Section */}
        <div className="pt-4 border-t border-slate-100">
          <div className="flex items-center justify-between px-2 mb-3">
            <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Store className="w-3 h-3 text-slate-400" /> Store Network
            </div>
          </div>

          {stores.length === 0 ? (
            <div className="text-xs text-slate-400 bg-slate-50 p-3 rounded-xl border border-slate-100 text-center font-medium">
              No active store risk.
            </div>
          ) : (
            <div className="space-y-3 px-1">
              {stores.map((store) => {
                const scorePercent = Math.min(100, Math.max(5, store.maxScore));

                return (
                  <div
                    key={store.name}
                    className="p-2.5 rounded-xl bg-slate-50/80 border border-slate-100 hover:border-slate-200 transition-all"
                  >
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-xs font-bold text-slate-800">
                        {store.name}
                      </span>
                      <span
                        className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                          store.critical
                            ? 'bg-amber-100 text-amber-800 border-amber-300'
                            : 'bg-emerald-100 text-emerald-700 border-emerald-200'
                        }`}
                      >
                        {store.critical ? 'At Risk' : 'Stable'}
                      </span>
                    </div>

                    {/* Progress Bar Visualizer */}
                    <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          store.critical ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${scorePercent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};