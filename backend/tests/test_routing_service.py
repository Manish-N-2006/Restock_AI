"""
Tests for Routing Intelligence Service.
Verifies:
- Accurate road distance calculation with OSRM and fallback.
- Explicit labeling: Never claim estimated straight-line or fallback as actual driving distance.
- Cold-chain suitability and feasibility gates.
- Transport cost calculation.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.routing_service import (
    RoutingService,
    haversine_distance,
    RouteEvaluation,
)


def test_haversine_distance_calculation():
    # Store A (Downtown Central: 37.7749, -122.4194) to Store B (North District: 37.7891, -122.4014)
    dist = haversine_distance(37.7749, -122.4194, 37.7891, -122.4014)
    assert 2.0 <= dist <= 3.0  # Approx 2.22 km


def test_routing_fallback_labeling():
    service = RoutingService(osrm_base_url="http://invalid.route.internal", request_timeout=0.1)
    eval_res = service.evaluate_route(
        origin_lat=37.7749,
        origin_lon=-122.4194,
        dest_lat=37.7891,
        dest_lon=-122.4014,
        carrier_base_cost=25.0,
        carrier_per_km=1.60,
        carrier_name="SwiftReefer Express",
        supports_cold_chain=True,
        requires_cold_chain=True,
        remaining_expiry_hours=24.0,
    )

    assert eval_res.is_actual_driving_distance is False
    assert eval_res.routing_engine == "HAVERSINE_CALIBRATED_FALLBACK"
    assert "NOT actual driving distance" in eval_res.telemetry_notes
    assert eval_res.road_distance_km > eval_res.straight_line_distance_km
    assert eval_res.route_feasibility == "FEASIBLE"
    assert eval_res.cold_chain_suitable is True
    assert eval_res.transportation_cost > 25.0


def test_routing_genuine_road_api_mocked():
    service = RoutingService()
    mock_road_response = {
        "road_distance_km": 3.45,
        "duration_minutes": 11,
        "engine": "OSRM_OPENSTREETMAP_ROAD_API",
    }

    with patch.object(service, "query_road_network", return_value=mock_road_response):
        eval_res = service.evaluate_route(
            origin_lat=37.7749,
            origin_lon=-122.4194,
            dest_lat=37.7891,
            dest_lon=-122.4014,
            carrier_base_cost=25.0,
            carrier_per_km=1.60,
        )

        assert eval_res.is_actual_driving_distance is True
        assert eval_res.road_distance_km == 3.45
        assert eval_res.estimated_journey_time_minutes == 11
        assert eval_res.routing_engine == "OSRM_OPENSTREETMAP_ROAD_API"
        assert "Verified road route via OSRM" in eval_res.telemetry_notes
        expected_cost = round(25.0 + 3.45 * 1.60, 2)
        assert eval_res.transportation_cost == expected_cost


def test_routing_cold_chain_rejection():
    service = RoutingService()
    # Carrier does not support cold chain for chilled product
    eval_res = service.evaluate_route(
        origin_lat=37.7749,
        origin_lon=-122.4194,
        dest_lat=37.7891,
        dest_lon=-122.4014,
        supports_cold_chain=False,
        requires_cold_chain=True,
    )

    assert eval_res.cold_chain_suitable is False
    assert "lacks certified active refrigeration" in eval_res.cold_chain_reason

