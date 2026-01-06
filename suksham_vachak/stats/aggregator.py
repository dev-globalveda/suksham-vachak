"""Aggregate matchup statistics from Cricsheet data."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from suksham_vachak.parser.cricsheet import CricsheetParser
from suksham_vachak.parser.events import CricketEvent, EventType

from .models import MatchupRecord
from .normalize import normalize_display_name, normalize_player_id


class MatchupAccumulator:
    """Accumulate per-ball stats into matchup records for a single match."""

    def __init__(self, match_id: str, match_date: str, match_format: str, venue: str) -> None:
        self.match_id = match_id
        self.match_date = match_date
        self.match_format = match_format
        self.venue = venue

        # Key: (batter_id, bowler_id) -> accumulated stats
        self._data: dict[tuple[str, str], dict] = defaultdict(
            lambda: {
                "batter_name": "",
                "bowler_name": "",
                "balls_faced": 0,
                "runs_scored": 0,
                "dots": 0,
                "fours": 0,
                "sixes": 0,
                "dismissals": 0,
                "dismissal_type": None,
            }
        )

    def add_delivery(self, event: CricketEvent) -> None:
        """Add a delivery to the accumulator."""
        batter_id = normalize_player_id(event.batter)
        bowler_id = normalize_player_id(event.bowler)
        key = (batter_id, bowler_id)

        stats = self._data[key]
        stats["batter_name"] = normalize_display_name(event.batter)
        stats["bowler_name"] = normalize_display_name(event.bowler)

        # Count legal deliveries (not wides)
        if event.extras_type != "wide":
            stats["balls_faced"] += 1

        # Count runs off bat (not extras)
        stats["runs_scored"] += event.runs_batter

        # Count dot balls
        if event.runs_batter == 0 and event.extras_type != "wide":
            stats["dots"] += 1

        # Count boundaries
        if event.event_type == EventType.BOUNDARY_FOUR:
            stats["fours"] += 1
        elif event.event_type == EventType.BOUNDARY_SIX:
            stats["sixes"] += 1

        # Count dismissals by this bowler
        if event.is_wicket:
            # Only count if bowler is credited (not run out, obstructing field, etc.)
            bowler_dismissals = {"bowled", "caught", "lbw", "stumped", "caught and bowled", "hit wicket"}
            if event.wicket_type and event.wicket_type.lower() in bowler_dismissals:
                stats["dismissals"] += 1
                stats["dismissal_type"] = event.wicket_type

    def get_records(self) -> list[MatchupRecord]:
        """Generate matchup records from accumulated data."""
        records = []
        for (batter_id, bowler_id), stats in self._data.items():
            if stats["balls_faced"] > 0:  # Only include if faced at least one ball
                records.append(
                    MatchupRecord(
                        batter_id=batter_id,
                        batter_name=stats["batter_name"],
                        bowler_id=bowler_id,
                        bowler_name=stats["bowler_name"],
                        match_id=self.match_id,
                        match_date=self.match_date,
                        match_format=self.match_format,
                        venue=self.venue,
                        balls_faced=stats["balls_faced"],
                        runs_scored=stats["runs_scored"],
                        dots=stats["dots"],
                        fours=stats["fours"],
                        sixes=stats["sixes"],
                        dismissals=stats["dismissals"],
                        dismissal_type=stats["dismissal_type"],
                    )
                )
        return records


class StatsAggregator:
    """Aggregate matchup statistics from Cricsheet data directory."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        """Initialize aggregator.

        Args:
            data_dir: Directory containing Cricsheet JSON files.
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data/cricsheet_sample")

    def process_match(self, file_path: str | Path) -> list[MatchupRecord]:
        """Process a single match file and return matchup records."""
        parser = CricsheetParser(file_path)
        match_info = parser.match_info

        accumulator = MatchupAccumulator(
            match_id=match_info.match_id,
            match_date=match_info.dates[0] if match_info.dates else "",
            match_format=match_info.format.value,
            venue=match_info.venue,
        )

        for event in parser.parse_all_innings():
            accumulator.add_delivery(event)

        return accumulator.get_records()

    def process_all(self) -> Iterator[list[MatchupRecord]]:
        """Process all match files and yield batches of matchup records.

        Yields:
            List of MatchupRecord for each match.
        """
        for json_file in self.data_dir.glob("*.json"):
            try:
                records = self.process_match(json_file)
                if records:
                    yield records
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue

    def count_matches(self) -> int:
        """Count total match files in data directory."""
        return len(list(self.data_dir.glob("*.json")))
