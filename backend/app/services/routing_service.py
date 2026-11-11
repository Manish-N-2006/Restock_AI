"""
Routing Intelligence Service for ReStockAI.

Provides:
1. Road-routing integration with OpenStreetMap / OSRM public API.
2. Graceful, labeled fallback to calibrated Haversine approximation when offline or sandboxed.
3. Explicit distance labeling: Never report approximate/straight-line distance as actual driving distance.
4. Route feasibility, cold-chain suitability, and multi-tier transport cost calculation.
"""

import math
import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("restock.routing")

EARTH_RADIUS_KM = 6371.0
DEFAULT_ROAD_TORTUOSITY_FACTOR = 1.25
DEFAULT_URBAN_SPEED_KMH = 35.0
SAFETY_EXPIRY_BUFFER_HOURS = 4.0


class RouteEvaluation(BaseModel):
    origin: Dict[str, float]
    destination: Dict[str, float]
    straight_line_distance_km: float
    road_distance_km: float
    is_actual_driving_distance: bool
    routing_engine: str
    estimated_journey_time_minutes: int
    route_feasibility: str  # "FEASIBLE" | "INSUFFICIENT_TIME" | "UNREACHABLE"
    cold_chain_suitable: bool
    cold_chain_reason: str
    transportation_cost: float
    carrier_evaluated: Optional[str] = None
    telemetry_notes: str


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic coordinates."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    return round(EARTH_RADIUS_KM * c, 2)


class RoutingService:
    """Enterprise Routing Engine supporting real road API queries with calibrated fallback."""

    def __init__(self, osrm_base_url: Optional[str] = None, request_timeout: float = 2.0):
        resolved_url = osrm_base_url or os.getenv("RESTOCKAI_OSRM_URL") or "https://router.project-osrm.org"
        self.osrm_base_url = resolved_url.rstrip("/")
        self.request_timeout = request_timeout

    def query_road_network(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempts to query genuine road routing via OSRM.
        Returns dict with road_km and duration_seconds, or None if unavailable/offline.
        """
        try:
            import urllib.request
            import json

            # OSRM expects coordinates in {lon},{lat} format
            url = f"{self.osrm_base_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ReStockAI-RoutingEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("code") == "Ok" and data.get("routes"):
                        best_route = data["routes"][0]
                        distance_meters = best_route.get("distance", 0.0)
                        duration_seconds = best_route.get("duration", 0.0)
                        return {
                            "road_distance_km": round(distance_meters / 1000.0, 2),
                            "duration_minutes": round(duration_seconds / 60.0),
                            "engine": "OSRM_OPENSTREETMAP_ROAD_API",
                        }
        except Exception as exc:
            logger.debug(f"Genuine road-routing API unavailable or timed out: {exc}. Utilizing calibrated fallback.")

        return None

    def evaluate_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        carrier_base_cost: float = 25.0,
        carrier_per_km: float = 1.60,
        carrier_name: str = "SwiftReefer Express",
        supports_cold_chain: bool = True,
        requires_cold_chain: bool = True,
        remaining_expiry_hours: float = 48.0,
    ) -> RouteEvaluation:
        """
        Evaluates road route, ETA, feasibility, cold-chain compliance, and freight cost.
        Never conflates straight-line or estimated distances with actual driving distances.
        """
        straight_km = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)

        # 1. Attempt genuine road routing API
        road_data = self.query_road_network(origin_lat, origin_lon, dest_lat, dest_lon)

        if road_data:
            road_km = road_data["road_distance_km"]
            transit_min = road_data["duration_minutes"]
            is_actual = True
            engine = road_data["engine"]
            notes = (
                f"Verified road route via OSRM: {road_km} km actual highway/arterial distance, "
                f"{transit_min} min journey time."
            )
        else:
            # 2. Clearly labeled calibrated Haversine fallback
            road_km = round(straight_km * DEFAULT_ROAD_TORTUOSITY_FACTOR, 2)
            transit_min = max(10, round((road_km / DEFAULT_URBAN_SPEED_KMH) * 60.0))
            is_actual = False
            engine = "HAVERSINE_CALIBRATED_FALLBACK"
            notes = (
                f"Estimated road distance via calibrated Haversine model (tortuosity factor: {DEFAULT_ROAD_TORTUOSITY_FACTOR}x, "
                f"assumed urban speed: {DEFAULT_URBAN_SPEED_KMH} km/h). NOT actual driving distance."
            )

        # 3. Route Feasibility Evaluation
        transit_hours = transit_min / 60.0
        if transit_hours + SAFETY_EXPIRY_BUFFER_HOURS > remaining_expiry_hours:
            route_feasibility = "INSUFFICIENT_TIME"
        elif road_km > 300.0:
            route_feasibility = "EXCEEDS_URBAN_RADIUS"
        else:
            route_feasibility = "FEASIBLE"

        # 4. Cold-Chain Suitability
        if requires_cold_chain and not supports_cold_chain:
            cold_suitable = False
            cold_reason = "Rejected: Carrier lacks certified active refrigeration unit for chilled inventory."
        elif route_feasibility == "INSUFFICIENT_TIME":
            cold_suitable = False
            cold_reason = f"Rejected: Transit time ({transit_min} min) exceeds safety shelf-life buffer ({remaining_expiry_hours:.1f} hrs remaining)."
        else:
            cold_suitable = True
            cold_reason = "Compliant: Active refrigeration verified, transit window safely within shelf-life threshold."

        # 5. Transportation Cost Calculation
        transport_cost = round(carrier_base_cost + (road_km * carrier_per_km), 2)

        return RouteEvaluation(
            origin={"lat": origin_lat, "lon": origin_lon},
            destination={"lat": dest_lat, "lon": dest_lon},
            straight_line_distance_km=straight_km,
            road_distance_km=road_km,
            is_actual_driving_distance=is_actual,
            routing_engine=engine,
            estimated_journey_time_minutes=transit_min,
            route_feasibility=route_feasibility,
            cold_chain_suitable=cold_suitable,
            cold_chain_reason=cold_reason,
            transportation_cost=transport_cost,
            carrier_evaluated=carrier_name,
            telemetry_notes=notes,
        )


routing_service = RoutingService()

