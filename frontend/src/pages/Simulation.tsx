import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Cpu,
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  CreditCard,
  Building2,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  FileText,
  Truck,
  Clock,
  DollarSign,
  MapPin,
  ThermometerSnowflake,
  Network,
  Store,
  Copy,
  Check,
  Eye,
  Receipt,
  X,
} from 'lucide-react';

import { useOfficeWebSocket } from '../features/virtual-office/hooks/useOfficeWebSocket';
import { VirtualOfficeCanvas } from '../features/virtual-office/components/VirtualOfficeCanvas';
import { AgentRoster } from '../features/virtual-office/components/AgentRoster';
import { AgentTaskPanel } from '../features/virtual-office/components/AgentTaskPanel';
import { PayPalCheckout, RecoveryOrderData, CaptureResult } from '../components/payments/PayPalCheckout';
import { SimulationState } from '../types/simulation';
import { apiFetch } from '../api/client';

const WORKFLOW_STEPS = [
  '1. INVENTORY AUDIT',
  '2. NETWORK MATCHING',
  '3. STRATEGY & ECONOMICS',
  '4. LOGISTICS OPTIMIZATION',
  '5. TRANSFER / ORDER MANIFEST',
  '6. CEDAR AUTHORIZATION',
  '7. SETTLEMENT / PAYPAL',
  '8. FULFILLMENT & DISPATCH',
  '9. RECONCILIATION & CEO REPORT',
];

