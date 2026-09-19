# ReStockAI - Phase 1

ReStockAI is an inventory recovery and network optimization platform for multi-location retail and quick-commerce businesses. 

## Phase 1 Scope
The goal of Phase 1 is to create a clean local foundation and implement the first working intelligence loop:
**Data → Backend → Risk Detection → Basic Recovery Economics**

**Note**: Phase 1 is fully deterministic. It does not include LLMs, machine learning, React frontends, AWS deployments, or external logistics API integrations. These will be added in future phases.

## Architecture
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: SQLite (via SQLAlchemy)
- **Validation**: Pydantic
- **Data Load**: CSV to SQLite seeding

### Folder Structure
```
ReStockAI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/           # SQLAlchemy DB Models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── routers/          # FastAPI route handlers
│   │   ├── services/         # Business logic (Risk/Recovery Engines)
│   │   └── data/             # CSV synthetic datasets
│   ├── tests/                # Pytest unit tests
│   └── requirements.txt
├── .gitignore
└── README.md
```

## Installation

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

2. **Install requirements**:
   ```bash
   pip install -r backend/requirements.txt
   ```

## Seeding the Database
To load the synthetic demo dataset into the local SQLite database, run the data loader service from the root of the repository:
```bash
python -m backend.app.services.data_loader
```
This will create `restock.db` in the root directory and populate it with stores, logistics partners, and inventory data.

