"""Configuration for the stats engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class StatsConfig:
    """Configuration for the stats engine."""

    # Database path
    db_path: str = "data/stats.db"

    # Cricsheet data directory
    cricsheet_data_dir: str = "data/cricsheet_sample"

    # Minimum balls faced for matchup to be considered significant
    min_balls_significant: int = 10

    # Minimum balls faced for matchup to be shown in queries
    min_balls_query: int = 6

    @classmethod
    def default(cls) -> StatsConfig:
        """Create default configuration."""
        return cls()

    @classmethod
    def from_env(cls) -> StatsConfig:
        """Create configuration from environment variables."""
        import os

        return cls(
            db_path=os.getenv("STATS_DB_PATH", "data/stats.db"),
            cricsheet_data_dir=os.getenv("CRICSHEET_DATA_DIR", "data/cricsheet_sample"),
            min_balls_significant=int(os.getenv("STATS_MIN_BALLS_SIGNIFICANT", "10")),
            min_balls_query=int(os.getenv("STATS_MIN_BALLS_QUERY", "6")),
        )

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
