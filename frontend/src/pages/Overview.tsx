import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { MetricCard } from '../components/ui/MetricCard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { AlertTriangle, TrendingUp, Truck, DollarSign } from 'lucide-react';
import { Transfer, Outcome } from '../types';
import { useNavigate } from 'react-router-dom';

// Sample fallback data to keep the overview war room populated during testing
const sampleTransfers: any[] = [
  {
    transfer_id: 'TRF-10928374',
    sku_id: 'YOG-001',
    source_store_id: 'STORE_A',
    destination_store_id: 'STORE_B',
    quantity: 120,
    status: 'IN_TRANSIT',
    created_at: new Date().toISOString(),
    expected_recovery: 12000,
  },
  {
    transfer_id: 'TRF-10884920',
    sku_id: 'MILK-204',
    source_store_id: 'STORE_C',
    destination_store_id: 'STORE_A',
    quantity: 85,
    status: 'APPROVED',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    expected_recovery: 8500,
  },
  {
    transfer_id: 'TRF-10821039',
    sku_id: 'CHEE-502',
    source_store_id: 'STORE_B',
    destination_store_id: 'STORE_D',
    quantity: 40,
    status: 'ASSIGNED',
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    expected_recovery: 4800,
  },
  {
    transfer_id: 'TRF-10759921',
    sku_id: 'BERR-109',
    source_store_id: 'STORE_A',
    destination_store_id: 'STORE_C',
    quantity: 200,
    status: 'CREATED',
    created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    expected_recovery: 16000,
  },
];

const sampleOutcomes: any[] = [
  {
    outcome_id: 'OUT-001',
    transfer_id: 'TRF-106094',
    predicted_recovery: 10000,
    actual_recovery: 11200,
    variance: 1200,
    status: 'FINALIZED',
  },
  {
    outcome_id: 'OUT-002',
    transfer_id: 'TRF-105581',
    predicted_recovery: 8000,
    actual_recovery: 7500,
    variance: -500,
    status: 'FINALIZED',
  },
  {
    outcome_id: 'OUT-003',
    transfer_id: 'TRF-104920',
    predicted_recovery: 15000,
    actual_recovery: 15800,
    variance: 800,
    status: 'FINALIZED',
  },
];

