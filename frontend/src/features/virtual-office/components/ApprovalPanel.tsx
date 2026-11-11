import React, { useState } from 'react';
import { PendingApproval } from '../types/office';
import { ShieldCheck, ShieldAlert, Check, X, ArrowRight, Truck, DollarSign } from 'lucide-react';

interface ApprovalPanelProps {
  pendingApprovals: PendingApproval[];
  onDecision: (approvalId: string, decision: 'APPROVED' | 'REJECTED') => Promise<boolean>;
}

export const ApprovalPanel: React.FC<ApprovalPanelProps> = ({ pendingApprovals, onDecision }) => {
  const [submittingId, setSubmittingId] = useState<string | null>(null);

  const handleDecision = async (id: string, decision: 'APPROVED' | 'REJECTED') => {
    setSubmittingId(id);
    await onDecision(id, decision);
    setSubmittingId(null);
  };

  if (pendingApprovals.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-extrabold text-slate-900">Human Authorization Queue Clear</h4>
            <p className="text-[11px] font-medium text-slate-500">
              No inter-store transfers or high-risk actions awaiting manager sign-off.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-extrabold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 uppercase">
          0 Pending
        </span>
      </div>
    );
  }

  return (
    <div className="bg-amber-50/70 rounded-2xl border border-amber-300 shadow-md p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-amber-200 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-amber-500 text-white shadow-xs">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-black uppercase tracking-wider text-amber-950">
              Human Manager Authorization Required ({pendingApprovals.length})
            </h3>
            <p className="text-[11px] font-medium text-amber-800">
              Autonomous workforce is paused awaiting human operational verification.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-black px-2.5 py-1 rounded-full bg-amber-200 text-amber-900 border border-amber-300 animate-pulse">
          Action Required
        </span>
      </div>

      <div className="space-y-3">
        {pendingApprovals.map((approval) => (
          <div
            key={approval.approval_id}
            className="bg-white p-4 rounded-xl border border-amber-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border">
                  {approval.approval_id}
                </span>
                <span className="text-xs font-extrabold text-slate-900">
                  Transfer {approval.quantity} units of {approval.sku_id}
                </span>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Cedar Policy: ALLOWED
                </span>
              </div>

              <div className="flex items-center gap-4 text-xs font-medium text-slate-600 flex-wrap">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <span>{approval.source_store_id}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                  <span>{approval.destination_store_id}</span>
                </div>
                <div className="flex items-center gap-1 text-slate-600">
                  <Truck className="w-3.5 h-3.5 text-slate-400" />
                  <span>Carrier: <strong className="text-slate-800">{approval.selected_partner}</strong></span>
                </div>
                <div className="flex items-center gap-1 text-emerald-700 font-bold">
                  <DollarSign className="w-3.5 h-3.5" />
                  <span>Net Recovery: ₹{approval.net_recovery.toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* Decision Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                disabled={submittingId === approval.approval_id}
                onClick={() => handleDecision(approval.approval_id, 'REJECTED')}
                className="px-3.5 py-2 bg-slate-100 hover:bg-rose-50 hover:text-rose-700 text-slate-700 font-extrabold text-xs rounded-xl border border-slate-200 transition-all flex items-center gap-1.5"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>
              <button
                disabled={submittingId === approval.approval_id}
                onClick={() => handleDecision(approval.approval_id, 'APPROVED')}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs rounded-xl shadow-md shadow-emerald-200 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Approve Transfer</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

