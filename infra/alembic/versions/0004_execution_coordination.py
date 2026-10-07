"""add durable execution coordination primitives

Revision ID: 0004_execution_coordination
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_execution_coordination"
down_revision = "0003_approval_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_idempotency",
        sa.Column("idempotency_key", sa.String(length=255), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_execution_idempotency_status",
        "execution_idempotency",
        ["status"],
    )

    op.create_table(
        "task_leases",
        sa.Column("task_id", sa.String(length=36), primary_key=True),
        sa.Column("worker_id", sa.String(length=255), nullable=False),
        sa.Column("lease_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_leases_worker_id", "task_leases", ["worker_id"])
    op.create_index("ix_task_leases_expires_at", "task_leases", ["expires_at"])

    op.create_table(
        "event_outbox",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_event_outbox_task_id", "event_outbox", ["task_id"])
    op.create_index("ix_event_outbox_published_at", "event_outbox", ["published_at"])
    op.create_index(
        "ix_event_outbox_pending_created",
        "event_outbox",
        ["published_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_outbox_pending_created", table_name="event_outbox")
    op.drop_index("ix_event_outbox_published_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_task_id", table_name="event_outbox")
    op.drop_table("event_outbox")

    op.drop_index("ix_task_leases_expires_at", table_name="task_leases")
    op.drop_index("ix_task_leases_worker_id", table_name="task_leases")
    op.drop_table("task_leases")

    op.drop_index("ix_execution_idempotency_status", table_name="execution_idempotency")
    op.drop_table("execution_idempotency")
