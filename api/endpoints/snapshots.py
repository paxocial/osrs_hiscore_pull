"""Snapshot management endpoints for OSRS Analytics API."""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from api.dependencies import (
    get_database_connection,
    parse_snapshot_query_params,
    validate_account_exists,
    get_snapshot_or_404
)
from api.schemas import (
    Snapshot,
    SnapshotCreate,
    SnapshotListResponse,
    SnapshotDetailResponse,
    SnapshotDelta,
    ErrorResponse
)
from api.exceptions import DataNotFoundException, ValidationException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=SnapshotListResponse, summary="List snapshots")
async def list_snapshots(
    params: SnapshotQueryParams = Depends(parse_snapshot_query_params),
    conn = Depends(get_database_connection)
):
    """
    Retrieve a paginated list of snapshots with optional filtering.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page, 1-100 (default: 10)
    - **account_name**: Filter by specific account (optional)
    - **mode**: Filter by game mode (optional)
    - **start_date**: Filter by start date (ISO format, optional)
    - **end_date**: Filter by end date (ISO format, optional)
    - **include_skills**: Include skill data (default: false)
    - **include_activities**: Include activity data (default: false)

    Returns snapshots with pagination metadata.
    """
    try:
        with conn:
            # Build base query with joins
            query = """
                SELECT
                    s.*,
                    a.name as account_name
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
            """
            count_query = """
                SELECT COUNT(*) as total
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
            """
            conditions = []
            params_list = []

            # Add filters
            if params.account_name:
                conditions.append("a.name = ?")
                params_list.append(params.account_name)

            if params.mode:
                conditions.append("s.resolved_mode = ?")
                params_list.append(params.mode)

            if params.start_date:
                conditions.append("s.fetched_at >= ?")
                params_list.append(params.start_date.isoformat())

            if params.end_date:
                conditions.append("s.fetched_at <= ?")
                params_list.append(params.end_date.isoformat())

            # Combine conditions
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
                query += where_clause
                count_query += where_clause

            # Add pagination
            offset = (params.page - 1) * params.page_size
            query += " ORDER BY s.fetched_at DESC LIMIT ? OFFSET ?"
            params_list.extend([params.page_size, offset])

            # Execute queries
            snapshots_data = conn.execute(query, params_list).fetchall()
            total_count = conn.execute(count_query, params_list[:len(params_list)-2]).fetchone()["total"]

            # Convert to Snapshot models
            snapshots = []
            for snapshot_row in snapshots_data:
                snapshot_dict = dict(snapshot_row)

                # Include skills if requested
                if params.include_skills:
                    skills_query = "SELECT * FROM skills WHERE snapshot_id = ?"
                    skills_data = conn.execute(skills_query, (snapshot_row["id"],)).fetchall()
                    snapshot_dict["skills"] = [dict(skill) for skill in skills_data]

                # Include activities if requested
                if params.include_activities:
                    activities_query = "SELECT * FROM activities WHERE snapshot_id = ?"
                    activities_data = conn.execute(activities_query, (snapshot_row["id"],)).fetchall()
                    snapshot_dict["activities"] = [dict(activity) for activity in activities_data]

                snapshots.append(Snapshot.model_validate(snapshot_dict))

            return SnapshotListResponse(
                snapshots=snapshots,
                total=total_count,
                page=params.page,
                page_size=params.page_size,
                account_name=params.account_name
            )

    except Exception as e:
        logger.error(f"Error listing snapshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve snapshots"
        )


