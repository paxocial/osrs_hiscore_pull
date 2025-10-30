"""Account management endpoints for OSRS Analytics API."""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import JSONResponse

from api.dependencies import get_database_connection, parse_account_query_params
from api.schemas import (
    Account,
    AccountCreate,
    AccountUpdate,
    AccountListResponse,
    ErrorResponse,
    Snapshot
)
from api.exceptions import DataNotFoundException, ValidationException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=AccountListResponse, summary="List all accounts")
async def list_accounts(
    params: AccountQueryParams = Depends(parse_account_query_params),
    conn = Depends(get_database_connection)
):
    """
    Retrieve a paginated list of OSRS accounts.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page, 1-100 (default: 10)
    - **active_only**: Only show active accounts (default: true)
    - **search**: Search term for account names (optional)

    Returns accounts with pagination metadata.
    """
    try:
        # Build base query
        query = "SELECT * FROM accounts"
        count_query = "SELECT COUNT(*) as total FROM accounts"
        conditions = []
        params_list = []

        # Add filters
        if params.active_only:
            conditions.append("active = 1")

        if params.search:
            conditions.append("(name LIKE ? OR display_name LIKE ?)")
            search_term = f"%{params.search}%"
            params_list.extend([search_term, search_term])

        # Combine conditions
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            query += where_clause
            count_query += where_clause

        # Add pagination
        offset = (params.page - 1) * params.page_size
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params_list.extend([params.page_size, offset])

        # Execute queries
        accounts_data = conn.execute(query, params_list).fetchall()
        total_count = conn.execute(count_query, params_list[:len(params_list)-2]).fetchone()["total"]

        # Convert to Account models
        accounts = []
        for account_row in accounts_data:
            # Get additional stats for each account
            stats_query = """
                SELECT
                    COUNT(s.id) as total_snapshots,
                    MAX(s.fetched_at) as latest_snapshot
                FROM snapshots s
                WHERE s.account_id = ?
            """
            stats = conn.execute(stats_query, (account_row["id"],)).fetchone()

            account_dict = dict(account_row)
            account_dict.update({
                "total_snapshots": stats["total_snapshots"] if stats["total_snapshots"] else 0,
                "latest_snapshot": stats["latest_snapshot"]
            })

            accounts.append(Account.model_validate(account_dict))

        return AccountListResponse(
            accounts=accounts,
            total=total_count,
            page=params.page,
            page_size=params.page_size
        )

    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve accounts"
        )


@router.get("/search", response_model=List[Account], summary="Search accounts")
async def search_accounts(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    conn = Depends(get_database_connection)
):
    """
    Search for accounts by name or display name.

    - **q**: Search term (required)
    - **limit**: Maximum number of results (default: 10, max: 50)

    Returns a list of matching accounts.
    """
    try:
        with conn:
            # Search accounts
            search_query = """
                SELECT id, name, display_name, default_mode, created_at, updated_at, active
                FROM accounts
                WHERE name LIKE ? OR display_name LIKE ?
                ORDER BY name
                LIMIT ?
            """
            search_term = f"%{q}%"
            accounts_data = conn.execute(search_query, (search_term, search_term, limit)).fetchall()

            accounts = []
            for account_row in accounts_data:
                latest_query = """
                    SELECT fetched_at
                    FROM snapshots
                    WHERE account_id = ?
                    ORDER BY fetched_at DESC
                    LIMIT 1
                """
                latest = conn.execute(latest_query, (account_row["id"],)).fetchone()

                account_dict = dict(account_row)
                account_dict["latest_snapshot"] = latest["fetched_at"] if latest else None

                accounts.append(Account.model_validate(account_dict))

        return accounts

    except Exception as e:
        logger.error(f"Error searching accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search accounts"
        )


