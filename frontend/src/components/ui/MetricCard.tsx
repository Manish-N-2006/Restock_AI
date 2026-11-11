import React from 'react';
import { ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts';

export interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
    label: string;
  };
  type?: 'risk' | 'recovery' | 'transfers' | 'value';
  data?: { value: number }[];
  sparklineData?: number[];
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon,
  trend,
  type = 'transfers',
  data,
  sparklineData,
}) => {
  // Convert array of numbers to object array if sparklineData is passed
  const chartData = data 
    ? data 
    : sparklineData 
    ? sparklineData.map((val) => ({ value: val }))
    : [];

  // Color schemes for light theme
  const theme = {
    risk: {
      cardBg: 'bg-amber-50/80 border-amber-200/80',
      lineColor: '#D97706',
      badge: 'bg-amber-100 text-amber-800',
      iconBg: 'bg-amber-100 text-amber-700',
    },
    recovery: {
      cardBg: 'bg-emerald-50/80 border-emerald-200/80',
      lineColor: '#059669',
      badge: 'bg-emerald-100 text-emerald-800',
      iconBg: 'bg-emerald-100 text-emerald-700',
    },
    transfers: {
      cardBg: 'bg-slate-50 border-slate-200/80',
      lineColor: '#059669',
      badge: 'bg-emerald-100 text-emerald-800',
      iconBg: 'bg-slate-200 text-slate-700',
    },
    value: {
      cardBg: 'bg-emerald-600 border-emerald-500 text-white',
      lineColor: '#FFFFFF',
      badge: 'bg-emerald-700 text-emerald-100',
      iconBg: 'bg-emerald-500 text-white',
    },
  }[type];

  return (
    <div className={`rounded-2xl p-5 border shadow-xs transition-all overflow-hidden flex flex-col justify-between ${theme.cardBg}`}>
      <div>
        {/* Header Row */}
        <div className="flex justify-between items-start mb-2">
          <span className={`text-[11px] font-extrabold tracking-wider uppercase ${type === 'value' ? 'text-emerald-100' : 'text-slate-500'}`}>
            {title}
          </span>
          <div className={`p-2 rounded-xl ${theme.iconBg}`}>
            {icon}
          </div>
        </div>

        {/* Value Row */}
        <div className="flex items-baseline gap-2 mb-3">
          <span className={`text-2xl font-black ${type === 'value' ? 'text-white' : 'text-slate-900'}`}>
            {value}
          </span>
          {trend && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${theme.badge}`}>
              {trend.isPositive ? '+' : '-'}{trend.value}% {trend.label}
            </span>
          )}
        </div>
      </div>

      {/* Clipped Sparkline Chart Container */}
      <div className="h-16 w-full mt-2 rounded-xl bg-slate-100/80 border border-slate-200/70 p-1 overflow-hidden relative">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" vertical={false} />
            <Line
              type="monotone"
              dataKey="value"
              stroke={theme.lineColor}
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};