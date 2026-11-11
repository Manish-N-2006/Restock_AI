import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Cpu, Play, CheckCircle2, ArrowRight, ShieldAlert, Sparkles, Truck } from 'lucide-react';
import { api } from '../api';

export const Workflow: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [sku, setSku] = useState(searchParams.get('sku') || '');
  const [store, setStore] = useState(searchParams.get('store') || '');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);

  useEffect(() => {
    const skuParam = searchParams.get('sku');
    const storeParam = searchParams.get('store');
    if (skuParam) setSku(skuParam);
    if (storeParam) setStore(storeParam);
  }, [searchParams]);

  const handleRunAnalysis = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!sku.trim()) return;

    setIsAnalyzing(true);
    setAnalysisResult(null);

    // Simulate agent orchestration workflow
    setTimeout(() => {
      setAnalysisResult({
        sku_id: sku || 'YOG-001',
        source_store: store || 'STORE_A',
        recommendation: 'INTER_STORE_TRANSFER',
        target_store: 'STORE_B',
        predicted_recovery: 12000,
        risk_score: 88,
        reasoning:
          'High demand at Store B with 94% sell-through probability before 4-day expiry threshold.',
      });
      setIsAnalyzing(false);
    }, 800);
  };

  const handlePreset = (presetSku: string, presetStore: string) => {
    setSku(presetSku);
    setStore(presetStore);
  };

  return (
    <div className="space-y-6 flex flex-col min-h-[calc(100vh-100px)] selection:bg-emerald-100">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-emerald-50/80 p-6 rounded-2xl border border-emerald-200/80 shadow-xs flex-shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-emerald-200/80 text-emerald-900 shadow-xs">
              <Cpu className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Workflow Cockpit
            </h1>
          </div>
          <p className="text-xs font-semibold text-slate-600 mt-1">
            End-to-end recovery orchestration agent triggering deterministic calculations and channel execution.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-emerald-900 bg-emerald-100/80 px-3.5 py-1.5 rounded-xl border border-emerald-300/60 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-emerald-600" />
            Agent Pipeline Ready
          </span>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Target Selection Form */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 flex flex-col justify-between space-y-6">
          <div className="space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-xs font-extrabold text-slate-800 tracking-wider uppercase">
                Target Selection
              </h2>
              <span className="text-[10px] font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full">
                Step 1
              </span>
            </div>

            <form onSubmit={handleRunAnalysis} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Target SKU
                </label>
                <input
                  type="text"
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  placeholder="e.g. YOG-001"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Source Store
                </label>
                <input
                  type="text"
                  value={store}
                  onChange={(e) => setStore(e.target.value)}
                  placeholder="e.g. STORE_A"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                />
              </div>

              <button
                type="submit"
                disabled={isAnalyzing || !sku}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-200 text-white font-extrabold text-xs rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center justify-center gap-2 mt-2"
              >
                {isAnalyzing ? (
                  <span>Running AI Analysis...</span>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Run AI Analysis</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Preset Buttons */}
          <div className="pt-4 border-t border-slate-100">
            <p className="text-[10px] font-bold uppercase text-slate-400 mb-2">
              Quick Test Presets:
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handlePreset('YOG-001', 'STORE_A')}
                className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-xs font-mono font-bold transition-all"
              >
                YOG-001
              </button>
              <button
                type="button"
                onClick={() => handlePreset('MILK-204', 'STORE_C')}
                className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-xs font-mono font-bold transition-all"
              >
                MILK-204
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Orchestration Pipeline Output */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-6">
              <h2 className="text-xs font-extrabold text-slate-800 tracking-wider uppercase">
                Orchestration Decision Output
              </h2>
              <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full">
                Step 2
              </span>
            </div>

            {isAnalyzing ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-3 text-slate-400">
                <div className="animate-pulse flex items-center space-x-2">
                  <span className="h-3 w-3 bg-emerald-500 rounded-full"></span>
                  <span className="h-3 w-3 bg-emerald-500 rounded-full"></span>
                  <span className="h-3 w-3 bg-emerald-500 rounded-full"></span>
                </div>
                <p className="text-xs font-bold text-slate-500">
                  Evaluating economic channels and deterministic margins...
                </p>
              </div>
            ) : analysisResult ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <div className="p-5 rounded-2xl bg-amber-50/80 border border-amber-200/80 flex justify-between items-center">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">
                      Evaluated Target
                    </span>
                    <h3 className="text-base font-extrabold text-slate-900 mt-0.5">
                      {analysisResult.sku_id} ({analysisResult.source_store})
                    </h3>
                  </div>
                  <span className="px-3 py-1 bg-emerald-600 text-white font-mono font-bold text-xs rounded-full shadow-xs">
                    Risk Score: {analysisResult.risk_score}/100
                  </span>
                </div>

                <div className="space-y-3 bg-slate-50 p-5 rounded-2xl border border-slate-100">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Recommended Action Strategy
                  </h4>
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-800 font-extrabold text-xs rounded-lg border border-emerald-300">
                      {analysisResult.recommendation}
                    </span>
                    <ArrowRight className="w-4 h-4 text-slate-400" />
                    <span className="text-xs font-bold text-slate-800">
                      Destination: {analysisResult.target_store}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 font-medium leading-relaxed mt-2">
                    {analysisResult.reasoning}
                  </p>
                </div>

                <div className="flex justify-between items-center p-4 bg-emerald-50 rounded-xl border border-emerald-200">
                  <div>
                    <p className="text-[10px] font-bold uppercase text-emerald-800">
                      Estimated Net Value Recovered
                    </p>
                    <p className="text-xl font-black text-emerald-900">
                      ₹{analysisResult.predicted_recovery.toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => navigate('/transfers')}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-extrabold rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center gap-2"
                  >
                    <span>Execute Transfer Manifest</span>
                    <Truck className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ) : (
              <div className="py-20 text-center text-xs text-slate-400 font-bold uppercase tracking-widest">
                Enter target parameters or click a preset to launch workflow analysis.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};