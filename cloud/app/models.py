"""SQLAlchemy ORM models for cloud backend."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TestStatus(enum.StrEnum):
    """Test execution status."""

    GENERATING = "generating"
    REVIEW = "review"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class UserTier(enum.StrEnum):
    """User subscription tier."""

    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class Test(Base):
    """A test run record."""

    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus), default=TestStatus.QUEUED, nullable=False
    )
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps_total: Mapped[int] = mapped_column(Integer, default=0)
    steps_completed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class User(Base):
    """User profile (synced from Supabase Auth)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # Supabase user UUID
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    tier: Mapped[UserTier] = mapped_column(
        Enum(UserTier), default=UserTier.FREE, nullable=False
    )
    lemon_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lemon_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class ScanStatus(enum.StrEnum):
    """Smart Scan status."""

    SCANNING = "scanning"
    COMPLETED = "completed"
    PLANNING = "planning"
    PLANNED = "planned"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Scan(Base):
    """A site scan record for Smart Scan."""

    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.SCANNING, nullable=False
    )
    max_pages: Mapped[int] = mapped_column(Integer, default=5)
    max_depth: Mapped[int] = mapped_column(Integer, default=2)
    # JSON text columns (SQLite compatible)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    broken_links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    logs_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of scan logs
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ScenarioCache(Base):
    """Cached AI-generated scenarios keyed by (user, url, fingerprint).

    Avoids redundant AI calls when site structure hasn't changed.
    """

    __tablename__ = "scenario_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    scan_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_tests_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    steps_total: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class ExecutionPath(Base):
    """Stored successful execution path for fast-mode replay.

    When a test passes, the exact selectors, values, and asserts are saved.
    On retest of the same URL, these are replayed without AI (Fast Mode).
    If a selector breaks, self-healing replaces it with AI-suggested alternative.
    """

    __tablename__ = "execution_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(512), nullable=False)
    scenario_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    steps_total: Mapped[int] = mapped_column(Integer, default=0)
    healed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_passed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class Document(Base):
    """User-uploaded reference document (stored as base64)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_base64: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class UserAIConfig(Base):
    """User's own AI API key configuration (BYOK)."""

    __tablename__ = "user_ai_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )  # openai | anthropic | deepseek | ollama
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted
    model: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class FixGuideStatus(enum.StrEnum):
    """Fix guide lifecycle status."""

    PENDING = "pending"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    PR_CREATED = "pr_created"
    FAILED = "failed"


class GitHubConnection(Base):
    """User's GitHub repository connection (PAT encrypted)."""

    __tablename__ = "github_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    pat_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet
    owner: Mapped[str] = mapped_column(String(256), nullable=False)
    repo: Mapped[str] = mapped_column(String(256), nullable=False)
    default_branch: Mapped[str] = mapped_column(
        String(128), default="main", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class FixGuide(Base):
    """AI-generated fix guide for a failed test scenario."""

    __tablename__ = "fix_guides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[FixGuideStatus] = mapped_column(
        Enum(FixGuideStatus), default=FixGuideStatus.PENDING, nullable=False
    )
    diff_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class ApiKey(Base):
    """API key for CI/CD authentication (X-API-Key header)."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # awt_xxxx (UI display)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
