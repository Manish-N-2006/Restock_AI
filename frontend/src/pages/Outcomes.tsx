import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api';
import { Outcome } from '../types';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { format } from 'date-fns';

type SortField = 'transfer_id' | 'predicted_recovery' | 'actual_recovery' | 'variance' | 'sell_through_rate' | 'recovery_accuracy';
type SortOrder = 'asc' | 'desc';

export const Outcomes: React.FC = () => {
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>('transfer_id');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const data = await api.getOutcomes();
        if (mounted) setOutcomes(data);
      } catch (error) {
        console.error("Failed to load outcomes:", error);
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

  const sortedData = useMemo(() => {
    return [...outcomes].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      
      if (aVal === undefined || aVal === null) aVal = 0;
      if (bVal === undefined || bVal === null) bVal = 0;

      return sortOrder === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
  }, [outcomes, sortField, sortOrder]);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-1" /> : <ChevronDown className="h-3 w-3 inline ml-1" />;
  };

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">Recovery Outcomes</h1>
          <p className="text-text-secondary mt-1 text-sm">Compare actual recovered value against predicted expectations.</p>
        </div>
      </div>

      <div className="flex flex-col flex-1 rounded border border-border bg-panel overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border bg-panel/50">
          <h2 className="text-sm font-semibold text-text-primary tracking-wide">Outcomes Ledger</h2>
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
                    Transfer ID <SortIcon field="transfer_id" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('predicted_recovery')}>
                    Predicted <SortIcon field="predicted_recovery" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('actual_recovery')}>
                    Actual <SortIcon field="actual_recovery" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('variance')}>
                    Variance <SortIcon field="variance" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('sell_through_rate')}>
                    Sell-Through <SortIcon field="sell_through_rate" />
                  </th>
                  <th className="px-4 py-2 font-semibold cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => handleSort('recovery_accuracy')}>
                    Accuracy <SortIcon field="recovery_accuracy" />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sortedData.map((item) => (
                  <tr 
                    key={item.outcome_id}
                    className="group bg-panel hover:bg-card transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-text-primary font-medium">{item.transfer_id.substring(0, 8)}...</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-text-secondary">₹{item.predicted_recovery.toLocaleString()}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-text-primary font-medium">
                        {item.actual_recovery !== undefined ? `₹${item.actual_recovery.toLocaleString()}` : 'PENDING'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      {item.variance !== undefined ? (
                        <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${
                          item.variance >= 0 
                            ? 'bg-semantic-green/10 text-semantic-green border-semantic-green/20' 
                            : 'bg-semantic-red/10 text-semantic-red border-semantic-red/20'
                        }`}>
                          {item.variance >= 0 ? '+' : ''}₹{item.variance.toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-xs font-mono text-text-muted">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-text-secondary">
                        {item.sell_through_rate !== undefined ? `${(item.sell_through_rate * 100).toFixed(1)}%` : '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-text-secondary">
                        {item.recovery_accuracy !== undefined ? `${(item.recovery_accuracy * 100).toFixed(1)}%` : '-'}
                      </span>
                    </td>
                  </tr>
                ))}
                {sortedData.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-text-muted">
                      No outcomes found.
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
