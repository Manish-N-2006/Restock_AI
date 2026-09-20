import { fetchApi } from './client';
import { RiskItem, Decision, LogisticsRecommendation, WorkflowResult, Transfer, Outcome, HistoricalRecord, AgentResponse } from '../types';

export const api = {
  // Risk APIs
  getRiskItems: () => fetchApi<RiskItem[]>('/api/risk'),
  getRiskSummary: () => fetchApi<any>('/api/risk/summary'),
  
  // Decision APIs
  getAllDecisions: () => fetchApi<Decision[]>('/api/decision/all'),
  getDecision: (sku: string, storeId: string) => 
    fetchApi<Decision>(`/api/decision/${sku}?store_id=${storeId}`),
    
  // Logistics APIs
  getLogisticsOptions: (sku: string, sourceStoreId: string, destStoreId: string, quantity: number) =>
    fetchApi<any>(`/api/logistics/options?sku=${sku}&source_store_id=${sourceStoreId}&destination_store_id=${destStoreId}&transfer_quantity=${quantity}`),
    
  // Workflow APIs
  executeWorkflow: (sku: string, storeId: string) =>
    fetchApi<WorkflowResult>('/api/workflow/execute', {
      method: 'POST',
      body: JSON.stringify({ sku, store_id: storeId })
    }),
  analyzeWorkflow: (sku: string, storeId: string) =>
    fetchApi<any>('/api/workflow/analyze', {
      method: 'POST',
      body: JSON.stringify({ sku, store_id: storeId })
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
  getOutcomes: () => fetchApi<Outcome[]>('/api/outcomes'),
  
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
