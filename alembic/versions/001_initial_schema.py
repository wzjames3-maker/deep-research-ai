"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    user_status = postgresql.ENUM("active", "locked", name="user_status", create_type=False)
    research_template = postgresql.ENUM(
        "tech_research", "competitive_analysis", "literature_review", "custom",
        name="research_template", create_type=False,
    )
    research_status = postgresql.ENUM(
        "draft", "confirmed", "running", "completed", "failed", "cancelled",
        name="research_status", create_type=False,
    )
    sub_agent_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", "cancelled",
        name="sub_agent_status", create_type=False,
    )

    user_status.create(op.get_bind(), checkfirst=True)
    research_template.create(op.get_bind(), checkfirst=True)
    research_status.create(op.get_bind(), checkfirst=True)
    sub_agent_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("status", user_status, server_default="active", nullable=False),
        sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remember_me", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_username", "users", ["username"], unique=True)
    op.create_index("idx_user_status", "users", ["status"])

    op.create_table(
        "researches",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("template", research_template, nullable=False),
        sa.Column("status", research_status, server_default="draft", nullable=False),
        sa.Column("plan_json", postgresql.JSONB(), nullable=True),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_research_user_id", "researches", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_research_status_user", "researches", ["user_id", "status"])
    op.create_index(
        "idx_research_deleted_at", "researches", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "sub_agent_results",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_id", postgresql.UUID(), sa.ForeignKey("researches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(200), nullable=False),
        sa.Column("agent_goal", sa.Text(), nullable=False),
        sa.Column("search_direction", sa.Text(), nullable=False),
        sa.Column("status", sub_agent_status, server_default="pending", nullable=False),
        sa.Column("rounds_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("visited_urls", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("findings_text", sa.Text(), nullable=True),
        sa.Column("token_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sub_agent_research_id", "sub_agent_results", ["research_id"])

    op.create_table(
        "research_plan_feedbacks",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_id", postgresql.UUID(), sa.ForeignKey("researches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("user_feedback", sa.Text(), nullable=False),
        sa.Column("plan_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute(
        "CREATE TRIGGER trg_users_updated_at "
        "BEFORE UPDATE ON users "
        "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
    )
    op.execute(
        "CREATE TRIGGER trg_researches_updated_at "
        "BEFORE UPDATE ON researches "
        "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_researches_updated_at ON researches")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    op.drop_table("research_plan_feedbacks")
    op.drop_table("sub_agent_results")
    op.drop_table("researches")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS sub_agent_status")
    op.execute("DROP TYPE IF EXISTS research_status")
    op.execute("DROP TYPE IF EXISTS research_template")
    op.execute("DROP TYPE IF EXISTS user_status")
