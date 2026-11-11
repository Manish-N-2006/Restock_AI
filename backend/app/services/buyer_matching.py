"""
Deterministic Buyer Matching Service for Commercial Inventory Recovery.
Evaluates external demonstration buyer profiles against at-risk inventory.
All buyer profiles are explicitly flagged as simulated demo data.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BuyerProfile(BaseModel):
    buyer_id: str
    name: str
    organization_type: str
    supported_categories: List[str]
    min_quantity: int
    max_quantity: int
    max_unit_price: float
    max_distance_km: float
    requires_cold_chain: bool
    verification_status: str
    location: str
    contact_email: str
    is_demo_data: bool = True

class BuyerMatchResult(BaseModel):
    buyer_id: str
    name: str
    organization_type: str
    match_score: float  # 0 to 100
    is_compatible: bool
    offered_quantity: int
    offered_unit_price: float
    estimated_total_order: float
    compatibility_reasons: List[str]
    disqualification_reasons: List[str]
    location: str
    contact_email: str
    is_demo_data: bool = True

# Deterministic Seeded Demonstration Buyer Database
DEMO_BUYER_REGISTRY: List[BuyerProfile] = [
    BuyerProfile(
        buyer_id="BUYER-METRO-01",
        name="Metro Retail Discount Mart",
        organization_type="Discount Retail Chain",
        supported_categories=["Dairy", "Produce", "Bakery", "Beverages", "Groceries"],
        min_quantity=20,
        max_quantity=400,
        max_unit_price=3.50,
        max_distance_km=50.0,
        requires_cold_chain=True,
        verification_status="VERIFIED_PAYPAL_SANDBOX_BUYER",
        location="Metro Logistics Zone 4 (18km)",
        contact_email="procurement@metroretail.example.com",
    ),
    BuyerProfile(
        buyer_id="BUYER-SMOOTHIE-03",
        name="Fresh Smoothies & Juice Co.",
        organization_type="Commercial Beverage Operator",
        supported_categories=["Dairy", "Produce", "Fruits"],
        min_quantity=15,
        max_quantity=150,
        max_unit_price=2.80,
        max_distance_km=30.0,
        requires_cold_chain=True,
        verification_status="VERIFIED_COMMERCIAL_BUYER",
        location="Downtown Kitchen Complex (12km)",
        contact_email="orders@freshsmoothie.example.com",
    ),
    BuyerProfile(
        buyer_id="BUYER-FOODBANK-02",
        name="Regional Community Food Bank",
        organization_type="Non-Profit Relief Network",
        supported_categories=["Dairy", "Bakery", "Pantry", "Produce"],
        min_quantity=10,
        max_quantity=300,
        max_unit_price=1.50,
        max_distance_km=60.0,
        requires_cold_chain=False,
        verification_status="VERIFIED_INSTITUTIONAL",
        location="East Valley Hub (35km)",
        contact_email="intake@communityfoodbank.example.org",
    ),
    BuyerProfile(
        buyer_id="BUYER-DELI-05",
        name="Grand Harbor Seafood & Bistro",
        organization_type="Hospitality & Restaurant Group",
        supported_categories=["Seafood", "Meat", "Dairy", "Specialty"],
        min_quantity=5,
        max_quantity=60,
        max_unit_price=16.00,
        max_distance_km=40.0,
        requires_cold_chain=True,
        verification_status="VERIFIED_COMMERCIAL_BUYER",
        location="Harbor Waterfront (22km)",
        contact_email="purchasing@grandharborbistro.example.com",
    ),
    BuyerProfile(
        buyer_id="BUYER-BULK-04",
        name="All-States B2B Liquidation Clearinghouse",
        organization_type="Wholesale Secondary Liquidator",
        supported_categories=["All", "Dairy", "Seafood", "Meat", "Dry Goods"],
        min_quantity=100,
        max_quantity=2000,
        max_unit_price=5.00,
        max_distance_km=120.0,
        requires_cold_chain=True,
        verification_status="VERIFIED_WHOLESALER",
        location="Intermodal Cargo Park (65km)",
        contact_email="deals@clearinghouse.example.com",
    ),
    BuyerProfile(
        buyer_id="BUYER-ECO-06",
        name="Eco-Salvage Animal Feed & Bio-Conversion",
        organization_type="Agricultural Conversion",
        supported_categories=["Organic Waste", "Expired Produce", "Spoiled Dairy", "Damaged"],
        min_quantity=50,
        max_quantity=1500,
        max_unit_price=0.50,
        max_distance_km=80.0,
        requires_cold_chain=False,
        verification_status="CERTIFIED_RECYCLER",
        location="Green Valley Facility (45km)",
        contact_email="logistics@ecosalvage.example.org",
    ),
]

def map_sku_to_category(sku_id: str, product_name: str) -> str:
    """Infers product category from SKU identifier and product name."""
    s = (sku_id + " " + product_name).lower()
    if any(k in s for k in ["yog", "yogurt", "milk", "cheese", "butter"]):
        return "Dairy"
    if any(k in s for k in ["sal", "salmon", "fish", "tuna", "seafood"]):
        return "Seafood"
    if any(k in s for k in ["ber", "berry", "blueberry", "apple", "produce", "salad"]):
        return "Produce"
    if any(k in s for k in ["bread", "bagel", "croissant", "bakery"]):
        return "Bakery"
    return "Groceries"

def match_buyers(
    sku_id: str,
    product_name: str,
    quantity: int,
    unit_price: float,
    requires_cold_chain: bool = True,
    max_acceptable_distance_km: float = 60.0,
) -> List[BuyerMatchResult]:
    """
    Deterministic Buyer Matching Engine.
    Evaluates demonstration buyer profiles using explicit compatibility criteria:
      1. Category alignment (30 pts)
      2. Quantity capacity constraint (25 pts)
      3. Price limit ceiling (25 pts)
      4. Geographic feasibility (10 pts)
      5. Verification and cold-chain compliance (10 pts)
    """
    category = map_sku_to_category(sku_id, product_name)
    results: List[BuyerMatchResult] = []

    for buyer in DEMO_BUYER_REGISTRY:
        score = 0.0
        compat_reasons: List[str] = []
        disqual_reasons: List[str] = []

        # 1. Category Matching (30 pts)
        if "All" in buyer.supported_categories or category in buyer.supported_categories:
            score += 30.0
            compat_reasons.append(f"Category matched: '{category}' supported")
        else:
            disqual_reasons.append(f"Category mismatch: buyer handles {', '.join(buyer.supported_categories)}, not '{category}'")

        # 2. Quantity Demand Matching (25 pts)
        if quantity < buyer.min_quantity:
            disqual_reasons.append(f"Lot size too small: {quantity} units < minimum {buyer.min_quantity}")
            score += max(0.0, 15.0 * (quantity / buyer.min_quantity))
        elif quantity > buyer.max_quantity:
            disqual_reasons.append(f"Lot size exceeds buyer capacity: {quantity} > maximum {buyer.max_quantity}")
            score += 10.0
        else:
            score += 25.0
            compat_reasons.append(f"Demand capacity optimal: {quantity} units within {buyer.min_quantity}–{buyer.max_quantity}")

        # 3. Price Limit Ceiling (25 pts)
        if unit_price <= buyer.max_unit_price:
            score += 25.0
            compat_reasons.append(f"Price acceptable: ${unit_price:.2f} <= buyer ceiling ${buyer.max_unit_price:.2f}")
        else:
            disqual_reasons.append(f"Price exceeds buyer ceiling: ${unit_price:.2f} > max ${buyer.max_unit_price:.2f}")
            price_ratio = buyer.max_unit_price / max(0.01, unit_price)
            score += max(0.0, 15.0 * price_ratio)

        # 4. Cold-chain and verification feasibility (10 pts)
        if requires_cold_chain and not buyer.requires_cold_chain:
            disqual_reasons.append("Cold chain incompatible: buyer lacks refrigerated receiving")
        else:
            score += 10.0
            compat_reasons.append("Refrigerated receiving equipment verified")

        # 5. Geographic Feasibility (10 pts)
        if buyer.max_distance_km <= max_acceptable_distance_km:
            score += 10.0
            compat_reasons.append(f"Logistics viable: location {buyer.location}")
        else:
            score += 5.0

        is_compatible = len(disqual_reasons) == 0
        final_score = round(min(100.0, max(0.0, score)), 1)

        # Matched purchasable quantity: Lot size capped by buyer max capacity
        purchasable_qty = min(quantity, buyer.max_quantity)
        total_order_value = round(purchasable_qty * unit_price, 2)

        results.append(
            BuyerMatchResult(
                buyer_id=buyer.buyer_id,
                name=buyer.name,
                organization_type=buyer.organization_type,
                match_score=final_score,
                is_compatible=is_compatible,
                offered_quantity=purchasable_qty,
                offered_unit_price=unit_price,
                estimated_total_order=total_order_value,
                compatibility_reasons=compat_reasons,
                disqualification_reasons=disqual_reasons,
                location=buyer.location,
                contact_email=buyer.contact_email,
                is_demo_data=True,
            )
        )

    # Sort descending by match score
    results.sort(key=lambda x: (x.is_compatible, x.match_score), reverse=True)
    return results