@router.get("/latest", response_model=List[Snapshot], summary="Get latest snapshots")
async def get_latest_snapshots(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    account_name: Optional[str] = Query(None, description="Filter by account name"),
    mode: Optional[str] = Query(None, description="Filter by game mode"),
    conn = Depends(get_database_connection)
):
    """
    Retrieve the most recent snapshots across all accounts or filtered by criteria.

    - **limit**: Maximum number of results (default: 10, max: 50)
    - **account_name**: Filter by specific account (optional)
    - **mode**: Filter by game mode (optional)

    Returns snapshots ordered by fetch date (newest first).
    """
    try:
        with conn:
            # Build query
            query = """
                SELECT
                    s.*,
                    a.name as account_name
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
            """
            conditions = []
            params_list = []

            # Add filters
            if account_name:
                conditions.append("a.name = ?")
                params_list.append(account_name)

            if mode:
                conditions.append("s.resolved_mode = ?")
                params_list.append(mode)

            # Combine conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add limit and ordering
            query += " ORDER BY s.fetched_at DESC LIMIT ?"
            params_list.append(limit)

            snapshots_data = conn.execute(query, params_list).fetchall()

            snapshots = []
            for snapshot_row in snapshots_data:
                snapshots.append(Snapshot.model_validate(dict(snapshot_row)))

            return snapshots

    except Exception as e:
        logger.error(f"Error getting latest snapshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest snapshots"
        )


@router.get("/{snapshot_id}", response_model=SnapshotDetailResponse, summary="Get snapshot details")
async def get_snapshot(
    snapshot_data: dict = Depends(get_snapshot_or_404),
    include_deltas: bool = Query(True, description="Include comparison with previous snapshot"),
    conn = Depends(get_database_connection)
):
    """
    Retrieve detailed information for a specific snapshot.

    - **snapshot_id**: The unique snapshot identifier
    - **include_deltas**: Whether to include comparison with previous snapshot

    Returns complete snapshot data with skills, activities, and optional deltas.
    """
    try:
        with conn:
            # Get account information
            account_query = """
                SELECT * FROM accounts WHERE id = ?
            """
            account = conn.execute(account_query, (snapshot_data["account_id"],)).fetchone()

            # Get skills
            skills_query = "SELECT * FROM skills WHERE snapshot_id = ? ORDER BY skill_id"
            skills_data = conn.execute(skills_query, (snapshot_data["id"],)).fetchall()

            # Get activities
            activities_query = "SELECT * FROM activities WHERE snapshot_id = ? ORDER BY activity_id"
            activities_data = conn.execute(activities_query, (snapshot_data["id"],)).fetchall()

            # Build complete snapshot
            snapshot_dict = snapshot_data.copy()
            snapshot_dict["skills"] = [dict(skill) for skill in skills_data]
            snapshot_dict["activities"] = [dict(activity) for activity in activities_data]

            snapshot = Snapshot.model_validate(snapshot_dict)

            # Get deltas if requested
            deltas = None
            if include_deltas:
                deltas_query = """
                    SELECT * FROM snapshots_deltas
                    WHERE current_snapshot_id = ?
                """
                deltas_data = conn.execute(deltas_query, (snapshot_data["id"],)).fetchone()

                if deltas_data:
                    deltas = SnapshotDelta.model_validate(dict(deltas_data))

            return SnapshotDetailResponse(
                snapshot=snapshot,
                deltas=deltas,
                account=account
            )

    except Exception as e:
        logger.error(f"Error getting snapshot {snapshot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve snapshot"
        )


@router.get("/{snapshot_id}/deltas", response_model=SnapshotDelta, summary="Get snapshot deltas")
async def get_snapshot_deltas(
    snapshot_data: dict = Depends(get_snapshot_or_404),
    conn = Depends(get_database_connection)
):
    """
    Retrieve the delta comparison for a snapshot against its previous snapshot.

    Returns the calculated differences in XP, levels, and other metrics between
    this snapshot and the immediately preceding one for the same account.
    """
    try:
        with conn:
            deltas_query = """
                SELECT * FROM snapshots_deltas
                WHERE current_snapshot_id = ?
            """
            deltas_data = conn.execute(deltas_query, (snapshot_data["id"],)).fetchone()

            if not deltas_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No deltas found for snapshot '{snapshot_data['snapshot_id']}'"
                )

            return SnapshotDelta.model_validate(dict(deltas_data))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deltas for snapshot {snapshot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve snapshot deltas"
        )


