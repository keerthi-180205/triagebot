"""Database tables. The `chunks` table is added in step 4."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Parent of every table class. Base.metadata lists all tables, and Alembic reads it."""


# Allowed values for Run.status, in the order a run normally moves through them.
RUN_STATUSES = ("received", "queued", "running", "succeeded", "fallback", "failed")


class Run(Base):
    """One triage of one GitHub issue, from webhook delivery to final outcome.

    delivery_id is unique, so a webhook delivered twice cannot create two runs. status follows
    RUN_STATUSES. The result columns (category, tokens, cost, latency, error) stay empty until
    the run finishes, so they must be nullable.
    """

    __tablename__ = "runs"
    __table_args__ = (Index("ix_runs_repo_created_at", "repo", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[str] = mapped_column(unique=True)
    repo: Mapped[str]
    status: Mapped[str] = mapped_column(default="received")
    input: Mapped[dict[str, Any]] = mapped_column(JSONB)
    category: Mapped[str | None]
    confidence: Mapped[float | None]
    model: Mapped[str | None]
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    latency_ms: Mapped[int | None]
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issue_number: Mapped[int]
    installation_id: Mapped[int] = mapped_column(BigInteger)


class ToolCall(Base):
    """One tool the agent called during a run, with its input, output and timing.

    A failed call is stored too (success=False, output may be empty) so failures can be measured.
    """

    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    tool: Mapped[str]
    input: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    success: Mapped[bool]
    latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
