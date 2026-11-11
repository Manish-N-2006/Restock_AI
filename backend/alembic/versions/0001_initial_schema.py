"""Initial ReStockAI database schema compatible with SQLite and PostgreSQL.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set:
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "stores" not in existing:
        op.create_table(
            "stores",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("store_id", sa.String(), nullable=True),
            sa.Column("store_name", sa.String(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("address", sa.String(), nullable=True),
            sa.Column("supports_cold_chain", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        )
        op.create_index("ix_stores_id", "stores", ["id"], unique=False)
        op.create_index("ix_stores_store_id", "stores", ["store_id"], unique=True)

    if "logistics_partners" not in existing:
        op.create_table(
            "logistics_partners",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("partner_id", sa.String(), nullable=True),
            sa.Column("partner_name", sa.String(), nullable=True),
            sa.Column("cost_per_km", sa.Float(), nullable=True),
            sa.Column("base_cost", sa.Float(), nullable=True),
            sa.Column("average_eta_minutes", sa.Integer(), nullable=True),
            sa.Column("capacity_units", sa.Integer(), nullable=True),
            sa.Column("supports_cold_chain", sa.Boolean(), nullable=True),
        )
        op.create_index("ix_logistics_partners_id", "logistics_partners", ["id"], unique=False)
        op.create_index("ix_logistics_partners_partner_id", "logistics_partners", ["partner_id"], unique=True)

    if "inventory" not in existing:
        op.create_table(
            "inventory",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("sku_id", sa.String(), nullable=True),
            sa.Column("product_name", sa.String(), nullable=True),
            sa.Column("store_id", sa.String(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("cost_price", sa.Float(), nullable=True),
            sa.Column("selling_price", sa.Float(), nullable=True),
            sa.Column("expiry_date", sa.DateTime(), nullable=True),
            sa.Column("daily_sales_7d", sa.Float(), nullable=True),
            sa.Column("temperature_class", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("return_allowed", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("supplier_return_value", sa.Float(), nullable=True),
            sa.Column("reserved_quantity", sa.Integer(), nullable=True, server_default=sa.text("0")),
        )
        op.create_index("ix_inventory_id", "inventory", ["id"], unique=False)
        op.create_index("ix_inventory_sku_id", "inventory", ["sku_id"], unique=False)
        op.create_index("ix_inventory_store_id", "inventory", ["store_id"], unique=False)

    transfer_status_enum = sa.Enum(
        "CREATED",
        "APPROVED",
        "ASSIGNED",
        "PICKUP_PENDING",
        "IN_TRANSIT",
        "DELIVERED",
        "COMPLETED",
        "CANCELLED",
        "FAILED",
        name="transferstatus",
    )
    transfer_status_enum_existing = sa.Enum(
        "CREATED",
        "APPROVED",
        "ASSIGNED",
        "PICKUP_PENDING",
        "IN_TRANSIT",
        "DELIVERED",
        "COMPLETED",
        "CANCELLED",
        "FAILED",
        name="transferstatus",
        create_type=False,
    )

    if "transfer_orders" not in existing:
        op.create_table(
            "transfer_orders",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("transfer_id", sa.String(), nullable=True),
            sa.Column("sku_id", sa.String(), nullable=True),
            sa.Column("product_name", sa.String(), nullable=True),
            sa.Column("source_store_id", sa.String(), nullable=True),
            sa.Column("destination_store_id", sa.String(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("status", transfer_status_enum, nullable=True),
            sa.Column("logistics_partner_id", sa.String(), nullable=True),
            sa.Column("logistics_partner_name", sa.String(), nullable=True),
            sa.Column("distance_km", sa.Float(), nullable=True),
            sa.Column("estimated_delivery_cost", sa.Float(), nullable=True),
            sa.Column("estimated_eta_minutes", sa.Integer(), nullable=True),
            sa.Column("expected_net_recovery", sa.Float(), nullable=True),
            sa.Column("logistics_adjusted_net_recovery", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=True),
            sa.Column("picked_up_at", sa.DateTime(), nullable=True),
            sa.Column("in_transit_at", sa.DateTime(), nullable=True),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_transfer_orders_id", "transfer_orders", ["id"], unique=False)
        op.create_index("ix_transfer_orders_transfer_id", "transfer_orders", ["transfer_id"], unique=True)
        op.create_index("ix_transfer_orders_sku_id", "transfer_orders", ["sku_id"], unique=False)
        op.create_index("ix_transfer_orders_source_store_id", "transfer_orders", ["source_store_id"], unique=False)
        op.create_index("ix_transfer_orders_destination_store_id", "transfer_orders", ["destination_store_id"], unique=False)
        op.create_index("ix_transfer_orders_status", "transfer_orders", ["status"], unique=False)

    if "transfer_events" not in existing:
        op.create_table(
            "transfer_events",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("transfer_id", sa.String(), sa.ForeignKey("transfer_orders.transfer_id"), nullable=True),
            sa.Column("from_status", transfer_status_enum_existing, nullable=True),
            sa.Column("to_status", transfer_status_enum_existing, nullable=True),
            sa.Column("event_type", sa.String(), nullable=True),
            sa.Column("message", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_transfer_events_id", "transfer_events", ["id"], unique=False)
        op.create_index("ix_transfer_events_transfer_id", "transfer_events", ["transfer_id"], unique=False)

    outcome_status_enum = sa.Enum("PENDING", "RECORDED", "FINALIZED", name="outcomestatus")

    if "outcomes" not in existing:
        op.create_table(
            "outcomes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("outcome_id", sa.String(), nullable=True),
            sa.Column("transfer_id", sa.String(), sa.ForeignKey("transfer_orders.transfer_id"), nullable=True),
            sa.Column("sku_id", sa.String(), nullable=True),
            sa.Column("source_store_id", sa.String(), nullable=True),
            sa.Column("destination_store_id", sa.String(), nullable=True),
            sa.Column("transferred_quantity", sa.Integer(), nullable=True),
            sa.Column("predicted_units_sold", sa.Integer(), nullable=True),
            sa.Column("predicted_recovered_value", sa.Float(), nullable=True),
            sa.Column("predicted_logistics_cost", sa.Float(), nullable=True),
            sa.Column("predicted_handling_cost", sa.Float(), nullable=True),
            sa.Column("predicted_net_recovery", sa.Float(), nullable=True),
            sa.Column("actual_units_sold", sa.Integer(), nullable=True),
            sa.Column("actual_unsold_units", sa.Integer(), nullable=True),
            sa.Column("actual_recovered_value", sa.Float(), nullable=True),
            sa.Column("actual_logistics_cost", sa.Float(), nullable=True),
            sa.Column("actual_handling_cost", sa.Float(), nullable=True),
            sa.Column("actual_net_recovery", sa.Float(), nullable=True),
            sa.Column("recovery_variance", sa.Float(), nullable=True),
            sa.Column("recovery_percentage", sa.Float(), nullable=True),
            sa.Column("unit_sales_variance", sa.Integer(), nullable=True),
            sa.Column("logistics_cost_variance", sa.Float(), nullable=True),
            sa.Column("recovery_accuracy_percentage", sa.Float(), nullable=True),
            sa.Column("sell_through_rate", sa.Float(), nullable=True),
            sa.Column("outcome_status", outcome_status_enum, nullable=True),
            sa.Column("outcome_recorded_at", sa.DateTime(), nullable=True),
            sa.Column("finalized_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_outcomes_id", "outcomes", ["id"], unique=False)
        op.create_index("ix_outcomes_outcome_id", "outcomes", ["outcome_id"], unique=True)
        op.create_index("ix_outcomes_transfer_id", "outcomes", ["transfer_id"], unique=True)
        op.create_index("ix_outcomes_sku_id", "outcomes", ["sku_id"], unique=False)
        op.create_index("ix_outcomes_source_store_id", "outcomes", ["source_store_id"], unique=False)
        op.create_index("ix_outcomes_destination_store_id", "outcomes", ["destination_store_id"], unique=False)
        op.create_index("ix_outcomes_outcome_status", "outcomes", ["outcome_status"], unique=False)

    if "outcome_events" not in existing:
        op.create_table(
            "outcome_events",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("outcome_id", sa.String(), sa.ForeignKey("outcomes.outcome_id"), nullable=True),
            sa.Column("event_type", sa.String(), nullable=True),
            sa.Column("message", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_outcome_events_id", "outcome_events", ["id"], unique=False)
        op.create_index("ix_outcome_events_outcome_id", "outcome_events", ["outcome_id"], unique=False)

    if "recovery_orders" not in existing:
        op.create_table(
            "recovery_orders",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("order_id", sa.String(), nullable=True),
            sa.Column("sku_id", sa.String(), nullable=True),
            sa.Column("product_name", sa.String(), nullable=True),
            sa.Column("source_store_id", sa.String(), nullable=True),
            sa.Column("channel", sa.String(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("total_amount", sa.Float(), nullable=True),
            sa.Column("currency", sa.String(), nullable=True),
            sa.Column("buyer_id", sa.String(), nullable=True),
            sa.Column("buyer_name", sa.String(), nullable=True),
            sa.Column("buyer_email", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("fulfillment_status", sa.String(), nullable=True),
            sa.Column("payment_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("paid_at", sa.DateTime(), nullable=True),
            sa.Column("fulfilled_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_recovery_orders_id", "recovery_orders", ["id"], unique=False)
        op.create_index("ix_recovery_orders_order_id", "recovery_orders", ["order_id"], unique=True)
        op.create_index("ix_recovery_orders_sku_id", "recovery_orders", ["sku_id"], unique=False)
        op.create_index("ix_recovery_orders_source_store_id", "recovery_orders", ["source_store_id"], unique=False)
        op.create_index("ix_recovery_orders_status", "recovery_orders", ["status"], unique=False)
        op.create_index("ix_recovery_orders_fulfillment_status", "recovery_orders", ["fulfillment_status"], unique=False)

    if "recovery_offers" not in existing:
        op.create_table(
            "recovery_offers",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("offer_id", sa.String(), nullable=True),
            sa.Column("sku_id", sa.String(), nullable=True),
            sa.Column("product_name", sa.String(), nullable=True),
            sa.Column("source_store_id", sa.String(), nullable=True),
            sa.Column("discount_pct", sa.Float(), nullable=True),
            sa.Column("offer_price", sa.Float(), nullable=True),
            sa.Column("original_price", sa.Float(), nullable=True),
            sa.Column("available_quantity", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_recovery_offers_id", "recovery_offers", ["id"], unique=False)
        op.create_index("ix_recovery_offers_offer_id", "recovery_offers", ["offer_id"], unique=True)
        op.create_index("ix_recovery_offers_sku_id", "recovery_offers", ["sku_id"], unique=False)
        op.create_index("ix_recovery_offers_source_store_id", "recovery_offers", ["source_store_id"], unique=False)

    if "payment_transactions" not in existing:
        op.create_table(
            "payment_transactions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("payment_id", sa.String(), nullable=True),
            sa.Column("recovery_order_id", sa.String(), sa.ForeignKey("recovery_orders.order_id"), nullable=True),
            sa.Column("paypal_order_id", sa.String(), nullable=True),
            sa.Column("paypal_capture_id", sa.String(), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("fee_amount", sa.Float(), nullable=True),
            sa.Column("net_amount", sa.Float(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("idempotency_key", sa.String(), nullable=True),
            sa.Column("payer_id", sa.String(), nullable=True),
            sa.Column("payer_email", sa.String(), nullable=True),
            sa.Column("payer_name", sa.String(), nullable=True),
            sa.Column("payment_method", sa.String(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("raw_response", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("captured_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_payment_transactions_id", "payment_transactions", ["id"], unique=False)
        op.create_index("ix_payment_transactions_payment_id", "payment_transactions", ["payment_id"], unique=True)
        op.create_index("ix_payment_transactions_recovery_order_id", "payment_transactions", ["recovery_order_id"], unique=False)
        op.create_index("ix_payment_transactions_paypal_order_id", "payment_transactions", ["paypal_order_id"], unique=True)
        op.create_index("ix_payment_transactions_paypal_capture_id", "payment_transactions", ["paypal_capture_id"], unique=True)
        op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"], unique=False)
        op.create_index("ix_payment_transactions_idempotency_key", "payment_transactions", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_table("payment_transactions")
    op.drop_table("recovery_offers")
    op.drop_table("recovery_orders")
    op.drop_table("outcome_events")
    op.drop_table("outcomes")
    op.drop_table("transfer_events")
    op.drop_table("transfer_orders")
    op.drop_table("inventory")
    op.drop_table("logistics_partners")
    op.drop_table("stores")

    if not context.is_offline_mode():
        bind = op.get_bind()
        if bind.dialect.name == "postgresql":
            sa.Enum(name="outcomestatus").drop(bind, checkfirst=True)
            sa.Enum(name="transferstatus").drop(bind, checkfirst=True)

