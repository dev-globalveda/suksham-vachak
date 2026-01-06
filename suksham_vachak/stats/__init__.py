"""Stats Engine for cricket player matchup statistics.

Provides head-to-head statistics between batters and bowlers,
aggregated from Cricsheet match data.

Example usage:
    from suksham_vachak.stats import create_engine, StatsConfig

    config = StatsConfig.default()
    engine = create_engine(config)

    matchup = engine.get_head_to_head("V Kohli", "JM Anderson")
    if matchup:
        print(matchup.to_commentary_context())
"""

from .config import StatsConfig
from .db import StatsDatabase
from .matchups import MatchupEngine
from .models import MatchupRecord, PlayerMatchupStats
from .normalize import normalize_display_name, normalize_player_id

__all__ = [
    "MatchupEngine",
    "MatchupRecord",
    "PlayerMatchupStats",
    "StatsConfig",
    "StatsDatabase",
    "create_engine",
    "normalize_display_name",
    "normalize_player_id",
]


def create_engine(config: StatsConfig | None = None) -> MatchupEngine:
    """Create a MatchupEngine with default or custom configuration.

    Args:
        config: Optional StatsConfig. Uses default if not provided.

    Returns:
        Initialized MatchupEngine ready for queries.
    """
    if config is None:
        config = StatsConfig.default()

    db = StatsDatabase(config.db_path)
    db.initialize()

    return MatchupEngine(db)
