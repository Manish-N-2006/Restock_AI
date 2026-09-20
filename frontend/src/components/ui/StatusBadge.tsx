import React from 'react';
import { TransferStatus } from '../../types';

interface StatusBadgeProps {
  status: TransferStatus;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getBadgeStyle = (status: TransferStatus) => {
    switch (status) {
      case 'CREATED':
        return 'bg-panel text-text-secondary border-border';
      case 'APPROVED':
        return 'bg-semantic-blue/20 text-semantic-blue border-semantic-blue/30';
      case 'ASSIGNED':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'PICKUP_PENDING':
        return 'bg-semantic-amber/20 text-semantic-amber border-semantic-amber/30';
      case 'IN_TRANSIT':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'DELIVERED':
        return 'bg-teal-500/20 text-teal-400 border-teal-500/30';
      case 'COMPLETED':
        return 'bg-semantic-green/20 text-semantic-green border-semantic-green/30';
      case 'CANCELLED':
      case 'FAILED':
        return 'bg-semantic-red/20 text-semantic-red border-semantic-red/30';
      default:
        return 'bg-panel text-text-secondary border-border';
    }
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider border ${getBadgeStyle(status)}`}>
      {status.replace('_', ' ')}
    </span>
  );
};
