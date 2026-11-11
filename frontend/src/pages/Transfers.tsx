import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api';
import { Transfer, TransferStatus } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Truck, Filter, ArrowRight } from 'lucide-react';
import { format } from 'date-fns';

type SortField =
  | 'transfer_id'
  | 'sku_id'
  | 'source_store_id'
  | 'quantity'
  | 'expected_recovery'
  | 'created_at';
type SortOrder = 'asc' | 'desc';

// Demo transfer records used as fallback if API database is currently empty
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

export const Transfers: React.FC = () => {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<TransferStatus | 'ALL'>('ALL');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const data = await api.getTransfers();
        if (mounted) {
          setTransfers(data && data.length > 0 ? data : sampleTransfers);
        }
      } catch (error) {
        console.error('Failed to load transfers:', error);
        if (mounted) setTransfers(sampleTransfers);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const filteredData = useMemo(() => {
    return transfers.filter(
      (item) => filter === 'ALL' || item.status === filter
    );
  }, [transfers, filter]);

  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      // Handle missing numbers
      if (aVal === undefined || aVal === null) aVal = 0;
      if (bVal === undefined || bVal === null) bVal = 0;

      return sortOrder === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [filteredData, sortField, sortOrder]);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? (
      <ChevronUp className="h-3 w-3 inline ml-1 text-emerald-600 font-bold" />
    ) : (
      <ChevronDown className="h-3 w-3 inline ml-1 text-emerald-600 font-bold" />
    );
  };

  return (
    <div className="space-y-6 flex flex-col min-h-[calc(100vh-100px)] selection:bg-emerald-100">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-amber-50/80 p-6 rounded-2xl border border-amber-200/80 shadow-xs flex-shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-amber-200/80 text-amber-900 shadow-xs">
              <Truck className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Active Transfers Manifest
            </h1>
          </div>
          <p className="text-xs font-semibold text-slate-600 mt-1">
            Monitor real-time operational status, cold-chain routes, and recovery metrics of inventory shipments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-amber-900 bg-amber-100/80 px-3.5 py-1.5 rounded-xl border border-amber-300/60">
            Total Manifests: <strong className="text-slate-900">{filteredData.length}</strong>
          </span>
        </div>
      </div>

      {/* Main Table Panel */}
      <div className="flex flex-col flex-1 rounded-2xl border border-slate-200/80 bg-white shadow-xs overflow-hidden">
        {/* Filters Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/70">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-emerald-600" />
            <h2 className="text-xs font-extrabold text-slate-800 tracking-wider uppercase">
              Filter Status Manifest
            </h2>
          </div>

          <div className="flex items-center space-x-1.5 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60 overflow-x-auto">
            {[
              'ALL',
              'CREATED',
              'APPROVED',
              'ASSIGNED',
              'IN_TRANSIT',
              'COMPLETED',
              'FAILED',
            ].map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status as TransferStatus | 'ALL')}
                className={`px-3 py-1 text-[10px] font-bold tracking-wider uppercase rounded-lg transition-all whitespace-nowrap ${
                  filter === status
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                {status.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Table Container */}
        <div className="overflow-x-auto flex-1 relative">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400 bg-white/80">
              <div className="animate-pulse flex items-center space-x-2">
                <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
                <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
                <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full"></span>
              </div>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] uppercase tracking-wider text-slate-500 font-extrabold">
                  <th
                    className="px-5 py-3 cursor-pointer hover:text-slate-900 transition-colors"
                    onClick={() => handleSort('transfer_id')}
                  >
                    ID <SortIcon field="transfer_id" />
                  </th>
                  <th
                    className="px-5 py-3 cursor-pointer hover:text-slate-900 transition-colors"
                    onClick={() => handleSort('sku_id')}
                  >
                    SKU <SortIcon field="sku_id" />
                  </th>
                  <th
                    className="px-5 py-3 cursor-pointer hover:text-slate-900 transition-colors"
                    onClick={() => handleSort('source_store_id')}
                  >
                    Route <SortIcon field="source_store_id" />
                  </th>
                  <th
                    className="px-5 py-3 cursor-pointer hover:text-slate-900 transition-colors text-right"
                    onClick={() => handleSort('quantity')}
                  >
                    Qty <SortIcon field="quantity" />
                  </th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th
                    className="px-5 py-3 cursor-pointer hover:text-slate-900 transition-colors text-right"
                    onClick={() => handleSort('expected_recovery')}
                  >
                    Expected Recovery <SortIcon field="expected_recovery" />
                  </th>
                  <th
                    className="px-5 py-3 cursor-pointer hover:text-slate-900 transition-colors text-right"
                    onClick={() => handleSort('created_at')}
                  >
                    Created <SortIcon field="created_at" />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedData.map((item) => (
                  <tr
                    key={item.transfer_id}
                    onClick={() => navigate(`/transfers/${item.transfer_id}`)}
                    className="group cursor-pointer bg-white hover:bg-amber-50/40 transition-all"
                  >
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="font-mono text-xs font-bold text-slate-900 bg-amber-100/60 border border-amber-200/80 px-2 py-0.5 rounded-md">
                        {item.transfer_id.length > 12
                          ? `${item.transfer_id.substring(0, 8)}...`
                          : item.transfer_id}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="font-mono text-xs font-bold text-slate-800">
                        {item.sku_id}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <div className="flex items-center text-xs space-x-2 font-medium text-slate-700">
                        <span className="font-bold text-slate-900">
                          {item.source_store_id}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-amber-500 font-bold" />
                        <span className="font-bold text-slate-900">
                          {item.destination_store_id}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-right">
                      <span className="text-xs text-slate-900 font-mono font-bold">
                        {item.quantity}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-center">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-right">
                      <span className="text-xs font-mono font-bold text-emerald-700">
                        {item.expected_recovery
                          ? `₹${item.expected_recovery.toLocaleString()}`
                          : '-'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-right">
                      <span className="text-xs font-mono font-semibold text-slate-400">
                        {format(new Date(item.created_at), 'MMM d, HH:mm')}
                      </span>
                    </td>
                  </tr>
                ))}
                {sortedData.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-12 text-center text-xs text-slate-400 font-bold uppercase tracking-widest"
                    >
                      No transfers found matching the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};