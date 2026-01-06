"""CLI for stats ingestion and queries.

Usage:
    python -m suksham_vachak.stats.cli ingest
    python -m suksham_vachak.stats.cli info
    python -m suksham_vachak.stats.cli matchup "V Kohli" "JM Anderson"
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
    elif args.command == "clear":
        clear_database(config)


if __name__ == "__main__":
    main()
