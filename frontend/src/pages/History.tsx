import React, { useState } from 'react';
import { Database, Search, ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';

interface HistoryRecord {
  transfer_id: string;
  sku_id: string;
  route: string;
  action_taken: string;
  units_sold: number;
  actual_net_recovery: number;
  accuracy: string;
}

const initialHistoryData: HistoryRecord[] = [
  {
    transfer_id: 'TRF-106094',
    sku_id: 'YOG-001',
    route: 'STORE_A → STORE_B',
    action_taken: 'INTER_STORE_TRANSFER',
    units_sold: 112,
    actual_net_recovery: 11200,
    accuracy: '96%',
  },
  {
    transfer_id: 'TRF-105581',
    sku_id: 'MILK-204',
    route: 'STORE_C → STORE_A',
    action_taken: 'MARKDOWN_DISCOUNT_50',
    units_sold: 80,
    actual_net_recovery: 7500,
    accuracy: '93%',
  },
  {
    transfer_id: 'TRF-104920',
    sku_id: 'CHEE-502',
    route: 'STORE_B → STORE_D',
    action_taken: 'INTER_STORE_TRANSFER',
    units_sold: 40,
    actual_net_recovery: 15800,
    accuracy: '97%',
  },
  {
    transfer_id: 'TRF-103819',
    sku_id: 'BERR-109',
    route: 'STORE_A → SUPPLIER_DC',
    action_taken: 'VENDOR_BUYBACK_RETURN',
    units_sold: 200,
    actual_net_recovery: 6500,
    accuracy: '100%',
  },
];

export const History: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<HistoryRecord[]>(initialHistoryData);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = (e?: React.FormEvent, presetQuery?: string) => {
    if (e) e.preventDefault();
    const query = presetQuery !== undefined ? presetQuery : searchQuery;
    setSearchQuery(query);
    setIsSearching(true);

    setTimeout(() => {
      if (!query.trim()) {
        setResults(initialHistoryData);
      } else {
        const lower = query.toLowerCase();
        const filtered = initialHistoryData.filter(
          (item) =>
            item.sku_id.toLowerCase().includes(lower) ||
            item.transfer_id.toLowerCase().includes(lower) ||
            item.action_taken.toLowerCase().includes(lower) ||
            item.route.toLowerCase().includes(lower)
        );
        setResults(filtered.length > 0 ? filtered : initialHistoryData);
      }
      setIsSearching(false);
    }, 400);
  };

  return (
    <div className="space-y-6 flex flex-col min-h-[calc(100vh-100px)] selection:bg-emerald-100">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-emerald-50/80 p-6 rounded-2xl border border-emerald-200/80 shadow-xs flex-shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-emerald-200/80 text-emerald-900 shadow-xs">
              <Database className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Historical Intelligence
            </h1>
          </div>
          <p className="text-xs font-semibold text-slate-600 mt-1">
            Semantic vector search across historical recovery decisions powered by OpenSearch.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-emerald-900 bg-emerald-100/80 px-3.5 py-1.5 rounded-xl border border-emerald-300/60 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-emerald-600" />
            OpenSearch Vector Index Active
          </span>
        </div>
      </div>

      {/* Main Content Box */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden flex flex-col flex-1">
        {/* Search Input Bar */}
        <div className="p-6 border-b border-slate-100 bg-slate-50/50 space-y-4">
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search historical outcomes... (e.g. 'YOG-001 behavior' or 'Cold Chain partners')"
                className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-2xs"
              />
            </div>
            <button
              type="submit"
              disabled={isSearching}
              className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center gap-2"
            >
              {isSearching ? (
                <span>Searching...</span>
              ) : (
                <>
                  <span>Search</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Query Sample Pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-extrabold uppercase text-slate-400 tracking-wider">
              Suggested Queries:
            </span>
            {['YOG-001 behavior', 'Cold Chain partners', 'High recovery rates'].map(
              (query) => (
                <button
                  key={query}
                  type="button"
                  onClick={() => handleSearch(undefined, query)}
                  className="px-2.5 py-1 bg-white hover:bg-emerald-50 text-slate-600 hover:text-emerald-700 border border-slate-200/80 rounded-lg text-[10px] font-bold transition-all shadow-2xs"
                >
                  {query}
                </button>
              )
            )}
          </div>
        </div>

        {/* Results Table */}
        <div className="overflow-x-auto flex-1 relative">
          {isSearching ? (
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
                  <th className="px-5 py-3">Transfer ID</th>
                  <th className="px-5 py-3">SKU</th>
                  <th className="px-5 py-3">Route</th>
                  <th className="px-5 py-3">Action Taken</th>
                  <th className="px-5 py-3 text-right">Units Sold</th>
                  <th className="px-5 py-3 text-right">Actual Net Recovery</th>
                  <th className="px-5 py-3 text-center">Accuracy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {results.map((item) => (
                  <tr
                    key={item.transfer_id}
                    className="hover:bg-slate-50/80 transition-all"
                  >
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                        {item.transfer_id}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="font-mono text-xs font-bold text-slate-800">
                        {item.sku_id}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="text-xs font-mono font-medium text-slate-600">
                        {item.route}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                        {item.action_taken}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-right font-mono text-xs font-bold text-slate-800">
                      {item.units_sold}
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-right font-mono text-xs font-extrabold text-emerald-700">
                      ₹{item.actual_net_recovery.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-center">
                      <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        {item.accuracy}
                      </span>
                    </td>
                  </tr>
                ))}
                {results.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-12 text-center text-xs text-slate-400 font-bold uppercase tracking-widest"
                    >
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