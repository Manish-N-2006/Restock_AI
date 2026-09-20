import { fetchApi } from './client';
import { RiskItem, Decision, LogisticsRecommendation, WorkflowResult, Transfer, Outcome, HistoricalRecord, AgentResponse } from '../types';

export const api = {
  // Risk APIs
  getRiskItems: () => fetchApi<{items: RiskItem[]}>('/api/risk').then(res => res.items),
  getRiskSummary: () => fetchApi<any>('/api/risk/summary'),
  
  // Decision APIs
  getAllDecisions: () => fetchApi<Decision[]>('/api/decision/all'),
  getDecision: (sku: string, storeId: string) => 
    fetchApi<Decision>(`/api/decision/${sku}?store_id=${storeId}`),
    
  // Logistics APIs
  getLogisticsOptions: (sku: string, sourceStoreId: string, destStoreId: string, quantity: number) =>
    fetchApi<any>(`/api/logistics/options?sku_id=${sku}&source_store_id=${sourceStoreId}&destination_store_id=${destStoreId}&transfer_quantity=${quantity}`),
    
  // Workflow APIs
  executeWorkflow: (sku: string, storeId: string, partnerId?: string) =>
    fetchApi<WorkflowResult>('/api/workflow/execute', {
      method: 'POST',
      body: JSON.stringify({ sku_id: sku, source_store_id: storeId, partner_id: partnerId })
    }),
  analyzeWorkflow: (sku: string, storeId: string) =>
    fetchApi<any>('/api/workflow/analyze', {
      method: 'POST',
      body: JSON.stringify({ sku_id: sku, source_store_id: storeId })
    }),
    
  // Transfer APIs
  getTransfers: () => fetchApi<Transfer[]>('/api/transfers'),
  getTransfer: (transferId: string) => fetchApi<Transfer>(`/api/transfers/${transferId}`),
  createTransfer: (data: { sku: string, source_store_id: string, destination_store_id: string, quantity: number, logistics_partner_id: string }) => 
    fetchApi<Transfer>('/api/transfers', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  approveTransfer: (transferId: string) =>
    fetchApi<Transfer>(`/api/transfers/${transferId}/approve`, { method: 'POST' }),
    
  // Outcome APIs
  getOutcomes: () => fetchApi<any[]>('/api/outcomes').then(outcomes => 
    outcomes.map(o => ({
      outcome_id: o.outcome_id,
      transfer_id: o.transfer_id,
      sku_id: o.sku_id,
      source_store_id: o.source_store_id,
      destination_store_id: o.destination_store_id,
      predicted_recovery: o.prediction?.predicted_net_recovery || 0,
      actual_recovery: o.actual?.actual_net_recovery || 0,
      variance: o.metrics?.recovery_variance || 0,
      sell_through_rate: o.metrics?.sell_through_rate,
      recovery_accuracy: o.metrics?.recovery_accuracy_percentage,
      status: o.outcome_status || 'PENDING',
      created_at: o.outcome_recorded_at,
      updated_at: o.outcome_recorded_at,
      finalized_at: o.finalized_at
    }))
  ),  
  // History APIs
  getHistory: (query: string = '') => 
    fetchApi<{ results: HistoricalRecord[] }>(`/api/history/search${query ? `?q=${query}` : ''}`),
    
  // Agent APIs
  askAgent: (query: string) => 
    fetchApi<AgentResponse>('/api/agent/ask', {
      method: 'POST',
      body: JSON.stringify({ question: query })
    }),
};
