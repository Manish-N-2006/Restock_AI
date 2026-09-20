export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface RiskItem {
  sku_id: string;
  store_id: string;
  at_risk_quantity: number;
  at_risk_value: number;
  days_to_expiry: number;
  risk_level: RiskLevel;
  risk_score: number;
  risk_reason: string;
}

export type RecoveryActionType = 'TRANSFER' | 'DISCOUNT' | 'BUNDLE' | 'PROMOTE' | 'RETURN' | 'DISPOSE' | 'NO_ACTION';

export interface EvaluatedAction {
  action: RecoveryActionType;
  available: boolean;
  quantity: number;
  expected_recovered_value: number;
  logistics_cost: number;
  handling_cost: number;
  risk_cost: number;
  expected_net_recovery: number;
  economically_viable: boolean;
  assumptions: string[];
  reason: string;
}

export interface Decision {
  sku_id: string;
  store_id: string;
  risk?: RiskItem;
  actions: EvaluatedAction[];
  selected_action: RecoveryActionType;
  selected_destination_store_id?: string;
  recommended_quantity: number;
  expected_net_recovery: number;
  decision_reason: string;
}

export interface LogisticsPartnerEvaluation {
  partner_id: string;
  partner_name: string;
  distance_km: number;
  transfer_quantity: number;
  capacity_units: number;
  capacity_headroom: number;
  cold_chain_available: boolean;
  cold_chain_required: boolean;
  base_cost: number;
  per_km_cost: number;
  cold_chain_surcharge: number;
  total_cost: number;
  estimated_transit_hours: number;
  suitability_score: number;
  eligible: boolean;
  rejection_reason?: string;
}

export interface LogisticsOptionsResponse {
  sku_id: string;
  source_store_id: string;
  destination_store_id: string;
  transfer_quantity: number;
  matched: boolean;
  options: LogisticsPartnerEvaluation[];
}

export interface LogisticsIntegrationResult {
  selected_partner?: LogisticsPartnerEvaluation;
  delivery_cost: number;
  eta_minutes: number;
}

export type TransferStatus = 'CREATED' | 'APPROVED' | 'ASSIGNED' | 'PICKUP_PENDING' | 'IN_TRANSIT' | 'DELIVERED' | 'COMPLETED' | 'CANCELLED' | 'FAILED';

export interface TransferEvent {
  event_id: string;
  transfer_id: string;
  event_type: string;
  previous_status: TransferStatus;
  new_status: TransferStatus;
  notes?: string;
  created_at: string;
}

export interface Transfer {
  transfer_id: string;
  sku_id: string;
  source_store_id: string;
  destination_store_id: string;
  quantity: number;
  status: TransferStatus;
  logistics_partner_id?: string;
  estimated_cost?: number;
  expected_recovery?: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  events?: TransferEvent[];
}

export type OutcomeStatus = 'PENDING' | 'FINALIZED';

export interface Outcome {
  outcome_id: string;
  transfer_id: string;
  sku_id: string;
  source_store_id: string;
  destination_store_id: string;
  predicted_recovery: number;
  actual_recovery?: number;
  variance?: number;
  sell_through_rate?: number;
  recovery_accuracy?: number;
  status: OutcomeStatus;
  created_at: string;
  updated_at: string;
  finalized_at?: string;
}

export interface HistoricalRecord {
  transfer_id: string;
  sku_id: string;
  source_store_id: string;
  destination_store_id?: string;
  action?: string;
  actual_net_recovery?: number;
  recovery_accuracy_percentage?: number;
  actual_units_sold?: number;
}

export interface AgentResponse {
  question: string;
  answer: string;
  tools_used: string[];
}

export interface IntegratedRecommendationResponse {
  decision: Decision;
  logistics?: LogisticsIntegrationResult;
  logistics_adjusted_net_recovery: number;
  transfer_still_viable: boolean;
  reason: string;
}

export interface WorkflowResult {
  status: string;
  message: string;
  recommendation?: IntegratedRecommendationResponse;
  transfer?: Transfer;
}
