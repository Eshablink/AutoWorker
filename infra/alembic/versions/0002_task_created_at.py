"""add indexed task creation timestamp for deterministic ordering

Revision ID: 0002_task_created_at
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_task_created_at"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE tasks
                SET created_at = (payload ->> 'created_at')::timestamptz
                WHERE payload ->> 'created_at' IS NOT NULL
                """
            )
        )
    elif bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                """
                UPDATE tasks
                SET created_at = json_extract(payload, '$.created_at')
                WHERE json_extract(payload, '$.created_at') IS NOT NULL
                """
            )
        )

    op.alter_column("tasks", "created_at", nullable=False)
    op.alter_column("tasks", "created_at", server_default=None)
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_column("tasks", "created_at")
