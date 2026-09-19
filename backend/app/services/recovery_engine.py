from ..schemas.recovery import RecoveryEvaluateRequest, RecoveryEvaluateResponse

def evaluate_recovery_action(request: RecoveryEvaluateRequest) -> RecoveryEvaluateResponse:
    """
    Evaluates the economics of a recovery action (transfer, discount, dispose, etc.).
    Expected Net Recovery = Expected Recovered Contribution - Logistics Cost - Handling Cost - Risk Cost
    """
    
    # Base calculation
    expected_recovered_value = request.expected_recovery_price * request.quantity
    
    net_recovery = (
        expected_recovered_value 
        - request.logistics_cost 
        - request.handling_cost 
        - request.risk_cost
    )
    
    # Do not allow negative values to produce misleading positive recovery
    net_recovery = max(net_recovery, -request.logistics_cost - request.handling_cost - request.risk_cost)
    
    economically_viable = net_recovery > 0

    return RecoveryEvaluateResponse(
        action=request.action,
        quantity=request.quantity,
        expected_recovered_value=expected_recovered_value,
        logistics_cost=request.logistics_cost,
        handling_cost=request.handling_cost,
        risk_cost=request.risk_cost,
        expected_net_recovery=net_recovery,
        economically_viable=economically_viable
    )
