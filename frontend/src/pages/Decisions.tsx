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
    const loadData = async () => {
      try {
        const data = await api.getAllDecisions();
        setDecisions(data);
      } catch (error) {
        console.error("Failed to load decisions:", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center text-slate-500">Evaluating recovery decisions...</div>;
  }

  if (decisions.length === 0) {
    return <div className="p-8 text-center text-slate-500 bg-white rounded-lg border border-slate-200">No decisions available.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Recovery Decisions</h1>
          <p className="text-slate-500 mt-1">Recommended actions to maximize recovered value for at-risk inventory.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {decisions.map((decision, idx) => (
          <div key={`${decision.sku}-${decision.source_store_id}-${idx}`} className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden flex flex-col">
            <div className="p-5 border-b border-slate-200 flex justify-between items-start">
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-lg font-bold text-slate-900">{decision.sku}</h2>
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">AT RISK</span>
                </div>
                <p className="text-sm text-slate-500 mt-1">Store: {decision.source_store_id} &bull; {decision.at_risk_quantity} units</p>
              </div>
              <button 
                onClick={() => navigate(`/workflow?sku=${decision.sku}&store=${decision.source_store_id}`)}
                className="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-md hover:bg-slate-800 transition-colors"
              >
                Execute
              </button>
            </div>
            
            <div className="p-5 bg-slate-50 border-b border-slate-200">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Recommended Action</h3>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2 text-base font-bold text-slate-900">
                      <span>{decision.recommended_action.action_type}</span>
                      {decision.recommended_action.destination_store_id && (
                        <>
                          <ArrowRight className="h-4 w-4 text-slate-400" />
                          <span>{decision.recommended_action.destination_store_id}</span>
                        </>
                      )}
                    </div>
                    <p className="text-sm text-slate-600">Expected Net Recovery: <span className="font-semibold text-green-600">₹{decision.recommended_action.expected_net_recovery.toLocaleString()}</span></p>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-5 flex-1">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Alternative Actions</h3>
              <div className="space-y-3">
                {decision.alternative_actions.map((alt, i) => (
                  <div key={i} className="flex justify-between items-center text-sm">
                    <span className="text-slate-700">{alt.action_type}</span>
                    <span className="font-medium text-slate-900">₹{alt.expected_net_recovery.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
