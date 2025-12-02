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

    def __init__(
        self,
        db_path: Optional[Path] = None,
        *,
        reuse_connection: bool = True,
        check_same_thread: bool = True,
    ) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
        self.reuse_connection = reuse_connection
        self.check_same_thread = check_same_thread

    def _connect(self, *, check_same_thread: Optional[bool] = None) -> sqlite3.Connection:
        cs_thread = self.check_same_thread if check_same_thread is None else check_same_thread
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=cs_thread,
        )
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Optimize for analytics queries
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 10000")
        conn.execute("PRAGMA temp_store = MEMORY")
        # Set row factory for dict-like access
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn: sqlite3.Connection
        if self.reuse_connection:
            if self._connection is None:
                self._connection = self._connect()
            conn = self._connection
        else:
            conn = self._connect()

        try:
            yield conn
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if not self.reuse_connection:
                try:
                    conn.close()
                except Exception:
                    pass

    def initialize_database(self) -> None:
        """Initialize database with schema if not exists and run migrations."""
        logger.info(f"Initializing database at {self.db_path}")

        # Check if database is already initialized
        if self._is_initialized():
            logger.info("Database already initialized")
            self._run_migrations()
            return

        # Run base schema setup
        with self.get_connection() as conn:
            initial_schema_path = SCHEMA_DIR / "001_initial_schema.sql"
            self._execute_sql_file(conn, initial_schema_path)

            indexes_path = SCHEMA_DIR / "002_performance_indexes.sql"
            self._execute_sql_file(conn, indexes_path)

            analytics_path = SCHEMA_DIR / "003_analytics_functions.sql"
            self._execute_sql_file(conn, analytics_path)

        # Apply any newer migrations after base load
        self._run_migrations()
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
            current_version_row = conn.execute(
                "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
            ).fetchone()

            current_version = float(current_version_row["version"]) if current_version_row else 0.0
            logger.info(f"Current schema version: {current_version}")

            migration_files = sorted(SCHEMA_DIR.glob("*.sql"))
            for sql_file in migration_files:
                file_version = self._parse_version_from_filename(sql_file)
                if file_version > current_version:
                    logger.info(f"Applying migration {sql_file.name} (version {file_version})")
                    self._execute_sql_file(conn, sql_file)
                    # Refresh current version after migration
                    version_row = conn.execute(
                        "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                    if version_row:
                        current_version = float(version_row["version"])

            logger.info(f"Database is up to date at version {current_version}")

    def _parse_version_from_filename(self, filename: Path) -> float:
        """Parse version number from migration filename.

        Migration filenames use a zero-padded ordinal prefix (e.g., 001, 002, 003).
        We map these to semantic versions: 001 -> 1.0, 002 -> 1.1, 003 -> 1.2, etc.
        """
        parts = filename.stem.split("_")
        try:
            ordinal = int(parts[0])
            # Example: 1 => 1.0, 2 => 1.1, 3 => 1.2
            return 1.0 + (ordinal - 1) * 0.1
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
