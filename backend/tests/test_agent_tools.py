import pytest
from app.agent.tools import (
    get_inventory_risk,
    find_destination_matches,
    evaluate_recovery_options,
    optimize_logistics,
    get_transfer_status,
    get_transfer_outcome,
    get_network_summary
)

def test_get_inventory_risk_tool_valid():
    res = get_inventory_risk(sku_id="YOG-001", store_id="STORE_A")
    assert isinstance(res, dict)
    assert "error" not in res
    assert res["sku_id"] == "YOG-001"
    assert "risk_level" in res

def test_get_inventory_risk_tool_invalid():
    res = get_inventory_risk(sku_id="UNKNOWN", store_id="STORE_A")
    assert "error" in res

def test_find_destination_matches_tool():
    res = find_destination_matches(sku_id="YOG-001", source_store_id="STORE_A")
    assert isinstance(res, dict)
    assert "destinations" in res

def test_evaluate_recovery_options_tool():
    res = evaluate_recovery_options(sku_id="YOG-001", store_id="STORE_A")
    assert isinstance(res, dict)
    assert "selected_action" in res

def test_optimize_logistics_tool():
    res = optimize_logistics(sku_id="YOG-001", source_store_id="STORE_A")
    assert isinstance(res, dict)
    assert "error" not in res
    assert "selected_partner" in res

def test_get_transfer_status_tool_invalid():
    res = get_transfer_status(transfer_id="INVALID")
    assert "error" in res

def test_get_transfer_outcome_tool_invalid():
    res = get_transfer_outcome(transfer_id="INVALID")
    assert "error" in res

def test_get_network_summary_tool():
    res = get_network_summary()
    assert isinstance(res, dict)
    assert "transfers" in res
    assert "outcomes" in res
