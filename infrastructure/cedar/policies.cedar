// Manager Permissions - Can do everything across the network
permit (
    principal,
    action,
    resource
)
when {
    principal.role == "MANAGER"
};

// Viewer Permissions - Global read access but no mutations
permit (
    principal,
    action in [
        ReStockAI::Action::"VIEW_INVENTORY",
        ReStockAI::Action::"VIEW_RISK",
        ReStockAI::Action::"VIEW_DECISION",
        ReStockAI::Action::"VIEW_HISTORY",
        ReStockAI::Action::"VIEW_OUTCOME",
        ReStockAI::Action::"VIEW_TRANSFER",
        ReStockAI::Action::"ANALYZE_WORKFLOW"
    ],
    resource
)
when {
    principal.role == "VIEWER"
};

// Operator Permissions - Can view network and execute transfers in scope
permit (
    principal,
    action in [
        ReStockAI::Action::"VIEW_INVENTORY",
        ReStockAI::Action::"VIEW_RISK",
        ReStockAI::Action::"VIEW_DECISION",
        ReStockAI::Action::"VIEW_TRANSFER",
        ReStockAI::Action::"ANALYZE_WORKFLOW"
    ],
    resource
)
when {
    principal.role == "OPERATOR"
};

// Operator Transfer Execution (Scoped by Store)
permit (
    principal,
    action in [
        ReStockAI::Action::"CREATE_TRANSFER",
        ReStockAI::Action::"APPROVE_TRANSFER",
        ReStockAI::Action::"ASSIGN_TRANSFER",
        ReStockAI::Action::"START_TRANSFER",
        ReStockAI::Action::"COMPLETE_TRANSFER",
        ReStockAI::Action::"CANCEL_TRANSFER"
    ],
    resource
)
when {
    principal.role == "OPERATOR" && 
    (principal.store_scope == "*" || principal.store_scope == resource.source_store_id)
};

// --- EXPLICIT DENIES ---

// Nobody can modify a finalized outcome
forbid (
    principal,
    action == ReStockAI::Action::"MODIFY_FINALIZED_OUTCOME",
    resource
)
when {
    resource.finalized == true
};

// Cannot cancel or complete a transfer that is already completed
forbid (
    principal,
    action in [
        ReStockAI::Action::"COMPLETE_TRANSFER",
        ReStockAI::Action::"CANCEL_TRANSFER"
    ],
    resource
)
when {
    resource.status == "COMPLETED" || resource.status == "CANCELLED"
};
