import csv
from datetime import datetime, timedelta
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from ..database import engine, SessionLocal, Base
from .. import models  # noqa: F401 — ensure all ORM tables are registered with Base.metadata
from ..models.inventory import Inventory
from ..models.store import Store
from ..models.logistics import LogisticsPartner
from ..models.transfer import TransferOrder, TransferEvent
from ..models.outcome import Outcome, OutcomeEvent
from ..models.commerce import RecoveryOrder, RecoveryOrderStatus, RecoveryFulfillmentStatus

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def init_db():
    """Idempotently create missing tables using existing SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)


def seed_data():
    """Populate initial retail and sample order data only if tables are empty (never overwrites existing data)."""
    db: Session = SessionLocal()
    try:
        # 1. Seed Stores
        if db.query(Store).count() == 0:
            stores_file = DATA_DIR / "stores.csv"
            if stores_file.exists():
                with open(stores_file, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        store = Store(
                            store_id=row["store_id"],
                            store_name=row["store_name"],
                            latitude=float(row["latitude"]),
                            longitude=float(row["longitude"]),
                            address=row["address"],
                            supports_cold_chain=row["supports_cold_chain"].lower() == "true",
                        )
                        db.add(store)
                db.commit()

        # 2. Seed Logistics Partners
        if db.query(LogisticsPartner).count() == 0:
            lp_file = DATA_DIR / "logistics_partners.csv"
            if lp_file.exists():
                with open(lp_file, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        lp = LogisticsPartner(
                            partner_id=row["partner_id"],
                            partner_name=row["partner_name"],
                            cost_per_km=float(row["cost_per_km"]),
                            base_cost=float(row["base_cost"]),
                            average_eta_minutes=int(row["average_eta_minutes"]),
                            capacity_units=int(row["capacity_units"]),
                            supports_cold_chain=row["supports_cold_chain"].lower() == "true",
                        )
                        db.add(lp)
                db.commit()

        # 3. Seed Inventory
        if db.query(Inventory).count() == 0:
            inv_file = DATA_DIR / "inventory.csv"
            if inv_file.exists():
                with open(inv_file, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        days_str = row.get("days_to_expire")
                        if days_str:
                            expiry = datetime.utcnow() + timedelta(days=int(days_str) + 1)
                        else:
                            expiry = datetime.strptime(row["expiry_date"], "%Y-%m-%d")

                        inv = Inventory(
                            sku_id=row["sku_id"],
                            product_name=row["product_name"],
                            store_id=row["store_id"],
                            quantity=int(row["quantity"]),
                            cost_price=float(row["cost_price"]),
                            selling_price=float(row["selling_price"]),
                            expiry_date=expiry,
                            daily_sales_7d=float(row["daily_sales_7d"]),
                            temperature_class=row["temperature_class"],
                            return_allowed=row.get("return_allowed", "false").lower() == "true",
                            supplier_return_value=(
                                float(row["supplier_return_value"])
                                if row.get("supplier_return_value")
                                else None
                            ),
                            created_at=datetime.utcnow(),
                        )
                        db.add(inv)
                db.commit()

        # 4. Seed Initial Recovery Orders for PayPal Sandbox testing
        if db.query(RecoveryOrder).count() == 0:
            sample_orders = [
                RecoveryOrder(
                    order_id="REC-ORD-YOG001",
                    sku_id="YOG-001",
                    product_name="Greek Yogurt 500g",
                    source_store_id="STORE_A",
                    channel="DISCOUNT_MARKETPLACE",
                    quantity=15,
                    unit_price=2.50,
                    total_amount=37.50,
                    currency="USD",
                    buyer_name="Organic Grocery Co.",
                    buyer_email="buyer@organicgrocery.com",
                    status=RecoveryOrderStatus.CREATED.value,
                    fulfillment_status=RecoveryFulfillmentStatus.UNFULFILLED.value,
                ),
                RecoveryOrder(
                    order_id="REC-ORD-SAL002",
                    sku_id="SAL-002",
                    product_name="Atlantic Salmon Fillet",
                    source_store_id="STORE_B",
                    channel="B2B_WHOLESALE",
                    quantity=8,
                    unit_price=12.00,
                    total_amount=96.00,
                    currency="USD",
                    buyer_name="Metro Seafood Market",
                    buyer_email="procurement@metroseafood.com",
                    status=RecoveryOrderStatus.CREATED.value,
                    fulfillment_status=RecoveryFulfillmentStatus.UNFULFILLED.value,
                ),
                RecoveryOrder(
                    order_id="REC-ORD-BER003",
                    sku_id="BER-003",
                    product_name="Organic Blueberries 250g",
                    source_store_id="STORE_A",
                    channel="LIQUIDATION",
                    quantity=20,
                    unit_price=1.80,
                    total_amount=36.00,
                    currency="USD",
                    buyer_name="Fresh Smoothie Bar",
                    buyer_email="orders@freshsmoothie.com",
                    status=RecoveryOrderStatus.CREATED.value,
                    fulfillment_status=RecoveryFulfillmentStatus.UNFULFILLED.value,
                ),
            ]
            for ord_item in sample_orders:
                db.add(ord_item)
            db.commit()

        logger.info("Database seeding check completed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize schema and seed ReStockAI database (SQLite or PostgreSQL)"
    )
    parser.add_argument("--reset", action="store_true", help="Reset database before loading")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
        print("Database schemas dropped.")

    init_db()
    seed_data()
    print("Database initialization and seeding completed.")
