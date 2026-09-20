import React from 'react';
import { IntegratedRecommendationResponse, EvaluatedAction } from '../../types';
import { X, CheckCircle2, TrendingUp, AlertTriangle, Truck } from 'lucide-react';

interface RecoveryDecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  recommendation: IntegratedRecommendationResponse | null;
  onExecute: (partnerId?: string) => void;
  isExecuting: boolean;
}

export const RecoveryDecisionModal: React.FC<RecoveryDecisionModalProps> = ({
  isOpen,
  onClose,
  recommendation,
  onExecute,
  isExecuting
}) => {
  const [logisticsOptions, setLogisticsOptions] = React.useState<any[]>([]);
  const [selectedPartnerId, setSelectedPartnerId] = React.useState<string | null>(null);
  const [isLoadingLogistics, setIsLoadingLogistics] = React.useState(false);

  React.useEffect(() => {
    if (isOpen && recommendation?.transfer_still_viable && recommendation.decision.selected_destination_store_id) {
      const fetchLogistics = async () => {
        setIsLoadingLogistics(true);
        try {
          const { api } = await import('../../api');
          const data = await api.getLogisticsOptions(
            recommendation.decision.sku_id,
            recommendation.decision.store_id,
            recommendation.decision.selected_destination_store_id!,
            recommendation.decision.recommended_quantity
          );
          if (data && data.options) {
            setLogisticsOptions(data.options);
            // Default select the AI's top choice
            if (recommendation.logistics?.selected_partner?.partner_id) {
              setSelectedPartnerId(recommendation.logistics.selected_partner.partner_id);
            } else if (data.options.length > 0) {
              setSelectedPartnerId(data.options[0].partner_id);
            }
          }
        } catch (error) {
          console.error('Failed to fetch logistics options', error);
        } finally {
          setIsLoadingLogistics(false);
        }
      };
      fetchLogistics();
    }
  }, [isOpen, recommendation]);

  if (!isOpen || !recommendation) return null;

  const { decision, logistics, logistics_adjusted_net_recovery, transfer_still_viable } = recommendation;
  const topAction = decision.actions.find(a => a.action === decision.selected_action);
  const altActions = decision.actions.filter(a => a.action !== decision.selected_action && a.available);

  const handleExecute = () => {
    onExecute(selectedPartnerId || undefined);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-panel border border-border rounded-lg shadow-2xl w-full max-w-3xl flex flex-col max-h-[90vh] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-[#14161a]">
          <div>
            <h2 className="text-lg font-bold text-text-primary tracking-tight">Recovery Decision</h2>
            <p className="text-text-secondary text-sm font-mono mt-1">
              {decision.sku_id} • {decision.store_id}
            </p>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {/* Top Recommendation */}
          <div className="bg-card border border-semantic-green/30 rounded-lg p-5">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="h-5 w-5 text-semantic-green" />
                <h3 className="text-base font-semibold text-semantic-green uppercase tracking-wider">
                  AI Recommendation: {decision.selected_action}
                </h3>
              </div>
              <div className="text-right">
                <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">Adjusted Net Recovery</div>
                <div className="text-xl font-bold font-mono text-text-primary">
                  ₹{(logistics_adjusted_net_recovery ?? topAction?.expected_net_recovery ?? 0).toLocaleString()}
                </div>
              </div>
            </div>

            <p className="text-sm text-text-secondary mb-4 leading-relaxed">
              {recommendation.reason}
            </p>

            {/* Metrics Breakdown */}
            <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
              <div>
                <div className="text-xs text-text-muted uppercase tracking-wider mb-1">Target</div>
                <div className="text-sm font-mono text-text-primary">{decision.selected_destination_store_id || 'N/A'}</div>
              </div>
              <div>
                <div className="text-xs text-text-muted uppercase tracking-wider mb-1">Quantity</div>
                <div className="text-sm font-mono text-text-primary">{decision.recommended_quantity} units</div>
              </div>
              {decision.selected_action === 'TRANSFER' && (
                <div>
                  <div className="text-xs text-text-muted uppercase tracking-wider mb-1">Viability</div>
                  <div className={`text-sm font-bold uppercase ${transfer_still_viable ? 'text-semantic-green' : 'text-semantic-red'}`}>
                    {transfer_still_viable ? 'GO' : 'NO-GO'}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Logistics Breakdown (if applicable) */}
          {logistics && transfer_still_viable && (
            <div className="bg-page border border-border rounded-lg p-5">
              <div className="flex items-center space-x-2 mb-3">
                <Truck className="h-4 w-4 text-semantic-blue" />
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Logistics Profile (Select Partner)</h4>
              </div>
              
              {isLoadingLogistics ? (
                <div className="text-sm text-text-muted animate-pulse">Scanning regional logistics networks...</div>
              ) : logisticsOptions.length > 0 ? (
                <div className="space-y-3">
                  {logisticsOptions.map(partner => (
                    <div 
                      key={partner.partner_id}
                      onClick={() => setSelectedPartnerId(partner.partner_id)}
                      className={`flex justify-between items-center p-3 rounded cursor-pointer transition-colors border ${
                        selectedPartnerId === partner.partner_id 
                          ? 'bg-semantic-blue/10 border-semantic-blue/50' 
                          : 'bg-card border-border hover:border-text-muted'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`h-4 w-4 rounded-full border flex items-center justify-center ${
                          selectedPartnerId === partner.partner_id ? 'border-semantic-blue' : 'border-text-muted'
                        }`}>
                          {selectedPartnerId === partner.partner_id && <div className="h-2 w-2 bg-semantic-blue rounded-full" />}
                        </div>
                        <div>
                          <div className="font-medium text-text-primary text-sm flex items-center space-x-2">
                            <span>{partner.partner_name}</span>
                            {partner.partner_id === logistics.selected_partner?.partner_id && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider bg-semantic-green/20 text-semantic-green">AI Pick</span>
                            )}
                          </div>
                          <div className="text-xs text-text-muted mt-0.5">{partner.distance_km} km away</div>
                        </div>
                      </div>
                      
                      <div className="flex space-x-6 text-sm text-right">
                        <div>
                          <span className="text-xs text-text-muted uppercase block">ETA</span>
                          <span className="font-mono text-text-primary">{((partner.average_eta_minutes ?? 0) / 60).toFixed(1)} hrs</span>
                        </div>
                        <div>
                          <span className="text-xs text-text-muted uppercase block">Cost</span>
                          <span className="font-mono text-semantic-red">-₹{(partner.estimated_delivery_cost ?? 0).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-text-muted">No logistics partners found for this route.</div>
              )}
            </div>
          )}

          {/* Alternative Actions */}
          {altActions.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Alternative Evaluations</h4>
              <div className="space-y-2">
                {altActions.map((alt, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded bg-card border border-border">
                    <div className="flex items-center space-x-3">
                      <TrendingUp className="h-4 w-4 text-text-muted" />
                      <span className="text-sm font-medium text-text-secondary uppercase">{alt.action}</span>
                    </div>
                    <div className="flex space-x-6 text-sm text-right">
                      <div>
                        <div className="text-[10px] text-text-muted uppercase">Gross</div>
                        <div className="font-mono text-text-primary">₹{(alt.expected_recovered_value ?? 0).toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-text-muted uppercase">Costs</div>
                        <div className="font-mono text-semantic-red">-₹{((alt.logistics_cost ?? 0) + (alt.handling_cost ?? 0)).toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-text-muted uppercase">Net</div>
                        <div className="font-mono text-text-primary">₹{(alt.expected_net_recovery ?? 0).toLocaleString()}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {decision.selected_action === 'TRANSFER' && !transfer_still_viable && (
             <div className="bg-[#2D1612] border border-semantic-red/30 rounded p-3 flex items-start space-x-3">
               <AlertTriangle className="h-5 w-5 text-semantic-red flex-shrink-0 mt-0.5" />
               <p className="text-xs text-semantic-red leading-relaxed">
                 Warning: Factoring in realtime logistics quotes, this transfer is no longer economically viable. The logistics costs exceed the marginal benefit of transferring the inventory.
               </p>
             </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border bg-[#14161a] flex justify-end space-x-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
            disabled={isExecuting}
          >
            Cancel
          </button>
          <button 
            onClick={handleExecute}
            disabled={
              isExecuting || 
              (decision.selected_action === 'TRANSFER' && !transfer_still_viable) || 
              (decision.selected_action === 'TRANSFER' && !selectedPartnerId)
            }
            className={`px-6 py-2 text-sm font-bold uppercase tracking-wide rounded transition-colors flex items-center space-x-2 ${
              isExecuting || (decision.selected_action === 'TRANSFER' && !transfer_still_viable)
                ? 'bg-semantic-green/30 text-white/50 cursor-not-allowed'
                : 'bg-semantic-green hover:bg-semantic-green/90 text-white'
            }`}
          >
            {isExecuting ? (
              <>
                <div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                <span>Executing...</span>
              </>
            ) : (
              <span>Execute {decision.selected_action}</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
