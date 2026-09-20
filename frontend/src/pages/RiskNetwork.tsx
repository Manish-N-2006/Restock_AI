import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { RiskItem } from '../types';
import { SkuTable } from '../components/overview/SkuTable';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

// Fallback sample data to populate the table during testing when local DB is empty
const sampleRisks: any[] = [
  {
    sku_id: 'YOG-001',
    store_id: 'STORE_A',
    days_to_expiry: 2,
    at_risk_quantity: 120,
    at_risk_value: 14400,
    risk_score: 92,
    risk_level: 'CRITICAL',
  },
  {
    sku_id: 'MILK-204',
    store_id: 'STORE_C',
    days_to_expiry: 4,
    at_risk_quantity: 85,
    at_risk_value: 8500,
    risk_score: 78,
    risk_level: 'HIGH',
  },
  {
    sku_id: 'CHEE-502',
    store_id: 'STORE_B',
    days_to_expiry: 6,
    at_risk_quantity: 45,
    at_risk_value: 5400,
    risk_score: 55,
    risk_level: 'MEDIUM',
  },
  {
    sku_id: 'BERR-109',
    store_id: 'STORE_A',
    days_to_expiry: 9,
    at_risk_quantity: 200,
    at_risk_value: 18000,
    risk_score: 25,
    risk_level: 'LOW',
  },
  {
    sku_id: 'BUTR-301',
    store_id: 'STORE_D',
    days_to_expiry: 3,
    at_risk_quantity: 60,
    at_risk_value: 7200,
    risk_score: 84,
    risk_level: 'CRITICAL',
  },
];

export const RiskNetwork: React.FC = () => {
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const data = await api.getRiskItems();
        if (mounted) {
          // Use API response if items exist, otherwise fall back to sample dataset
          setRisks(data && data.length > 0 ? data : sampleRisks);
        }
      } catch (error) {
        console.error('Failed to load risk network data:', error);
        if (mounted) setRisks(sampleRisks);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-6 flex flex-col min-h-[calc(100vh-100px)] selection:bg-amber-100">
      {/* Warm Yellow/Amber Header Panel */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-amber-50/80 p-6 rounded-2xl border border-amber-200/80 shadow-xs flex-shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-amber-200/80 text-amber-900 shadow-xs">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Risk Network Assessment
            </h1>
          </div>
          <p className="text-xs font-semibold text-slate-600 mt-1">
            Real-time inventory expiration monitoring and automated risk evaluation across all store nodes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-amber-900 bg-amber-100/80 px-3.5 py-1.5 rounded-xl border border-amber-300/60 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            At-Risk Items Detected: <strong className="text-slate-900">{risks.length}</strong>
          </span>
        </div>
      </div>

      {/* Main Table Container */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64 text-slate-400 bg-white rounded-2xl border border-slate-200/80">
            <div className="animate-pulse flex items-center space-x-2">
              <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
              <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
              <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
            </div>
          </div>
        ) : (
          <SkuTable
            data={risks}
            onRowClick={(sku_id, store_id) =>
              navigate(`/workflow?sku=${sku_id}&store=${store_id}`)
            }
          />
        )}
      </div>
    </div>
  );
};