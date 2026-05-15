"""Tests for API dependencies including require_plugin_key."""

import hashlib
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.dependencies import require_plugin_key, require_plugin_ingest_key, parse_token_scopes


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    conn = MagicMock(spec=sqlite3.Connection)
    return conn


@pytest.fixture
def valid_token():
    """Generate a valid test token."""
    return "test_token_12345678901234567890"


@pytest.fixture
def valid_token_hash(valid_token):
    """Generate the hash for the valid token."""
    return hashlib.sha256(valid_token.encode("utf-8")).hexdigest()


class TestRequirePluginKey:
    """Test suite for require_plugin_key dependency."""

    @pytest.mark.asyncio
    async def test_missing_api_key(self, mock_db_connection):
        """Test that missing X-API-Key header raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await require_plugin_key(x_api_key=None, conn=mock_db_connection)

        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, mock_db_connection, valid_token):
        """Test that invalid/non-existent API key raises 401."""
        # Mock database returning no results
        mock_db_connection.execute.return_value.fetchone.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)

        assert exc_info.value.status_code == 401
        assert "Invalid or revoked" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_revoked_api_key(self, mock_db_connection, valid_token):
        """Test that revoked API key raises 401."""
        # Mock database returning None for revoked token
        mock_db_connection.execute.return_value.fetchone.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_without_plugin_scope(self, mock_db_connection, valid_token):
        """Test that token without 'plugin' scope raises 403."""
        # Mock database returning token without plugin scope
        mock_token = {
            "id": 1,
            "user_id": 100,
            "scopes": "read,write",
            "label": "Test Token"
        }
        mock_db_connection.execute.return_value.fetchone.return_value = mock_token

        with pytest.raises(HTTPException) as exc_info:
            await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)

        assert exc_info.value.status_code == 403
        assert "plugin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_valid_plugin_token(self, mock_db_connection, valid_token, valid_token_hash):
        """Test that valid token with plugin scope succeeds."""
        # Mock database returning valid token with plugin scope
        mock_token = {
            "id": 1,
            "user_id": 100,
            "scopes": "plugin,read",
            "label": "RuneLite Plugin"
        }

        # Setup mock to return token on SELECT, then handle UPDATE
        mock_select_result = MagicMock()
        mock_select_result.fetchone.return_value = mock_token
        mock_update_result = MagicMock()

        # First call (SELECT) returns token, second call (UPDATE) returns update result
        mock_db_connection.execute.side_effect = [mock_select_result, mock_update_result]

        result = await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)

        # Verify the result
        assert result["id"] == 1
        assert result["user_id"] == 100
        assert result["scopes"] == "plugin,read"
        assert result["label"] == "RuneLite Plugin"

        # Verify database calls
        assert mock_db_connection.execute.call_count == 2

        # Check SELECT query was called with correct hash
        select_call = mock_db_connection.execute.call_args_list[0]
        assert "SELECT id, user_id, scopes, label" in select_call[0][0]
        assert "token_hash = ?" in select_call[0][0]
        assert "revoked_at IS NULL" in select_call[0][0]
        assert select_call[0][1] == (valid_token_hash,)

        # Check UPDATE query was called with correct token ID
        update_call = mock_db_connection.execute.call_args_list[1]
        assert "UPDATE api_tokens" in update_call[0][0]
        assert "last_used_at = CURRENT_TIMESTAMP" in update_call[0][0]
        assert update_call[0][1] == (1,)

        # Verify commit was called
        mock_db_connection.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_hash_calculation(self, mock_db_connection, valid_token):
        """Test that token is hashed correctly using SHA-256."""
        expected_hash = hashlib.sha256(valid_token.encode("utf-8")).hexdigest()

        # Mock database returning None to avoid full execution
        mock_db_connection.execute.return_value.fetchone.return_value = None

        try:
            await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)
        except HTTPException:
            pass  # Expected

        # Verify the hash used in the query matches expected
        call_args = mock_db_connection.execute.call_args
        assert call_args[0][1] == (expected_hash,)

    @pytest.mark.asyncio
    async def test_plugin_scope_exact_token_match(self, mock_db_connection, valid_token):
        """Test exact tokenized plugin scope matching."""
        test_cases = [
            "plugin",
            "plugin,read,write",
            "read,plugin,write",
            "read write plugin"
        ]

        for scopes in test_cases:
            mock_token = {
                "id": 1,
                "user_id": 100,
                "scopes": scopes,
                "label": "Test"
            }

            mock_select_result = MagicMock()
            mock_select_result.fetchone.return_value = mock_token
            mock_update_result = MagicMock()

            mock_db_connection.execute.side_effect = [mock_select_result, mock_update_result]
            mock_db_connection.commit.reset_mock()

            result = await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)
            assert result["scopes"] == scopes

    @pytest.mark.asyncio
    async def test_plugin_scope_false_positive_fails(self, mock_db_connection, valid_token):
        """Test that substring false-positives fail exact scope matching."""
        mock_token = {
            "id": 1,
            "user_id": 100,
            "scopes": "my_plugin_api",
            "label": "Test"
        }

        mock_select_result = MagicMock()
        mock_select_result.fetchone.return_value = mock_token
        mock_update_result = MagicMock()

        mock_db_connection.execute.side_effect = [mock_select_result, mock_update_result]

        with pytest.raises(HTTPException) as exc_info:
            await require_plugin_key(x_api_key=valid_token, conn=mock_db_connection)
        assert exc_info.value.status_code == 403

    def test_parse_token_scopes(self):
        assert parse_token_scopes("plugin,read write") == {"plugin", "read", "write"}
        assert parse_token_scopes("") == set()

    @pytest.mark.asyncio
    async def test_require_plugin_ingest_key_allows_plugin_and_plugin_ingest(self, mock_db_connection, valid_token):
        for scopes in ("plugin", "plugin:ingest", "read plugin:ingest"):
            mock_token = {"id": 1, "user_id": 100, "scopes": scopes, "label": "Test"}
            mock_select_result = MagicMock()
            mock_select_result.fetchone.return_value = mock_token
            mock_update_result = MagicMock()
            mock_db_connection.execute.side_effect = [mock_select_result, mock_update_result]
            result = await require_plugin_ingest_key(x_api_key=valid_token, conn=mock_db_connection)
            assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_require_plugin_ingest_key_rejects_insufficient_scope(self, mock_db_connection, valid_token):
        mock_token = {"id": 1, "user_id": 100, "scopes": "readplugin", "label": "Test"}
        mock_select_result = MagicMock()
        mock_select_result.fetchone.return_value = mock_token
        mock_update_result = MagicMock()
        mock_db_connection.execute.side_effect = [mock_select_result, mock_update_result]
        with pytest.raises(HTTPException) as exc_info:
            await require_plugin_ingest_key(x_api_key=valid_token, conn=mock_db_connection)
        assert exc_info.value.status_code == 403
