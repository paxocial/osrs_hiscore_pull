"""Plugin API endpoints for RuneLite client telemetry ingestion.

This module provides 12 API endpoints for the Catherby RuneLite plugin to submit
gameplay telemetry, including XP snapshots, session events, collection log entries,
quest progress, and more.

All endpoints require authentication via the X-API-Key header with 'plugin' scope.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    require_plugin_key,
    get_database_connection,
    plugin_rate_limiter,
    batch_rate_limiter
)
from api.schemas.plugin import (
    SessionEvent,
    XpSnapshot,
    CollectionLogEntry,
    QuestStatus,
    DiaryProgress,
    CombatAchievementProgress,
    EquipmentState,
    LootDrop,
    ActivityUpdate,
    BankSnapshot,
    BatchPayload,
    StatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_account_id(rsn: str, conn: sqlite3.Connection) -> int:
    """Resolve RSN to account_id.

    Args:
        rsn: RuneScape display name
        conn: Database connection

    Returns:
        Account ID

    Raises:
        HTTPException: 404 if account not found
    """
    row = conn.execute(
        "SELECT id FROM accounts WHERE lower(name) = lower(?)",
        (rsn,)
    ).fetchone()

    if not row:
        logger.warning(f"Plugin API: Unknown RSN '{rsn}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {rsn}"
        )

    return row[0]


def _log_sync(
    conn: sqlite3.Connection,
    account_id: int,
    token_id: int,
    category: str,
    payload_summary: Dict[str, Any]
) -> None:
    """Log sync event to plugin_sync_log table.

    Args:
        conn: Database connection
        account_id: Account ID
        token_id: API token ID
        category: Payload category (e.g., 'xp', 'session')
        payload_summary: Summary of payload for logging
    """
    conn.execute(
        """
        INSERT INTO plugin_sync_log (
            account_id,
            token_id,
            category,
            payload_summary,
            synced_at
        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (account_id, token_id, category, json.dumps(payload_summary))
    )


