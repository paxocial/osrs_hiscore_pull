"""SQLAlchemy models for OSRS Hiscore Analytics database."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    create_engine, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.types import TypeDecorator

Base = declarative_base()


class JSONType(TypeDecorator):
    """Custom JSON type for SQLite."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return '{}'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        return json.loads(value)


# Database setup
def get_engine(db_path: str = "data/analytics.db"):
    """Create database engine."""
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={
            "check_same_thread": False,
            "detect_types": True,  # Enable datetime detection
        },
        echo=False,  # Set to True for SQL logging
    )


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_db_session(db_path: str = "data/analytics.db") -> Session:
    """Get database session."""
    engine = get_engine(db_path)
    SessionLocal.configure(bind=engine)
    return SessionLocal()


class Account(Base):
    """Represents an OSRS account."""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    default_mode = Column(String(50), default="main")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True, nullable=False)
    metadata_column = Column("metadata", JSONType, default="{}")

    # Relationships
    snapshots = relationship("Snapshot", back_populates="account", cascade="all, delete-orphan")
    mode_cache = relationship("ModeCache", back_populates="account", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name='{self.name}', active={self.active})>"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        return self.metadata_column

    @metadata.setter
    def metadata(self, value: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.metadata_column = value

    def get_latest_snapshot(self) -> Optional["Snapshot"]:
        """Get the most recent snapshot for this account."""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.fetched_at)


