"""OSRS Analytics Engine.

This module provides comprehensive analytics calculations for OSRS hiscore data.
Transforms raw snapshot data into meaningful insights about progress, rates, and trends.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
import sqlite3
from pathlib import Path

from core.constants import SKILLS, ACTIVITY_LOOKUP

logger = logging.getLogger(__name__)


def _parse_datetime(dt):
    """Parse datetime from various formats."""
    if isinstance(dt, str):
        return datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt


@dataclass
class XPRate:
    """XP rate calculation result."""
    skill_name: str
    xp_gained: int
    time_period_hours: float
    xp_per_hour: float
    xp_per_day: float
    start_xp: int
    end_xp: int
    start_level: int
    end_level: int


@dataclass
class SkillProgression:
    """Skill progression over time."""
    skill_name: str
    snapshots: List[Dict]
    xp_gained: int
    levels_gained: int
    time_span_days: int
    avg_xp_per_day: float
    avg_xp_per_hour: float


@dataclass
class Milestone:
    """Achievement milestone."""
    skill_name: str
    milestone_type: str  # level, xp_rank, etc.
    milestone_value: int
    achieved_at: datetime
    snapshot_id: str
    time_to_achieve: Optional[timedelta] = None


@dataclass
class ProgressDelta:
    """Progress difference between two snapshots."""
    account_name: str
    time_period_hours: float
    skills_gained: Dict[str, XPRate]
    total_xp_gained: int
    total_levels_gained: int
    activities_progress: Dict[str, Dict]


@dataclass
class ActivityTrend:
    """Activity trend analysis."""
    activity_name: str
    score_changes: List[Tuple[datetime, int]]
    total_score_gained: int
    rank_changes: List[Tuple[datetime, int]]
    best_rank: int
    current_rank: int
    trend_direction: str  # improving, declining, stable


class AnalyticsEngine:
    """Main analytics calculator for OSRS hiscore data."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize analytics engine.

        Args:
            db_path: Path to the analytics database. Defaults to data/analytics.db
        """
        self.db_path = db_path or Path("data/analytics.db")

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get a database connection for analytics calculations."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
            timeout=30.0
        )

        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row

        return conn

    def _get_account_snapshots(self, account_name: str, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict]:
        """Get snapshots for an account within a date range."""
        with self._get_db_connection() as conn:
            # Get account ID
            account = conn.execute(
                "SELECT id FROM accounts WHERE name = ?",
                (account_name,)
            ).fetchone()

            if not account:
                raise ValueError(f"Account '{account_name}' not found")

            account_id = account["id"]

            # Build query
            query = """
                SELECT s.*,
                       GROUP_CONCAT(
                           CASE WHEN sk.name IS NOT NULL THEN
                               sk.name || ':' || sk.level || ':' || sk.xp || ':' || sk.rank
                           END
                       ) as skills_data,
                       GROUP_CONCAT(
                           CASE WHEN ac.name IS NOT NULL THEN
                               ac.name || ':' || ac.score || ':' || ac.rank
                           END
                       ) as activities_data
                FROM snapshots s
                LEFT JOIN skills sk ON s.id = sk.snapshot_id
                LEFT JOIN activities ac ON s.id = ac.snapshot_id
                WHERE s.account_id = ?
            """
            params = [account_id]

            if start_date:
                query += " AND s.fetched_at >= ?"
                params.append(start_date)

            if end_date:
                query += " AND s.fetched_at <= ?"
                params.append(end_date)

            query += " GROUP BY s.id ORDER BY s.fetched_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            snapshots_data = conn.execute(query, params).fetchall()

            # Parse the grouped data into structured format
            snapshots = []
            for row in snapshots_data:
                snapshot = dict(row)

                # Parse skills data
                skills = {}
                if snapshot["skills_data"]:
                    for skill_data in snapshot["skills_data"].split(","):
                        if skill_data:
                            name, level, xp, rank = skill_data.split(":")
                            skills[name] = {
                                "level": int(level),
                                "xp": int(xp),
                                "rank": int(rank)
                            }

                # Parse activities data
                activities = {}
                if snapshot["activities_data"]:
                    for activity_data in snapshot["activities_data"].split(","):
                        if activity_data:
                            # Handle activity names that may contain colons
                            parts = activity_data.split(":")
                            if len(parts) >= 3:
                                name = ":".join(parts[:-2])  # Everything except last 2 parts
                                score = parts[-2]  # Second to last part
                                rank = parts[-1]  # Last part
                                activities[name] = {
                                    "score": int(score),
                                    "rank": int(rank)
                                }

                snapshot["skills"] = skills
                snapshot["activities"] = activities
                snapshots.append(snapshot)

            return snapshots

    def calculate_xp_rates(self, account_name: str, skill_name: Optional[str] = None,
                          start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[XPRate]:
        """Calculate XP rates for an account between two dates.

        Args:
            account_name: Name of the account to analyze
            skill_name: Specific skill to analyze (optional, defaults to all skills)
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            List of XPRate objects for each skill
        """
        snapshots = self._get_account_snapshots(account_name, start_date, end_date)

        if len(snapshots) < 2:
            logger.warning(f"Need at least 2 snapshots for XP rate calculation, got {len(snapshots)}")
            return []

        # Use the two most recent snapshots for rate calculation
        recent_snapshot = snapshots[0]
        previous_snapshot = snapshots[1]

        # Calculate time difference
        time_diff = _parse_datetime(recent_snapshot["fetched_at"]) - _parse_datetime(previous_snapshot["fetched_at"])
        time_period_hours = time_diff.total_seconds() / 3600

        skills_to_analyze = [skill_name] if skill_name else list(SKILLS)
        # Normalize skill names to match database capitalization
        skill_name_map = {skill.lower(): skill for skill in recent_snapshot["skills"].keys()}
        xp_rates = []

        for skill in skills_to_analyze:
            # Map lowercase skill name to database capitalization
            db_skill_name = skill_name_map.get(skill.lower(), skill)

            if db_skill_name not in recent_snapshot["skills"] or db_skill_name not in previous_snapshot["skills"]:
                continue

            recent_data = recent_snapshot["skills"][db_skill_name]
            previous_data = previous_snapshot["skills"][db_skill_name]

            xp_gained = recent_data["xp"] - previous_data["xp"]
            levels_gained = recent_data["level"] - previous_data["level"]

            if xp_gained <= 0:
                continue  # Skip skills with no progress

            xp_rate = XPRate(
                skill_name=skill,
                xp_gained=xp_gained,
                time_period_hours=time_period_hours,
                xp_per_hour=xp_gained / time_period_hours if time_period_hours > 0 else 0,
                xp_per_day=(xp_gained / time_period_hours * 24) if time_period_hours > 0 else 0,
                start_xp=previous_data["xp"],
                end_xp=recent_data["xp"],
                start_level=previous_data["level"],
                end_level=recent_data["level"]
            )

            xp_rates.append(xp_rate)

        return xp_rates

    def calculate_progress_deltas(self, account_name: str, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Optional[ProgressDelta]:
        """Calculate comprehensive progress deltas between snapshots.

        Args:
            account_name: Name of the account to analyze
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            ProgressDelta object with detailed progress information
        """
        snapshots = self._get_account_snapshots(account_name, start_date, end_date)

        if len(snapshots) < 2:
            logger.warning(f"Need at least 2 snapshots for progress delta calculation, got {len(snapshots)}")
            return None

        recent_snapshot = snapshots[0]
        previous_snapshot = snapshots[1]

        # Calculate time difference
        time_diff = _parse_datetime(recent_snapshot["fetched_at"]) - _parse_datetime(previous_snapshot["fetched_at"])
        time_period_hours = time_diff.total_seconds() / 3600

        # Calculate XP rates for all skills
        xp_rates = self.calculate_xp_rates(account_name, start_date=start_date, end_date=end_date)
        skills_gained = {rate.skill_name: rate for rate in xp_rates}

        # Calculate total progress
        total_xp_gained = sum(rate.xp_gained for rate in xp_rates)
        total_levels_gained = sum(rate.end_level - rate.start_level for rate in xp_rates)

        # Calculate activity progress
        activities_progress = {}
        for activity_name in ACTIVITY_LOOKUP:
            if (activity_name in recent_snapshot["activities"] and
                activity_name in previous_snapshot["activities"]):

                recent_score = recent_snapshot["activities"][activity_name]["score"]
                previous_score = previous_snapshot["activities"][activity_name]["score"]
                score_diff = recent_score - previous_score

                if score_diff != 0:
                    activities_progress[activity_name] = {
                        "score_gained": score_diff,
                        "start_score": previous_score,
                        "end_score": recent_score,
                        "start_rank": previous_snapshot["activities"][activity_name]["rank"],
                        "end_rank": recent_snapshot["activities"][activity_name]["rank"]
                    }

        return ProgressDelta(
            account_name=account_name,
            time_period_hours=time_period_hours,
            skills_gained=skills_gained,
            total_xp_gained=total_xp_gained,
            total_levels_gained=total_levels_gained,
            activities_progress=activities_progress
        )

    def get_skill_progression(self, account_name: str, skill_name: str, days: int = 30) -> Optional[SkillProgression]:
        """Get detailed progression data for a specific skill.

        Args:
            account_name: Name of the account to analyze
            skill_name: Name of the skill to analyze
            days: Number of days to look back

        Returns:
            SkillProgression object with detailed progression data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        snapshots = self._get_account_snapshots(account_name, start_date, end_date)

        if len(snapshots) < 2:
            return None

        # Filter snapshots that have data for the requested skill
        skill_name_map = {skill.lower(): skill for skill in snapshots[0]["skills"].keys()}
        db_skill_name = skill_name_map.get(skill_name.lower(), skill_name)
        skill_snapshots = [s for s in snapshots if db_skill_name in s["skills"]]

        if len(skill_snapshots) < 2:
            return None

        # Calculate progression metrics
        earliest_snapshot = skill_snapshots[-1]
        latest_snapshot = skill_snapshots[0]

        xp_gained = latest_snapshot["skills"][db_skill_name]["xp"] - earliest_snapshot["skills"][db_skill_name]["xp"]
        levels_gained = latest_snapshot["skills"][db_skill_name]["level"] - earliest_snapshot["skills"][db_skill_name]["level"]
        time_span_days = (_parse_datetime(latest_snapshot["fetched_at"]) - _parse_datetime(earliest_snapshot["fetched_at"])).days
        time_span_hours = (_parse_datetime(latest_snapshot["fetched_at"]) - _parse_datetime(earliest_snapshot["fetched_at"])).total_seconds() / 3600

        return SkillProgression(
            skill_name=skill_name,
            snapshots=skill_snapshots,
            xp_gained=xp_gained,
            levels_gained=levels_gained,
            time_span_days=time_span_days,
            avg_xp_per_day=xp_gained / time_span_days if time_span_days > 0 else 0,
            avg_xp_per_hour=xp_gained / time_span_hours if time_span_hours > 0 else 0
        )

    def calculate_milestones(self, account_name: str, skill_milestones: Optional[List[int]] = None,
                           days: int = 30) -> List[Milestone]:
        """Calculate achievement milestones for an account.

        Args:
            account_name: Name of the account to analyze
            skill_milestones: List of milestone levels to track (optional)
            days: Number of days to look back

        Returns:
            List of Milestone objects
        """
        if skill_milestones is None:
            skill_milestones = [10, 25, 50, 75, 99]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        snapshots = self._get_account_snapshots(account_name, start_date, end_date, limit=100)
        milestones = []

        # Track when each skill achieves milestone levels
        skill_levels = {}  # skill_name -> last seen level

        # Process snapshots in chronological order (oldest to newest)
        for snapshot in reversed(snapshots):
            for skill_name, skill_data in snapshot["skills"].items():
                current_level = skill_data["level"]
                last_level = skill_levels.get(skill_name, 0)

                # Check if this skill achieved any new milestones
                for milestone in skill_milestones:
                    if (last_level < milestone <= current_level and
                        milestone not in [m.milestone_value for m in milestones
                                        if m.skill_name == skill_name and m.milestone_type == "level"]):

                        milestone_obj = Milestone(
                            skill_name=skill_name,
                            milestone_type="level",
                            milestone_value=milestone,
                            achieved_at=_parse_datetime(snapshot["fetched_at"]),
                            snapshot_id=snapshot["snapshot_id"]
                        )
                        milestones.append(milestone_obj)

                skill_levels[skill_name] = current_level

        return sorted(milestones, key=lambda m: m.achieved_at, reverse=True)

    def get_activity_trends(self, account_name: str, days: int = 30) -> List[ActivityTrend]:
        """Analyze activity trends for an account.

        Args:
            account_name: Name of the account to analyze
            days: Number of days to look back

        Returns:
            List of ActivityTrend objects
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        snapshots = self._get_account_snapshots(account_name, start_date, end_date, limit=50)

        if len(snapshots) < 2:
            return []

        trends = []

        # Analyze each activity
        for activity_name in ACTIVITY_LOOKUP:
            activity_data = []

            for snapshot in reversed(snapshots):  # Chronological order
                if activity_name in snapshot["activities"]:
                    activity_data.append((
                        snapshot["fetched_at"],
                        snapshot["activities"][activity_name]["score"],
                        snapshot["activities"][activity_name]["rank"]
                    ))

            if len(activity_data) < 2:
                continue

            # Calculate trend metrics
            start_score = activity_data[0][1]
            end_score = activity_data[-1][1]
            score_gained = end_score - start_score

            ranks = [data[2] for data in activity_data]
            best_rank = min(ranks) if ranks else 0
            current_rank = ranks[-1] if ranks else 0

            # Determine trend direction
            if len(activity_data) >= 3:
                recent_scores = [data[1] for data in activity_data[-3:]]
                if all(recent_scores[i] <= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                    trend_direction = "improving"
                elif all(recent_scores[i] >= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"

            trend = ActivityTrend(
                activity_name=activity_name,
                score_changes=activity_data,
                total_score_gained=score_gained,
                rank_changes=[(data[0], data[2]) for data in activity_data],
                best_rank=best_rank,
                current_rank=current_rank,
                trend_direction=trend_direction
            )

            trends.append(trend)

        return trends