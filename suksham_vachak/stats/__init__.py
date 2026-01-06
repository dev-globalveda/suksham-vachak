"""Stats Engine for cricket player matchup statistics.

Provides head-to-head statistics between batters and bowlers,
aggregated from Cricsheet match data. Includes phase-based analysis
and recent form tracking.

Example usage:
    from suksham_vachak.stats import create_engines, StatsConfig

    config = StatsConfig.default()
    matchup_engine, phase_engine, form_engine = create_engines(config)

    matchup = matchup_engine.get_head_to_head("V Kohli", "JM Anderson")
    if matchup:
        print(matchup.to_commentary_context())

    phase_stats = phase_engine.get_phase_performance("V Kohli", "powerplay", "T20")
    form = form_engine.get_recent_form("V Kohli")
"""

from .config import StatsConfig
from .db import StatsDatabase
from .form import FormEngine, FormTrend
from .matchups import MatchupEngine
from .models import MatchPerformance, MatchupRecord, PhaseStats, PlayerMatchupStats, RecentForm
from .normalize import normalize_display_name, normalize_player_id
from .phases import Phase, PhaseEngine

__all__ = [
    "FormEngine",
    "FormTrend",
    "MatchPerformance",
    "MatchupEngine",
    "MatchupRecord",
    "Phase",
    "PhaseEngine",
    "PhaseStats",
    "PlayerMatchupStats",
    "RecentForm",
    "StatsConfig",
    "StatsDatabase",
    "create_engine",
    "create_engines",
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
    db.migrate_to_v2()

    return MatchupEngine(db)


def create_engines(
    config: StatsConfig | None = None,
) -> tuple[MatchupEngine, PhaseEngine, FormEngine]:
    """Create all stats engines with shared database.

    Args:
        config: Optional StatsConfig. Uses default if not provided.

    Returns:
        Tuple of (MatchupEngine, PhaseEngine, FormEngine).
    """
    if config is None:
        config = StatsConfig.default()

    db = StatsDatabase(config.db_path)
    db.initialize()
    db.migrate_to_v2()

    return (
        MatchupEngine(db),
        PhaseEngine(db),
        FormEngine(db),
    )
