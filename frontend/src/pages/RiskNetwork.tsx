import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { RiskItem } from '../types';
import { SkuTable } from '../components/overview/SkuTable';
import { useNavigate } from 'react-router-dom';

export const RiskNetwork: React.FC = () => {
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const data = await api.getRiskItems();
        if (mounted) setRisks(data);
      } catch (error) {
        console.error("Failed to load risk network data:", error);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">Risk Network</h1>
          <p className="text-text-secondary mt-1 text-sm">Real-time inventory risk monitoring and assessment.</p>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-text-muted">
            <div className="animate-pulse flex items-center space-x-2">
              <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
              <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
              <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
            </div>
          </div>
        ) : (
          <SkuTable 
            data={risks} 
            onRowClick={(sku_id, store_id) => navigate(`/workflow?sku=${sku_id}&store=${store_id}`)} 
          />
        )}
      </div>
    </div>
  );
};
