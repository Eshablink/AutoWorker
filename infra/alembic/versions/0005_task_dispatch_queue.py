"""add durable task dispatch queue

Revision ID: 0005_task_dispatch_queue
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_task_dispatch_queue"
down_revision = "0004_execution_coordination"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_dispatch_queue",
        sa.Column("task_id", sa.String(length=36), primary_key=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_task_dispatch_queue_ready",
        "task_dispatch_queue",
        ["state", "available_at"],
    )
    op.create_index(
        "ix_task_dispatch_queue_claimed_by",
        "task_dispatch_queue",
        ["claimed_by"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                INSERT INTO task_dispatch_queue (task_id, state, available_at)
                SELECT task_id, 'READY',
                       COALESCE((payload->>'created_at')::timestamptz, CURRENT_TIMESTAMP)
                FROM tasks
                WHERE payload->>'status' IN ('CREATED', 'READY', 'RECOVERING', 'RUNNING')
                ON CONFLICT (task_id) DO NOTHING
                """
            )
        )
    elif bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                """
                INSERT OR IGNORE INTO task_dispatch_queue (task_id, state, available_at)
                SELECT task_id, 'READY',
                       COALESCE(json_extract(payload, '$.created_at'), CURRENT_TIMESTAMP)
                FROM tasks
                WHERE json_extract(payload, '$.status')
                    IN ('CREATED', 'READY', 'RECOVERING', 'RUNNING')
                """
            )
        )


def downgrade() -> None:
    op.drop_index("ix_task_dispatch_queue_claimed_by", table_name="task_dispatch_queue")
    op.drop_index("ix_task_dispatch_queue_ready", table_name="task_dispatch_queue")
    op.drop_table("task_dispatch_queue")