export const Overview: React.FC = () => {
  const navigate = useNavigate();
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [riskCount, setRiskCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const [transfersData, outcomesData, riskData] = await Promise.all([
          api.getTransfers(),
          api.getOutcomes(),
          api.getRiskItems(),
        ]);

        if (mounted) {
          // Use backend API data if available, otherwise populate with sample data
          setTransfers(
            transfersData && transfersData.length > 0
              ? transfersData
              : sampleTransfers
          );
          setOutcomes(
            outcomesData && outcomesData.length > 0
              ? outcomesData
              : sampleOutcomes
          );
          setRiskCount(
            riskData && riskData.length > 0 ? riskData.length : 12
          );
        }
      } catch (error) {
        console.error('Failed to load overview data:', error);
        if (mounted) {
          setTransfers(sampleTransfers);
          setOutcomes(sampleOutcomes);
          setRiskCount(12);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const activeTransfers = transfers.filter(
    (t) => !['COMPLETED', 'CANCELLED', 'FAILED'].includes(t.status)
  );

  const totalRecoveredValue = outcomes.reduce(
    (sum, o) => sum + (o.actual_recovery || 0),
    0
  );

  // Sparkline chart data formatted for Recharts LineChart
  const riskSparkline = [
    { value: 50 },
    { value: 40 },
    { value: 45 },
    { value: 60 },
    { value: 55 },
    { value: 65 },
    { value: 75 },
    { value: riskCount * 10 },
  ];
  const recoverySparkline = [
    { value: 1000 },
    { value: 3000 },
    { value: 2500 },
    { value: 5000 },
    { value: 4500 },
    { value: 7000 },
    { value: 10000 },
    { value: 15000 },
  ];
  const transfersSparkline = [
    { value: 1 },
    { value: 2 },
    { value: 2 },
    { value: 4 },
    { value: 3 },
    { value: 5 },
    { value: 4 },
    { value: activeTransfers.length },
  ];
  const valueSparkline = [
    { value: 10 },
    { value: 15 },
    { value: 20 },
    { value: 18 },
    { value: 30 },
    { value: 40 },
    { value: 35 },
    { value: 50 },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="animate-pulse flex items-center space-x-2">
          <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
          <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
          <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 selection:bg-emerald-100">
      {/* KPI Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="At-Risk SKUs"
          value={riskCount}
          icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}
          trend={{ value: 12, isPositive: false, label: 'vs yesterday' }}
          type="risk"
          data={riskSparkline}
        />
        <MetricCard
          title="Potential Recovery"
          value="₹24,500"
          icon={<TrendingUp className="h-4 w-4 text-emerald-600" />}
          trend={{ value: 8, isPositive: true, label: 'vs yesterday' }}
          type="recovery"
          data={recoverySparkline}
        />
        <MetricCard
          title="Active Transfers"
          value={activeTransfers.length}
          icon={<Truck className="h-4 w-4 text-slate-700" />}
          trend={{ value: 2, isPositive: true, label: 'vs yesterday' }}
          type="transfers"
          data={transfersSparkline}
        />
        <MetricCard
          title="Value Recovered"
          value={`₹${totalRecoveredValue.toLocaleString()}`}
          icon={<DollarSign className="h-4 w-4 text-white" />}
          trend={{ value: 24, isPositive: true, label: 'mtd' }}
          type="value"
          data={valueSparkline}
        />
      </div>

      {/* Two-Column Operations Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Active Operations Card */}
        <div className="bg-white border border-slate-200/80 rounded-2xl shadow-xs flex flex-col max-h-[500px] overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/70 flex justify-between items-center">
            <h2 className="text-xs font-extrabold text-slate-800 tracking-wider uppercase">
              Active Operations
            </h2>
            <span className="text-[10px] font-bold text-slate-400 bg-slate-200/60 px-2 py-0.5 rounded-full">
              {activeTransfers.length} Live
            </span>
          </div>

          <div className="divide-y divide-slate-100 overflow-y-auto flex-1">
            {activeTransfers.slice(0, 8).map((transfer) => (
              <div
                key={transfer.transfer_id}
                className="px-6 py-4 flex items-center justify-between hover:bg-slate-50/80 cursor-pointer transition-all"
                onClick={() => navigate(`/transfers`)}
              >
                <div>
                  <p className="text-xs font-mono font-bold text-slate-900">
                    {transfer.sku_id}
                  </p>
                  <p className="text-xs text-slate-500 mt-1 font-medium flex items-center gap-1">
                    <span>{transfer.source_store_id}</span>
                    <span className="text-slate-300 font-bold">→</span>
                    <span>{transfer.destination_store_id}</span>
                    <span className="ml-2 px-2 py-0.5 bg-slate-100 border border-slate-200/60 rounded-full text-[10px] font-mono font-bold text-slate-700">
                      {transfer.quantity} UNITS
                    </span>
                  </p>
                </div>
                <StatusBadge status={transfer.status} />
              </div>
            ))}

            {activeTransfers.length === 0 && (
              <div className="px-6 py-12 text-center text-xs text-slate-400 font-bold uppercase tracking-widest">
                No active transfers running.
              </div>
            )}
          </div>
        </div>

        {/* Recent Outcomes Card */}
        <div className="bg-white border border-slate-200/80 rounded-2xl shadow-xs flex flex-col max-h-[500px] overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/70 flex justify-between items-center">
            <h2 className="text-xs font-extrabold text-slate-800 tracking-wider uppercase">
              Recent Outcomes
            </h2>
            <span className="text-[10px] font-bold text-slate-400 bg-slate-200/60 px-2 py-0.5 rounded-full">
              {outcomes.length} Total
            </span>
          </div>

          <div className="divide-y divide-slate-100 overflow-y-auto flex-1">
            {outcomes.slice(0, 8).map((outcome) => (
              <div
                key={outcome.outcome_id}
                className="px-6 py-4 hover:bg-slate-50/80 transition-all"
              >
                <div className="flex justify-between items-center mb-2">
                  <p className="text-xs font-mono font-bold text-slate-900">
                    {outcome.transfer_id}
                  </p>
                  <span
                    className={`text-xs font-bold font-mono px-2.5 py-0.5 rounded-full border ${
                      (outcome.variance ?? 0) >= 0
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                        : 'bg-red-100 text-red-800 border-red-300'
                    }`}
                  >
                    {(outcome.variance ?? 0) >= 0 ? '+' : ''}₹
                    {(outcome.variance ?? 0).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <div className="text-[11px] font-mono text-slate-600 flex space-x-4">
                    <span>
                      <span className="text-slate-400 font-bold">EST:</span> ₹
                      {outcome.predicted_recovery.toLocaleString()}
                    </span>
                    <span>
                      <span className="text-slate-400 font-bold">ACT:</span> ₹
                      {(outcome.actual_recovery ?? 0).toLocaleString()}
                    </span>
                  </div>
                  <span
                    className={`text-[9px] uppercase tracking-widest font-extrabold px-2 py-0.5 rounded-full ${
                      outcome.status === 'FINALIZED'
                        ? 'bg-slate-100 text-slate-600'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {outcome.status}
                  </span>
                </div>
              </div>
            ))}

            {outcomes.length === 0 && (
              <div className="px-6 py-12 text-center text-xs text-slate-400 font-bold uppercase tracking-widest">
                No finalized outcomes recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};