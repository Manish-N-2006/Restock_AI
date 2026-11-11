export interface BuyerMatchResult {
  buyer_id: string;
  name: string;
  organization_type: string;
  match_score: number;
  is_compatible: boolean;
  offered_quantity: number;
  offered_unit_price: number;
  estimated_total_order: number;
  compatibility_reasons: string[];
  disqualification_reasons: string[];
  location: string;
  contact_email: string;
  is_demo_data: boolean;
}

export interface BranchCandidateMatch {
  branch_type: 'RECEIVING_BRANCH' | 'DONOR_BRANCH';
  store_id: string;
  store_name: string;
  match_score: number;
  is_eligible: boolean;
  recommended_transfer_qty: number;
  straight_line_distance_km: number;
  simulated_road_distance_km: number;
  estimated_transit_minutes: number;
  cold_chain_compatible: boolean;
  capacity_status: string;
  net_economic_value: number;
  reasons: string[];
  rejection_reasons: string[];
}

export interface LogisticsCarrierOption {
  partner_id: string;
  partner_name: string;
  vehicle_type: string;
  straight_line_km: number;
  road_distance_km: number;
  is_simulated_road_distance: boolean;
  estimated_journey_time_minutes: number;
  transport_cost: number;
  vehicle_capacity: number;
  cold_chain_available: boolean;
  expected_delivery_time: string;
  eligible: boolean;
  final_score: number;
  selection_reason: string;
  rejection_reason?: string;
}

export interface IncrementalNetworkEconomics {
  transfer_quantity: number;
  retail_price: number;
  cost_price: number;
  margin_protected_at_receiver: number;
  avoided_markdown_writeoff_loss: number;
  gross_revenue_protected: number;
  transport_cost: number;
  handling_cost: number;
  transit_spoilage_risk_cost: number;
  donor_opportunity_cost: number;
  net_incremental_network_value: number;
  supplier_replenishment_comparison?: {
    supplier_lead_time_hours: number;
    supplier_emergency_surcharge: number;
    lost_sales_before_supplier_arrival: number;
    supplier_net_penalty: number;
    internal_transfer_advantage: number;
    economic_conclusion: string;
  };
  alternative_actions_ranking?: Array<{
    action: string;
    net_value: number;
    viable: boolean;
    rank: number;
    reason?: string;
  }>;
}

export interface SimulationState {
  simulation_run_id: string;
  scenario_id: 'SCENARIO_A' | 'SCENARIO_B' | 'SCENARIO_C' | 'SCENARIO_D';
  scenario_name: string;
  scenario_description: string;
  operating_perspective: 'SURPLUS_DONOR' | 'STOCKOUT_RECEIVER' | 'NETWORK_BALANCING' | 'EXTERNAL_LIQUIDATION';
  sku_id: string;
  source_store_id: string;
  product_name: string;
  status: 'IDLE' | 'RUNNING' | 'PAUSED' | 'AWAITING_APPROVAL' | 'AWAITING_PAYMENT' | 'COMPLETED' | 'REJECTED';
  current_step_index: number;
  current_step_name: string;
  playback_speed: number;
  auto_approve: boolean;
  is_simulation: boolean;
  timeline: Array<{
    timestamp: string;
    agent: string;
    action: string;
    details: string;
    step: string;
  }>;
  live_event_feed: Array<{
    timestamp: string;
    agent: string;
    action: string;
    details: string;
    step: string;
  }>;