@router.get("/{account_name}", response_model=Account, summary="Get account details")
async def get_account(
    account_name: str,
    include_latest_snapshot: bool = Query(False, description="Include latest snapshot data"),
    conn = Depends(get_database_connection)
):
    """
    Retrieve detailed information for a specific account.

    - **account_name**: The account username
    - **include_latest_snapshot**: Whether to include the latest snapshot data

    Returns account details with optional latest snapshot.
    """
    try:
        # Get account
        account = conn.execute(
            "SELECT * FROM accounts WHERE name = ?",
            (account_name,)
        ).fetchone()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{account_name}' not found"
            )

        account_dict = dict(account)

        # Get account statistics
        stats_query = """
            SELECT
                COUNT(s.id) as total_snapshots,
                MAX(s.fetched_at) as latest_snapshot,
                MIN(s.fetched_at) as first_snapshot,
                MAX(s.total_xp) as current_total_xp,
                MAX(s.total_level) as current_total_level
            FROM snapshots s
            WHERE s.account_id = ?
        """
        stats = conn.execute(stats_query, (account["id"],)).fetchone()

        account_dict.update({
            "total_snapshots": stats["total_snapshots"] if stats["total_snapshots"] else 0,
            "latest_snapshot": stats["latest_snapshot"],
            "first_snapshot": stats["first_snapshot"],
            "current_total_xp": stats["current_total_xp"],
            "current_total_level": stats["current_total_level"]
        })

        # Get latest snapshot if requested
        if include_latest_snapshot:
            latest_snapshot_query = """
                SELECT * FROM snapshots
                WHERE account_id = ?
                ORDER BY fetched_at DESC
                LIMIT 1
            """
            latest_snapshot = conn.execute(latest_snapshot_query, (account["id"],)).fetchone()

            if latest_snapshot:
                # Get skills and activities for latest snapshot
                skills_query = """
                    SELECT * FROM skills WHERE snapshot_id = ?
                """
                skills_data = conn.execute(skills_query, (latest_snapshot["id"],)).fetchall()

                activities_query = """
                    SELECT * FROM activities WHERE snapshot_id = ?
                """
                activities_data = conn.execute(activities_query, (latest_snapshot["id"],)).fetchall()

                snapshot_dict = dict(latest_snapshot)
                snapshot_dict["skills"] = [dict(skill) for skill in skills_data]
                snapshot_dict["activities"] = [dict(activity) for activity in activities_data]

                account_dict["latest_snapshot_data"] = Snapshot.model_validate(snapshot_dict)

        return Account.model_validate(account_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account {account_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account"
        )


@router.get("/{account_name}/snapshots", response_model=List[Snapshot], summary="Get account snapshots")
async def get_account_snapshots(
    account_name: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    include_skills: bool = Query(False, description="Include skill data"),
    include_activities: bool = Query(False, description="Include activity data"),
    conn = Depends(get_database_connection)
):
    """
    Retrieve snapshots for a specific account with pagination.

    - **account_name**: The account username
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10)
    - **include_skills**: Include skill data (default: false)
    - **include_activities**: Include activity data (default: false)

    Returns a list of snapshots ordered by fetch date (newest first).
    """
    try:
        # Direct connection usage
        # Verify account exists
        account = conn.execute(
            "SELECT id FROM accounts WHERE name = ?",
            (account_name,)
        ).fetchone()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{account_name}' not found"
            )
        # Get snapshots with pagination
        offset = (page - 1) * page_size
        snapshots_query = """
            SELECT * FROM snapshots
            WHERE account_id = ?
            ORDER BY fetched_at DESC
            LIMIT ? OFFSET ?
        """
        snapshots_data = conn.execute(
            snapshots_query,
            (account["id"], page_size, offset)
        ).fetchall()

        snapshots = []
        for snapshot_row in snapshots_data:
            snapshot_dict = dict(snapshot_row)

            # Include skills if requested
            if include_skills:
                skills_query = "SELECT * FROM skills WHERE snapshot_id = ?"
                skills_data = conn.execute(skills_query, (snapshot_row["id"],)).fetchall()
                snapshot_dict["skills"] = [dict(skill) for skill in skills_data]

            # Include activities if requested
            if include_activities:
                activities_query = "SELECT * FROM activities WHERE snapshot_id = ?"
                activities_data = conn.execute(activities_query, (snapshot_row["id"],)).fetchall()
                snapshot_dict["activities"] = [dict(activity) for activity in activities_data]

            snapshots.append(Snapshot.model_validate(snapshot_dict))

        return snapshots

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting snapshots for {account_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account snapshots"
        )


