import time
from app.services.orchestration_engine import run_complete_recovery_workflow, run_recovery_analysis

def main():
    print("=" * 60)
    print("ReStockAI End-to-End Orchestration Demo")
    print("=" * 60)
    print("\nScenario: YOG-001 at STORE_A")
    print("-" * 60)
    
    sku = "YOG-001"
    store = "STORE_A"
    
    print("\nPhase A: Analysis Only (READ ONLY)")
    print("-" * 60)
    time.sleep(1)
    
    analysis = run_recovery_analysis(sku, store)
    
    print(f"[1] Risk detected: {analysis['risk'].get('risk_level')}")
    print(f"[2] Destinations found: {len(analysis['destination_matches'].get('destinations', []))}")
    print(f"[3] Recovery action selected: {analysis['decision'].get('selected_action')}")
    print(f"[4] Logistics selected: {analysis['logistics'].get('logistics', {}).get('selected_partner', {}).get('partner_name', 'None')}")
    
    print("\nPhase B: Execution (MUTATES STATE)")
    print("-" * 60)
    time.sleep(1)
    
    print("Executing full transfer lifecycle...")
    workflow = run_complete_recovery_workflow(
        sku_id=sku,
        source_store_id=store,
        actual_units_sold=42,
        actual_recovered_value=6720.0,
        actual_logistics_cost=320.0,
        actual_handling_cost=50.0
    )
    
    if workflow["workflow_status"] == "COMPLETED":
        print("\nWorkflow Execution Log:")
        print(f"[5] Transfer created: {workflow.get('transfer', {}).get('transfer_id')}")
        print(f"[6] Transfer status: {workflow.get('transfer', {}).get('status')}")
        print(f"[7] Outcome recorded: {workflow.get('outcome', {}).get('outcome_id')}")
        print(f"[8] Outcome finalized: {workflow.get('outcome', {}).get('status')}")
        print(f"[9] OpenSearch history indexed: {workflow.get('history', {}).get('indexed')}")
        print("\nWorkflow COMPLETED")
    else:
        print("\nWorkflow FAILED:")
        print(f"Failed Stage: {workflow.get('failed_stage')}")
        print(f"Message: {workflow.get('message')}")

if __name__ == "__main__":
    main()
