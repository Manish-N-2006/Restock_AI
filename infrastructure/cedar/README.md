# Cedar Authorization Layer

ReStockAI uses [Cedar](https://www.cedarpolicy.com/) to enforce role- and resource-aware authorization before any operational mutations occur.

Cedar acts as a pure **Policy Engine** separating authorization logic from business logic.

## Architecture

```text
Manager (X-ReStockAI-User: manager-demo)
  ↓
Cedar Authorization (Evaluates Policies)
  ↓ (ALLOW)
ReStockAI Service Layer (Evaluates Business/Economic Logic)
  ↓
Database
```

- **Cedar** answers: *"Is this actor allowed to request this action?"*
- **ReStockAI Services** answer: *"Is this action valid and economically/operationally possible?"*

## Principals

- **MANAGER**: Network-wide access to all operations.
- **OPERATOR**: Execution capabilities bounded by their `store_scope` (can only transfer items from their assigned store).
- **VIEWER**: Global read-only access. Cannot execute transfers or modify outcomes.

## Explicit Denies

Cedar policies also ensure that critical business rules are never bypassed:
- Finalized outcomes cannot be modified.
- Completed transfers cannot be cancelled or completed again.

## Running Policy Validation

```bash
python -m backend.app.authorization.validate
```
