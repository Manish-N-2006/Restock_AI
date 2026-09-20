import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { WorkflowResult, IntegratedRecommendationResponse } from '../types';
import { Play, Activity, Package, Loader2, ArrowRight, Code, TerminalSquare, CheckCircle2 } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { RecoveryDecisionModal } from '../components/decisions/RecoveryDecisionModal';
import { StatusBadge } from '../components/ui/StatusBadge';

export const Workflow: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [sku, setSku] = useState(searchParams.get('sku') || '');
  const [store, setStore] = useState(searchParams.get('store') || '');
  
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<IntegratedRecommendationResponse | null>(null);
  
  const [isExecuting, setIsExecuting] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [showRawJson, setShowRawJson] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  const navigate = useNavigate();

  // Auto-analyze if URL params are present
  useEffect(() => {
    if (sku && store && !analysisResult && !isAnalyzing && !error) {
      handleAnalyze();
    }
    // eslint-disable-next-line
  }, []);

  const handleAnalyze = async () => {
    if (!sku || !store) return;
    
    setIsAnalyzing(true);
    setAnalysisResult(null);
    setWorkflowResult(null);
    setError(null);
    setShowRawJson(false);
    
    try {
      const data = await api.analyzeWorkflow(sku, store);
      setAnalysisResult(data);
    } catch (err: any) {
      setError(err.message || "Engine analysis failed. Please verify SKU and Store ID.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExecute = async (partnerId?: string) => {
    if (!sku || !store) return;
    
    setIsExecuting(true);
    setError(null);
    
    try {
      const data = await api.executeWorkflow(sku, store, partnerId);
      setWorkflowResult(data);
      setIsModalOpen(false); // Close the modal upon success
    } catch (err: any) {
      setError(err.message || "Failed to execute recovery workflow.");
      setIsModalOpen(false); // Close modal to show error
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-10">
      
      {/* Header */}
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight flex items-center space-x-2">
            <TerminalSquare className="h-5 w-5 text-semantic-blue" />
            <span>Workflow Cockpit</span>
          </h1>
          <p className="text-text-secondary mt-1 text-sm uppercase tracking-widest font-mono">End-to-End Recovery Orchestration</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Telemetry & Input */}
        <div className="space-y-6">
          <div className="bg-panel border border-border rounded shadow-sm overflow-hidden">
            <div className="px-5 py-3 bg-[#14161a] border-b border-border">
              <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest">Target Selection</h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-2">Target SKU</label>
                <input 
                  type="text" 
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  placeholder="e.g. YOG-001"
                  className="w-full px-4 py-2.5 bg-card border border-border text-text-primary font-mono text-sm rounded focus:outline-none focus:border-semantic-blue transition-colors placeholder-text-muted"
                />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-2">Source Store</label>
                <input 
                  type="text" 
                  value={store}
                  onChange={(e) => setStore(e.target.value)}
                  placeholder="e.g. STORE_A"
                  className="w-full px-4 py-2.5 bg-card border border-border text-text-primary font-mono text-sm rounded focus:outline-none focus:border-semantic-blue transition-colors placeholder-text-muted"
                />
              </div>
              <button 
                onClick={handleAnalyze}
                disabled={isAnalyzing || !sku || !store}
                className="w-full flex justify-center items-center px-4 py-3 bg-card border border-border hover:border-semantic-blue text-semantic-blue font-bold text-xs uppercase tracking-widest rounded transition-colors disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analyzing...</>
                ) : (
                  <><Activity className="h-4 w-4 mr-2" /> Run AI Analysis</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Middle/Right Column: Execution Engine Output */}
        <div className="lg:col-span-2 space-y-6">
          
          {error && (
            <div className="bg-[#2D1612] border border-semantic-red/30 rounded p-4 flex items-start space-x-3">
              <p className="text-sm font-mono text-semantic-red">
                <span className="font-bold">FATAL:</span> {error}
              </p>
            </div>
          )}

          {/* Analysis View */}
          {analysisResult && !workflowResult && (
            <div className="bg-panel border border-border rounded shadow-sm overflow-hidden flex flex-col">
              <div className="px-5 py-3 bg-[#14161a] border-b border-border flex justify-between items-center">
                <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest flex items-center">
                  <Activity className="h-4 w-4 text-semantic-green mr-2" /> Engine Intelligence
                </h2>
                <button 
                  onClick={() => setShowRawJson(!showRawJson)}
                  className="flex items-center text-[10px] uppercase font-bold text-text-muted hover:text-text-primary transition-colors tracking-widest"
                >
                  <Code className="h-3 w-3 mr-1" /> Raw Payload
                </button>
              </div>
              
              {showRawJson ? (
                <div className="p-0 overflow-x-auto bg-[#0a0c0f]">
                  <pre className="text-xs font-mono text-semantic-green p-5">
                    {JSON.stringify(analysisResult, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="p-8 flex flex-col items-center justify-center text-center space-y-6 min-h-[300px]">
                  <div>
                    <h3 className="text-sm font-bold text-text-primary tracking-tight uppercase">AI Decision Computed</h3>
                    <p className="text-text-secondary mt-2 text-sm max-w-lg leading-relaxed">
                      The execution engine has analyzed realtime demand parameters and live logistics quotes to determine the optimal recovery path for <span className="font-mono text-semantic-blue">{sku}</span> at <span className="font-mono text-text-primary">{store}</span>.
                    </p>
                  </div>
                  
                  <div className="p-4 bg-card border border-border rounded-lg inline-block">
                    <p className="text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-1">Recommended Action</p>
                    <p className="text-2xl font-bold text-semantic-green uppercase">{analysisResult.decision.selected_action}</p>
                    <p className="text-sm font-mono text-text-primary mt-2">Net Recovery: ₹{(analysisResult as any).logistics?.logistics_adjusted_net_recovery?.toLocaleString() ?? 0}</p>
                  </div>

                  <button 
                    onClick={() => setIsModalOpen(true)}
                    className="flex items-center px-8 py-3 bg-semantic-blue text-white font-bold text-sm uppercase tracking-wider rounded hover:bg-semantic-blue/90 transition-colors shadow-lg shadow-semantic-blue/20"
                  >
                    <Play className="h-4 w-4 mr-2" /> Launch Execution Modal
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Workflow Result View */}
          {workflowResult && (
            <div className="bg-panel border border-border rounded shadow-sm overflow-hidden flex flex-col border-l-4 border-l-semantic-green">
              <div className="px-5 py-3 bg-[#14161a] border-b border-border flex justify-between items-center">
                <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest flex items-center">
                  <CheckCircle2 className="h-4 w-4 text-semantic-green mr-2" /> Execution Complete
                </h2>
                <StatusBadge status="COMPLETED" />
              </div>
              <div className="p-8 flex flex-col items-center justify-center text-center space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-text-primary tracking-tight">Recovery Operation Dispatched</h3>
                  <p className="text-text-secondary mt-2 text-sm max-w-lg leading-relaxed">
                    The workflow has been fully executed. A new transfer instruction has been dispatched to the logistics partner.
                  </p>
                </div>

                {workflowResult.transfer && (
                  <div className="w-full max-w-md bg-card border border-border rounded-lg p-5">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-2">
                        <Package className="h-5 w-5 text-semantic-blue" />
                        <span className="text-sm font-bold text-text-primary uppercase tracking-wider">Transfer ID</span>
                      </div>
                      <span className="font-mono text-sm font-bold text-text-primary">{workflowResult.transfer.transfer_id}</span>
                    </div>
                    
                    <button 
                      onClick={() => navigate(`/transfers/${workflowResult.transfer?.transfer_id}`)}
                      className="w-full flex items-center justify-center px-4 py-2 border border-border text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors rounded text-sm font-medium tracking-wide uppercase"
                    >
                      View Transfer Telemetry <ArrowRight className="h-4 w-4 ml-2" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Recovery Decision Modal Mount */}
      <RecoveryDecisionModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        recommendation={analysisResult}
        onExecute={handleExecute}
        isExecuting={isExecuting}
      />
      
    </div>
  );
};
