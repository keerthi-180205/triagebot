"""Database tables. The `chunks` table is added in step 4."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Allowed values for Run.status, in the order a run normally moves through them.
RUN_STATUSES = ("received", "queued", "running", "succeeded", "fallback", "failed")


class Run(Base):
    __tablename__ = "runs"
    # TODO: add Index("ix_runs_repo_created_at", "repo", "created_at") to __table_args__
    __table_args__ = ()

    id: Mapped[int] = mapped_column(primary_key=True)
    # TODO: delivery_id (str) - unique, not null. This is what makes webhooks idempotent.
    # TODO: repo (str), issue_number (int), installation_id (BigInteger)
    # TODO: status (str) - default "received"
    # TODO: input (JSONB) - the issue payload the run was started with
    # TODO: category (str, nullable), confidence (float, nullable)
    # TODO: model (str, nullable)
    # TODO: input_tokens, output_tokens (int, nullable)
    # TODO: cost_usd (Numeric, nullable) - Decimal, not float, for money
    # TODO: latency_ms (int, nullable)
    # TODO: error (str, nullable)
    # TODO: created_at (DateTime with timezone) - filled by the database (server_default=func.now())
    # TODO: finished_at (DateTime with timezone, nullable)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    # TODO: run_id (int) - ForeignKey("runs.id"), not null, indexed
    # TODO: tool (str)
    # TODO: input (JSONB), output (JSONB, nullable - a failed call may have no output)
    # TODO: success (bool)
    # TODO: latency_ms (int)
    # TODO: created_at (DateTime with timezone) - filled by the database
