import csv
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from ..database import engine, SessionLocal, Base
from ..models.inventory import Inventory
from ..models.store import Store
from ..models.logistics import LogisticsPartner
from ..models.transfer import TransferOrder, TransferEvent
from ..models.outcome import Outcome, OutcomeEvent

DATA_DIR = Path(__file__).parent.parent / "data"

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_data():
    db: Session = SessionLocal()
    
    # 1. Seed Stores
    if db.query(Store).count() == 0:
        stores_file = DATA_DIR / "stores.csv"
        if stores_file.exists():
            with open(stores_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    store = Store(
                        store_id=row["store_id"],
                        store_name=row["store_name"],
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        address=row["address"],
                        supports_cold_chain=row["supports_cold_chain"].lower() == 'true'
                    )
                    db.add(store)
            db.commit()

    # 2. Seed Logistics Partners
    if db.query(LogisticsPartner).count() == 0:
        lp_file = DATA_DIR / "logistics_partners.csv"
        if lp_file.exists():
            with open(lp_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lp = LogisticsPartner(
                        partner_id=row["partner_id"],
                        partner_name=row["partner_name"],
                        cost_per_km=float(row["cost_per_km"]),
                        base_cost=float(row["base_cost"]),
                        average_eta_minutes=int(row["average_eta_minutes"]),
                        capacity_units=int(row["capacity_units"]),
                        supports_cold_chain=row["supports_cold_chain"].lower() == 'true'
                    )
                    db.add(lp)
            db.commit()

    # 3. Seed Inventory
    if db.query(Inventory).count() == 0:
        inv_file = DATA_DIR / "inventory.csv"
        if inv_file.exists():
            with open(inv_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Calculate expiry relative to today if the CSV just provides days
                    days_str = row.get("days_to_expire")
                    if days_str:
                        from datetime import timedelta
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
                        return_allowed=row.get("return_allowed", "false").lower() == 'true',
                        supplier_return_value=float(row["supplier_return_value"]) if row.get("supplier_return_value") else None,
                        created_at=datetime.utcnow()
                    )
                    db.add(inv)
            db.commit()

    db.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    init_db()
    seed_data()
