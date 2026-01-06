"""CLI for stats ingestion and queries.

Usage:
    python -m suksham_vachak.stats.cli ingest
    python -m suksham_vachak.stats.cli info
    python -m suksham_vachak.stats.cli matchup "V Kohli" "JM Anderson"
    python -m suksham_vachak.stats.cli phase "V Kohli" powerplay --format T20
    python -m suksham_vachak.stats.cli form "V Kohli"
    python -m suksham_vachak.stats.cli clear
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import StatsConfig


def ingest_all(config: StatsConfig) -> None:
    """Ingest all Cricsheet matches into stats database."""
    from .aggregator import StatsAggregator
    from .db import StatsDatabase

    print("Initializing Stats Engine...")
    print(f"  Database: {config.db_path}")
    print(f"  Cricsheet dir: {config.cricsheet_data_dir}")

    config.ensure_directories()

    db = StatsDatabase(config.db_path)
    db.initialize()
    db.migrate_to_v2()  # Ensure phase column exists

    aggregator = StatsAggregator(config.cricsheet_data_dir)
    total_matches = aggregator.count_matches()
    print(f"  Found {total_matches} match files")

    if total_matches == 0:
        print("\nNo match files found. Check your cricsheet_data_dir path.")
        return

    print("\nProcessing matches...")
    matches_processed = 0
    records_total = 0

    for match_records in aggregator.process_all():
        db.add_matchup_records_batch(match_records)
        matches_processed += 1
        records_total += len(match_records)

        if matches_processed % 10 == 0:
            print(f"  Processed {matches_processed}/{total_matches} matches...")

    print("\nComplete!")
    print(f"  Matches processed: {matches_processed}")
    print(f"  Matchup records: {records_total}")
    print(f"  Players: {db.get_player_count()}")


def show_info(config: StatsConfig) -> None:
    """Show database statistics."""
    from .db import StatsDatabase

    db_path = Path(config.db_path)
    if not db_path.exists():
        print(f"Database not found: {config.db_path}")
        print("Run 'python -m suksham_vachak.stats.cli ingest' to create it.")
        return

    db = StatsDatabase(config.db_path)
    db.initialize()

    print(f"Stats Database: {config.db_path}")
    print(f"  Size: {db_path.stat().st_size / 1024:.1f} KB")
    print(f"  Players: {db.get_player_count()}")
    print(f"  Matchup records: {db.get_matchup_count()}")
    print(f"  Unique matches: {db.get_match_count()}")


def query_matchup(config: StatsConfig, batter: str, bowler: str) -> None:
    """Query head-to-head matchup between batter and bowler."""
    from .db import StatsDatabase
    from .matchups import MatchupEngine

    db_path = Path(config.db_path)
    if not db_path.exists():
        print(f"Database not found: {config.db_path}")
        print("Run 'python -m suksham_vachak.stats.cli ingest' first.")
        return

    db = StatsDatabase(config.db_path)
    db.initialize()

    engine = MatchupEngine(db)
    stats = engine.get_head_to_head(batter, bowler)

    if stats is None:
        print(f"No matchup data found for {batter} vs {bowler}")
        return

    print(f"\n=== {stats.batter_name} vs {stats.bowler_name} ===")
    print(f"Matches: {stats.matches}")
    print(f"Runs: {stats.runs_scored} off {stats.balls_faced} balls")
    print(f"Strike Rate: {stats.strike_rate:.1f}")
    if stats.dismissals > 0:
        print(f"Dismissed: {stats.dismissals}x (avg {stats.average:.1f})")
    else:
        print("Dismissed: Never")
    print(f"Boundaries: {stats.fours} fours, {stats.sixes} sixes")
    print(f"Dot %: {stats.dot_percentage:.1f}%")


def query_player(config: StatsConfig, player: str, as_batter: bool = True) -> None:
    """Show a player's matchup stats against all opponents."""
    from .db import StatsDatabase
    from .matchups import MatchupEngine

    db_path = Path(config.db_path)
    if not db_path.exists():
        print(f"Database not found: {config.db_path}")
        return

    db = StatsDatabase(config.db_path)
    db.initialize()

    engine = MatchupEngine(db)

    if as_batter:
        matchups = engine.get_batter_vs_all(player, min_balls=config.min_balls_query)
        print(f"\n=== {player} as batter ===")
    else:
        matchups = engine.get_bowler_vs_all(player, min_balls=config.min_balls_query)
        print(f"\n=== {player} as bowler ===")

    if not matchups:
        print("No matchup data found.")
        return

    for m in matchups:
        opponent = m.bowler_name if as_batter else m.batter_name
        avg_str = f"avg {m.average:.0f}" if m.dismissals > 0 else "not out"
        print(f"  vs {opponent}: {m.runs_scored}/{m.balls_faced} SR {m.strike_rate:.0f}, {avg_str}")


