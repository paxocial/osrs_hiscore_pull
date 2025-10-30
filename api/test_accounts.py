"""Simple test accounts endpoint to verify database connection works."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, status

from api.schemas import Account

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db_connection():
    """Get a fresh database connection."""
    db_path = Path("data/analytics.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        db_path,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )

    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/test", response_model=List[Account])
async def test_accounts():
    """Test endpoint to verify database connection works."""
    try:
        conn = get_db_connection()

        # Get accounts
        accounts_data = conn.execute(
            "SELECT * FROM accounts ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

        accounts = []
        for account_row in accounts_data:
            account_dict = dict(account_row)
            accounts.append(Account.model_validate(account_dict))

        conn.close()

        return accounts

    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )