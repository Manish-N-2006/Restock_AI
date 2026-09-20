import React, { useEffect, useState } from 'react';
import { AlertOctagon, X, ArrowRight } from 'lucide-react';
import { api } from '../../api';
import { RiskItem } from '../../types';
import { useNavigate } from 'react-router-dom';

export const AlertBanner: React.FC = () => {
  const [criticalItem, setCriticalItem] = useState<RiskItem | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (sessionStorage.getItem('restock_alert_dismissed') === 'true') {
      setDismissed(true);
      return;
    }

    let mounted = true;
    api.getRiskItems().then(items => {
      if (!mounted) return;
      const criticals = items.filter(i => i.risk_level === 'CRITICAL');
      if (criticals.length > 0) {
        criticals.sort((a, b) => b.risk_score - a.risk_score);
        setCriticalItem(criticals[0]);
      }
    }).catch(console.error);

    return () => { mounted = false; };
  }, []);

  if (dismissed || !criticalItem) {
    return null;
  }

  const handleDismiss = () => {
    sessionStorage.setItem('restock_alert_dismissed', 'true');
    setDismissed(true);
  };

  const handleReview = () => {
    // Uses the workflow cockpit route for deep linking
    navigate(`/workflow?sku=${criticalItem.sku_id}&store=${criticalItem.store_id}`);
  };

  return (
    <div className="bg-[#2D1612] border-b border-semantic-red/30 px-6 py-3 flex items-center justify-between shadow-lg">
      <div className="flex items-center space-x-4">
        <div className="bg-semantic-red/20 p-2 rounded flex-shrink-0">
          <AlertOctagon className="h-5 w-5 text-semantic-red" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[13px] font-bold text-semantic-red tracking-wider uppercase">
              Critical Inventory Alert
            </span>
            <span className="text-text-muted text-xs px-1">|</span>
            <span className="font-mono text-sm text-text-primary bg-black/20 px-1.5 py-0.5 rounded">{criticalItem.sku_id}</span>
            <span className="text-text-secondary text-sm ml-1">· {criticalItem.store_id}</span>
          </div>
          <div className="text-xs text-text-secondary mt-1">
            <span className="text-text-primary font-medium">{criticalItem.at_risk_quantity} units</span> at risk • 
            <span className="text-text-primary font-medium ml-1">{criticalItem.days_to_expiry} days</span> to expiry
          </div>
        </div>
      </div>
      <div className="flex items-center space-x-4">
        <button 
          onClick={handleReview}
          className="flex items-center space-x-2 bg-semantic-red hover:bg-semantic-red/90 text-white px-4 py-1.5 rounded text-sm font-medium transition-colors"
        >
          <span>Review Transfer</span>
          <ArrowRight className="h-4 w-4" />
        </button>
        <button 
          onClick={handleDismiss}
          className="text-text-muted hover:text-text-primary transition-colors p-1"
          title="Dismiss for session"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
};
