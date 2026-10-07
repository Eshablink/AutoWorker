"""add normalized approval request projection

Revision ID: 0003_approval_requests
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_approval_requests"
down_revision = "0002_task_created_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("approval_id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("policy_decision_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("tool_id", sa.String(length=255), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approval_requests_task_id", "approval_requests", ["task_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_expires_at", "approval_requests", ["expires_at"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                INSERT INTO approval_requests (
                    approval_id, task_id, action_id, policy_decision_id,
                    status, tool_id, risk_level, expires_at, created_at, decided_at
                )
                SELECT
                    action->'approval_request'->>'approval_id',
                    t.task_id,
                    action->'approval_request'->>'action_id',
                    action->'approval_request'->>'policy_decision_id',
                    action->'approval_request'->>'status',
                    action->'approval_request'->>'tool_id',
                    action->'approval_request'->>'risk_level',
                    CASE
                        WHEN action->'approval_request'->>'expires_at' IS NULL THEN NULL
                        ELSE (action->'approval_request'->>'expires_at')::timestamptz
                    END,
                    (action->'approval_request'->>'created_at')::timestamptz,
                    CASE
                        WHEN action->'approval_request'->>'decided_at' IS NULL THEN NULL
                        ELSE (action->'approval_request'->>'decided_at')::timestamptz
                    END
                FROM tasks AS t
                CROSS JOIN LATERAL json_array_elements(t.payload->'actions') AS action
                WHERE action->'approval_request' IS NOT NULL
                  AND action->'approval_request'->>'approval_id' IS NOT NULL
                ON CONFLICT (approval_id) DO NOTHING
                """
            )
        )
    elif bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                """
                INSERT OR IGNORE INTO approval_requests (
                    approval_id, task_id, action_id, policy_decision_id,
                    status, tool_id, risk_level, expires_at, created_at, decided_at
                )
                SELECT
                    json_extract(value, '$.approval_request.approval_id'),
                    t.task_id,
                    json_extract(value, '$.approval_request.action_id'),
                    json_extract(value, '$.approval_request.policy_decision_id'),
                    json_extract(value, '$.approval_request.status'),
                    json_extract(value, '$.approval_request.tool_id'),
                    json_extract(value, '$.approval_request.risk_level'),
                    json_extract(value, '$.approval_request.expires_at'),
                    json_extract(value, '$.approval_request.created_at'),
                    json_extract(value, '$.approval_request.decided_at')
                FROM tasks AS t
                JOIN json_each(t.payload, '$.actions')
                WHERE json_extract(value, '$.approval_request.approval_id') IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    op.drop_index("ix_approval_requests_expires_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_task_id", table_name="approval_requests")
    op.drop_table("approval_requests")
