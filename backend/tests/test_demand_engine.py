from app.services.demand_engine import (
    calculate_distance_km,
    calculate_destination_capacity,
    check_cold_chain,
    calculate_candidate_score,
    TARGET_FILL_RATIO
)
from app.models.store import Store

def test_calculate_distance():
    # Identical coordinates
    assert calculate_distance_km(34.0, -118.0, 34.0, -118.0) == 0.0
    # Known pair (approx 13km distance)
    dist = calculate_distance_km(34.0522, -118.2437, 34.1425, -118.2551)
    assert dist > 0
    assert 10.0 < dist < 15.0

def test_calculate_destination_capacity():
    # normal demand
    cap = calculate_destination_capacity(current_stock=5, daily_demand=18, remaining_days=2)
    assert cap == 31.0 # (18 * 2) - 5
    
    # zero demand
    cap = calculate_destination_capacity(current_stock=10, daily_demand=0, remaining_days=5)
    assert cap == 0.0
    
    # insufficient demand (overstocked)
    cap = calculate_destination_capacity(current_stock=50, daily_demand=2, remaining_days=5)
    assert cap == 0.0
    
    # expiry = 0
    cap = calculate_destination_capacity(current_stock=5, daily_demand=10, remaining_days=0)
    assert cap == 0.0

def test_check_cold_chain():
    store_ambient = Store(store_name="A", supports_cold_chain=False)
    store_cold = Store(store_name="B", supports_cold_chain=True)
    
    # Cold chain product
    assert check_cold_chain("2-8 C", store_ambient) is False
    assert check_cold_chain("2-8 C", store_cold) is True
    
    # Ambient product
    assert check_cold_chain("Ambient", store_ambient) is True
    assert check_cold_chain("Ambient", store_cold) is True
    
def test_calculate_candidate_score():
    score1 = calculate_candidate_score(demand=20.0, capacity=100.0, distance=0.0)
    assert score1 == 100.0 # perfect score
    
    score2 = calculate_candidate_score(demand=0.0, capacity=0.0, distance=20.0)
    assert score2 == 0.0 # terrible score
    
    # Check that score is deterministic and correctly ordered
    score3 = calculate_candidate_score(demand=10.0, capacity=50.0, distance=5.0)
    score4 = calculate_candidate_score(demand=10.0, capacity=50.0, distance=10.0)
    assert score3 > score4 # Closer distance is better