export const Simulation: React.FC = () => {
  const [searchParams] = useSearchParams();
  const currentView = searchParams.get('mode') || 'unified';

  // Primary mode: 'unified' (Unified Autonomous Simulation Center) | 'calculator' (Standalone Formula Calculator)
  const [mode, setMode] = useState<'unified' | 'calculator'>(
    currentView === 'calculator' ? 'calculator' : 'unified'
  );

  // Office WebSocket connection
  const {
    connected,
    agents,
    selectedAgentId,
    setSelectedAgentId,
    officeState,
    speechBubbles,
    setSpeechBubbles,
  } = useOfficeWebSocket();

  // Simulation State
  const [simState, setSimState] = useState<SimulationState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAutoRunning, setIsAutoRunning] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<'SCENARIO_A' | 'SCENARIO_B' | 'SCENARIO_C' | 'SCENARIO_D'>('SCENARIO_A');
  const [isPayPalModalOpen, setIsPayPalModalOpen] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<'matching' | 'logistics' | 'economics' | 'network_plan'>('matching');
  const [paymentToast, setPaymentToast] = useState<{
    visible: boolean;
    payment_id: string;
    paypal_order_id: string;
    paypal_capture_id: string;
    amount: number;
    currency: string;
  } | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [inspectedPayment, setInspectedPayment] = useState<any | null>(null);
  const [isInspectingPayment, setIsInspectingPayment] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleInspectPayment = async (paymentId: string) => {
    setIsInspectingPayment(true);
    try {
      const res = await apiFetch(`/api/payments/${encodeURIComponent(paymentId)}`);
      if (res.ok) {
        const data = await res.json();
        setInspectedPayment(data);
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to fetch payment details: ${err.detail || 'Not found'}`);
      }
    } catch (e) {
      console.error('Error inspecting payment:', e);
    } finally {
      setIsInspectingPayment(false);
    }
  };

  useEffect(() => {
    if (paymentToast?.visible) {
      const timer = setTimeout(() => {
        setPaymentToast(null);
      }, 7000);
      return () => clearTimeout(timer);
    }
  }, [paymentToast]);

  // Standalone Calculator State (Preserved)
  const [calcSku, setCalcSku] = useState('YOG-001');
  const [calcStore, setCalcStore] = useState('STORE_A');
  const [calcResult, setCalcResult] = useState<any | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);

  // 1. Fetch active simulation state
  const fetchSimState = async () => {
    try {
      const res = await apiFetch('/api/simulation/state');
      if (res.ok) {
        const data: SimulationState = await res.json();
        setSimState(data);
        setSelectedScenario(data.scenario_id);
      }
    } catch (err) {
      console.warn('Failed to fetch simulation state:', err);
    }
  };

  useEffect(() => {
    fetchSimState();
    const interval = setInterval(fetchSimState, 2500);
    return () => clearInterval(interval);
  }, []);

  // 2. Scenario & Step Execution Handlers
  const handleResetScenario = async (scenarioType: 'SCENARIO_A' | 'SCENARIO_B' | 'SCENARIO_C' | 'SCENARIO_D') => {
    setIsLoading(true);
    setIsAutoRunning(false);
    setSpeechBubbles({});
    try {
      const res = await apiFetch('/api/simulation/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_type: scenarioType }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimState(data);
        setSelectedScenario(scenarioType);
      }
    } catch (e) {
      console.error('Error resetting scenario:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStepForward = async () => {
    if (!simState || isLoading) return;
    setIsLoading(true);
    try {
      const res = await apiFetch(`/api/simulation/step?run_id=${simState.simulation_run_id}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setSimState(data);
      }
    } catch (e) {
      console.error('Error executing step:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunAll = async () => {
    if (!simState || isLoading) return;
    setIsLoading(true);
    setIsAutoRunning(true);
    try {
      const res = await apiFetch(`/api/simulation/run?run_id=${simState.simulation_run_id}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setSimState(data);
      }
    } catch (e) {
      console.error('Error running simulation:', e);
    } finally {
      setIsLoading(false);
      setIsAutoRunning(false);
    }
  };

  const handlePause = async () => {
    if (!simState) return;
    try {
      const res = await apiFetch(`/api/simulation/pause?run_id=${simState.simulation_run_id}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setSimState(data);
        setIsAutoRunning(false);
      }
    } catch (e) {
      console.error('Error pausing simulation:', e);
    }
  };

  const handleApproveDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!simState) return;
    setIsLoading(true);
    try {
      const res = await apiFetch('/api/simulation/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: simState.simulation_run_id, decision }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimState(data);
      }
    } catch (e) {
      console.error('Error submitting approval:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePayPalPaymentSuccess = async (capture: CaptureResult) => {
    if (!simState) return;
    try {
      const res = await apiFetch('/api/simulation/paypal/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: simState.simulation_run_id,
          payment_id: capture.payment_id,
          paypal_order_id: capture.paypal_order_id,
          paypal_capture_id: capture.paypal_capture_id,
          amount: capture.amount,
          currency: capture.currency,
          fee_amount: capture.fee_amount,
          net_amount: capture.net_amount,
          payer_id: capture.payer_id,
          payer_email: capture.payer_email,
          payer_name: capture.payer_name,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimState(data);
        setIsPayPalModalOpen(false);
        setPaymentError(null);
        setPaymentToast({
          visible: true,
          payment_id: capture.payment_id,
          paypal_order_id: capture.paypal_order_id,
          paypal_capture_id: capture.paypal_capture_id,
          amount: capture.amount,
          currency: capture.currency,
        });
      } else {
        const err = await res.json().catch(() => ({}));
        setPaymentError(err.detail || 'Payment confirmation failed');
      }
    } catch (e: any) {
      console.error('Error recording payment capture:', e);
      setPaymentError(e.message || 'Payment confirmation failed');
    }
  };

  // Standalone Calculator Execution
  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCalculating(true);
    try {
      const res = await apiFetch(`/api/agent/analyze/${calcSku}?store_id=${calcStore}`);
      if (res.ok) {
        const data = await res.json();
        setCalcResult({
          recommendation: data.answer.includes('Transfer') ? 'INTERNAL_TRANSFER' : 'MARKDOWN_DISCOUNT',
          predicted_recovery: '280.28',
          reasoning: data.answer,
        });
      }
    } catch (err) {
      console.error('Calculator analysis failed:', err);
    } finally {
      setIsCalculating(false);
    }
  };

  const activeRecoveryOrder: RecoveryOrderData | null =
    simState?.offer_creation && simState.offer_creation.type === 'RECOVERY_ORDER'
      ? {
          order_id: simState.offer_creation.order_id || 'SIM-ORD-EXT-01',
          sku_id: simState.offer_creation.sku_id || simState.sku_id,
          product_name: simState.offer_creation.product_name || simState.product_name,
          source_store_id: simState.source_store_id,
          channel: 'DISCOUNT_MARKETPLACE',
          quantity: simState.offer_creation.quantity || 120,
          unit_price: simState.offer_creation.unit_price || 1.80,
          total_amount: simState.offer_creation.total_amount || 216.00,
          currency: simState.offer_creation.currency || 'USD',
          buyer_name: simState.offer_creation.buyer_name || 'Metro Retail Discount Mart',
          buyer_email: simState.offer_creation.buyer_email || 'procurement@metroretail.example.com',
          status: 'CREATED',
          fulfillment_status: 'UNFULFILLED',
        }
      : null;

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) || agents[0];

  return (
    <div className="space-y-6 max-w-[1720px] mx-auto pb-12">
      {/* TOP HEADER: NAVIGATION & MODE TOGGLE */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200/80 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-emerald-600 text-white shadow-sm">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                <span>ReStockAI</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-mono font-bold">
                  Network-First Intelligence
                </span>
              </h1>
              <p className="text-xs text-slate-500 font-medium">
                Multi-Branch Inventory Redistribution, Incremental Network Economics & Autonomous Commerce
              </p>
            </div>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1.5 rounded-xl border border-slate-200">
          <button
            onClick={() => setMode('unified')}
            className={`px-4 py-2 rounded-lg text-xs font-extrabold transition-all flex items-center gap-2 cursor-pointer ${
              mode === 'unified'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Building2 className="w-4 h-4 text-emerald-600" />
            <span>Multi-Branch Simulation Center</span>
          </button>

          <button
            onClick={() => setMode('calculator')}
            className={`px-4 py-2 rounded-lg text-xs font-extrabold transition-all flex items-center gap-2 cursor-pointer ${
              mode === 'calculator'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sliders className="w-4 h-4 text-emerald-600" />
            <span>Standalone Calculator</span>
          </button>
        </div>
      </div>

      {/* VIEW 1: UNIFIED MULTI-BRANCH SIMULATION CENTER */}
      {mode === 'unified' && (
        <div className="space-y-6">
          {/* SECTION A: 4 SCENARIOS CONTROL BAR */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-5">
            {/* Scenario Selection Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-extrabold text-slate-700 uppercase tracking-wider mr-1">
                Scenario:
              </span>
              <button
                onClick={() => handleResetScenario('SCENARIO_A')}
                className={`px-3.5 py-2 rounded-xl text-xs font-extrabold transition-all border flex items-center gap-1.5 cursor-pointer ${
                  selectedScenario === 'SCENARIO_A'
                    ? 'bg-emerald-600 text-white border-emerald-700 shadow-sm'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <span>A: Surplus Rescue (Donor)</span>
              </button>

              <button
                onClick={() => handleResetScenario('SCENARIO_B')}
                className={`px-3.5 py-2 rounded-xl text-xs font-extrabold transition-all border flex items-center gap-1.5 cursor-pointer ${
                  selectedScenario === 'SCENARIO_B'
                    ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <span>B: Stockout Prevention (Receiver)</span>
              </button>

              <button
                onClick={() => handleResetScenario('SCENARIO_C')}
                className={`px-3.5 py-2 rounded-xl text-xs font-extrabold transition-all border flex items-center gap-1.5 cursor-pointer ${
                  selectedScenario === 'SCENARIO_C'
                    ? 'bg-purple-600 text-white border-purple-700 shadow-sm'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <span>C: Network-Wide Balancing</span>
              </button>

              <button
                onClick={() => handleResetScenario('SCENARIO_D')}
                className={`px-3.5 py-2 rounded-xl text-xs font-extrabold transition-all border flex items-center gap-1.5 cursor-pointer ${
                  selectedScenario === 'SCENARIO_D'
                    ? 'bg-amber-600 text-white border-amber-700 shadow-sm'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <span>D: External B2B Liquidation</span>
              </button>
            </div>

            {/* Run / Step / Pause / Reset Action Controls */}
            <div className="flex items-center gap-2.5 flex-wrap">
              <button
                onClick={handleRunAll}
                disabled={isLoading || simState?.status === 'COMPLETED' || simState?.status === 'REJECTED'}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-extrabold text-xs rounded-xl transition-all shadow-sm flex items-center gap-2 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Simulation</span>
              </button>

              <button
                onClick={handleStepForward}
                disabled={isLoading || simState?.status === 'COMPLETED' || simState?.status === 'REJECTED'}
                className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-white font-extrabold text-xs rounded-xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
                title="Execute single step forward"
              >
                <SkipForward className="w-3.5 h-3.5" />
                <span>Next Step</span>
              </button>

              {isAutoRunning && (
                <button
                  onClick={handlePause}
                  className="px-3 py-2 bg-amber-500 hover:bg-amber-600 text-white font-extrabold text-xs rounded-xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
                >
                  <Pause className="w-3.5 h-3.5 fill-current" />
                  <span>Pause</span>
                </button>
              )}

              <button
                onClick={() => handleResetScenario(selectedScenario)}
                className="p-2 border border-slate-200 text-slate-600 hover:bg-slate-100 rounded-xl transition-all cursor-pointer"
                title="Reset Scenario to Step 1"
              >
                <RotateCcw className="w-4 h-4" />
              </button>

              {/* Status Indicator Badge */}
              <div className="flex items-center gap-2 border-l border-slate-200 pl-3">
                <span
                  className={`px-3 py-1.5 rounded-xl text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 ${
                    simState?.status === 'COMPLETED'
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : simState?.status === 'REJECTED'
                      ? 'bg-amber-100 text-amber-800 border border-amber-300'
                      : simState?.status === 'AWAITING_APPROVAL'
                      ? 'bg-rose-100 text-rose-800 border border-rose-300 animate-pulse'
                      : simState?.status === 'AWAITING_PAYMENT'
                      ? 'bg-indigo-100 text-indigo-800 border border-indigo-300 animate-pulse'
                      : simState?.status === 'RUNNING'
                      ? 'bg-blue-100 text-blue-800 border border-blue-300'
                      : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-current"></span>
                  <span>{simState?.status || 'IDLE'}</span>
                </span>

                <span className="font-mono text-[10px] text-slate-400 font-semibold hidden lg:inline">
                  {simState?.simulation_run_id}
                </span>
              </div>
            </div>
          </div>

          {/* SECTION B: PERSPECTIVE BANNER & OPERATIONAL PROFILE */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4.5 space-y-3 shadow-2xs">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-black uppercase px-2.5 py-0.5 rounded-full border ${
                      simState?.operating_perspective === 'STOCKOUT_RECEIVER'
                        ? 'bg-indigo-100 text-indigo-900 border-indigo-300'
                        : simState?.operating_perspective === 'NETWORK_BALANCING'
                        ? 'bg-purple-100 text-purple-900 border-purple-300'
                        : simState?.operating_perspective === 'EXTERNAL_LIQUIDATION'
                        ? 'bg-amber-100 text-amber-900 border-amber-300'
                        : 'bg-emerald-100 text-emerald-900 border-emerald-300'
                    }`}
                  >
                    {simState?.operating_perspective === 'STOCKOUT_RECEIVER'
                      ? 'Stockout Prevention View (Receiver)'
                      : simState?.operating_perspective === 'NETWORK_BALANCING'
                      ? 'Network-Wide Balancing View'
                      : simState?.operating_perspective === 'EXTERNAL_LIQUIDATION'
                      ? 'External B2B Liquidation View'
                      : 'Surplus Branch View (Donor)'}
                  </span>
                  <h2 className="text-sm font-extrabold text-slate-900">{simState?.scenario_name}</h2>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  {simState?.scenario_description}
                </p>
              </div>

              {/* Incremental Network Value Highlight */}
              <div className="bg-white px-4 py-2.5 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Expected Network Value
                  </span>
                  <span className="text-base font-black font-mono text-emerald-600">
                    +${simState?.recovery_analysis?.expected_net_recovery?.toFixed(2) ?? '280.28'} USD
                  </span>
                </div>
                <div className="w-px h-8 bg-slate-200"></div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Recommended Action
                  </span>
                  <span className="text-xs font-extrabold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                    {simState?.recovery_analysis?.selected_action ?? 'INTERNAL_TRANSFER'}
                  </span>
                </div>
              </div>
            </div>

            {/* Branch Profiles Strip */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 border-t border-slate-200/70 text-xs">
              <div className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200">
                <Store className="w-4 h-4 text-emerald-600 shrink-0" />
                <div className="truncate">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">Donor / Source Branch</span>
                  <span className="font-extrabold text-slate-900 font-mono">
                    {simState?.donor_branch?.store_name || (simState?.source_store_id === 'STORE_D' ? 'Store A (Surplus Donor)' : 'Main Hub (Store A)')}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200">
                <MapPin className="w-4 h-4 text-indigo-600 shrink-0" />
                <div className="truncate">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">Receiving Destination</span>
                  <span className="font-extrabold text-slate-900 font-mono">
                    {simState?.receiving_branch?.store_name || (simState?.scenario_id === 'SCENARIO_B' ? 'East Branch (Store D)' : 'North Branch (Store B)')}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200">
                <ThermometerSnowflake className="w-4 h-4 text-blue-500 shrink-0" />
                <div className="truncate">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">Cold-Chain & Expiry Window</span>
                  <span className="font-bold text-slate-900">
                    Active Reefer Required &bull; {simState?.scenario_id === 'SCENARIO_B' ? '6.0h Stockout Deadline' : '3.0 Days Expiry Clock'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION C: 9-STAGE WORKFLOW PIPELINE PROGRESS BAR */}
          <div className="bg-white p-4.5 rounded-2xl border border-slate-200/80 shadow-xs">
            <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
              {WORKFLOW_STEPS.map((stepName, sIdx) => {
                const currentIdx = simState?.current_step_index ?? 0;
                const isPast = sIdx < currentIdx;
                const isCurrent = sIdx === currentIdx;

                return (
                  <div
                    key={sIdx}
                    className={`p-2.5 rounded-xl border text-center transition-all ${
                      isPast
                        ? 'bg-emerald-50/90 border-emerald-300 text-emerald-950 font-bold'
                        : isCurrent
                        ? 'bg-indigo-900 text-white border-indigo-700 shadow-md ring-2 ring-indigo-400 font-black'
                        : 'bg-slate-50 text-slate-400 border-slate-200 font-medium'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-1 mb-1">
                      {isPast ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <span className="text-[10px] font-mono">{sIdx + 1}</span>
                      )}
                    </div>
                    <span className="text-[9.5px] leading-tight block truncate uppercase tracking-wider">
                      {stepName.replace(/^\d+\.\s*/, '')}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SECTION D: PIXEL AGENTS VIRTUAL OFFICE CANVAS & AGENT ROSTER */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left 8 Cols: Native Pixel Agents 2D Canvas */}
            <div className="lg:col-span-8 bg-slate-950 p-3 rounded-2xl border border-slate-800 shadow-xl overflow-hidden relative">
              <div className="flex items-center justify-between pb-3 px-2 border-b border-slate-800/80 mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-200">
                    Live Virtual AI Office &bull; 7 AI Employees
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Sarah Chen (CEO) &bull; Specialist Workstations &bull; Approval Room
                </span>
              </div>

              {/* Canvas with Compact Floating Speech Bubbles */}
              <VirtualOfficeCanvas
                officeState={officeState}
                connected={connected}
                selectedAgentId={selectedAgentId}
                onSelectAgent={(id) => setSelectedAgentId(id)}
                speechBubbles={speechBubbles}
                onDismissBubble={(id) => {
                  setSpeechBubbles((prev) => {
                    const copy = { ...prev };
                    delete copy[id];
                    return copy;
                  });
                }}
              />
            </div>

            {/* Right 4 Cols: Agent Workforce Roster & Subtask Panel */}
            <div className="lg:col-span-4 space-y-5">
              <AgentRoster
                agents={agents}
                selectedAgentId={selectedAgentId}
                onSelectAgent={(id) => setSelectedAgentId(id)}
              />

              <AgentTaskPanel
                agent={selectedAgent}
                onSendToRoom={(agentId, room) => officeState.sendToDestination(agentId, room)}
              />
            </div>
          </div>

          {/* SECTION E: MULTI-PERSPECTIVE INTELLIGENCE HUB & DECISION AUDIT */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
            {/* Tab Navigation */}
            <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-50/70 p-3">
              <button
                onClick={() => setActiveBottomTab('matching')}
                className={`px-4 py-2 rounded-xl text-xs font-extrabold flex items-center gap-2 cursor-pointer transition ${
                  activeBottomTab === 'matching'
                    ? 'bg-white text-slate-900 border border-slate-200 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Store className="w-3.5 h-3.5 text-emerald-600" />
                <span>Candidate Branch Matching</span>
              </button>

              <button
                onClick={() => setActiveBottomTab('logistics')}
                className={`px-4 py-2 rounded-xl text-xs font-extrabold flex items-center gap-2 cursor-pointer transition ${
                  activeBottomTab === 'logistics'
                    ? 'bg-white text-slate-900 border border-slate-200 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Truck className="w-3.5 h-3.5 text-indigo-600" />
                <span>Logistics Fleet Optimization</span>
              </button>

              <button
                onClick={() => setActiveBottomTab('economics')}
                className={`px-4 py-2 rounded-xl text-xs font-extrabold flex items-center gap-2 cursor-pointer transition ${
                  activeBottomTab === 'economics'
                    ? 'bg-white text-slate-900 border border-slate-200 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
                <span>Incremental Network Economics</span>
              </button>

              {simState?.scenario_id === 'SCENARIO_C' && (
                <button
                  onClick={() => setActiveBottomTab('network_plan')}
                  className={`px-4 py-2 rounded-xl text-xs font-extrabold flex items-center gap-2 cursor-pointer transition ${
                    activeBottomTab === 'network_plan'
                      ? 'bg-white text-slate-900 border border-slate-200 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Network className="w-3.5 h-3.5 text-purple-600" />
                  <span>Multi-Branch Balancing Plan</span>
                </button>
              )}
            </div>

            {/* Tab Contents */}
            <div className="p-6">
              {/* TAB 1: CANDIDATE BRANCH MATCHING */}
              {activeBottomTab === 'matching' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-extrabold text-slate-900">
                        {simState?.operating_perspective === 'STOCKOUT_RECEIVER'
                          ? 'Ranked Donor Branches (Surplus Availability)'
                          : simState?.operating_perspective === 'EXTERNAL_LIQUIDATION'
                          ? 'External B2B Commercial Buyers'
                          : 'Ranked Receiving Branches (Demand Velocity & Absorption Capacity)'}
                      </h3>
                      <p className="text-xs text-slate-500 font-medium">
                        Deterministic matching evaluates capacity, safety stock preservation, road distance, and net economic value.
                      </p>
                    </div>
                  </div>

                  {/* Candidate Branches Table / Cards */}
                  {simState?.candidate_branches && simState.candidate_branches.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {simState.candidate_branches.map((b, idx) => (
                        <div
                          key={b.store_id || idx}
                          className={`p-4 rounded-xl border text-xs space-y-2.5 transition ${
                            b.is_eligible
                              ? 'bg-slate-50/80 border-slate-200 hover:border-emerald-300 shadow-xs'
                              : 'bg-slate-50/40 border-slate-200/60 opacity-65'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-extrabold text-slate-900 text-sm">{b.store_name}</span>
                            <span
                              className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                                b.is_eligible
                                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                  : 'bg-rose-100 text-rose-800 border border-rose-200'
                              }`}
                            >
                              {b.is_eligible ? `${b.match_score}% Match` : 'Ineligible'}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 font-mono">
                            <div>
                              <span className="text-slate-400 block text-[9.5px]">ROAD DISTANCE</span>
                              <span className="font-bold text-slate-800">{b.simulated_road_distance_km} km ({b.estimated_transit_minutes} min)</span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[9.5px]">ALLOCATION QTY</span>
                              <span className="font-bold text-slate-800">{b.recommended_transfer_qty} units</span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[9.5px]">COLD CHAIN</span>
                              <span className={`font-bold ${b.cold_chain_compatible ? 'text-emerald-700' : 'text-rose-600'}`}>
                                {b.cold_chain_compatible ? 'Certified Active' : 'No Cold Chain'}
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[9.5px]">NET VALUE</span>
                              <span className="font-bold text-emerald-700">+${b.net_economic_value.toFixed(2)} USD</span>
                            </div>
                          </div>

                          {/* Reasons */}
                          <div className="pt-2 border-t border-slate-200/70 text-[10.5px]">
                            {b.is_eligible ? (
                              <p className="text-emerald-800 leading-snug font-medium">
                                {b.reasons.join(' ')}
                              </p>
                            ) : (
                              <p className="text-rose-700 leading-snug font-medium">
                                <span className="font-bold">Rejection reason:</span> {b.rejection_reasons.join(' | ')}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : simState?.scenario_id === 'SCENARIO_D' && simState.buyer_discovery ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {simState.buyer_discovery.candidates.map((buyer) => (
                        <div
                          key={buyer.buyer_id}
                          className="p-4 rounded-xl border border-slate-200 bg-slate-50/80 text-xs space-y-2 shadow-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900">{buyer.name}</span>
                            <span className="font-mono text-[10px] font-extrabold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                              {buyer.match_score}% Match
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500">{buyer.organization_type} &bull; {buyer.location}</p>
                          <div className="text-[11px] text-slate-700 font-mono">
                            Offer: ${buyer.offered_unit_price.toFixed(2)}/unit &bull; Demand: up to {buyer.offered_quantity} units
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-400 text-xs font-semibold">
                      Click 'Run Simulation' or 'Next Step' to initiate multi-branch candidate evaluation.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: LOGISTICS FLEET OPTIMIZATION */}
              {activeBottomTab === 'logistics' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-900">
                      Transport Carrier Optimization & Simulated Road Network
                    </h3>
                    <p className="text-xs text-slate-500 font-medium">
                      Mandatory constraints enforce active refrigeration, vehicle capacity, and arrival window before shelf-life expiry.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px] font-black">
                          <th className="py-2.5 px-3">Carrier Partner</th>
                          <th className="py-2.5 px-3">Vehicle Type</th>
                          <th className="py-2.5 px-3 font-mono">Road Dist.</th>
                          <th className="py-2.5 px-3 font-mono">Transit ETA</th>
                          <th className="py-2.5 px-3 font-mono">Freight Cost</th>
                          <th className="py-2.5 px-3">Cold Chain</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Evaluation & Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {simState?.logistics_comparison?.map((carrier) => (
                          <tr
                            key={carrier.partner_id}
                            className={`hover:bg-slate-50/70 transition ${
                              carrier.eligible ? 'text-slate-900 font-medium' : 'text-slate-400 opacity-60'
                            }`}
                          >
                            <td className="py-3 px-3 font-extrabold">{carrier.partner_name}</td>
                            <td className="py-3 px-3">{carrier.vehicle_type}</td>
                            <td className="py-3 px-3 font-mono">{carrier.road_distance_km} km (simulated)</td>
                            <td className="py-3 px-3 font-mono">{carrier.estimated_journey_time_minutes} min</td>
                            <td className="py-3 px-3 font-mono font-bold text-slate-900">${carrier.transport_cost.toFixed(2)} USD</td>
                            <td className="py-3 px-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  carrier.cold_chain_available
                                    ? 'bg-blue-100 text-blue-800'
                                    : 'bg-slate-200 text-slate-600'
                                }`}
                              >
                                {carrier.cold_chain_available ? 'Active Reefer' : 'Ambient'}
                              </span>
                            </td>
                            <td className="py-3 px-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${
                                  carrier.eligible
                                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                    : 'bg-rose-100 text-rose-800 border border-rose-300'
                                }`}
                              >
                                {carrier.eligible ? `Score: ${carrier.final_score}` : 'Ineligible'}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-[11px] leading-relaxed max-w-sm">
                              {carrier.eligible ? carrier.selection_reason : carrier.rejection_reason}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 3: INCREMENTAL NETWORK ECONOMICS */}
              {activeBottomTab === 'economics' && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-900">
                      Consolidated Incremental Network Economic Impact
                    </h3>
                    <p className="text-xs text-slate-500 font-medium">
                      Evaluates net economic advantage across the enterprise retail network, avoiding double-counting internal transfers as consolidated revenue.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-bold block">Protected Margin at Receiver</span>
                      <span className="text-lg font-black text-slate-900">
                        +${simState?.network_economics?.margin_protected_at_receiver?.toFixed(2) ?? '134.10'} USD
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-bold block">Avoided Spoilage / Write-off</span>
                      <span className="text-lg font-black text-slate-900">
                        +${simState?.network_economics?.avoided_markdown_writeoff_loss?.toFixed(2) ?? '208.25'} USD
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-bold block">Freight & Cross-Dock Handling</span>
                      <span className="text-lg font-black text-rose-600">
                        -${simState?.network_economics?.transport_cost?.toFixed(2) ?? '45.19'} USD
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300">
                      <span className="text-[10px] text-emerald-800 uppercase font-bold block">Net Incremental Value</span>
                      <span className="text-lg font-black text-emerald-700">
                        +${simState?.network_economics?.net_incremental_network_value?.toFixed(2) ?? '280.28'} USD
                      </span>
                    </div>
                  </div>

                  {/* Supplier Replenishment Comparison Card */}
                  {simState?.network_economics?.supplier_replenishment_comparison && (
                    <div className="p-4 rounded-xl bg-indigo-50/80 border border-indigo-200 space-y-1.5 text-xs">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-indigo-700" />
                        <h4 className="font-extrabold text-indigo-950 uppercase text-[11px]">
                          Supplier Emergency Replenishment vs Internal Transfer
                        </h4>
                      </div>
                      <p className="text-indigo-900 leading-relaxed font-medium">
                        {simState.network_economics.supplier_replenishment_comparison.economic_conclusion}
                      </p>
                    </div>
                  )}

                  {/* Action Rankings Table */}
                  <div className="space-y-2">
                    <span className="text-[11px] font-extrabold text-slate-500 uppercase tracking-wider block">
                      Comparative Recovery Actions Ranking
                    </span>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      {simState?.recovery_analysis?.evaluated_actions?.map((act, i) => (
                        <div
                          key={i}
                          className={`p-3 rounded-xl border flex items-center justify-between ${
                            act.economically_viable
                              ? 'bg-slate-50 border-slate-200'
                              : 'bg-slate-50/50 border-slate-100 opacity-50'
                          }`}
                        >
                          <div>
                            <span className="font-bold text-slate-900 block">{act.action}</span>
                            <span className="text-[10px] text-slate-500">{act.reason || 'Economically evaluated'}</span>
                          </div>
                          <span className="font-mono font-extrabold text-slate-800">
                            ${act.expected_net_recovery.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: MULTI-BRANCH BALANCING PLAN (SCENARIO C) */}
              {activeBottomTab === 'network_plan' && simState?.network_balance_plan && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-900">
                      Multi-Branch Redistribution Schedule ({simState.network_balance_plan.algorithm})
                    </h3>
                    <p className="text-xs text-slate-500 font-medium leading-relaxed">
                      {simState.network_balance_plan.limitations}
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px] font-black">
                          <th className="py-2.5 px-3">Transfer ID</th>
                          <th className="py-2.5 px-3">Donor Store</th>
                          <th className="py-2.5 px-3">Receiver Store</th>
                          <th className="py-2.5 px-3">Product / SKU</th>
                          <th className="py-2.5 px-3 font-mono">Qty</th>
                          <th className="py-2.5 px-3">Carrier</th>
                          <th className="py-2.5 px-3 font-mono">Freight</th>
                          <th className="py-2.5 px-3 font-mono">Net Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-medium">
                        {simState.network_balance_plan.transfers.map((t) => (
                          <tr key={t.transfer_id} className="hover:bg-slate-50 transition">
                            <td className="py-3 px-3 font-mono font-bold text-slate-800">{t.transfer_id}</td>
                            <td className="py-3 px-3">{t.donor_store_name}</td>
                            <td className="py-3 px-3 font-bold text-indigo-700">{t.receiver_store_name}</td>
                            <td className="py-3 px-3">{t.product_name}</td>
                            <td className="py-3 px-3 font-mono font-bold">{t.quantity} units</td>
                            <td className="py-3 px-3">{t.carrier_name}</td>
                            <td className="py-3 px-3 font-mono text-slate-600">${t.freight_cost.toFixed(2)}</td>
                            <td className="py-3 px-3 font-mono font-bold text-emerald-700">+${t.net_network_value.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="p-3 bg-purple-50 rounded-xl border border-purple-200 flex items-center justify-between text-xs font-mono font-extrabold text-purple-950">
                    <span>TOTAL NETWORK VALUE CREATED: +${simState.network_balance_plan.total_net_network_value.toFixed(2)} USD</span>
                    <span>TOTAL REBALANCED UNITS: {simState.network_balance_plan.total_units_rebalanced} UNITS</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* SECTION F: INTERACTIVE ACTION GATES & LIVE EVENT STREAM */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Interactive Actions (Cedar Approval & PayPal Sandbox) */}
            <div className="space-y-4">
              {/* CEDAR HUMAN APPROVAL PROMPT */}
              {simState?.status === 'AWAITING_APPROVAL' && (
                <div className="bg-rose-50 border border-rose-300 rounded-2xl p-5 space-y-3 animate-in fade-in shadow-sm">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-black text-rose-950 uppercase tracking-wider">
                        Cedar Authorization Required
                      </h4>
                      <p className="text-xs text-rose-800 mt-0.5 leading-relaxed font-medium">
                        Workflow paused. Policy: {simState.human_approval?.threshold_evaluated}. Agent waiting in Approval Room.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => handleApproveDecision('APPROVED')}
                      className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs rounded-xl transition shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Approve Decision</span>
                    </button>
                    <button
                      onClick={() => handleApproveDecision('REJECTED')}
                      className="flex-1 py-2.5 bg-rose-600 hover:bg-rose-500 text-white font-extrabold text-xs rounded-xl transition shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              )}

              {/* PAYMENT ERROR NOTIFICATION (if any) */}
              {paymentError && (
                <div className="bg-rose-50 border border-rose-300 rounded-2xl p-4 text-xs text-rose-800 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-extrabold flex items-center gap-1.5 text-rose-900">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      Payment Verification Failed
                    </span>
                    <button
                      onClick={() => setPaymentError(null)}
                      className="text-rose-500 hover:text-rose-800"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="font-mono text-[11px] text-rose-700">{paymentError}</p>
                </div>
              )}

              {/* PAYPAL SANDBOX CHECKOUT TRIGGER (Scenario D) */}
              {simState?.status === 'AWAITING_PAYMENT' && activeRecoveryOrder && (
                <div className="bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-950 text-white rounded-2xl p-5 space-y-3.5 border border-indigo-700/50 shadow-md">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CreditCard className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-black uppercase tracking-wider text-emerald-300">
                        PayPal Orders v2 Checkout (Scenario D Fallback)
                      </span>
                    </div>
                    <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                      Live Sandbox Ready
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed font-medium">
                    Commercial order <span className="font-mono font-bold text-white">{activeRecoveryOrder.order_id}</span> created for {activeRecoveryOrder.buyer_name} (${activeRecoveryOrder.total_amount.toFixed(2)} USD).
                  </p>

                  <button
                    onClick={() => setIsPayPalModalOpen(true)}
                    className="w-full py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black text-xs rounded-xl transition shadow-md flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <span>Launch PayPal Sandbox Checkout</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {/* VERIFIED PAYPAL SANDBOX TRANSACTION RECEIPT CARD */}
              {simState?.paypal_checkout && simState.paypal_checkout.status === 'CAPTURED' && (
                <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-indigo-950 border border-emerald-500/40 rounded-2xl p-5 text-white space-y-4 shadow-lg animate-in fade-in">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-wider text-emerald-300">
                          PayPal Sandbox Transaction Receipt
                        </h4>
                        <span className="text-[10px] text-slate-400">Orders v2 Verified Capture</span>
                      </div>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      COMPLETED
                    </span>
                  </div>

                  {/* 3 Identifiers Grid */}
                  <div className="space-y-2 text-xs font-mono">
                    <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[9px] text-slate-400 uppercase font-sans font-bold block">Internal Payment ID</span>
                        <span className="text-emerald-400 font-extrabold text-[11px]">{simState.paypal_checkout.payment_id || 'PAY-SIM-CAPTURED'}</span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(simState.paypal_checkout?.payment_id || '', 'payment_id')}
                        className="p-1 text-slate-400 hover:text-white transition cursor-pointer"
                        title="Copy Payment ID"
                      >
                        {copiedKey === 'payment_id' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[9px] text-slate-400 uppercase font-sans font-bold block">PayPal Capture ID</span>
                        <span className="text-emerald-400 font-extrabold text-[11px]">{simState.paypal_checkout.paypal_capture_id || simState.paypal_checkout.capture_id || 'N/A'}</span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(simState.paypal_checkout?.paypal_capture_id || simState.paypal_checkout?.capture_id || '', 'capture_id')}
                        className="p-1 text-slate-400 hover:text-white transition cursor-pointer"
                        title="Copy Capture ID"
                      >
                        {copiedKey === 'capture_id' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[9px] text-slate-400 uppercase font-sans font-bold block">PayPal Order ID</span>
                        <span className="text-slate-300 text-[11px]">{simState.paypal_checkout.paypal_order_id || 'N/A'}</span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(simState.paypal_checkout?.paypal_order_id || '', 'order_id')}
                        className="p-1 text-slate-400 hover:text-white transition cursor-pointer"
                        title="Copy PayPal Order ID"
                      >
                        {copiedKey === 'order_id' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Financial Settlement Breakdown */}
                  <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Gross Paid:</span>
                      <span className="font-bold text-white font-mono">${(simState.paypal_checkout.amount || 216).toFixed(2)} {simState.paypal_checkout.currency || 'USD'}</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                      <span>PayPal Sandbox Fee:</span>
                      <span className="font-mono text-rose-400">-${(simState.paypal_checkout.fee_amount || 8.03).toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between text-emerald-400 pt-1 border-t border-slate-800 font-bold">
                      <span>Net Recovered:</span>
                      <span className="font-mono">${(simState.paypal_checkout.net_amount || ((simState.paypal_checkout.amount || 216) - (simState.paypal_checkout.fee_amount || 8.03))).toFixed(2)}</span>
                    </div>
                  </div>

                  {/* Inspection Actions */}
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      onClick={() => handleInspectPayment(simState.paypal_checkout?.payment_id || simState.paypal_checkout?.paypal_order_id || '')}
                      disabled={isInspectingPayment}
                      className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>{isInspectingPayment ? 'Inspecting...' : 'Inspect via API'}</span>
                    </button>
                    <button
                      onClick={() => {
                        const receiptText = `ReStockAI PayPal Receipt:
Payment ID: ${simState.paypal_checkout?.payment_id}
PayPal Order ID: ${simState.paypal_checkout?.paypal_order_id}
PayPal Capture ID: ${simState.paypal_checkout?.paypal_capture_id}
Gross: $${simState.paypal_checkout?.amount} ${simState.paypal_checkout?.currency}
Status: COMPLETED`;
                        copyToClipboard(receiptText, 'all_details');
                      }}
                      className="py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-bold text-xs rounded-xl transition flex items-center justify-center gap-1.5 cursor-pointer border border-slate-700"
                    >
                      {copiedKey === 'all_details' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKey === 'all_details' ? 'Copied' : 'Copy All'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Status summary banner if not awaiting approval or payment */}
              {simState?.status !== 'AWAITING_APPROVAL' && simState?.status !== 'AWAITING_PAYMENT' && (
                <div className="bg-slate-50 rounded-2xl border border-slate-200 p-5 space-y-2">
                  <span className="text-[10px] text-slate-400 uppercase font-black tracking-wider block">
                    Execution Status & Governance
                  </span>
                  <p className="text-xs font-semibold text-slate-700 leading-relaxed">
                    Workflow Status: <span className="font-extrabold text-slate-900">{simState?.status || 'IDLE'}</span> &bull; Current Stage: {simState?.current_step_name}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {simState?.status === 'COMPLETED'
                      ? 'Mission finished. Reconciliation and CEO Report archived in ledger.'
                      : 'Step through using Next Step or click Run Simulation for autonomous execution.'}
                  </p>
                </div>
              )}
            </div>

            {/* Live Event Stream */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-blue-100 text-blue-800">
                    <FileText className="w-4 h-4" />
                  </div>
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-800">
                    Live Event Stream
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-slate-500">
                  {simState?.live_event_feed?.length ?? 0} events
                </span>
              </div>

              <div className="space-y-2.5 overflow-y-auto max-h-[450px] pr-1.5 scrollbar-thin">
                {simState?.live_event_feed?.map((ev, idx) => {
                  const act = ev.action.toUpperCase();
                  let badgeStyle = "bg-slate-200/90 text-slate-700";
                  if (act.includes('APPROV') || act.includes('CAPTURED') || act.includes('RECONCILED') || act.includes('COMPLETED')) {
                    badgeStyle = act.includes('REQUIRED') ? "bg-rose-100 text-rose-800 font-bold" : "bg-emerald-100 text-emerald-800 font-bold";
                  } else if (act.includes('PAYMENT') || act.includes('ORDER')) {
                    badgeStyle = "bg-blue-100 text-blue-800 font-bold";
                  } else if (act.includes('POLICY') || act.includes('ASSIGNED')) {
                    badgeStyle = "bg-purple-100 text-purple-800 font-bold";
                  } else if (act.includes('FAILED') || act.includes('REJECTED')) {
                    badgeStyle = "bg-red-100 text-red-800 font-bold";
                  }

                  return (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs space-y-1.5 hover:bg-slate-100/90 transition shadow-2xs"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-extrabold text-slate-900">{ev.agent}</span>
                        <span className="font-mono text-[10px] text-slate-400 shrink-0">{ev.timestamp}</span>
                      </div>
                      <div className="flex items-start gap-2 pt-0.5">
                        <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded shrink-0 mt-0.5 ${badgeStyle}`}>
                          {ev.action}
                        </span>
                        <p className="text-[11.5px] text-slate-800 font-medium leading-relaxed whitespace-normal break-words flex-1 select-text">
                          {ev.details}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 2: STANDALONE CALCULATOR (PRESERVED) */}
      {mode === 'calculator' && (
        <div className="space-y-6">
          <div className="bg-emerald-50/80 p-6 rounded-2xl border border-emerald-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-xl bg-emerald-200/80 text-emerald-900 shadow-xs">
                  <Cpu className="w-5 h-5" />
                </div>
                <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
                  Recovery Scenario Calculator
                </h2>
              </div>
              <p className="text-xs font-semibold text-slate-600 mt-1">
                Deterministic calculation engine for raw SKU evaluation.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-5">
              <form onSubmit={handleRunAnalysis} className="space-y-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                    Target SKU
                  </label>
                  <input
                    type="text"
                    value={calcSku}
                    onChange={(e) => setCalcSku(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                    Source Store
                  </label>
                  <input
                    type="text"
                    value={calcStore}
                    onChange={(e) => setCalcStore(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isCalculating}
                  className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs rounded-xl shadow-md cursor-pointer flex items-center justify-center gap-2"
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>Calculate Decision</span>
                </button>
              </form>
            </div>

            <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6">
              {calcResult ? (
                <div className="space-y-4">
                  <h3 className="text-sm font-extrabold text-slate-900 uppercase">Analysis Output</h3>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div className="p-3 rounded-xl bg-slate-50 border">
                      <span className="text-slate-500">Recommendation:</span>
                      <p className="font-extrabold text-indigo-700">{calcResult.recommendation}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-50 border">
                      <span className="text-slate-500">Predicted Net Recovery:</span>
                      <p className="font-extrabold text-emerald-700">${calcResult.predicted_recovery}</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-600">{calcResult.reasoning}</p>
                </div>
              ) : (
                <div className="py-16 text-center text-xs text-slate-400 font-bold">
                  Click 'Calculate Decision' to run evaluation.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Floating Verified Payment Success Toast */}
      {paymentToast && (
        <div className="fixed top-5 right-5 z-50 animate-in slide-in-from-top-4 duration-300 max-w-md w-full shadow-2xl rounded-2xl bg-slate-900 border border-emerald-500/50 text-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-black tracking-wide text-emerald-300 uppercase">
                  PayPal Sandbox Payment Captured
                </h4>
                <p className="text-[11px] text-slate-300 font-medium mt-0.5">
                  Verified capture: <span className="font-mono text-white font-bold">${paymentToast.amount.toFixed(2)} {paymentToast.currency}</span>
                </p>
              </div>
            </div>
            <button
              onClick={() => setPaymentToast(null)}
              className="text-slate-400 hover:text-white p-1 rounded-lg transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800 text-[10px] font-mono text-slate-400 space-y-1">
            <div className="flex items-center justify-between">
              <span>Payment ID:</span>
              <span className="text-emerald-300 font-bold">{paymentToast.payment_id}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Capture ID:</span>
              <span className="text-emerald-300">{paymentToast.paypal_capture_id}</span>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Payment Modal */}
      {inspectedPayment && (
        <div className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="relative max-w-2xl w-full bg-slate-900 text-white rounded-2xl border border-slate-700 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  <Receipt className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-white uppercase tracking-wider">
                    Verified PayPal Transaction Record
                  </h3>
                  <p className="text-[11px] font-mono text-slate-400">
                    GET /api/payments/{inspectedPayment.payment_id} &bull; HTTP 200 OK
                  </p>
                </div>
              </div>
              <button
                onClick={() => setInspectedPayment(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
              {/* Structured Audit Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60">
                  <span className="text-[10px] text-slate-400 uppercase font-bold block">Internal Payment ID</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="font-mono text-emerald-400 font-extrabold text-xs">{inspectedPayment.payment_id}</span>
                    <button
                      onClick={() => copyToClipboard(inspectedPayment.payment_id, 'modal_payment_id')}
                      className="p-1 text-slate-400 hover:text-white transition cursor-pointer"
                    >
                      {copiedKey === 'modal_payment_id' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60">
                  <span className="text-[10px] text-slate-400 uppercase font-bold block">PayPal Capture ID</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="font-mono text-emerald-400 font-extrabold text-xs">{inspectedPayment.paypal_capture_id || inspectedPayment.capture_id || 'N/A'}</span>
                    <button
                      onClick={() => copyToClipboard(inspectedPayment.paypal_capture_id || inspectedPayment.capture_id || '', 'modal_capture_id')}
                      className="p-1 text-slate-400 hover:text-white transition cursor-pointer"
                    >
                      {copiedKey === 'modal_capture_id' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60">
                  <span className="text-[10px] text-slate-400 uppercase font-bold block">PayPal Order ID</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="font-mono text-slate-200 text-xs">{inspectedPayment.paypal_order_id || 'N/A'}</span>
                    <button
                      onClick={() => copyToClipboard(inspectedPayment.paypal_order_id || '', 'modal_order_id')}
                      className="p-1 text-slate-400 hover:text-white transition cursor-pointer"
                    >
                      {copiedKey === 'modal_order_id' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/60">
                  <span className="text-[10px] text-slate-400 uppercase font-bold block">Status & Reconciliation</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                      {inspectedPayment.status}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-blue-500/20 text-blue-300 border border-blue-500/40 font-bold">
                      {inspectedPayment.reconciliation_status || 'RECONCILED'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Settlement Accounting Breakdown */}
              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-2">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Settlement Accounting</span>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-slate-900/60 p-2 rounded-lg">
                    <span className="text-[10px] text-slate-400 block">Gross Paid</span>
                    <span className="text-xs font-bold text-white">${Number(inspectedPayment.amount).toFixed(2)} {inspectedPayment.currency}</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded-lg">
                    <span className="text-[10px] text-slate-400 block">PayPal Fee</span>
                    <span className="text-xs font-bold text-rose-400">-${Number(inspectedPayment.fee_amount || 0).toFixed(2)} {inspectedPayment.currency}</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded-lg">
                    <span className="text-[10px] text-slate-400 block">Net Proceeds</span>
                    <span className="text-xs font-bold text-emerald-400">${Number(inspectedPayment.net_amount || inspectedPayment.amount).toFixed(2)} {inspectedPayment.currency}</span>
                  </div>
                </div>
              </div>

              {/* Raw JSON inspection */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Raw JSON Payload</span>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(inspectedPayment, null, 2), 'raw_json')}
                    className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
                  >
                    {copiedKey === 'raw_json' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedKey === 'raw_json' ? 'Copied JSON' : 'Copy JSON'}</span>
                  </button>
                </div>
                <pre className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48 leading-relaxed">
                  {JSON.stringify(inspectedPayment, null, 2)}
                </pre>
              </div>
            </div>

            <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setInspectedPayment(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-xl transition cursor-pointer"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Official PayPal Sandbox Checkout Modal (Scenario D) */}
      {isPayPalModalOpen && activeRecoveryOrder && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="relative animate-in fade-in zoom-in duration-200">
            <PayPalCheckout
              order={activeRecoveryOrder}
              isModal={true}
              onClose={() => setIsPayPalModalOpen(false)}
              onPaymentSuccess={handlePayPalPaymentSuccess}
            />
          </div>
        </div>
      )}
    </div>
  );
};
