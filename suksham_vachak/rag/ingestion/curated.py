"""Ingest curated iconic cricket moments.

Loads hand-curated iconic moments from YAML for high-quality
RAG retrieval. These moments have higher priority than
auto-indexed moments from Cricsheet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..models import CricketMoment, MomentSource, MomentType


class CuratedIngester:
    """Ingest hand-curated iconic cricket moments.

    Curated moments have higher retrieval priority than auto-indexed
    moments from Cricsheet data.
    """

    def __init__(self, file_path: str | Path | None = None) -> None:
        """Initialize ingester.

        Args:
            file_path: Path to curated moments YAML file.
        """
        self.file_path = Path(file_path) if file_path else Path("data/curated/iconic_moments.yaml")

    def ingest(self) -> list[CricketMoment]:
        """Load and parse curated moments from YAML."""
        if not self.file_path.exists():
            return []

        with open(self.file_path) as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        moments = []
        for entry in data.get("moments", []):
            moment = self._parse_moment(entry)
            moments.append(moment)

        return moments

    def _parse_moment(self, entry: dict[str, Any]) -> CricketMoment:
        """Parse a single curated moment entry."""
        # Map string type to enum
        type_str = entry.get("type", "iconic")
        try:
            moment_type = MomentType(type_str)
        except ValueError:
            moment_type = MomentType.ICONIC

        return CricketMoment(
            moment_id=f"curated_{entry['id']}",
            source=MomentSource.CURATED,
            priority=entry.get("priority", 2.0),  # Higher than auto-indexed
            match_id=entry.get("match_id", ""),
            match_format=entry.get("format", "ODI"),
            date=entry.get("date", ""),
            venue=entry.get("venue", ""),
            teams=(entry.get("team1", ""), entry.get("team2", "")),
            moment_type=moment_type,
            ball_number=entry.get("ball_number"),
            innings=entry.get("innings", 1),
            primary_player=entry["player"],
            secondary_player=entry.get("opponent"),
            score=entry.get("score", 0),
            wickets=entry.get("wickets", 0),
            overs=entry.get("overs", 0.0),
            phase=entry.get("phase", "middle"),
            pressure_level=entry.get("pressure", "high"),
            momentum=entry.get("momentum", "balanced"),
            target=entry.get("target"),
            runs_required=entry.get("runs_required"),
            description=entry["description"],
            significance=entry.get("significance", ""),
            embedding_text=entry.get("embedding_text", ""),
            tags=entry.get("tags", []),
        )
