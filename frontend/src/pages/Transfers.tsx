import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api';
import { Transfer, TransferStatus } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { format } from 'date-fns';

type SortField = 'transfer_id' | 'sku_id' | 'source_store_id' | 'quantity' | 'expected_recovery' | 'created_at';
type SortOrder = 'asc' | 'desc';

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
        if (mounted) setTransfers(data);
      } catch (error) {
        console.error("Failed to load transfers:", error);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
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
    return transfers.filter(item => filter === 'ALL' || item.status === filter);
  }, [transfers, filter]);

  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      
      // Handle missing numbers
      if (aVal === undefined || aVal === null) aVal = 0;
      if (bVal === undefined || bVal === null) bVal = 0;

      return sortOrder === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
  }, [filteredData, sortField, sortOrder]);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-1" /> : <ChevronDown className="h-3 w-3 inline ml-1" />;
  };

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">Active Transfers</h1>
          <p className="text-text-secondary mt-1 text-sm">Monitor operational status of inventory shipments.</p>
        </div>
      </div>

      <div className="flex flex-col flex-1 rounded border border-border bg-panel overflow-hidden">
        {/* Filters Header */}
        <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-panel/50">
          <h2 className="text-sm font-semibold text-text-primary tracking-wide">Transfer Manifest</h2>
          <div className="flex items-center space-x-2 overflow-x-auto">
            {['ALL', 'CREATED', 'APPROVED', 'ASSIGNED', 'IN_TRANSIT', 'COMPLETED', 'FAILED'].map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status as TransferStatus | 'ALL')}
                className={`px-3 py-1 text-[11px] font-medium tracking-wider uppercase rounded transition-colors border whitespace-nowrap ${
                  filter === status
                    ? 'bg-border text-text-primary border-text-muted'
                    : 'bg-transparent text-text-secondary border-transparent hover:bg-border/50'
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
            <div className="absolute inset-0 flex items-center justify-center text-text-muted">
              <div className="animate-pulse flex items-center space-x-2">
                <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
                <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
                <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
              </div>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-page border-b border-border text-[10px] uppercase tracking-wider text-text-secondary">
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors" onClick={() => handleSort('transfer_id')}>
                    ID <SortIcon field="transfer_id" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors" onClick={() => handleSort('sku_id')}>
                    SKU <SortIcon field="sku_id" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors" onClick={() => handleSort('source_store_id')}>
                    Route <SortIcon field="source_store_id" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('quantity')}>
                    Qty <SortIcon field="quantity" />
                  </th>
                  <th className="px-4 py-2 font-semibold text-center">
                    Status
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('expected_recovery')}>
                    Expected Recovery <SortIcon field="expected_recovery" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('created_at')}>
                    Created <SortIcon field="created_at" />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sortedData.map((item) => (
                  <tr 
                    key={item.transfer_id}
                    onClick={() => navigate(`/transfers/${item.transfer_id}`)}
                    className="group cursor-pointer bg-panel hover:bg-card transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-text-primary font-medium">{item.transfer_id.substring(0, 8)}...</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-text-secondary">{item.sku_id}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center text-xs space-x-2">
                        <span className="text-text-primary font-mono">{item.source_store_id}</span>
                        <span className="text-text-muted">→</span>
                        <span className="text-text-primary font-mono">{item.destination_store_id}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs text-text-primary font-mono">{item.quantity}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-semantic-green">
                        {item.expected_recovery ? `₹${item.expected_recovery.toLocaleString()}` : '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-text-muted">
                        {format(new Date(item.created_at), 'MMM d, HH:mm')}
                      </span>
                    </td>
                  </tr>
                ))}
                {sortedData.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-text-muted">
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