@router.post("/session")
async def submit_session_event(
    payload: SessionEvent,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit a player session event (login, logout, world hop).

    Args:
        payload: Session event data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_sessions table
    conn.execute(
        """
        INSERT INTO plugin_sessions (
            account_id,
            session_id,
            event,
            world,
            duration_seconds,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            payload.session_id,
            payload.event.value,
            payload.world,
            payload.duration_seconds,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "session",
        {"event": payload.event.value, "session_id": payload.session_id}
    )

    conn.commit()
    logger.info(f"Session event stored: {payload.rsn} - {payload.event.value}")

    return {"status": "ok"}


@router.post("/xp")
async def submit_xp_snapshot(
    payload: XpSnapshot,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit an XP snapshot with all 23 skill values.

    Args:
        payload: XP snapshot data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_xp_snapshots table
    conn.execute(
        """
        INSERT INTO plugin_xp_snapshots (
            account_id,
            skills,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            json.dumps(payload.skills),
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    total_xp = sum(payload.skills.values())
    _log_sync(
        conn,
        account_id,
        token["id"],
        "xp",
        {"total_xp": total_xp, "skill_count": len(payload.skills)}
    )

    conn.commit()
    logger.info(f"XP snapshot stored: {payload.rsn} - {total_xp:,} total XP")

    return {"status": "ok"}


@router.post("/collection-log")
async def submit_collection_log_entry(
    payload: CollectionLogEntry,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit a collection log item obtained event.

    Args:
        payload: Collection log entry data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_collection_log table
    conn.execute(
        """
        INSERT INTO plugin_collection_log (
            account_id,
            item_id,
            item_name,
            quantity,
            source,
            obtained_at,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            payload.item_id,
            payload.item_name,
            payload.quantity,
            payload.source,
            payload.obtained_at,
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "collection_log",
        {"item_id": payload.item_id, "item_name": payload.item_name, "source": payload.source}
    )

    conn.commit()
    logger.info(f"Collection log entry stored: {payload.rsn} - {payload.item_name} from {payload.source}")

    return {"status": "ok"}


@router.post("/quests")
async def submit_quest_status(
    payload: QuestStatus,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit a quest progress update.

    Args:
        payload: Quest status data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_quests table
    conn.execute(
        """
        INSERT INTO plugin_quests (
            account_id,
            quest_name,
            state,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            payload.quest_name,
            payload.state.value,
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "quest",
        {"quest_name": payload.quest_name, "state": payload.state.value}
    )

    conn.commit()
    logger.info(f"Quest status stored: {payload.rsn} - {payload.quest_name} ({payload.state.value})")

    return {"status": "ok"}


@router.post("/diaries")
async def submit_diary_progress(
    payload: DiaryProgress,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit achievement diary progress update.

    Args:
        payload: Diary progress data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_diaries table
    conn.execute(
        """
        INSERT INTO plugin_diaries (
            account_id,
            region,
            easy,
            medium,
            hard,
            elite,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            payload.region,
            payload.easy,
            payload.medium,
            payload.hard,
            payload.elite,
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    completed_tiers = [
        tier for tier, done in [
            ("easy", payload.easy),
            ("medium", payload.medium),
            ("hard", payload.hard),
            ("elite", payload.elite)
        ] if done
    ]
    _log_sync(
        conn,
        account_id,
        token["id"],
        "diary",
        {"region": payload.region, "completed_tiers": completed_tiers}
    )

    conn.commit()
    logger.info(f"Diary progress stored: {payload.rsn} - {payload.region} ({len(completed_tiers)} tiers)")

    return {"status": "ok"}


@router.post("/combat-achievements")
async def submit_combat_achievement_progress(
    payload: CombatAchievementProgress,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit combat achievement progress update.

    Args:
        payload: Combat achievement progress data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_combat_achievements table
    conn.execute(
        """
        INSERT INTO plugin_combat_achievements (
            account_id,
            tier_progress,
            completed_tasks,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            json.dumps(payload.tier_progress),
            json.dumps(payload.completed_tasks),
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    total_completed = sum(payload.tier_progress.values())
    _log_sync(
        conn,
        account_id,
        token["id"],
        "combat_achievement",
        {"total_completed": total_completed, "task_count": len(payload.completed_tasks)}
    )

    conn.commit()
    logger.info(f"Combat achievement progress stored: {payload.rsn} - {total_completed} total")

    return {"status": "ok"}


@router.post("/equipment")
async def submit_equipment_state(
    payload: EquipmentState,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit equipment and inventory snapshot.

    Args:
        payload: Equipment state data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_equipment table
    conn.execute(
        """
        INSERT INTO plugin_equipment (
            account_id,
            equipment,
            inventory,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            json.dumps(payload.equipment),
            json.dumps(payload.inventory),
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "equipment",
        {"equipment_slots": len(payload.equipment), "inventory_items": len(payload.inventory)}
    )

    conn.commit()
    logger.info(f"Equipment state stored: {payload.rsn} - {len(payload.equipment)} equipped, {len(payload.inventory)} inventory")

    return {"status": "ok"}


@router.post("/loot")
async def submit_loot_drop(
    payload: LootDrop,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit loot drop received event.

    Args:
        payload: Loot drop data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_loot table
    conn.execute(
        """
        INSERT INTO plugin_loot (
            account_id,
            item_id,
            item_name,
            quantity,
            ge_value,
            source,
            source_type,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            payload.item_id,
            payload.item_name,
            payload.quantity,
            payload.ge_value,
            payload.source,
            payload.source_type.value,
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "loot",
        {
            "item_id": payload.item_id,
            "item_name": payload.item_name,
            "source": payload.source,
            "source_type": payload.source_type.value,
            "value": payload.ge_value
        }
    )

    conn.commit()
    logger.info(f"Loot drop stored: {payload.rsn} - {payload.item_name} x{payload.quantity} from {payload.source}")

    return {"status": "ok"}


@router.post("/activity")
async def submit_activity_update(
    payload: ActivityUpdate,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit general activity update event.

    Args:
        payload: Activity update data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_activity table
    conn.execute(
        """
        INSERT INTO plugin_activity (
            account_id,
            activity,
            detail,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            payload.activity,
            payload.detail,
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "activity",
        {"activity": payload.activity, "has_detail": payload.detail is not None}
    )

    conn.commit()
    logger.info(f"Activity update stored: {payload.rsn} - {payload.activity}")

    return {"status": "ok"}


@router.post("/bank")
async def submit_bank_snapshot(
    payload: BankSnapshot,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit bank contents snapshot.

    Args:
        payload: Bank snapshot data
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    account_id = _resolve_account_id(payload.rsn, conn)

    # Persist to plugin_bank table
    conn.execute(
        """
        INSERT INTO plugin_bank (
            account_id,
            items,
            total_value,
            world,
            timestamp,
            plugin_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            json.dumps(payload.items),
            payload.total_value,
            payload.world,
            payload.timestamp,
            payload.plugin_version
        )
    )

    # Log to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "bank",
        {"item_count": len(payload.items), "total_value": payload.total_value}
    )

    conn.commit()
    logger.info(f"Bank snapshot stored: {payload.rsn} - {len(payload.items)} items, {payload.total_value:,} gp value")

    return {"status": "ok"}


@router.post("/batch")
async def submit_batch_payload(
    payload: BatchPayload,
    token: Dict = Depends(require_plugin_key),
    conn: sqlite3.Connection = Depends(get_database_connection)
):
    """Submit batch payload containing multiple event categories.

    Args:
        payload: Batch payload with multiple event lists
        token: API token metadata (from auth)
        conn: Database connection

    Returns:
        Status response with processed counts
    """
    # Rate limit check (batch endpoint uses separate limiter)
    if not batch_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (10 batch requests per minute)"
        )

    # Resolve account ID once for all events (they all share same RSN from base)
    account_id = _resolve_account_id(payload.rsn, conn)

    processed: Dict[str, int] = {}

    # Process sessions
    if payload.sessions:
        for event in payload.sessions:
            conn.execute(
                """
                INSERT INTO plugin_sessions (
                    account_id,
                    session_id,
                    event,
                    world,
                    duration_seconds,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    event.session_id,
                    event.event.value,
                    event.world,
                    event.duration_seconds,
                    event.timestamp,
                    event.plugin_version
                )
            )
        processed["sessions"] = len(payload.sessions)

    # Process XP snapshots
    if payload.xp_snapshots:
        for xp in payload.xp_snapshots:
            conn.execute(
                """
                INSERT INTO plugin_xp_snapshots (
                    account_id,
                    skills,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    json.dumps(xp.skills),
                    xp.world,
                    xp.timestamp,
                    xp.plugin_version
                )
            )
        processed["xp"] = len(payload.xp_snapshots)

    # Process collection log
    if payload.collection_log:
        for entry in payload.collection_log:
            conn.execute(
                """
                INSERT INTO plugin_collection_log (
                    account_id,
                    item_id,
                    item_name,
                    quantity,
                    source,
                    obtained_at,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    entry.item_id,
                    entry.item_name,
                    entry.quantity,
                    entry.source,
                    entry.obtained_at,
                    entry.world,
                    entry.timestamp,
                    entry.plugin_version
                )
            )
        processed["collection_log"] = len(payload.collection_log)

    # Process quests
    if payload.quests:
        for quest in payload.quests:
            conn.execute(
                """
                INSERT INTO plugin_quests (
                    account_id,
                    quest_name,
                    state,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    quest.quest_name,
                    quest.state.value,
                    quest.world,
                    quest.timestamp,
                    quest.plugin_version
                )
            )
        processed["quests"] = len(payload.quests)

    # Process diaries
    if payload.diaries:
        for diary in payload.diaries:
            conn.execute(
                """
                INSERT INTO plugin_diaries (
                    account_id,
                    region,
                    easy,
                    medium,
                    hard,
                    elite,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    diary.region,
                    diary.easy,
                    diary.medium,
                    diary.hard,
                    diary.elite,
                    diary.world,
                    diary.timestamp,
                    diary.plugin_version
                )
            )
        processed["diaries"] = len(payload.diaries)

    # Process combat achievements
    if payload.combat_achievements:
        for ca in payload.combat_achievements:
            conn.execute(
                """
                INSERT INTO plugin_combat_achievements (
                    account_id,
                    tier_progress,
                    completed_tasks,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    json.dumps(ca.tier_progress),
                    json.dumps(ca.completed_tasks),
                    ca.world,
                    ca.timestamp,
                    ca.plugin_version
                )
            )
        processed["combat_achievements"] = len(payload.combat_achievements)

    # Process equipment
    if payload.equipment:
        for equip in payload.equipment:
            conn.execute(
                """
                INSERT INTO plugin_equipment (
                    account_id,
                    equipment,
                    inventory,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    json.dumps(equip.equipment),
                    json.dumps(equip.inventory),
                    equip.world,
                    equip.timestamp,
                    equip.plugin_version
                )
            )
        processed["equipment"] = len(payload.equipment)

    # Process loot
    if payload.loot:
        for loot in payload.loot:
            conn.execute(
                """
                INSERT INTO plugin_loot (
                    account_id,
                    item_id,
                    item_name,
                    quantity,
                    ge_value,
                    source,
                    source_type,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    loot.item_id,
                    loot.item_name,
                    loot.quantity,
                    loot.ge_value,
                    loot.source,
                    loot.source_type.value,
                    loot.world,
                    loot.timestamp,
                    loot.plugin_version
                )
            )
        processed["loot"] = len(payload.loot)

    # Process activity
    if payload.activity:
        for act in payload.activity:
            conn.execute(
                """
                INSERT INTO plugin_activity (
                    account_id,
                    activity,
                    detail,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    act.activity,
                    act.detail,
                    act.world,
                    act.timestamp,
                    act.plugin_version
                )
            )
        processed["activity"] = len(payload.activity)

    # Process bank
    if payload.bank:
        for bank in payload.bank:
            conn.execute(
                """
                INSERT INTO plugin_bank (
                    account_id,
                    items,
                    total_value,
                    world,
                    timestamp,
                    plugin_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    account_id,
                    json.dumps(bank.items),
                    bank.total_value,
                    bank.world,
                    bank.timestamp,
                    bank.plugin_version
                )
            )
        processed["bank"] = len(payload.bank)

    # Log batch submission to audit table
    _log_sync(
        conn,
        account_id,
        token["id"],
        "batch",
        {"categories": list(processed.keys()), "total_events": sum(processed.values())}
    )

    conn.commit()
    logger.info(f"Batch payload processed: {payload.rsn} - {sum(processed.values())} total events across {len(processed)} categories")

    return {"status": "ok", "processed": processed}


@router.get("/status")
async def get_status(
    token: Dict = Depends(require_plugin_key)
) -> StatusResponse:
    """Get API status and verify authentication.

    Args:
        token: API token metadata (from auth)

    Returns:
        Status response with authentication details
    """
    # Rate limit check
    if not plugin_rate_limiter.is_allowed(token["id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (30 requests per minute)"
        )

    return StatusResponse(
        status="ok",
        version="1.0.0",
        authenticated=True,
        user_id=token["user_id"]
    )