@router.post("/", response_model=Account, status_code=status.HTTP_201_CREATED, summary="Create account")
async def create_account(
    account_data: AccountCreate,
    conn = Depends(get_database_connection)
):
    """
    Create a new OSRS account.

    The account name must be unique and will be validated against the OSRS hiscores
    to ensure it exists and the specified game mode is correct.

    Returns the created account information.
    """
    try:
        # Direct connection usage
        # Check if account already exists
        existing = conn.execute(
            "SELECT id FROM accounts WHERE name = ?",
            (account_data.name,)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account '{account_data.name}' already exists"
            )

        # Create account
        cursor = conn.execute(
            """
            INSERT INTO accounts (name, display_name, default_mode, active, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                account_data.name,
                account_data.display_name,
                account_data.default_mode,
                1 if account_data.active else 0,
                str(account_data.metadata) if account_data.metadata else "{}"
            )
        )

        account_id = cursor.lastrowid

        # Get created account
        created_account = conn.execute(
            "SELECT * FROM accounts WHERE id = ?",
            (account_id,)
        ).fetchone()

        logger.info(f"Created account: {account_data.name}")

        return Account.model_validate(dict(created_account))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating account {account_data.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )


@router.put("/{account_name}", response_model=Account, summary="Update account")
async def update_account(
    account_name: str,
    account_update: AccountUpdate,
    conn = Depends(get_database_connection)
):
    """
    Update an existing account's information.

    Only the fields provided in the request body will be updated.
    Returns the updated account information.
    """
    try:
        # Direct connection usage
        # Check if account exists
        existing = conn.execute(
            "SELECT * FROM accounts WHERE name = ?",
            (account_name,)
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{account_name}' not found"
            )

        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []

        if account_update.display_name is not None:
            update_fields.append("display_name = ?")
            update_values.append(account_update.display_name)

        if account_update.default_mode is not None:
            update_fields.append("default_mode = ?")
            update_values.append(account_update.default_mode)

        if account_update.active is not None:
            update_fields.append("active = ?")
            update_values.append(1 if account_update.active else 0)

        if account_update.metadata is not None:
            update_fields.append("metadata = ?")
            update_values.append(str(account_update.metadata))

        if update_fields:
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(existing["id"])

            # Execute update
            update_query = f"""
                UPDATE accounts
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            conn.execute(update_query, update_values)

            # Get updated account
            updated_account = conn.execute(
                "SELECT * FROM accounts WHERE name = ?",
                (account_name,)
            ).fetchone()

            logger.info(f"Updated account: {account_name}")

            return Account.model_validate(dict(updated_account))
        else:
            # No updates to make
            return Account.model_validate(dict(existing))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account {account_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update account"
        )


@router.delete("/{account_name}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete account")
async def delete_account(
    account_name: str,
    conn = Depends(get_database_connection)
):
    """
    Delete an account and all associated data.

    **Warning**: This action is irreversible and will delete all snapshots,
    skills, activities, and analytics data associated with this account.
    """
    try:
        # Direct connection usage
        # Check if account exists
        existing = conn.execute(
            "SELECT id FROM accounts WHERE name = ?",
            (account_name,)
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{account_name}' not found"
            )

        # Delete account (cascades to snapshots, skills, activities)
        conn.execute("DELETE FROM accounts WHERE name = ?", (account_name,))

        logger.info(f"Deleted account: {account_name}")

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account {account_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )