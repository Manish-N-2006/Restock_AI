import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, GitBranch, Truck, Activity, History, Bot, Workflow, Package } from 'lucide-react';
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
    api.getRiskItems().then(items => {
      if (mounted) setRiskItems(items);
    }).catch(console.error);
    return () => { mounted = false; };
  }, []);

  const storeMap = new Map<string, { count: number; maxScore: number; critical: boolean }>();
  riskItems.forEach(item => {
    const current = storeMap.get(item.store_id) || { count: 0, maxScore: 0, critical: false };
    current.count += item.at_risk_quantity;
    current.maxScore = Math.max(current.maxScore, item.risk_score);
    if (item.risk_level === 'CRITICAL') {
      current.critical = true;
    }
    storeMap.set(item.store_id, current);
  });

  const stores = Array.from(storeMap.entries()).map(([name, data]) => ({ name, ...data }));

  return (
    <div className="w-[200px] bg-panel border-r border-border h-screen flex flex-col flex-shrink-0">
      <div className="flex-1 overflow-y-auto py-6 space-y-1 px-2">
        <div className="text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-3 ml-2">Navigation</div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center px-3 py-2 text-[13px] font-medium rounded transition-colors ${
                isActive
                  ? 'bg-card text-text-primary border-l-2 border-semantic-blue'
                  : 'text-text-secondary hover:bg-card hover:text-text-primary border-l-2 border-transparent'
              }`
            }
          >
            <item.icon
              className="mr-3 h-4 w-4 flex-shrink-0"
              aria-hidden="true"
            />
            {item.name}
          </NavLink>
        ))}

        <div className="mt-8 pt-6 border-t border-border">
          <div className="text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-4 ml-2">Store Network</div>
          {stores.length === 0 ? (
            <div className="text-[11px] text-text-muted ml-2">No active risk.</div>
          ) : (
            <div className="space-y-4 px-2">
              {stores.map(store => {
                const fillCount = Math.max(1, Math.ceil((store.maxScore / 100) * 10));
                const bars = Array.from({length: 10}).map((_, i) => i < fillCount ? '█' : '░').join('');
                return (
                  <div key={store.name} className="flex flex-col">
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="text-[11px] font-mono text-text-primary">{store.name}</span>
                      <span className={`text-[9px] uppercase font-semibold ${store.critical ? 'text-semantic-red' : 'text-text-secondary'}`}>
                        {store.critical ? 'Critical' : 'Stable'}
                      </span>
                    </div>
                    <div className={`text-[10px] font-mono leading-none tracking-widest ${store.critical ? 'text-semantic-red' : 'text-semantic-blue'}`}>
                      {bars}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