## Running the Server
Start the FastAPI development server using `uvicorn`:
```bash
uvicorn backend.app.main:app --reload
```
The server will start on `http://127.0.0.1:8000`. You can view the interactive API documentation at:
- [Swagger UI](http://127.0.0.1:8000/docs)

## API Endpoints
- `GET /health` - Health check.
- `GET /api/inventory` - Get all inventory.
- `GET /api/inventory/{sku_id}` - Get inventory for a specific SKU.
- `GET /api/risk` - Evaluate risk for all inventory items.
- `GET /api/risk/summary` - Get a high-level summary of network inventory risk.
- `POST /api/recovery/evaluate` - Evaluate the economics of a recovery action (transfer, discount, dispose, etc.).

## Business Logic
### Rule-based Inventory Risk Score
Calculated in `risk_engine.py`:
- **Days to expiry** = `expiry_date` - `today`
- **Expected sales before expiry** = `daily_sales_7d` × `max(days_to_expiry, 0)`
- **Expected remaining quantity** = `max(quantity - expected_sales_before_expiry, 0)`
- **At-risk quantity** = `min(expected_remaining_quantity, quantity)`
- **At-risk value** = `at_risk_quantity` × `cost_price`
- **Risk Score** = Normalized 0-100 score based on risk percentage and urgency (expiry proximity).
- **Risk Level** = LOW, MEDIUM, HIGH, or CRITICAL based on the score and expiry days.

### Recovery Economics
Calculated in `recovery_engine.py`. Evaluates actions deterministically:
`Expected Net Recovery = Expected Recovered Value - Logistics Cost - Handling Cost - Risk Cost`

## Running Tests
Run the pytest suite to verify the logic:
```bash
pytest backend/tests/
```

## Example Requests

**Get Risk Summary:**
```bash
curl -X GET "http://127.0.0.1:8000/api/risk/summary"
```

**Evaluate a Transfer Action:**
```bash
curl -X POST "http://127.0.0.1:8000/api/recovery/evaluate" -H "Content-Type: application/json" -d '{
  "sku_id": "YOG-001",
  "quantity": 42,
  "source_store_id": "STORE_A",
  "action": "transfer",
  "expected_recovery_price": 160,
  "logistics_cost": 50,
  "handling_cost": 20,
  "risk_cost": 0
}'
```

## Phase 2 — Demand Intelligence

The Demand Engine determines which nearby stores can absorb at-risk inventory.

### Core Capabilities
- **Geographic Matching**: Calculates the Haversine distance between stores. Excludes matches beyond the 15km maximum transfer radius.
- **Same-SKU Demand Matching**: Uses `daily_sales_7d` as the deterministic demand signal for the destination store.
- **Destination Capacity**: Safely calculates how much inventory the destination can absorb before expiry, capped by a safety buffer (`TARGET_FILL_RATIO` of 80%).
- **Cold-Chain Compatibility**: Rejects matches if the product requires cold-chain transport (e.g. 2-8 C) but the destination store does not support it.

### Suitability Scoring & Ranking
Destination candidates are ranked by a deterministic 0-100 `destination_suitability_score`, which is a weighted combination of:
1. Normalized daily demand (50% weight)
2. Normalized usable destination capacity (35% weight)
3. Normalized distance score (closer is better) (15% weight)

*Note: This is a rule-based destination ranking, not an AI prediction.*

### Recommended Transfer Quantity
The system explicitly recommends a deterministic `recommended_transfer_quantity`:
`min(source_at_risk_quantity, usable_destination_capacity)`

### Phase 2 Example API Requests

**Get Candidates for a SKU:**
```bash
curl -X GET "http://127.0.0.1:8000/api/demand/candidates/YOG-001?source_store_id=STORE_A"
```

**Get the Single Best Match for a SKU:**
```bash
curl -X GET "http://127.0.0.1:8000/api/demand/best-match/YOG-001?source_store_id=STORE_A"
```

**Get the Network Match Summary:**
```bash
curl -X GET "http://127.0.0.1:8000/api/demand/summary"
```

### Scenario: The Yogurt Match
- **Source (STORE_A)**: Has 50 units of YOG-001. Demand is low (4/day), and expiry is 2 days. The Risk Engine calculates 42 units are at high risk.
- **Destination (STORE_B)**: Has high demand (10/day) and low stock (5 units). It is geographically nearby and supports the required cold chain.
- **Result**: The Demand Engine produces `STORE_B` as a qualified destination candidate with a high suitability score, and an explicit recommendation to transfer ~24 units based on capacity constraints.

### Phase 3: Recovery Decision Engine
- `GET /api/decision/evaluate`
- `GET /api/decision/summary`

### Phase 4: Logistics Partner Selection
- `GET /api/logistics/options`
- `GET /api/logistics/best`
- `GET /api/logistics/recommend/{sku_id}`
- `GET /api/logistics/summary` and determines the absolute best economic recovery action.

### The Pipeline
1. **Risk Engine** = Detects danger. Gating prevents healthy inventory from unnecessary evaluation.
2. **Demand Engine** = Finds possible transfer destinations.
3. **Decision Engine** = Chooses the economically best recovery action.

### Supported Actions & Economics
- **`TRANSFER`**: Uses Phase 2 destinations. `Net Recovery = (Qty * Price) - Logistics Cost - Handling Cost`
- **`DISCOUNT`**: Markdown at current store. `Net Recovery = (Qty * Discounted Price)`
- **`BUNDLE`**: Combine with another product. `Net Recovery = (Qty * Bundle Price) - Handling Cost`
- **`PROMOTE`**: Boost visibility to increase sales. `Net Recovery = (Additional Qty * Price) - Promotion Handling`
- **`RETURN`**: Send back to supplier. `Net Recovery = (Qty * Supplier Price) - Return Logistics - Handling`
- **`DISPOSE`**: Destroy stock. `Net Recovery = -(Qty * Disposal Cost)`
- **`NO_ACTION`**: Fallback for items with no viable positive recovery.

### Selection Rule
The Engine strictly selects the action that yields the **highest positive expected net recovery**.
Ties are broken deterministically:
1. Highest net recovery
2. Highest gross recovered value
3. Lowest operational complexity (Discount > Promote > Bundle > Return > Transfer)

### Example Output
```json
{
  "selected_action": "TRANSFER",
  "selected_destination_store_id": "STORE_B",
  "recommended_quantity": 42,
  "expected_net_recovery": 6247.35,
  "decision_reason": "Transfer to STORE_B is recommended because it produces the highest positive expected net recovery of 6247.35."
}
```

### Phase 3 API Requests
**Get Full Decision for a SKU:**
```bash
curl -X GET "http://127.0.0.1:8000/api/decision/YOG-001?store_id=STORE_A"
```

**Get Action Comparison Array Only:**
```bash
curl -X GET "http://127.0.0.1:8000/api/decision/YOG-001/actions?store_id=STORE_A"
```

**Get Network Decision Summary:**
```bash
curl -X GET "http://127.0.0.1:8000/api/decision/summary"
```

**Evaluate Entire Network (Bulk):**
```bash
curl -X GET "http://127.0.0.1:8000/api/decision/all"
```
