import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { HistoricalRecord } from '../types';
import { Search, Database, ArrowRight } from 'lucide-react';

export const History: React.FC = () => {
  const [history, setHistory] = useState<HistoricalRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [searchTrigger, setSearchTrigger] = useState(0);

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      setIsLoading(true);
      try {
        const data = await api.getHistory(query);
        if (mounted) setHistory(data.results || []);
      } catch (error) {
        console.error("Failed to load history:", error);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, [searchTrigger]); // eslint-disable-line

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchTrigger(prev => prev + 1);
  };

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight flex items-center space-x-2">
            <Database className="h-5 w-5 text-semantic-blue" />
            <span>Historical Intelligence</span>
          </h1>
          <p className="text-text-secondary mt-1 text-sm">Semantic search powered by OpenSearch.</p>
        </div>
      </div>

      <div className="flex flex-col flex-1 rounded border border-border bg-panel overflow-hidden">
        
        {/* Search Bar / Header */}
        <div className="p-4 border-b border-border bg-[#14161a]">
          <form onSubmit={handleSearch} className="flex space-x-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-text-muted" />
              </div>
              <input 
                type="text" 
                placeholder="Search historical outcomes... (e.g. 'YOG-001 behavior' or 'Cold Chain partners')"
                className="w-full pl-9 pr-4 py-2 border border-border bg-page text-text-primary rounded focus:outline-none focus:border-semantic-blue font-mono text-sm placeholder-text-muted transition-colors"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <button 
              type="submit" 
              disabled={isLoading}
              className="px-6 py-2 bg-semantic-blue hover:bg-semantic-blue/90 text-white font-bold uppercase tracking-wider text-[11px] rounded transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Querying...' : 'Search'}
            </button>
          </form>
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
                  <th className="px-4 py-2 font-semibold">Transfer ID</th>
                  <th className="px-4 py-2 font-semibold">SKU</th>
                  <th className="px-4 py-2 font-semibold">Route</th>
                  <th className="px-4 py-2 font-semibold">Action Taken</th>
                  <th className="px-4 py-2 font-semibold text-right">Units Sold</th>
                  <th className="px-4 py-2 font-semibold text-right">Actual Net Recovery</th>
                  <th className="px-4 py-2 font-semibold text-right">Accuracy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((item, idx) => (
                  <tr 
                    key={item.transfer_id || idx}
                    className="group bg-panel hover:bg-card transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-text-primary font-medium">
                        {item.transfer_id ? item.transfer_id.substring(0, 8) + '...' : 'N/A'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-text-secondary">{item.sku_id}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center text-xs space-x-2">
                        <span className="text-text-primary font-mono">{item.source_store_id}</span>
                        {item.destination_store_id && (
                          <>
                            <span className="text-text-muted"><ArrowRight className="h-3 w-3" /></span>
                            <span className="text-text-primary font-mono">{item.destination_store_id}</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-[11px] font-bold tracking-wider uppercase text-semantic-blue bg-semantic-blue/10 px-2 py-0.5 rounded border border-semantic-blue/20">
                        {item.action || 'TRANSFER'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs text-text-primary font-mono">
                        {item.actual_units_sold !== undefined ? item.actual_units_sold : '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-semantic-green font-medium">
                        {item.actual_net_recovery !== undefined ? `₹${item.actual_net_recovery.toLocaleString()}` : '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-xs font-mono text-text-secondary">
                        {item.recovery_accuracy_percentage !== undefined ? `${item.recovery_accuracy_percentage.toFixed(1)}%` : '-'}
                      </span>
                    </td>
                  </tr>
                ))}
                {history.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-text-muted font-mono">
                      No historical records matched your semantic query.
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
