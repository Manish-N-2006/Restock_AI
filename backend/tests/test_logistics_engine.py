from app.services.logistics_engine import (
    evaluate_logistics_options,
    get_best_logistics_partner,
    get_integrated_recommendation
)
from app.models.inventory import Inventory
from app.models.store import Store
from app.models.logistics import LogisticsPartner
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.database import SessionLocal

def test_evaluate_logistics_options_success():
    db = SessionLocal()
    try:
        # This assumes mock data is already populated by data_loader
        options = evaluate_logistics_options(
            db=db,
            sku_id="YOG-001",
            source_store_id="STORE_A",
            destination_store_id="STORE_B",
            transfer_quantity=10
        )
    finally:
        db.close()
    
    assert options.matched is True
    assert len(options.options) > 0
    
    # YOG-001 is a cold chain product (2-8 C)
    # Check that any eligible partner has supports_cold_chain = True
    eligible_partners = [p for p in options.options if p.eligible]
    for p in eligible_partners:
        assert p.supports_cold_chain is True
        assert p.capacity_units >= 10
        assert p.logistics_suitability_score > 0
        assert 0 <= p.cost_score <= 100
        assert 0 <= p.eta_score <= 100
        assert 0 <= p.capacity_score <= 100
        
def test_evaluate_logistics_options_insufficient_capacity():
    db = SessionLocal()
    try:
        # Ask for 10000 units, which no single truck can handle
        options = evaluate_logistics_options(
            db=db,
            sku_id="YOG-001",
            source_store_id="STORE_A",
            destination_store_id="STORE_B",
            transfer_quantity=10000
        )
    finally:
        db.close()
    
    assert options.matched is False
    assert len(options.options) > 0
    
    for p in options.options:
        assert p.eligible is False
        assert p.reason == "Insufficient transport capacity"

def test_get_best_logistics_partner():
    db = SessionLocal()
    try:
        best = get_best_logistics_partner(
            db=db,
            sku_id="YOG-001",
            source_store_id="STORE_A",
            destination_store_id="STORE_B",
            transfer_quantity=10
        )
    finally:
        db.close()
    
    assert best.matched is True
    assert best.selected_partner is not None
    assert best.selected_partner.eligible is True
    
def test_get_integrated_recommendation():
    db = SessionLocal()
    try:
        rec = get_integrated_recommendation(db, "YOG-001", "STORE_A")
    finally:
        db.close()
    
    # We know YOG-001 at STORE_A leads to a TRANSFER to STORE_B based on Phase 3
    assert rec.decision.selected_action.value == "TRANSFER"
    assert rec.logistics is not None
    assert rec.logistics.selected_partner is not None
    assert rec.logistics_adjusted_net_recovery > 0
    assert rec.transfer_still_viable is True
