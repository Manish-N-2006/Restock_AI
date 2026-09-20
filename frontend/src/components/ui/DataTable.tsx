import React from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
}

export function DataTable<T>({ columns, data, onRowClick, isLoading = false }: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
        <div className="animate-pulse">
          <div className="h-12 bg-slate-100 border-b border-slate-200" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-white border-b border-slate-100 px-6 py-4 flex items-center space-x-4">
              {columns.map((_, j) => (
                <div key={j} className="h-4 bg-slate-200 rounded w-1/4" />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-8 text-center text-slate-500">
        No data available
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {data.map((item, i) => (
              <tr
                key={i}
                onClick={() => onRowClick && onRowClick(item)}
                className={onRowClick ? 'cursor-pointer hover:bg-slate-50 transition-colors' : ''}
              >
                {columns.map((column) => (
                  <td key={column.key} className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                    {column.render(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
