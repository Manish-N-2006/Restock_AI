import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { MetricCard } from '../components/ui/MetricCard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { AlertTriangle, TrendingUp, Truck, DollarSign } from 'lucide-react';
import { Transfer, Outcome } from '../types';
import { useNavigate } from 'react-router-dom';

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
          api.getRiskItems()
        ]);
        if (mounted) {
          setTransfers(transfersData);
          setOutcomes(outcomesData);
          setRiskCount(riskData.length);
        }
      } catch (error) {
        console.error("Failed to load overview data:", error);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, []);

  const activeTransfers = transfers.filter(t => 
    !['COMPLETED', 'CANCELLED', 'FAILED'].includes(t.status)
  );

  const totalRecoveredValue = outcomes.reduce((sum, o) => sum + (o.actual_recovery || 0), 0);

  // Mock sparkline data for visual aesthetic in the war room
  const riskSparkline = [50, 40, 45, 60, 55, 65, 75, riskCount * 10];
  const recoverySparkline = [1000, 3000, 2500, 5000, 4500, 7000, 10000, 15000];
  const transfersSparkline = [1, 2, 2, 4, 3, 5, 4, activeTransfers.length];
  const valueSparkline = [10, 15, 20, 18, 30, 40, 35, 50];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted">
        <div className="animate-pulse flex items-center space-x-2">
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* KPI Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard 
          title="At-Risk SKUs"
          value={riskCount}
          icon={<AlertTriangle className="h-4 w-4 text-semantic-red" />}
          trend={{ value: 12, isPositive: false, label: 'vs yesterday' }}
          sparklineData={riskSparkline}
        />
        <MetricCard 
          title="Potential Recovery"
          value={`₹24,500`}
          icon={<TrendingUp className="h-4 w-4 text-semantic-blue" />}
          trend={{ value: 8, isPositive: true, label: 'vs yesterday' }}
          sparklineData={recoverySparkline}
        />
        <MetricCard 
          title="Active Transfers"
          value={activeTransfers.length}
          icon={<Truck className="h-4 w-4 text-semantic-amber" />}
          trend={{ value: 2, isPositive: true, label: 'vs yesterday' }}
          sparklineData={transfersSparkline}
        />
        <MetricCard 
          title="Value Recovered"
          value={`₹${totalRecoveredValue.toLocaleString()}`}
          icon={<DollarSign className="h-4 w-4 text-semantic-green" />}
          trend={{ value: 24, isPositive: true, label: 'mtd' }}
          sparklineData={valueSparkline}
        />
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Active Operations */}
        <div className="bg-panel border border-border rounded-lg shadow-sm flex flex-col max-h-[500px]">
          <div className="px-5 py-4 border-b border-border bg-[#14161a] rounded-t-lg">
            <h2 className="text-[13px] font-bold text-text-primary tracking-wider uppercase">Active Operations</h2>
          </div>
          <div className="divide-y divide-border overflow-y-auto flex-1">
            {activeTransfers.slice(0, 8).map(transfer => (
              <div 
                key={transfer.transfer_id} 
                className="px-5 py-4 flex items-center justify-between hover:bg-card cursor-pointer transition-colors"
                onClick={() => navigate(`/transfers`)}
              >
                <div>
                  <p className="text-sm font-mono font-medium text-text-primary">{transfer.sku_id}</p>
                  <p className="text-xs text-text-secondary mt-1 tracking-wide">
                    {transfer.source_store_id} <span className="text-text-muted mx-1">→</span> {transfer.destination_store_id} 
                    <span className="ml-2 px-1.5 py-0.5 bg-card border border-border rounded text-[10px] text-text-muted">
                      {transfer.quantity} UNITS
                    </span>
                  </p>
                </div>
                <StatusBadge status={transfer.status} />
              </div>
            ))}
            {activeTransfers.length === 0 && (
              <div className="px-6 py-8 text-center text-xs text-text-muted uppercase tracking-widest">
                No active transfers.
              </div>
            )}
          </div>
        </div>

        {/* Recent Outcomes */}
        <div className="bg-panel border border-border rounded-lg shadow-sm flex flex-col max-h-[500px]">
          <div className="px-5 py-4 border-b border-border bg-[#14161a] rounded-t-lg">
            <h2 className="text-[13px] font-bold text-text-primary tracking-wider uppercase">Recent Outcomes</h2>
          </div>
          <div className="divide-y divide-border overflow-y-auto flex-1">
            {outcomes.slice(0, 8).map(outcome => (
              <div key={outcome.outcome_id} className="px-5 py-4 hover:bg-card transition-colors">
                <div className="flex justify-between items-center mb-2">
                  <p className="text-sm font-mono text-text-primary">{outcome.transfer_id}</p>
                  <span className={`text-[11px] font-bold font-mono px-2 py-0.5 rounded border ${(outcome.variance ?? 0) >= 0 ? 'bg-semantic-green/10 text-semantic-green border-semantic-green/20' : 'bg-semantic-red/10 text-semantic-red border-semantic-red/20'}`}>
                    {(outcome.variance ?? 0) >= 0 ? '+' : ''}₹{(outcome.variance ?? 0).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <div className="text-[10px] font-mono text-text-secondary flex space-x-4">
                    <span><span className="text-text-muted">EST:</span> ₹{outcome.predicted_recovery.toLocaleString()}</span>
                    <span><span className="text-text-muted">ACT:</span> ₹{(outcome.actual_recovery ?? 0).toLocaleString()}</span>
                  </div>
                  <span className={`text-[9px] uppercase tracking-widest font-bold ${outcome.status === 'FINALIZED' ? 'text-text-secondary' : 'text-semantic-amber'}`}>
                    {outcome.status}
                  </span>
                </div>
              </div>
            ))}
            {outcomes.length === 0 && (
              <div className="px-6 py-8 text-center text-xs text-text-muted uppercase tracking-widest">
                No finalized outcomes yet.
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
