export interface AgentSpeechBubbleItem {
  id: number;
  agentId: number;
  message: string;
  kind: 'instruction' | 'working' | 'reporting' | 'approval' | 'success' | 'failure' | 'general';
  expiresAt: number;
}

export type AgentRole =
  | 'CEO / Operations Supervisor'
  | 'Inventory Risk Specialist'
  | 'Recovery Strategy Specialist'
  | 'Logistics & Route Specialist'
  | 'Commerce & Markdown Specialist'
  | 'Fulfillment & Warehouse Specialist'
  | 'Finance & Margins Specialist';

export type AgentDepartment =
  | 'Executive Office'
  | 'AI Agent Workroom'
  | 'Human Approval'
  | 'Conference Room'
  | 'Breakroom';

export type AgentStatusType = 'idle' | 'active' | 'moving' | 'working' | 'waiting_approval' | 'completed';

export interface VirtualAgent {
  id: number;
  name: string;
  role: AgentRole;
  department: AgentDepartment;
  status: AgentStatusType;
  color: string;
  currentTask?: string;
  currentTool?: string;
  isAwaitingInput?: boolean;
  isPermissionActive?: boolean;
  x?: number;
  y?: number;
}

export interface ToolActivity {
  toolId: string;
  agentId: number;
  status: string;
  toolName?: string;
  permissionActive?: boolean;
  startTime: number;
}

export interface PendingApproval {
  approval_id: string;
  scenario_id: string;
  sku_id: string;
  source_store_id: string;
  destination_store_id: string;
  quantity: number;
  selected_partner: string;
  net_recovery: number;
  cedar_allowed: boolean;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: number;
}

export interface TimelineEntry {
  timestamp: string;
  agent: string;
  action: string;
  details: string;
}

export interface InventoryFindings {
  agent_id: number;
  sku_id: string;
  store_id: string;
  product_name: string;
  quantity: number;
  days_to_expiry: number;
  at_risk_quantity: number;
  at_risk_value: number;
  risk_level: string;
  risk_score: number;
  recommendation_summary: string;
}

export interface StrategyRecommendation {
  agent_id: number;
  sku_id: string;
  source_store_id: string;
  selected_action: string;
  recommended_quantity: number;
  expected_net_recovery: number;
  target_destination_store_id: string;
  candidate_destinations_count: number;
  decision_reason: string;
}

export interface LogisticsPlan {
  agent_id: number;
  sku_id: string;
  source_store_id: string;
  destination_store_id: string;
  transfer_quantity: number;
  selected_partner: string;
  distance_km: number;
  estimated_delivery_cost: number;
  estimated_eta_minutes: number;
  cold_chain_compliant: boolean;
  logistics_adjusted_net_recovery: number;
  transfer_viable: boolean;
  reason: string;
}

export interface CEOOpsReport {
  scenario_id: string;
  sku_id: string;
  source_store_id: string;
  product_name: string;
  overall_status: string;
  inventory_findings?: InventoryFindings;
  strategy_recommendation?: StrategyRecommendation;
  logistics_plan?: LogisticsPlan;
  commerce_plan?: any;
  fulfillment_summary?: any;
  financial_audit?: any;
  requires_human_approval: boolean;
  approval_id?: string;
  approval_details?: PendingApproval;
  executive_summary: string;
  timeline: TimelineEntry[];
}

export type ServerMessage =
  | { type: 'layout'; layout: any }
  | { type: 'existingAgents'; agents: Array<{ id: number; name?: string }> }
  | { type: 'agentCreated'; agentId: number; name?: string }
  | { type: 'agentClosed'; agentId: number }
  | { type: 'agentSelected'; agentId: number | null }
  | { type: 'agentStatus'; agentId: number; status: 'active' | 'idle' }
  | { type: 'agentAwaitingInput'; agentId: number; awaiting: boolean }
  | { type: 'agentToolStart'; agentId: number; toolId: string; status: string; toolName?: string; permissionActive?: boolean }
  | { type: 'agentToolDone'; agentId: number; toolId: string }
  | { type: 'agentToolsClear'; agentId: number }
  | { type: 'agentToolPermission'; agentId: number; required: boolean }
  | { type: 'agentMoveTo'; agentId: number; destination: string; x?: number; y?: number }
  | { type: 'pong'; timestamp?: number };

export type ClientMessage =
  | { type: 'webviewReady' }
  | { type: 'saveAgentSeats'; seats: any }
  | { type: 'focusAgent'; agentId: number }
  | { type: 'ping' };
