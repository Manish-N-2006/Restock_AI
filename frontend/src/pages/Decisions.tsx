import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GitBranch, Truck, Tag, RefreshCw, ArrowRight, ShieldCheck, AlertTriangle } from 'lucide-react';
import { api } from '../api';

interface RecoveryOption {
  action: 'TRANSFER' | 'DISCOUNT' | 'BUNDLE' | 'PROMOTE' | 'RETURN' | 'DISPOSE';
  recommendedTargetStore?: string;
  logisticsCost: number;
  estimatedRecovery: number;
  netRecovery: number;
  logisticsPartner?: string;
  riskScore: number;
  description: string;
}

// Fallback demo decision evaluation when no item is pre-selected
const sampleDecisionData = {
  sku_id: 'YOG-001',
  productName: 'Organic Greek Yogurt 500g',
  sourceStore: 'STORE_A (Seattle)',
  daysToExpiry: 4,
  atRiskQty: 120,
  atRiskValue: 14400,
  options: [
    {
      action: 'TRANSFER',
      recommendedTargetStore: 'STORE_B (Bellevue)',
      logisticsCost: 800,
      estimatedRecovery: 12800,
      netRecovery: 12000,
      logisticsPartner: 'ColdChain Express',
      riskScore: 12,
      description: 'Transfer 120 units to Store B. High demand detected with 94% predicted sell-through before expiry.',
    },
    {
      action: 'DISCOUNT',
      recommendedTargetStore: 'STORE_A (Local)',
      logisticsCost: 0,
      estimatedRecovery: 7200,
      netRecovery: 7200,
      logisticsPartner: 'In-Store',
      riskScore: 28,
      description: 'Apply 50% markdown locally. Quick recovery, but forfeits 50% of original stock value.',
    },
    {
      action: 'RETURN',
      recommendedTargetStore: 'SUPPLIER_DC',
      logisticsCost: 1500,
      estimatedRecovery: 5000,
      netRecovery: 3500,
      logisticsPartner: 'Vendor Logistics',
      riskScore: 45,
      description: 'Vendor buyback credit agreement. Subject to 30% restocking fee.',
    },
    {
      action: 'DISPOSE',
      recommendedTargetStore: 'N/A',
      logisticsCost: 200,
      estimatedRecovery: 0,
      netRecovery: -200,
      logisticsPartner: 'Local Waste Mgmt',
      riskScore: 100,
      description: 'Complete inventory write-off. Incurs disposal fee.',
    },
  ] as RecoveryOption[],
};

export const Decisions: React.FC = () => {
  const [executingAction, setExecutingAction] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string>('');

  const handleExecute = (action: string) => {
    setExecutingAction(action);
    setTimeout(() => {
      setExecutingAction(null);
      setSuccessMessage(`Successfully executed ${action} strategy for SKU YOG-001!`);
    }, 1000);
  };

  return (
    <div className="space-y-8 selection:bg-emerald-100">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-emerald-100 text-emerald-700">
              <GitBranch className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Recovery Decision Engine
            </h1>
          </div>
          <p className="text-xs font-semibold text-slate-500 mt-1">
            Economic trade-off analysis comparing net value recovery across all available channels.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-500 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
            Evaluating SKU: <strong className="text-slate-900">{sampleDecisionData.sku_id}</strong>
          </span>
        </div>
      </div>

      {/* Target Item Focus Card */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-md flex flex-wrap items-center justify-between gap-6">
        <div>
          <span className="text-[10px] font-extrabold uppercase tracking-widest text-emerald-400 bg-emerald-950/80 border border-emerald-800 px-2.5 py-1 rounded-full">
            Active Risk Assessment
          </span>
          <h2 className="text-lg font-bold mt-2">
            {sampleDecisionData.productName} ({sampleDecisionData.sku_id})
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Source: <strong className="text-slate-200">{sampleDecisionData.sourceStore}</strong> | Days Left: <strong className="text-amber-400">{sampleDecisionData.daysToExpiry} Days</strong>
          </p>
        </div>

        <div className="flex items-center gap-6 border-l border-slate-800 pl-6">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">At-Risk Quantity</p>
            <p className="text-xl font-black text-white">{sampleDecisionData.atRiskQty} <span className="text-xs text-slate-400 font-normal">units</span></p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Risk Value</p>
            <p className="text-xl font-black text-amber-400">₹{sampleDecisionData.atRiskValue.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-bold flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage('')} className="text-emerald-900 font-extrabold">✕</button>
        </motion.div>
      )}

      {/* Recovery Channels Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {sampleDecisionData.options.map((opt) => {
          const isBest = opt.action === 'TRANSFER';

          return (
            <motion.div
              key={opt.action}
              whileHover={{ y: -4 }}
              className={`rounded-2xl p-6 border shadow-xs transition-all flex flex-col justify-between relative bg-white ${
                isBest ? 'border-emerald-500 ring-2 ring-emerald-500/20' : 'border-slate-200/80'
              }`}
            >
              {isBest && (
                <span className="absolute -top-3 left-4 bg-emerald-600 text-white text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full shadow-sm">
                  ⭐ AI Recommended Option
                </span>
              )}

              <div>
                <div className="flex justify-between items-center mb-3">
                  <span className="text-xs font-black uppercase tracking-wider text-slate-900">
                    {opt.action}
                  </span>
                  <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded-full ${
                    opt.netRecovery > 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                  }`}>
                    Net: ₹{opt.netRecovery.toLocaleString()}
                  </span>
                </div>

                <p className="text-xs text-slate-500 font-medium leading-relaxed mb-4">
                  {opt.description}
                </p>

                <div className="space-y-2 bg-slate-50 p-3 rounded-xl border border-slate-100 text-[11px] font-mono text-slate-600 mb-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Target:</span>
                    <span className="font-bold text-slate-800">{opt.recommendedTargetStore}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Logistics Cost:</span>
                    <span className="font-bold text-red-600">-₹{opt.logisticsCost}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Partner:</span>
                    <span className="font-bold text-slate-800">{opt.logisticsPartner}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => handleExecute(opt.action)}
                disabled={executingAction === opt.action}
                className={`w-full py-2.5 rounded-xl font-extrabold text-xs transition-all flex items-center justify-center gap-2 ${
                  isBest
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-200'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
                }`}
              >
                {executingAction === opt.action ? (
                  <span>Executing Engine...</span>
                ) : (
                  <>
                    <span>Execute {opt.action}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};