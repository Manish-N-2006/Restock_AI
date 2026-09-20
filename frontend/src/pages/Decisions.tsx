import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { Decision } from '../types';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Decisions: React.FC = () => {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const data = await api.getAllDecisions();
        if (mounted) setDecisions(data);
      } catch (error) {
        console.error("Failed to load decisions:", error);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-text-muted">
        <div className="animate-pulse flex items-center space-x-2">
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
        </div>
      </div>
    );
  }

  if (decisions.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-text-muted">
        <div className="text-center">
          <p className="text-sm font-mono tracking-widest uppercase mb-2">No Active Decisions</p>
          <p className="text-xs">All inventory risks have been mitigated or no risks are present.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">Recovery Decisions</h1>
          <p className="text-sm text-text-secondary mt-1">Recommended actions to maximize recovered value for at-risk inventory.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {decisions.map((decision, idx) => {
          // Find the selected action object to display full details
          const selectedActionObj = decision.actions.find(a => a.action === decision.selected_action);
          
          return (
            <div key={`${decision.sku_id}-${decision.store_id}-${idx}`} className="bg-panel border border-border rounded-lg shadow-sm flex flex-col max-h-[500px]">
              <div className="px-5 py-4 border-b border-border bg-[#14161a] rounded-t-lg flex justify-between items-start">
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-sm font-mono font-bold text-text-primary">{decision.sku_id}</h2>
                    <span className="px-1.5 py-0.5 rounded border text-[10px] font-bold bg-semantic-red/10 text-semantic-red border-semantic-red/20 uppercase tracking-widest">
                      AT RISK
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1 tracking-wide">
                    STORE: {decision.store_id} &bull; {decision.recommended_quantity} UNITS
                  </p>
                </div>
                <button 
                  onClick={() => navigate(`/workflow?sku=${decision.sku_id}&store=${decision.store_id}`)}
                  className="px-3 py-1.5 bg-semantic-blue/10 border border-semantic-blue/30 text-semantic-blue text-[11px] uppercase tracking-widest font-bold rounded hover:bg-semantic-blue/20 transition-colors"
                >
                  Execute
                </button>
              </div>
              
              <div className="p-5 border-b border-border">
                <h3 className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-3">Recommended Action</h3>
                <div className="flex items-center space-x-3">
                  <div className="h-10 w-10 rounded bg-semantic-green/10 flex items-center justify-center border border-semantic-green/20">
                    <CheckCircle2 className="h-5 w-5 text-semantic-green" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2 text-sm font-bold text-text-primary font-mono uppercase">
                      <span>{decision.selected_action}</span>
                      {decision.selected_destination_store_id && (
                        <>
                          <ArrowRight className="h-3 w-3 text-text-muted" />
                          <span>{decision.selected_destination_store_id}</span>
                        </>
                      )}
                    </div>
                    <p className="text-xs text-text-secondary mt-1">
                      Expected Net Recovery: <span className="font-mono text-semantic-green font-bold">₹{decision.expected_net_recovery.toLocaleString()}</span>
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-5 flex-1 overflow-y-auto">
                <h3 className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-3">Alternative Actions</h3>
                <div className="space-y-3">
                  {decision.actions.filter(a => a.action !== decision.selected_action).map((alt, i) => (
                    <div key={i} className="flex justify-between items-center text-xs border-b border-border/50 pb-2 last:border-0 last:pb-0">
                      <span className="text-text-secondary font-mono">{alt.action}</span>
                      <span className="font-mono text-text-primary">
                        {alt.expected_net_recovery > 0 ? `₹${alt.expected_net_recovery.toLocaleString()}` : 'Not Viable'}
                      </span>
                    </div>
                  ))}
                  {decision.actions.length <= 1 && (
                    <p className="text-xs text-text-muted">No viable alternative actions available.</p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

