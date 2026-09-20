import React, { useState, useMemo } from 'react';
import { RiskItem, RiskLevel } from '../../types';
import { ChevronDown, ChevronUp, AlertCircle, AlertTriangle } from 'lucide-react';

interface SkuTableProps {
  data: RiskItem[];
  onRowClick: (sku: string, store: string) => void;
}

type SortField = 'sku_id' | 'store_id' | 'days_to_expiry' | 'at_risk_quantity' | 'at_risk_value' | 'risk_score';
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
      setSortOrder('desc'); // Default to descending when changing sort
    }
  };

  const filteredData = useMemo(() => {
    return data.filter(item => filter === 'ALL' || item.risk_level === filter);
  }, [data, filter]);

  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      
      return sortOrder === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
  }, [filteredData, sortField, sortOrder]);

  const getExpiryColor = (days: number) => {
    if (days <= 3) return 'text-semantic-red';
    if (days <= 6) return 'text-semantic-amber';
    return 'text-semantic-green';
  };

  const getRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL': return <span className="bg-semantic-red/20 text-semantic-red border border-semantic-red/30 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">Critical</span>;
      case 'HIGH': return <span className="bg-semantic-amber/20 text-semantic-amber border border-semantic-amber/30 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">High</span>;
      case 'MEDIUM': return <span className="bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">Medium</span>;
      case 'LOW': return <span className="bg-semantic-green/20 text-semantic-green border border-semantic-green/30 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">Low</span>;
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-1" /> : <ChevronDown className="h-3 w-3 inline ml-1" />;
  };

  const getRowBg = (level: RiskLevel) => {
    if (level === 'CRITICAL') return 'bg-[#0e0a08] hover:bg-[#1a0f0a]';
    if (level === 'HIGH') return 'bg-panel hover:bg-card';
    if (level === 'MEDIUM') return 'bg-[#0f1218] hover:bg-card';
    return 'bg-panel hover:bg-card';
  };

  return (
    <div className="flex flex-col h-full rounded border border-border bg-panel overflow-hidden">
      
      {/* Filters Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-panel/50">
        <h2 className="text-sm font-semibold text-text-primary tracking-wide">Network Risk Assessment</h2>
        <div className="flex items-center space-x-2">
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((level) => (
            <button
              key={level}
              onClick={() => setFilter(level as RiskLevel | 'ALL')}
              className={`px-3 py-1 text-[11px] font-medium tracking-wider uppercase rounded transition-colors border ${
                filter === level
                  ? 'bg-border text-text-primary border-text-muted'
                  : 'bg-transparent text-text-secondary border-transparent hover:bg-border/50'
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
            <tr className="bg-page border-b border-border text-[10px] uppercase tracking-wider text-text-secondary">
              <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors" onClick={() => handleSort('sku_id')}>
                SKU <SortIcon field="sku_id" />
              </th>
              <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors" onClick={() => handleSort('store_id')}>
                Store <SortIcon field="store_id" />
              </th>
              <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('days_to_expiry')}>
                Expiry <SortIcon field="days_to_expiry" />
              </th>
              <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('at_risk_quantity')}>
                At-Risk Units <SortIcon field="at_risk_quantity" />
              </th>
              <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('at_risk_value')}>
                Value <SortIcon field="at_risk_value" />
              </th>
              <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-center" onClick={() => handleSort('risk_score')}>
                Risk Score <SortIcon field="risk_score" />
              </th>
              <th className="px-4 py-2 font-semibold text-center">
                Level
              </th>
              <th className="px-4 py-2 font-semibold text-right">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sortedData.map((item) => (
              <tr 
                key={`${item.sku_id}-${item.store_id}`}
                onClick={() => onRowClick(item.sku_id, item.store_id)}
                className={`group cursor-pointer transition-colors ${getRowBg(item.risk_level)}`}
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') onRowClick(item.sku_id, item.store_id); }}
              >
                <td className="px-4 py-2.5 whitespace-nowrap">
                  <span className="font-mono text-xs text-text-primary font-medium">{item.sku_id}</span>
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap">
                  <span className="text-xs text-text-secondary">{item.store_id}</span>
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap text-right">
                  <span className={`text-xs font-mono font-medium ${getExpiryColor(item.days_to_expiry)}`}>
                    {item.days_to_expiry}d
                  </span>
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap text-right">
                  <span className="text-xs text-text-primary font-medium">{item.at_risk_quantity}</span>
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap text-right">
                  <span className="text-xs font-mono text-text-secondary">₹{item.at_risk_value.toLocaleString()}</span>
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap text-center">
                  <div className="flex items-center justify-center space-x-1.5">
                    {item.risk_score >= 80 && <AlertTriangle className="h-3 w-3 text-semantic-red" />}
                    <span className="text-xs font-mono font-medium text-text-primary">{item.risk_score}</span>
                  </div>
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap text-center">
                  {getRiskBadge(item.risk_level)}
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap text-right text-xs">
                  <span className="text-semantic-blue font-medium group-hover:underline">Review</span>
                </td>
              </tr>
            ))}
            {sortedData.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-text-muted">
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
