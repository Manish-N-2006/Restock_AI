import React, { useState } from 'react';
import { useOfficeWebSocket } from '../hooks/useOfficeWebSocket';
import { apiFetch } from '../../../api/client';
import { VirtualOfficeCanvas } from './VirtualOfficeCanvas';
import { AgentRoster } from './AgentRoster';
import { AgentTaskPanel } from './AgentTaskPanel';
import { ApprovalPanel } from './ApprovalPanel';
import { OfficeActivityTimeline } from './OfficeActivityTimeline';
import { Play, RefreshCw, FileText } from 'lucide-react';

export const VirtualOfficeView: React.FC = () => {
  const {
    connected,
    agents,
    selectedAgentId,
    setSelectedAgentId,
    pendingApprovals,
    timeline,
    latestReport,
    isRunningWorkflow,
    officeState,
    triggerWorkflow,
    submitApprovalDecision,
  } = useOfficeWebSocket();

  const [skuId, setSkuId] = useState('YOG-001');
  const [storeId, setStoreId] = useState('STORE_A');
  const [autoApprove, setAutoApprove] = useState(false);

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  const handleLaunchWorkflow = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    await triggerWorkflow(skuId, storeId, autoApprove);
  };

  const handleSendToRoom = async (agentId: number, room: 'workstation' | 'conference' | 'approval' | 'breakroom') => {
    try {
      await apiFetch('/api/office/agent/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, destination: room }),
      });
    } catch (e) {
      console.warn('Failed to move agent', e);
    }
  };

  return (
    <div className="space-y-6 flex flex-col min-h-[calc(100vh-100px)] selection:bg-emerald-100">
      {/* Top Header & Operational Trigger Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-slate-900 text-emerald-400 flex items-center justify-center font-black text-sm shadow-sm">
              🏢
            </div>
            <div>
              <h1 className="text-base font-extrabold text-slate-900 tracking-tight">
                Autonomous Workforce — Virtual AI Office
              </h1>
              <p className="text-xs font-semibold text-slate-500">
                Multi-agent inventory recovery workforce running on Groq & Strands AI.
              </p>
            </div>
          </div>
        </div>

        {/* Trigger Form Controls */}
        <form onSubmit={handleLaunchWorkflow} className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={skuId}
              onChange={(e) => setSkuId(e.target.value)}
              placeholder="SKU (e.g. YOG-001)"
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900 w-28 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
            <input
              type="text"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              placeholder="Store (e.g. STORE_A)"
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900 w-28 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>

          <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={autoApprove}
              onChange={(e) => setAutoApprove(e.target.checked)}
              className="rounded text-emerald-600 focus:ring-emerald-500/20"
            />
            <span>Auto-Approve</span>
          </label>

          <button
            type="submit"
            disabled={isRunningWorkflow || !skuId}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-200 text-white font-extrabold text-xs rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center gap-2 cursor-pointer"
          >
            {isRunningWorkflow ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>CEO Orchestrating...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Dispatch Workforce</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Human Approval Alert Section (Shows when approval is needed) */}
      <ApprovalPanel
        pendingApprovals={pendingApprovals}
        onDecision={submitApprovalDecision}
      />

      {/* Main Grid: Interactive Canvas (Left 7 cols) & Agent Roster (Right 5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-8 space-y-6">
          {/* Canvas Component */}
          <VirtualOfficeCanvas
            officeState={officeState}
            connected={connected}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
          />

          {/* Selected Agent Task Detail Panel */}
          <AgentTaskPanel
            agent={selectedAgent}
            onSendToRoom={handleSendToRoom}
          />
        </div>

        <div className="lg:col-span-4 space-y-6">
          {/* Agent Roster List */}
          <AgentRoster
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
          />

          {/* Activity Stream */}
          <OfficeActivityTimeline timeline={timeline} />
        </div>
      </div>

      {/* Latest Executive Ops Report Card (When generated) */}
      {latestReport && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-50 text-blue-700">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-900">
                  CEO Executive Ops Report — Scenario {latestReport.scenario_id}
                </h3>
                <p className="text-[11px] font-semibold text-slate-500">
                  Product: {latestReport.product_name} ({latestReport.sku_id}) | Store: {latestReport.source_store_id}
                </p>
              </div>
            </div>

            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
              Status: {latestReport.overall_status}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 text-xs font-medium text-slate-800 leading-relaxed">
            {latestReport.executive_summary}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {latestReport.inventory_findings && (
              <div className="p-3.5 rounded-xl bg-rose-50/60 border border-rose-200/60 space-y-1">
                <span className="text-[10px] font-extrabold uppercase text-rose-800">
                  Inventory Risk Audit
                </span>
                <p className="font-extrabold text-slate-900">
                  {latestReport.inventory_findings.at_risk_quantity} units at {latestReport.inventory_findings.risk_level} Risk
                </p>
                <p className="text-[11px] text-slate-600">
                  Value at Risk: ₹{latestReport.inventory_findings.at_risk_value.toLocaleString()} ({latestReport.inventory_findings.days_to_expiry} days to expiry)
                </p>
              </div>
            )}

            {latestReport.strategy_recommendation && (
              <div className="p-3.5 rounded-xl bg-purple-50/60 border border-purple-200/60 space-y-1">
                <span className="text-[10px] font-extrabold uppercase text-purple-800">
                  Recovery Strategy
                </span>
                <p className="font-extrabold text-slate-900">
                  Action: {latestReport.strategy_recommendation.selected_action} ({latestReport.strategy_recommendation.recommended_quantity} units)
                </p>
                <p className="text-[11px] text-slate-600">
                  Destination: {latestReport.strategy_recommendation.target_destination_store_id}
                </p>
              </div>
            )}

            {latestReport.logistics_plan && (
              <div className="p-3.5 rounded-xl bg-amber-50/60 border border-amber-200/60 space-y-1">
                <span className="text-[10px] font-extrabold uppercase text-amber-800">
                  Logistics Route Optimization
                </span>
                <p className="font-extrabold text-slate-900">
                  Carrier: {latestReport.logistics_plan.selected_partner}
                </p>
                <p className="text-[11px] text-slate-600">
                  Distance: {latestReport.logistics_plan.distance_km} km | Net: ₹{latestReport.logistics_plan.logistics_adjusted_net_recovery.toLocaleString()}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