  // Network Perspectives & Data
  donor_branch?: {
    store_id: string;
    store_name: string;
    sku_id: string;
    product_name: string;
    current_stock: number;
    safety_stock: number;
    transferable_quantity: number;
    daily_velocity: number;
    days_to_expiry: number;
    cost_price: number;
    selling_price: number;
    temperature_class: string;
    requires_cold_chain: boolean;
  };
  receiving_branch?: {
    store_id: string;
    store_name: string;
    sku_id: string;
    product_name: string;
    current_stock: number;
    target_stock: number;
    daily_demand: number;
    shortage_quantity: number;
    storage_capacity: number;
    available_capacity: number;
    stockout_deadline_hours: number;
    supports_cold_chain: boolean;
  };
  candidate_branches?: BranchCandidateMatch[];
  logistics_comparison?: LogisticsCarrierOption[];
  network_economics?: IncrementalNetworkEconomics;
  network_balance_plan?: {
    plan_id: string;
    transfers: Array<{
      transfer_id: string;
      donor_store_id: string;
      donor_store_name: string;
      receiver_store_id: string;
      receiver_store_name: string;
      sku_id: string;
      product_name: string;
      quantity: number;
      carrier_name: string;
      road_distance_km: number;
      transit_minutes: number;
      freight_cost: number;
      margin_protected: number;
      net_network_value: number;
      temperature_compliant: boolean;
    }>;
    total_units_rebalanced: number;
    total_freight_cost: number;
    total_margin_protected: number;
    total_net_network_value: number;
    algorithm: string;
    limitations: string;
  };

  // Stage Outputs
  inventory_discovery?: {
    sku_id: string;
    product_name: string;
    store_id: string;
    quantity: number;
    days_to_expiry: number;
    at_risk_quantity: number;
    at_risk_value: number;
    risk_score: number;
    risk_level: string;
  };
  buyer_discovery?: {
    total_candidates_evaluated: number;
    compatible_candidates_count: number;
    top_matched_buyer?: BuyerMatchResult;
    candidates: BuyerMatchResult[];
  };
  recovery_analysis?: {
    selected_action: string;
    expected_net_recovery: number;
    reasoning: string;
    evaluated_actions: Array<{
      action: string;
      expected_net_recovery: number;
      economically_viable: boolean;
      reason?: string;
      destination_store?: string;
    }>;
  };
  recovery_planning?: {
    type: string;
    buyer_id?: string;
    buyer_name?: string;
    buyer_email?: string;
    quantity: number;
    unit_price?: number;
    total_amount?: number;
    target_store_id?: string;
    selected_carrier?: string;
    road_distance_km?: number;
    transit_minutes?: number;
    freight_cost?: number;
    cold_chain_verified?: boolean;
  };
  offer_creation?: {
    type: string;
    order_id?: string;
    transfer_id?: string;
    sku_id?: string;
    product_name?: string;
    buyer_name?: string;
    buyer_email?: string;
    quantity: number;
    unit_price?: number;
    total_amount?: number;
    currency?: string;
    carrier?: string;
    freight_cost?: number;
    status: string;
  };
  human_approval?: {
    approval_id: string;
    status: string;
    threshold_evaluated: string;
    cedar_allowed: boolean;
    approver_role: string;
  };
  paypal_checkout?: {
    status: string;
    payment_id?: string;
    paypal_order_id?: string;
    paypal_capture_id?: string;
    capture_id?: string;
    recovery_order_id?: string;
    amount?: number;
    currency?: string;
    fee_amount?: number;
    net_amount?: number;
    payer_id?: string;
    payer_email?: string;
    payer_name?: string;
    buyer_details?: {
      payer_id?: string;
      payer_email?: string;
      payer_name?: string;
    };
    captured_at?: string;
    is_live_sandbox?: boolean;
    details?: string;
    capture_status?: string;
    payment_status?: string;
    reconciliation_status?: string;
  };
  fulfillment?: {
    status: string;
    order_id?: string;
    transfer_id?: string;
    carrier?: string;
    tracking_number?: string;
    released_inventory_units?: number;
    buyer_pickup_code?: string;
    pallet_staged_zone?: string;
    eta_minutes?: number;
    temperature_logged_celsius?: number;
  };
  financial_reconciliation?: {
    status: string;
    gross_recovered: number;
    fees_and_costs: number;
    net_recovery: number;
    waste_avoided_percentage: number;
    audit_notes: string;
  };
  ceo_report?: {
    report_id: string;
    executive_summary: string;
    action_executed: string;
    governance_status: string;
    recommended_operational_change: string;
  };
}