@router.get("/compare/{snapshot_id1}/{snapshot_id2}", summary="Compare two snapshots")
async def compare_snapshots(
    snapshot_id1: str,
    snapshot_id2: str,
    conn = Depends(get_database_connection)
):
    """
    Compare two snapshots side-by-side.

    Returns detailed comparison of skills, activities, and overall progress
    between the two specified snapshots.
    """
    try:
        # Get both snapshots using direct database queries
        snapshot1_query = """
            SELECT s.*, a.name as account_name
            FROM snapshots s
            JOIN accounts a ON s.account_id = a.id
            WHERE s.snapshot_id = ?
        """
        snapshot1 = conn.execute(snapshot1_query, (snapshot_id1,)).fetchone()

        snapshot2_query = """
            SELECT s.*, a.name as account_name
            FROM snapshots s
            JOIN accounts a ON s.account_id = a.id
            WHERE s.snapshot_id = ?
        """
        snapshot2 = conn.execute(snapshot2_query, (snapshot_id2,)).fetchone()

        if not snapshot1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id1}' not found"
            )

        if not snapshot2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id2}' not found"
            )

        # Ensure snapshots are from the same account
        if snapshot1["account_id"] != snapshot2["account_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Snapshots must be from the same account for comparison"
            )

        with conn:
            # Get account info
            account = conn.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (snapshot1["account_id"],)
            ).fetchone()

            # Calculate time difference
            from datetime import datetime
            time_diff = None
            if snapshot1.get("fetched_at") and snapshot2.get("fetched_at"):
                time1 = datetime.fromisoformat(snapshot1["fetched_at"])
                time2 = datetime.fromisoformat(snapshot2["fetched_at"])
                time_diff = abs((time2 - time1).total_seconds() / 3600)  # hours

            # Calculate differences
            total_xp_diff = (snapshot2.get("total_xp", 0) - snapshot1.get("total_xp", 0))
            total_level_diff = (snapshot2.get("total_level", 0) - snapshot1.get("total_level", 0))

            # Build skill comparison
            skills1 = {skill["name"]: skill for skill in snapshot1.get("skills", [])}
            skills2 = {skill["name"]: skill for skill in snapshot2.get("skills", [])}

            skill_comparisons = []
            for skill_name in set(skills1.keys()) | set(skills2.keys()):
                skill1 = skills1.get(skill_name, {})
                skill2 = skills2.get(skill_name, {})

                skill_comparisons.append({
                    "name": skill_name,
                    "level1": skill1.get("level"),
                    "level2": skill2.get("level"),
                    "level_diff": (skill2.get("level", 0) - skill1.get("level", 0)),
                    "xp1": skill1.get("xp"),
                    "xp2": skill2.get("xp"),
                    "xp_diff": (skill2.get("xp", 0) - skill1.get("xp", 0)),
                    "rank1": skill1.get("rank"),
                    "rank2": skill2.get("rank"),
                    "rank_diff": (skill2.get("rank", 0) - skill1.get("rank", 0))
                })

            # Build activity comparison
            activities1 = {activity["name"]: activity for activity in snapshot1.get("activities", [])}
            activities2 = {activity["name"]: activity for activity in snapshot2.get("activities", [])}

            activity_comparisons = []
            for activity_name in set(activities1.keys()) | set(activities2.keys()):
                activity1 = activities1.get(activity_name, {})
                activity2 = activities2.get(activity_name, {})

                activity_comparisons.append({
                    "name": activity_name,
                    "score1": activity1.get("score"),
                    "score2": activity2.get("score"),
                    "score_diff": (activity2.get("score", 0) - activity1.get("score", 0)),
                    "rank1": activity1.get("rank"),
                    "rank2": activity2.get("rank"),
                    "rank_diff": (activity2.get("rank", 0) - activity1.get("rank", 0))
                })

            return {
                "snapshot1": {
                    "id": snapshot1["snapshot_id"],
                    "fetched_at": snapshot1["fetched_at"],
                    "total_level": snapshot1.get("total_level"),
                    "total_xp": snapshot1.get("total_xp"),
                    "mode": snapshot1.get("resolved_mode")
                },
                "snapshot2": {
                    "id": snapshot2["snapshot_id"],
                    "fetched_at": snapshot2["fetched_at"],
                    "total_level": snapshot2.get("total_level"),
                    "total_xp": snapshot2.get("total_xp"),
                    "mode": snapshot2.get("resolved_mode")
                },
                "account": {
                    "name": account["name"],
                    "display_name": account.get("display_name")
                },
                "time_diff_hours": time_diff,
                "total_xp_diff": total_xp_diff,
                "total_level_diff": total_level_diff,
                "skill_comparisons": skill_comparisons,
                "activity_comparisons": activity_comparisons
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing snapshots {snapshot_id1} and {snapshot_id2}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare snapshots"
        )


