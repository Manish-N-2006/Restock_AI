import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TerminalSquare, Server, Database, CheckCircle2, ShieldAlert } from 'lucide-react';

const STORES = [
  { id: 'STORE_A', name: 'Delhi Hub', region: 'North' },
  { id: 'STORE_B', name: 'Mumbai Central', region: 'West' },
  { id: 'STORE_C', name: 'Bangalore Primary', region: 'South' },
  { id: 'STORE_D', name: 'Kolkata East', region: 'East' }
];

export const SimulationSetup: React.FC = () => {
  const [isInitializing, setIsInitializing] = useState(false);
  const [progress, setProgress] = useState<Record<string, number>>({});
  const [isComplete, setIsComplete] = useState(false);
  const navigate = useNavigate();

  const handleStart = () => {
    setIsInitializing(true);
    
    // Initialize progress to 0
    const initialProgress = STORES.reduce((acc, store) => {
      acc[store.id] = 0;
      return acc;
    }, {} as Record<string, number>);
    setProgress(initialProgress);

    // Simulate downloading data with randomized intervals for each store
    STORES.forEach(store => {
      let currentProgress = 0;
      const interval = setInterval(() => {
        currentProgress += Math.floor(Math.random() * 15) + 5;
        if (currentProgress >= 100) {
          currentProgress = 100;
          clearInterval(interval);
        }
        setProgress(prev => {
          const updated = { ...prev, [store.id]: currentProgress };
          
          // Check if all are 100
          if (Object.values(updated).every(p => p === 100)) {
            setTimeout(() => {
              setIsComplete(true);
              sessionStorage.setItem('restock_simulation_initialized', 'true');
              setTimeout(() => {
                navigate('/');
              }, 1500);
            }, 500);
          }
          
          return updated;
        });
      }, Math.random() * 300 + 200); // random interval between 200-500ms
    });
  };

  return (
    <div className="min-h-screen bg-[#0a0c0f] flex items-center justify-center p-6 font-mono text-text-primary selection:bg-semantic-blue/30">
      
      <div className="w-full max-w-4xl">
        
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center p-3 bg-semantic-blue/10 border border-semantic-blue/30 rounded-xl mb-6">
            <TerminalSquare className="h-10 w-10 text-semantic-blue" />
          </div>
          <h1 className="text-4xl font-bold tracking-tighter text-white mb-3">ReStockAI Operations OS</h1>
          <p className="text-text-secondary uppercase tracking-widest text-sm">Secure Command Center Boot Sequence</p>
        </div>

        {/* Console Box */}
        <div className="bg-panel border border-border rounded-xl shadow-2xl overflow-hidden relative">
          
          {/* Mac style header */}
          <div className="h-10 bg-[#14161a] border-b border-border flex items-center px-4">
            <div className="flex space-x-2">
              <div className="h-3 w-3 rounded-full bg-semantic-red/80"></div>
              <div className="h-3 w-3 rounded-full bg-semantic-amber/80"></div>
              <div className="h-3 w-3 rounded-full bg-semantic-green/80"></div>
            </div>
            <div className="mx-auto text-xs text-text-muted font-bold tracking-widest uppercase">sys_init.sh</div>
          </div>

          <div className="p-8">
            {!isInitializing ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-8">
                <ShieldAlert className="h-16 w-16 text-semantic-amber opacity-50" />
                <div className="text-center">
                  <h2 className="text-xl text-white font-bold mb-2">Network Telemetry Offline</h2>
                  <p className="text-text-secondary text-sm max-w-md leading-relaxed">
                    The operations dashboard requires live inventory state from regional distribution centers before it can power up the AI engine.
                  </p>
                </div>
                <button 
                  onClick={handleStart}
                  className="px-8 py-4 bg-semantic-blue text-white font-bold tracking-widest uppercase text-sm rounded shadow-lg shadow-semantic-blue/20 hover:bg-semantic-blue/90 hover:scale-105 transition-all cursor-pointer"
                >
                  Sync Store Telemetry Data
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between mb-8 pb-4 border-b border-border border-dashed">
                  <div className="flex items-center space-x-3 text-semantic-blue animate-pulse">
                    <Database className="h-5 w-5" />
                    <span className="text-sm font-bold uppercase tracking-widest">Establishing secure channels...</span>
                  </div>
                  <div className="text-xs text-text-muted">NODE: ASIA-SOUTH1</div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {STORES.map((store) => {
                    const p = progress[store.id] || 0;
                    const isDone = p === 100;
                    
                    return (
                      <div key={store.id} className="bg-[#14161a] border border-border rounded p-5">
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <div className="flex items-center space-x-2 mb-1">
                              <Server className={`h-4 w-4 ${isDone ? 'text-semantic-green' : 'text-text-secondary'}`} />
                              <span className="text-sm font-bold text-white tracking-wider">{store.id}</span>
                            </div>
                            <span className="text-xs text-text-muted uppercase tracking-widest">{store.name}</span>
                          </div>
                          {isDone ? (
                            <CheckCircle2 className="h-5 w-5 text-semantic-green" />
                          ) : (
                            <span className="text-xs font-bold text-semantic-amber">{p}%</span>
                          )}
                        </div>
                        
                        {/* Progress Bar */}
                        <div className="h-2 w-full bg-[#0a0c0f] rounded-full overflow-hidden border border-border">
                          <div 
                            className={`h-full transition-all duration-300 ease-out ${isDone ? 'bg-semantic-green' : 'bg-semantic-blue'}`}
                            style={{ width: `${p}%` }}
                          />
                        </div>
                        <div className="mt-2 text-[10px] text-text-muted flex justify-between uppercase">
                          <span>{isDone ? 'SYNC_COMPLETE' : 'FETCHING_INVENTORY_DELTA...'}</span>
                          <span>{p === 100 ? '0ms' : `${Math.floor(Math.random() * 50) + 12}ms`}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {isComplete && (
                  <div className="mt-8 pt-6 border-t border-border flex flex-col items-center justify-center animate-fade-in text-semantic-green">
                    <span className="text-sm font-bold uppercase tracking-widest mb-2">System Ready</span>
                    <span className="text-xs text-text-muted">Redirecting to Operations Dashboard...</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
