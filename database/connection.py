"""Database connection management for OSRS Hiscore Analytics."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/analytics.db")
SCHEMA_DIR = Path(__file__).parent / "sql"


class DatabaseConnection:
    """Manages SQLite database connections and operations."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None

    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Optimize for analytics queries
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = NORMAL")
            self._connection.execute("PRAGMA cache_size = 10000")
            self._connection.execute("PRAGMA temp_store = MEMORY")
            # Set row factory for dict-like access
            self._connection.row_factory = sqlite3.Row

        try:
            yield self._connection
            self._connection.commit()
        except Exception:
            if self._connection:
                self._connection.rollback()
            raise

    def initialize_database(self) -> None:
        """Initialize database with schema if not exists."""
        logger.info(f"Initializing database at {self.db_path}")

        # Check if database is already initialized
        if self._is_initialized():
            logger.info("Database already initialized")
            self._run_migrations()
            return

        # Run initial schema setup
        with self.get_connection() as conn:
            # Execute initial schema
            initial_schema_path = SCHEMA_DIR / "001_initial_schema.sql"
            self._execute_sql_file(conn, initial_schema_path)

            # Execute performance indexes
            indexes_path = SCHEMA_DIR / "002_performance_indexes.sql"
            self._execute_sql_file(conn, indexes_path)

            # Execute analytics functions
            analytics_path = SCHEMA_DIR / "003_analytics_functions.sql"
            self._execute_sql_file(conn, analytics_path)

        logger.info("Database initialized successfully")

    def _is_initialized(self) -> bool:
        """Check if database has been initialized."""
        try:
            with self.get_connection() as conn:
                result = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
                ).fetchone()
                return result is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking database initialization: {e}")
            return False

    def _run_migrations(self) -> None:
        """Run pending database migrations."""
        with self.get_connection() as conn:
            # Get current schema version
            current_version = conn.execute(
                "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
            ).fetchone()

            if not current_version:
                logger.warning("No schema version found, re-initializing")
                self.initialize_database()
                return

            current_version_num = float(current_version["version"])
            logger.info(f"Current schema version: {current_version_num}")

            # Check for available migration files
            migration_files = sorted(SCHEMA_DIR.glob("*.sql"))
            latest_version = self._parse_version_from_filename(migration_files[-1])

            if current_version_num >= latest_version:
                logger.info("Database is up to date")
                return

            logger.info(f"Running migrations from {current_version_num} to {latest_version}")

    def _parse_version_from_filename(self, filename: Path) -> float:
        """Parse version number from migration filename."""
        # Extract version from filename like "001_initial_schema.sql"
        parts = filename.stem.split("_")
        try:
            return float(parts[0]) / 100.0
        except (ValueError, IndexError):
            return 1.0

    def _execute_sql_file(self, conn: sqlite3.Connection, sql_file: Path) -> None:
        """Execute SQL commands from a file."""
        if not sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file}")

        logger.info(f"Executing SQL file: {sql_file}")

        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Split by semicolons but handle multi-line statements better
        statements = []
        current_statement = ""

        for line in sql_content.split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("--"):
                continue
            current_statement += line + "\n"
            # If line ends with semicolon, we have a complete statement
            if line.endswith(";"):
                statements.append(current_statement.strip())
                current_statement = ""

        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())

        for i, statement in enumerate(statements, 1):
            if statement and not statement.startswith("--"):
                try:
                    conn.execute(statement)
                    logger.debug(f"Executed statement {i}: {statement[:50]}...")
                except sqlite3.Error as e:
                    logger.warning(f"Warning executing statement {i}: {e}")
                    logger.debug(f"Statement: {statement}")
                    # Continue execution for non-critical statements

    def health_check(self) -> dict[str, str]:
        """Perform database health check."""
        health_status = {"status": "healthy", "issues": []}

        try:
            with self.get_connection() as conn:
                # Check database file exists and is writable
                if not self.db_path.exists():
                    health_status["status"] = "error"
                    health_status["issues"].append("Database file does not exist")
                    return health_status

                # Check basic connectivity
                conn.execute("SELECT 1").fetchone()

                # Check schema version
                version_result = conn.execute(
                    "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
                ).fetchone()

                if not version_result:
                    health_status["status"] = "warning"
                    health_status["issues"].append("No schema version found")
                else:
                    health_status["schema_version"] = version_result["version"]

                # Check table integrity
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()

                expected_tables = {
                    "accounts", "snapshots", "skills", "activities",
                    "snapshots_deltas", "mode_cache", "schema_version"
                }

                table_names = {table["name"] for table in tables}
                missing_tables = expected_tables - table_names

                if missing_tables:
                    health_status["status"] = "error"
                    health_status["issues"].append(f"Missing tables: {missing_tables}")

                # Check data counts
                account_count = conn.execute("SELECT COUNT(*) as count FROM accounts").fetchone()["count"]
                snapshot_count = conn.execute("SELECT COUNT(*) as count FROM snapshots").fetchone()["count"]

                health_status["accounts_count"] = account_count
                health_status["snapshots_count"] = snapshot_count

        except sqlite3.Error as e:
            health_status["status"] = "error"
            health_status["issues"].append(f"Database error: {e}")
            logger.error(f"Database health check failed: {e}")

        return health_status

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __del__(self) -> None:
        """Cleanup connection on deletion."""
        self.close()