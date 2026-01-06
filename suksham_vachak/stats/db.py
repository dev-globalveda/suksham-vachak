"""SQLite database layer for cricket statistics."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import MatchupRecord

# SQL schema for stats database
SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    full_name TEXT,
    team TEXT
);

CREATE TABLE IF NOT EXISTS matchups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batter_id TEXT NOT NULL,
    bowler_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    match_date TEXT,
    match_format TEXT,
    venue TEXT,

    balls_faced INTEGER DEFAULT 0,
    runs_scored INTEGER DEFAULT 0,
    dots INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    dismissals INTEGER DEFAULT 0,
    dismissal_type TEXT,
    phase TEXT,

    FOREIGN KEY (batter_id) REFERENCES players(id),
    FOREIGN KEY (bowler_id) REFERENCES players(id)
);

CREATE INDEX IF NOT EXISTS idx_matchups_batter ON matchups(batter_id);
CREATE INDEX IF NOT EXISTS idx_matchups_bowler ON matchups(bowler_id);
CREATE INDEX IF NOT EXISTS idx_matchups_pair ON matchups(batter_id, bowler_id);
CREATE INDEX IF NOT EXISTS idx_matchups_match ON matchups(match_id);
"""

# Schema v2: Add phase column and date indexes for phase/form queries
SCHEMA_V2_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_matchups_phase ON matchups(batter_id, phase, match_format);
CREATE INDEX IF NOT EXISTS idx_matchups_bowler_phase ON matchups(bowler_id, phase, match_format);
CREATE INDEX IF NOT EXISTS idx_matchups_batter_date ON matchups(batter_id, match_date DESC);
CREATE INDEX IF NOT EXISTS idx_matchups_bowler_date ON matchups(bowler_id, match_date DESC);
"""


class StatsDatabase:
    """SQLite database for cricket statistics.

    Provides methods for storing and querying player matchup statistics.
    For file-based databases, uses connection-per-operation for thread safety.
    For in-memory databases, reuses a single connection.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory DB.
        """
        self.db_path = str(db_path)
        self._initialized = False
        # For in-memory databases, keep a persistent connection
        self._memory_conn: sqlite3.Connection | None = None

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Create a database connection context."""
        if self.db_path == ":memory:":
            # Reuse persistent connection for in-memory DB
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:")
                self._memory_conn.row_factory = sqlite3.Row
            yield self._memory_conn
        else:
            # Create new connection for file-based DB
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def initialize(self) -> None:
        """Create database schema if not exists."""
        if self._initialized and self.db_path != ":memory:":
            return

        with self._connection() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

        self._initialized = True

    def migrate_to_v2(self) -> None:
        """Migrate schema to v2: add phase column and indexes.

        Safe to call multiple times - uses IF NOT EXISTS.
        """
        with self._connection() as conn:
            # Check if phase column exists
            cursor = conn.execute("PRAGMA table_info(matchups)")
            columns = {row[1] for row in cursor.fetchall()}

            if "phase" not in columns:
                conn.execute("ALTER TABLE matchups ADD COLUMN phase TEXT")

            # Create v2 indexes (safe - uses IF NOT EXISTS)
            conn.executescript(SCHEMA_V2_INDEXES)
            conn.commit()

    def upsert_player(
        self,
        player_id: str,
        name: str,
        full_name: str | None = None,
        team: str | None = None,
    ) -> None:
        """Insert or update a player record."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO players (id, name, full_name, team)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = COALESCE(excluded.name, name),
                    full_name = COALESCE(excluded.full_name, full_name),
                    team = COALESCE(excluded.team, team)
                """,
                (player_id, name, full_name, team),
            )
            conn.commit()

    def add_matchup_record(self, record: MatchupRecord) -> None:
        """Add a single matchup record."""
        with self._connection() as conn:
            # Ensure players exist
            conn.execute(
                "INSERT OR IGNORE INTO players (id, name) VALUES (?, ?)",
                (record.batter_id, record.batter_name),
            )
            conn.execute(
                "INSERT OR IGNORE INTO players (id, name) VALUES (?, ?)",
                (record.bowler_id, record.bowler_name),
            )

            # Insert matchup record
            conn.execute(
                """
                INSERT INTO matchups (
                    batter_id, bowler_id, match_id, match_date, match_format, venue,
                    balls_faced, runs_scored, dots, fours, sixes, dismissals, dismissal_type,
                    phase
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.batter_id,
                    record.bowler_id,
                    record.match_id,
                    record.match_date,
                    record.match_format,
                    record.venue,
                    record.balls_faced,
                    record.runs_scored,
                    record.dots,
                    record.fours,
                    record.sixes,
                    record.dismissals,
                    record.dismissal_type,
                    record.phase,
                ),
            )
            conn.commit()

    def add_matchup_records_batch(self, records: list[MatchupRecord]) -> None:
        """Add multiple matchup records in a single transaction."""
        if not records:
            return

        with self._connection() as conn:
            # Collect unique players
            players: dict[str, str] = {}
            for record in records:
                players[record.batter_id] = record.batter_name
                players[record.bowler_id] = record.bowler_name

            # Insert all players
            conn.executemany(
                "INSERT OR IGNORE INTO players (id, name) VALUES (?, ?)",
                list(players.items()),
            )

            # Insert all matchup records
            conn.executemany(
                """
                INSERT INTO matchups (
                    batter_id, bowler_id, match_id, match_date, match_format, venue,
                    balls_faced, runs_scored, dots, fours, sixes, dismissals, dismissal_type,
                    phase
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.batter_id,
                        r.bowler_id,
                        r.match_id,
                        r.match_date,
                        r.match_format,
                        r.venue,
                        r.balls_faced,
                        r.runs_scored,
                        r.dots,
                        r.fours,
                        r.sixes,
                        r.dismissals,
                        r.dismissal_type,
                        r.phase,
                    )
                    for r in records
                ],
            )
            conn.commit()

    def get_player_count(self) -> int:
        """Get total number of players in database."""
        with self._connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM players").fetchone()
            return result[0] if result else 0

    def get_matchup_count(self) -> int:
        """Get total number of matchup records in database."""
        with self._connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM matchups").fetchone()
            return result[0] if result else 0

    def get_match_count(self) -> int:
        """Get total number of unique matches in database."""
        with self._connection() as conn:
            result = conn.execute("SELECT COUNT(DISTINCT match_id) FROM matchups").fetchone()
            return result[0] if result else 0

    def clear(self) -> None:
        """Clear all data from the database."""
        with self._connection() as conn:
            conn.execute("DELETE FROM matchups")
            conn.execute("DELETE FROM players")
            conn.commit()

    def get_player_name(self, player_id: str) -> str | None:
        """Get player display name by ID."""
        with self._connection() as conn:
            result = conn.execute("SELECT name FROM players WHERE id = ?", (player_id,)).fetchone()
            return result["name"] if result else None