def query_phase(
    config: StatsConfig,
    player: str,
    phase: str,
    match_format: str | None = None,
    as_bowler: bool = False,
) -> None:
    """Query player performance in a specific phase."""
    from .db import StatsDatabase
    from .phases import PhaseEngine

    db_path = Path(config.db_path)
    if not db_path.exists():
        print(f"Database not found: {config.db_path}")
        return

    db = StatsDatabase(config.db_path)
    db.initialize()
    db.migrate_to_v2()

    engine = PhaseEngine(db)
    role = "bowler" if as_bowler else "batter"
    stats = engine.get_phase_performance(player, phase, match_format, role)

    if stats is None:
        fmt_str = f" ({match_format})" if match_format else ""
        print(f"No {phase} data found for {player}{fmt_str}")
        return

    print(f"\n=== {stats.player_name} in {stats.phase} ({stats.match_format}) ===")
    print(f"Matches: {stats.matches}")

    if role == "batter":
        print(f"Runs: {stats.runs} off {stats.balls} balls")
        print(f"Strike Rate: {stats.strike_rate:.1f}")
        if stats.wickets > 0:
            print(f"Dismissed: {stats.wickets}x (avg {stats.average:.1f})")
        else:
            print("Dismissed: Never")
        print(f"Boundaries: {stats.fours} fours, {stats.sixes} sixes")
    else:
        overs = stats.balls / 6
        print(f"Overs: {overs:.1f}")
        print(f"Runs conceded: {stats.runs}")
        print(f"Economy: {stats.economy:.2f}")
        print(f"Wickets: {stats.wickets}")


def query_form(config: StatsConfig, player: str, as_bowler: bool = False) -> None:
    """Query player's recent form."""
    from .db import StatsDatabase
    from .form import FormEngine

    db_path = Path(config.db_path)
    if not db_path.exists():
        print(f"Database not found: {config.db_path}")
        return

    db = StatsDatabase(config.db_path)
    db.initialize()
    db.migrate_to_v2()

    engine = FormEngine(db, window_size=5)
    role = "bowler" if as_bowler else "batter"
    form = engine.get_recent_form(player, role)

    if form is None:
        print(f"No recent form data found for {player}")
        return

    print(f"\n=== {form.player_name} Recent Form ({form.role}) ===")
    print(f"Trend: {form.trend.upper()}")
    print(f"Summary: {form.trend_description}")
    print(f"\nLast {len(form.matches)} matches:")

    for m in form.matches:
        if role == "batter":
            print(f"  {m.match_date}: {m.runs}/{m.balls} SR {m.strike_rate:.0f} @ {m.venue}")
        else:
            print(f"  {m.match_date}: {m.dismissals} wkts, {m.runs} runs @ {m.venue}")


def clear_database(config: StatsConfig) -> None:
    """Clear all data from the database."""
    from .db import StatsDatabase

    db = StatsDatabase(config.db_path)
    db.initialize()
    db.clear()
    print("Stats database cleared.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Stats Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m suksham_vachak.stats.cli ingest
  python -m suksham_vachak.stats.cli info
  python -m suksham_vachak.stats.cli matchup "V Kohli" "JM Anderson"
  python -m suksham_vachak.stats.cli player "V Kohli"
  python -m suksham_vachak.stats.cli phase "V Kohli" powerplay --format T20
  python -m suksham_vachak.stats.cli form "V Kohli"
  python -m suksham_vachak.stats.cli clear
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    subparsers.add_parser("ingest", help="Ingest Cricsheet data into stats database")

    # Info command
    subparsers.add_parser("info", help="Show database statistics")

    # Matchup command
    matchup_parser = subparsers.add_parser("matchup", help="Query batter vs bowler matchup")
    matchup_parser.add_argument("batter", help="Batter name")
    matchup_parser.add_argument("bowler", help="Bowler name")

    # Player command
    player_parser = subparsers.add_parser("player", help="Show player matchup stats")
    player_parser.add_argument("name", help="Player name")
    player_parser.add_argument("--bowler", action="store_true", help="Show as bowler (default: batter)")

    # Phase command
    phase_parser = subparsers.add_parser("phase", help="Query phase-based stats")
    phase_parser.add_argument("player", help="Player name")
    phase_parser.add_argument(
        "phase",
        choices=["powerplay", "middle", "death", "session1", "session2", "session3"],
        help="Match phase",
    )
    phase_parser.add_argument("--format", dest="match_format", help="Match format (T20, ODI, Test)")
    phase_parser.add_argument("--bowler", action="store_true", help="Query as bowler (default: batter)")

    # Form command
    form_parser = subparsers.add_parser("form", help="Query recent form (last 5 matches)")
    form_parser.add_argument("player", help="Player name")
    form_parser.add_argument("--bowler", action="store_true", help="Query as bowler (default: batter)")

    # Clear command
    subparsers.add_parser("clear", help="Clear all data from database")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config = StatsConfig.from_env()

    if args.command == "ingest":
        ingest_all(config)
    elif args.command == "info":
        show_info(config)
    elif args.command == "matchup":
        query_matchup(config, args.batter, args.bowler)
    elif args.command == "player":
        query_player(config, args.name, as_batter=not args.bowler)
    elif args.command == "phase":
        query_phase(config, args.player, args.phase, args.match_format, args.bowler)
    elif args.command == "form":
        query_form(config, args.player, args.bowler)
    elif args.command == "clear":
        clear_database(config)


if __name__ == "__main__":
    main()