@router.post("/", response_model=Snapshot, status_code=status.HTTP_201_CREATED, summary="Create snapshot")
async def create_snapshot(
    snapshot_data: SnapshotCreate,
    conn = Depends(get_database_connection)
):
    """
    Create a new snapshot for an account.

    This endpoint is primarily used by the SnapshotAgent to store new hiscore data.
    """
    try:
        # Get account ID
        account = conn.execute(
            "SELECT id FROM accounts WHERE name = ?",
            (snapshot_data.account_name,)
        ).fetchone()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{snapshot_data.account_name}' not found"
            )

        # Insert snapshot
        cursor = conn.execute(
            """
            INSERT INTO snapshots (
                snapshot_id, account_id, fetched_at, total_xp, total_level,
                endpoint, latency_ms, agent_version, requested_mode, resolved_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_data.snapshot_id,
                account["id"],
                snapshot_data.fetched_at,
                snapshot_data.total_xp,
                snapshot_data.total_level,
                snapshot_data.endpoint,
                snapshot_data.latency_ms,
                snapshot_data.agent_version,
                snapshot_data.requested_mode,
                snapshot_data.resolved_mode
            )
        )

        snapshot_id = cursor.lastrowid

        # Insert skills
        for skill in snapshot_data.skills:
            conn.execute(
                """
                INSERT INTO skills (
                    snapshot_id, skill_id, skill_name, level, xp, rank
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    skill.id,
                    skill.name,
                    skill.level,
                    skill.xp,
                    skill.rank
                )
            )

        # Insert activities
        for activity in snapshot_data.activities:
            conn.execute(
                """
                INSERT INTO activities (
                    snapshot_id, activity_id, activity_name, score, rank
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    activity.id,
                    activity.name,
                    activity.score,
                    activity.rank
                )
            )

        # Retrieve and return the created snapshot
        created_snapshot = conn.execute(
            "SELECT * FROM snapshots WHERE id = ?",
            (snapshot_id,)
        ).fetchone()

        if not created_snapshot:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Snapshot was stored but could not be retrieved"
            )

        # Get skills and activities for the response
        skills_data = conn.execute(
            "SELECT * FROM skills WHERE snapshot_id = ?",
            (snapshot_id,)
        ).fetchall()

        activities_data = conn.execute(
            "SELECT * FROM activities WHERE snapshot_id = ?",
            (snapshot_id,)
        ).fetchall()

        snapshot_dict = dict(created_snapshot)
        snapshot_dict["skills"] = [dict(skill) for skill in skills_data]
        snapshot_dict["activities"] = [dict(activity) for activity in activities_data]

        logger.info(f"Created snapshot: {snapshot_data.snapshot_id}")

        return Snapshot.model_validate(snapshot_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create snapshot"
        )


@router.delete("/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete snapshot")
async def delete_snapshot(
    snapshot_data: dict = Depends(get_snapshot_or_404),
    conn = Depends(get_database_connection)
):
    """
    Delete a specific snapshot and all associated data.

    **Warning**: This action is irreversible.
    """
    try:
        with conn:
            # Delete snapshot (cascades to skills, activities, deltas)
            conn.execute(
                "DELETE FROM snapshots WHERE id = ?",
                (snapshot_data["id"],)
            )

            logger.info(f"Deleted snapshot: {snapshot_data['snapshot_id']}")

            return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Error deleting snapshot {snapshot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete snapshot"
        )