import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
    label?: string; // e.g., "vs yesterday"
  };
  sparklineData?: number[]; // Array of 10-20 numbers for the mini chart
}

export const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon, 
  trend,
  sparklineData 
}) => {
  // Generate a simple SVG sparkline if data is provided
  const renderSparkline = () => {
    if (!sparklineData || sparklineData.length === 0) return null;
    
    const max = Math.max(...sparklineData);
    const min = Math.min(...sparklineData);
    const range = max - min || 1;
    
    const width = 100;
    const height = 30;
    const stepX = width / (sparklineData.length - 1);
    
    const points = sparklineData.map((val, i) => {
      const x = i * stepX;
      // Invert Y axis for SVG (0 is top)
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    }).join(' ');

    const strokeColor = trend?.isPositive === false ? '#D85A30' : '#1D9E75'; // semantic-red vs semantic-green

    return (
      <div className="w-[100px] h-[30px] ml-4 flex-shrink-0 opacity-80">
        <svg width="100%" height="100%" viewBox={`0 -2 ${width} ${height + 4}`} preserveAspectRatio="none">
          <polyline 
            points={points} 
            fill="none" 
            stroke={strokeColor} 
            strokeWidth="1.5" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
          />
        </svg>
      </div>
    );
  };

  return (
    <div className="bg-card rounded-md border border-border p-4 flex flex-col justify-between h-[100px] hover:border-text-muted transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2">
          {icon && <div className="text-text-secondary">{icon}</div>}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">{title}</h3>
        </div>
      </div>
      
      <div className="flex items-end justify-between mt-2">
        <div>
          <div className="flex items-baseline space-x-2">
            <p className="text-2xl font-bold font-mono text-text-primary tracking-tight">{value}</p>
            {trend && (
              <span
                className={`text-xs font-bold font-mono ${
                  trend.isPositive ? 'text-semantic-green' : 'text-semantic-red'
                }`}
              >
                {trend.isPositive ? '+' : '-'}{Math.abs(trend.value)}%
              </span>
            )}
          </div>
          {(subtitle || (trend && trend.label)) && (
            <p className="text-[10px] text-text-muted uppercase tracking-widest mt-0.5">
              {subtitle || trend?.label || 'VS PREV. PERIOD'}
            </p>
          )}
        </div>
        
        {renderSparkline()}
      </div>
    </div>
  );
};
