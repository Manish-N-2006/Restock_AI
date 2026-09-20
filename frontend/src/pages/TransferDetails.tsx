import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Transfer } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { format } from 'date-fns';
import { ArrowLeft, ArrowRight, Truck, DollarSign, CheckCircle2, Clock } from 'lucide-react';

export const TransferDetails: React.FC = () => {
  const { transferId } = useParams<{ transferId: string }>();
  const navigate = useNavigate();
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      if (!transferId) return;
      try {
        const data = await api.getTransfer(transferId);
        if (mounted) setTransfer(data);
      } catch (error) {
        console.error("Failed to load transfer details:", error);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, [transferId]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-text-muted">
        <div className="animate-pulse flex items-center space-x-2">
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
          <span className="h-2 w-2 bg-semantic-blue rounded-full"></span>
        </div>
      </div>
    );
  }

  if (!transfer) {
    return (
      <div className="p-8 text-center bg-card rounded-lg border border-border">
        <p className="text-text-secondary">Transfer not found or access denied.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      
      {/* Header */}
      <div className="flex items-center space-x-4">
        <button onClick={() => navigate('/transfers')} className="p-2 hover:bg-card border border-transparent hover:border-border rounded transition-colors">
          <ArrowLeft className="h-5 w-5 text-text-secondary" />
        </button>
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-xl font-bold text-text-primary tracking-tight font-mono uppercase">
              {transfer.transfer_id}
            </h1>
            <StatusBadge status={transfer.status} />
          </div>
          <p className="text-xs text-text-muted font-mono uppercase tracking-widest flex items-center">
            <Clock className="h-3 w-3 mr-1.5" /> 
            Created {format(new Date(transfer.created_at), 'yyyy-MM-dd HH:mm:ss')}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Route & Timeline */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Route Card */}
          <div className="bg-panel rounded border border-border overflow-hidden">
            <div className="px-5 py-3 bg-[#14161a] border-b border-border">
              <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest">Routing Manifest</h2>
            </div>
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="text-center flex-1">
                  <p className="text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-2">Source</p>
                  <p className="text-2xl font-bold font-mono text-text-primary">{transfer.source_store_id}</p>
                </div>
                
                <div className="px-6 flex flex-col items-center">
                  <div className="text-xs font-mono font-medium text-text-secondary mb-2 bg-card px-2 py-0.5 rounded border border-border">
                    {transfer.quantity} UNITS
                  </div>
                  <div className="relative w-full h-px bg-border flex items-center justify-center my-2 min-w-[100px]">
                    <div className="absolute right-0 -top-[5px] text-border">
                      <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                  <p className="text-sm font-mono text-semantic-blue mt-2 font-medium">{transfer.sku_id}</p>
                </div>

                <div className="text-center flex-1">
                  <p className="text-[10px] font-semibold text-text-muted uppercase tracking-widest mb-2">Destination</p>
                  <p className="text-2xl font-bold font-mono text-text-primary">{transfer.destination_store_id}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Operational Timeline */}
          <div className="bg-panel rounded border border-border overflow-hidden">
            <div className="px-5 py-3 bg-[#14161a] border-b border-border">
              <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest">Operational Timeline</h2>
            </div>
            <div className="p-6">
              <div className="space-y-6 relative before:absolute before:inset-0 before:ml-[1.125rem] before:h-full before:w-px before:bg-border/50">
                {transfer.events && transfer.events.map((event, idx) => (
                  <div key={event.event_id || idx} className="relative flex items-start group">
                    <div className="flex items-center justify-center w-9 h-9 rounded-full border border-semantic-blue/30 bg-semantic-blue/10 text-semantic-blue z-10 shrink-0 shadow-[0_0_10px_rgba(55,138,221,0.2)]">
                      <CheckCircle2 className="h-4 w-4" />
                    </div>
                    <div className="ml-4 p-4 rounded bg-card border border-border w-full hover:border-text-muted transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="font-bold text-sm text-text-primary uppercase tracking-wide">{event.event_type}</h3>
                        <time className="text-xs font-mono text-text-muted">
                          {format(new Date(event.created_at), 'MMM dd, HH:mm:ss')}
                        </time>
                      </div>
                      <p className="text-xs text-text-secondary mt-2 font-mono">
                        {event.notes || `State transition: ${event.previous_status} ➔ ${event.new_status}`}
                      </p>
                    </div>
                  </div>
                ))}
                {(!transfer.events || transfer.events.length === 0) && (
                  <p className="text-text-muted text-xs uppercase tracking-widest font-mono ml-12">No telemetry events recorded.</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Logistics & Economics */}
        <div className="space-y-6">
          
          {/* Logistics Profile */}
          <div className="bg-panel rounded border border-border overflow-hidden">
            <div className="px-5 py-3 bg-[#14161a] border-b border-border flex items-center space-x-2">
              <Truck className="h-3.5 w-3.5 text-semantic-amber" />
              <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest">Logistics Profile</h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <dt className="text-[10px] uppercase tracking-widest text-text-muted mb-1">Partner Selection</dt>
                <dd className="text-sm font-mono text-text-primary">{transfer.logistics_partner_id || 'PENDING ASSIGNMENT'}</dd>
              </div>
              <div className="pt-4 border-t border-border">
                <dt className="text-[10px] uppercase tracking-widest text-text-muted mb-1">Estimated Cost</dt>
                <dd className="text-sm font-mono text-semantic-red">
                  {transfer.estimated_cost ? `-₹${transfer.estimated_cost.toLocaleString()}` : 'CALCULATING...'}
                </dd>
              </div>
            </div>
          </div>

          {/* Economics Profile */}
          <div className="bg-panel rounded border border-border overflow-hidden">
            <div className="px-5 py-3 bg-[#14161a] border-b border-border flex items-center space-x-2">
              <DollarSign className="h-3.5 w-3.5 text-semantic-green" />
              <h2 className="text-[11px] font-semibold text-text-primary uppercase tracking-widest">Financial Impact</h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <dt className="text-[10px] uppercase tracking-widest text-text-muted mb-1">Expected Net Recovery</dt>
                <dd className="text-2xl font-mono font-bold text-semantic-green">
                  {transfer.expected_recovery ? `+₹${transfer.expected_recovery.toLocaleString()}` : 'PENDING'}
                </dd>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
