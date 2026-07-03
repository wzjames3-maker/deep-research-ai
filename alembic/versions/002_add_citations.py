"""add citations table

Revision ID: 002
Revises: 001
Create Date: 2026-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_id", postgresql.UUID(), sa.ForeignKey("researches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("citation_number", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_agent", sa.String(200), nullable=False, server_default=""),
        sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_citation_research_id", "citations", ["research_id"])
    op.create_index(
        "idx_citation_research_number", "citations", ["research_id", "citation_number"], unique=True
    )


def downgrade() -> None:
    op.drop_index("idx_citation_research_number", table_name="citations")
    op.drop_index("idx_citation_research_id", table_name="citations")
    op.drop_table("citations")