class Snapshot(Base):
    """Represents a snapshot of an account's hiscores."""
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    snapshot_id = Column(String(100), unique=True, nullable=False, index=True)
    requested_mode = Column(String(50), nullable=False)
    resolved_mode = Column(String(50), nullable=False, index=True)
    fetched_at = Column(DateTime, nullable=False, index=True)
    endpoint = Column(String(500))
    latency_ms = Column(Float)
    agent_version = Column(String(50))
    total_level = Column(Integer, index=True)
    total_xp = Column(Integer, index=True)
    metadata_column = Column("metadata", JSONType, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="snapshots")
    skills = relationship("Skill", back_populates="snapshot", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="snapshot", cascade="all, delete-orphan")
    deltas_as_current = relationship(
        "SnapshotDelta", foreign_keys="SnapshotDelta.current_snapshot_id",
        back_populates="current_snapshot", cascade="all, delete-orphan"
    )
    deltas_as_previous = relationship(
        "SnapshotDelta", foreign_keys="SnapshotDelta.previous_snapshot_id",
        back_populates="previous_snapshot"
    )

    def __repr__(self) -> str:
        return f"<Snapshot(id={self.id}, account='{self.account.name if self.account else 'Unknown'}', fetched_at='{self.fetched_at}')>"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        return self.metadata_column

    @metadata.setter
    def metadata(self, value: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.metadata_column = value

    def get_skill(self, skill_name: str) -> Optional["Skill"]:
        """Get a specific skill by name."""
        for skill in self.skills:
            if skill.name == skill_name:
                return skill
        return None

    def get_activity(self, activity_name: str) -> Optional["Activity"]:
        """Get a specific activity by name."""
        for activity in self.activities:
            if activity.name == activity_name:
                return activity
        return None


class Skill(Base):
    """Represents a skill in a snapshot."""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False, index=True)
    skill_id = Column(Integer, nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    level = Column(Integer, index=True)
    xp = Column(Integer, index=True)
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    snapshot = relationship("Snapshot", back_populates="skills")

    def __repr__(self) -> str:
        return f"<Skill(name='{self.name}', level={self.level}, xp={self.xp})>"


class Activity(Base):
    """Represents an activity/minigame/boss in a snapshot."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False, index=True)
    activity_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    score = Column(Integer, index=True)
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    snapshot = relationship("Snapshot", back_populates="activities")

    def __repr__(self) -> str:
        return f"<Activity(name='{self.name}', score={self.score})>"


class SnapshotDelta(Base):
    """Represents deltas between two snapshots."""
    __tablename__ = "snapshots_deltas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    current_snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False, index=True)
    previous_snapshot_id = Column(Integer, ForeignKey("snapshots.id"), index=True)
    total_xp_delta = Column(Integer, default=0, index=True)
    skill_deltas_json = Column(JSONType, default="[]")
    activity_deltas_json = Column(JSONType, default="[]")
    time_diff_hours = Column(Float, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    current_snapshot = relationship(
        "Snapshot", foreign_keys=[current_snapshot_id],
        back_populates="deltas_as_current"
    )
    previous_snapshot = relationship(
        "Snapshot", foreign_keys=[previous_snapshot_id],
        back_populates="deltas_as_previous"
    )

    def __repr__(self) -> str:
        return f"<SnapshotDelta(total_xp_delta={self.total_xp_delta}, time_diff_hours={self.time_diff_hours})>"

    @property
    def skill_deltas(self) -> List[Dict[str, Any]]:
        """Get skill deltas as list of dictionaries."""
        return self.skill_deltas_json

    @skill_deltas.setter
    def skill_deltas(self, value: List[Dict[str, Any]]) -> None:
        """Set skill deltas from list of dictionaries."""
        self.skill_deltas_json = value

    @property
    def activity_deltas(self) -> List[Dict[str, Any]]:
        """Get activity deltas as list of dictionaries."""
        return self.activity_deltas_json

    @activity_deltas.setter
    def activity_deltas(self, value: List[Dict[str, Any]]) -> None:
        """Set activity deltas from list of dictionaries."""
        self.activity_deltas_json = value


class ModeCache(Base):
    """Represents cached mode information for an account."""
    __tablename__ = "mode_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, unique=True, index=True)
    mode = Column(String(50), nullable=False)
    detected_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    endpoint_used = Column(String(500))

    # Relationships
    account = relationship("Account", back_populates="mode_cache")

    def __repr__(self) -> str:
        return f"<ModeCache(account='{self.account.name if self.account else 'Unknown'}', mode='{self.mode}')>"


class SchemaVersion(Base):
    """Represents database schema version."""
    __tablename__ = "schema_version"

    id = Column(Integer, primary_key=True)
    version = Column(String(20), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    description = Column(String(500))

    def __repr__(self) -> str:
        return f"<SchemaVersion(version='{self.version}', applied_at='{self.applied_at}')>"


# Database event listeners for automatic timestamp updates
@event.listens_for(Account, "before_update")
def receive_before_update(mapper, connection, target):
    """Update updated_at timestamp for Account."""
    target.updated_at = datetime.utcnow()


@event.listens_for(ModeCache, "before_update")
def receive_mode_cache_before_update(mapper, connection, target):
    """Update updated_at timestamp for ModeCache."""
    target.updated_at = datetime.utcnow()


# Utility functions for common operations
def create_account(db: Session, name: str, display_name: Optional[str] = None,
                  default_mode: str = "main", metadata: Optional[Dict[str, Any]] = None) -> Account:
    """Create a new account."""
    account = Account(
        name=name,
        display_name=display_name,
        default_mode=default_mode,
        metadata=metadata or {}
    )
    db.add(account)
    db.commit()
    return account


def get_or_create_account(db: Session, name: str, **kwargs) -> Account:
    """Get existing account or create new one."""
    account = db.query(Account).filter(Account.name == name).first()
    if account:
        return account

    return create_account(db, name, **kwargs)


def create_snapshot(db: Session, account: Account, snapshot_data: Dict[str, Any]) -> Snapshot:
    """Create a new snapshot from data."""
    snapshot = Snapshot(
        account=account,
        snapshot_id=snapshot_data["metadata"]["snapshot_id"],
        requested_mode=snapshot_data["metadata"]["requested_mode"],
        resolved_mode=snapshot_data["metadata"]["resolved_mode"],
        fetched_at=datetime.fromisoformat(snapshot_data["metadata"]["fetched_at"].replace("Z", "+00:00")),
        endpoint=snapshot_data["metadata"].get("endpoint"),
        latency_ms=snapshot_data["metadata"].get("latency_ms"),
        agent_version=snapshot_data["metadata"].get("agent_version"),
        total_level=snapshot_data.get("total_level"),
        total_xp=snapshot_data.get("total_xp"),
        metadata=snapshot_data.get("metadata", {})
    )

    # Add skills
    for skill_data in snapshot_data.get("data", {}).get("skills", []):
        skill = Skill(
            snapshot=snapshot,
            skill_id=skill_data["id"],
            name=skill_data["name"],
            level=skill_data.get("level"),
            xp=skill_data.get("xp"),
            rank=skill_data.get("rank")
        )
        db.add(skill)

    # Add activities
    for activity_data in snapshot_data.get("data", {}).get("activities", []):
        activity = Activity(
            snapshot=snapshot,
            activity_id=activity_data["id"],
            name=activity_data["name"],
            score=activity_data.get("score"),
            rank=activity_data.get("rank")
        )
        db.add(activity)

    db.add(snapshot)
    db.commit()
    return snapshot


def get_latest_snapshot_for_account(db: Session, account_name: str) -> Optional[Snapshot]:
    """Get the latest snapshot for an account."""
    return (db.query(Snapshot)
            .join(Account)
            .filter(Account.name == account_name)
            .order_by(Snapshot.fetched_at.desc())
            .first())