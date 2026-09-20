import React, { useState, useMemo } from 'react';
import { RiskItem, RiskLevel } from '../../types';
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';

interface SkuTableProps {
  data: RiskItem[];
  onRowClick: (sku: string, store: string) => void;
}

type SortField =
  | 'sku_id'
  | 'store_id'
  | 'days_to_expiry'
  | 'at_risk_quantity'
  | 'at_risk_value'
  | 'risk_score';

type SortOrder = 'asc' | 'desc';

export const SkuTable: React.FC<SkuTableProps> = ({ data, onRowClick }) => {
  const [filter, setFilter] = useState<RiskLevel | 'ALL'>('ALL');
  const [sortField, setSortField] = useState<SortField>('risk_score');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const filteredData = useMemo(() => {
    return data.filter((item) => filter === 'ALL' || item.risk_level === filter);
  }, [data, filter]);

  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortOrder === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [filteredData, sortField, sortOrder]);

  const getExpiryColor = (days: number) => {
    if (days <= 3) return 'text-red-600 font-bold';
    if (days <= 6) return 'text-amber-600 font-bold';
    return 'text-emerald-600 font-medium';
  };

  const getRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL':
        return (
          <span className="bg-red-100 text-red-800 border border-red-300 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider">
            Critical
          </span>
        );
      case 'HIGH':
        return (
          <span className="bg-amber-100 text-amber-800 border border-amber-300 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider">
            High
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="bg-yellow-100 text-yellow-800 border border-yellow-300 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider">
            Medium
          </span>
        );
      case 'LOW':
        return (
          <span className="bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider">
            Low
          </span>
        );
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? (
      <ChevronUp className="h-3 w-3 inline ml-1 text-emerald-600" />
    ) : (
      <ChevronDown className="h-3 w-3 inline ml-1 text-emerald-600" />
    );
  };

  const getRowBg = (level: RiskLevel) => {
    if (level === 'CRITICAL') return 'bg-red-50/40 hover:bg-red-50/80';
    if (level === 'HIGH') return 'bg-amber-50/30 hover:bg-amber-50/70';
    return 'bg-white hover:bg-slate-50';
  };

  return (
    <div className="flex flex-col h-full rounded-2xl border border-slate-200/80 bg-white shadow-xs overflow-hidden">
      {/* Filters Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
        <h2 className="text-sm font-extrabold text-slate-900 tracking-tight">
          Network Risk Assessment
        </h2>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1.5 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60">
          {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((level) => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`px-3 py-1 text-[10px] font-bold tracking-wider uppercase rounded-lg transition-all ${
                filter === level
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] uppercase tracking-wider text-slate-500 font-bold">
              <th
                className="px-4 py-3 cursor-pointer hover:text-slate-900 transition-colors"
                onClick={() => handleSort('sku_id')}
              >
                SKU <SortIcon field="sku_id" />
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:text-slate-900 transition-colors"
                onClick={() => handleSort('store_id')}
              >
                Store <SortIcon field="store_id" />
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:text-slate-900 transition-colors text-right"
                onClick={() => handleSort('days_to_expiry')}
              >
                Expiry <SortIcon field="days_to_expiry" />
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:text-slate-900 transition-colors text-right"
                onClick={() => handleSort('at_risk_quantity')}
              >
                At-Risk Units <SortIcon field="at_risk_quantity" />
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:text-slate-900 transition-colors text-right"
                onClick={() => handleSort('at_risk_value')}
              >
                Value <SortIcon field="at_risk_value" />
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:text-slate-900 transition-colors text-center"
                onClick={() => handleSort('risk_score')}
              >
                Risk Score <SortIcon field="risk_score" />
              </th>
              <th className="px-4 py-3 text-center">Level</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedData.map((item) => (
              <tr
                key={`${item.sku_id}-${item.store_id}`}
                onClick={() => onRowClick(item.sku_id, item.store_id)}
                className={`group cursor-pointer transition-colors ${getRowBg(item.risk_level)}`}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onRowClick(item.sku_id, item.store_id);
                }}
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="font-mono text-xs text-slate-900 font-bold">
                    {item.sku_id}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-xs text-slate-600 font-medium">
                    {item.store_id}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className={`text-xs font-mono ${getExpiryColor(item.days_to_expiry)}`}>
                    {item.days_to_expiry}d
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className="text-xs text-slate-900 font-bold">
                    {item.at_risk_quantity}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className="text-xs font-mono font-bold text-slate-800">
                    ₹{item.at_risk_value.toLocaleString()}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-center">
                  <div className="flex items-center justify-center space-x-1.5">
                    {item.risk_score >= 80 && (
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                    )}
                    <span className="text-xs font-mono font-extrabold text-slate-900">
                      {item.risk_score}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-center">
                  {getRiskBadge(item.risk_level)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <button className="px-3 py-1 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white transition-all text-xs font-bold shadow-2xs">
                    Evaluate
                  </button>
                </td>
              </tr>
            ))}

            {sortedData.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-400 font-medium">
                  No risk items found matching the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};