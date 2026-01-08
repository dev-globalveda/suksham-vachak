"""Ingest cricket moments from Cricsheet match data.

Parses Cricsheet JSON files and extracts significant moments
(wickets, boundaries, milestones) for RAG retrieval.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from suksham_vachak.logging import get_logger
from suksham_vachak.parser.cricsheet import CricsheetParser
from suksham_vachak.parser.events import CricketEvent, EventType, MatchInfo

from ..models import CricketMoment, MomentSource, MomentType

logger = get_logger(__name__)


class CricsheetIngester:
    """Ingest significant moments from Cricsheet match files.

    Extracts:
    - All wickets
    - All boundaries (4s and 6s)
    - Milestones (50, 100, 150, 200)
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        """Initialize ingester.

        Args:
            data_dir: Directory containing Cricsheet JSON files.
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data/cricsheet_sample")

    def ingest_match(self, file_path: str | Path) -> list[CricketMoment]:
        """Ingest moments from a single match file."""
        parser = CricsheetParser(file_path)
        match_info = parser.match_info

        moments: list[CricketMoment] = []

        # Track state for milestone detection
        batter_runs: dict[str, int] = {}
        milestones_achieved: dict[str, set[int]] = {}

        for event in parser.parse_all_innings():
            # Track batter runs for milestones
            batter = event.batter
            if batter not in batter_runs:
                batter_runs[batter] = 0
                milestones_achieved[batter] = set()

            batter_runs[batter] += event.runs_batter

            # Check for significant moments
            if event.is_wicket:
                moment = self._create_wicket_moment(event, match_info)
                moments.append(moment)

            elif event.event_type == EventType.BOUNDARY_SIX:
                moment = self._create_boundary_moment(event, match_info, is_six=True)
                moments.append(moment)

            elif event.event_type == EventType.BOUNDARY_FOUR:
                moment = self._create_boundary_moment(event, match_info, is_six=False)
                moments.append(moment)

            # Check milestones
            for milestone in [50, 100, 150, 200]:
                if batter_runs[batter] >= milestone and milestone not in milestones_achieved[batter]:
                    milestones_achieved[batter].add(milestone)
                    moment = self._create_milestone_moment(event, match_info, batter_runs[batter], milestone)
                    moments.append(moment)

        return moments

    def ingest_all(self) -> Iterator[CricketMoment]:
        """Ingest moments from all matches in data directory."""
        for json_file in self.data_dir.glob("*.json"):
            try:
                moments = self.ingest_match(json_file)
                yield from moments
            except Exception as e:
                # Log error but continue with other files
                logger.warning("Error parsing match file", file=json_file.name, error=str(e))
                continue

    def _create_wicket_moment(
        self,
        event: CricketEvent,
        match_info: MatchInfo,
    ) -> CricketMoment:
        """Create a moment from a wicket event."""
        dismissed_player = event.wicket_player or event.batter
        description = f"{dismissed_player} dismissed {event.wicket_type} by {event.bowler}"
        if event.fielder:
            description += f" (c: {event.fielder})"

        return CricketMoment(
            moment_id=f"w_{match_info.match_id}_{event.event_id}",
            source=MomentSource.CRICSHEET,
            priority=0.8,  # Base priority for auto-indexed
            match_id=match_info.match_id,
            match_format=match_info.format.value,
            date=match_info.dates[0] if match_info.dates else "",
            venue=match_info.venue,
            teams=match_info.teams,
            moment_type=MomentType.WICKET,
            ball_number=event.ball_number,
            innings=event.match_context.innings,
            primary_player=dismissed_player,
            secondary_player=event.bowler,
            fielder=event.fielder,
            score=event.match_context.current_score,
            wickets=event.match_context.current_wickets,
            overs=event.match_context.overs_completed,
            phase=self._detect_phase(event, match_info),
            pressure_level=self._estimate_pressure(event),
            target=event.match_context.target,
            runs_required=event.match_context.runs_required(),
            description=description,
            tags=[event.wicket_type or "dismissed", match_info.format.value.lower()],
        )

    def _create_boundary_moment(
        self,
        event: CricketEvent,
        match_info: MatchInfo,
        is_six: bool,
    ) -> CricketMoment:
        """Create a moment from a boundary."""
        description = f"{event.batter} hits {'six' if is_six else 'four'} off {event.bowler}"

        return CricketMoment(
            moment_id=f"b_{match_info.match_id}_{event.event_id}",
            source=MomentSource.CRICSHEET,
            priority=0.5 if is_six else 0.3,  # Sixes more memorable
            match_id=match_info.match_id,
            match_format=match_info.format.value,
            date=match_info.dates[0] if match_info.dates else "",
            venue=match_info.venue,
            teams=match_info.teams,
            moment_type=MomentType.BOUNDARY_SIX if is_six else MomentType.BOUNDARY_FOUR,
            ball_number=event.ball_number,
            innings=event.match_context.innings,
            primary_player=event.batter,
            secondary_player=event.bowler,
            score=event.match_context.current_score,
            wickets=event.match_context.current_wickets,
            overs=event.match_context.overs_completed,
            phase=self._detect_phase(event, match_info),
            target=event.match_context.target,
            description=description,
            tags=["six" if is_six else "four", match_info.format.value.lower()],
        )

    def _create_milestone_moment(
        self,
        event: CricketEvent,
        match_info: MatchInfo,
        current_runs: int,
        milestone: int,
    ) -> CricketMoment:
        """Create a moment for a batting milestone."""
        opponent = match_info.teams[1] if event.match_context.innings == 1 else match_info.teams[0]
        description = f"{event.batter} reaches {milestone} against {opponent}"

        priority_map = {50: 0.7, 100: 0.9, 150: 0.85, 200: 0.95}

        return CricketMoment(
            moment_id=f"m_{match_info.match_id}_{event.event_id}_{milestone}",
            source=MomentSource.CRICSHEET,
            priority=priority_map.get(milestone, 0.7),
            match_id=match_info.match_id,
            match_format=match_info.format.value,
            date=match_info.dates[0] if match_info.dates else "",
            venue=match_info.venue,
            teams=match_info.teams,
            moment_type=MomentType.MILESTONE,
            ball_number=event.ball_number,
            innings=event.match_context.innings,
            primary_player=event.batter,
            score=event.match_context.current_score,
            wickets=event.match_context.current_wickets,
            overs=event.match_context.overs_completed,
            phase=self._detect_phase(event, match_info),
            target=event.match_context.target,
            description=description,
            significance=f"{milestone} runs milestone",
            tags=["milestone", str(milestone), match_info.format.value.lower()],
        )

    def _detect_phase(self, event: CricketEvent, match_info: MatchInfo) -> str:
        """Detect match phase from overs."""
        overs = event.match_context.overs_completed
        format_type = match_info.format.value.lower()

        if format_type in ("t20", "t20i"):
            if overs <= 6:
                return "powerplay"
            elif overs <= 15:
                return "middle"
            else:
                return "death"
        elif format_type == "odi":
            if overs <= 10:
                return "powerplay"
            elif overs <= 40:
                return "middle"
            else:
                return "death"
        else:  # Test
            if overs <= 30:
                return "early"
            elif overs <= 60:
                return "middle"
            else:
                return "late"

    def _estimate_pressure(self, event: CricketEvent) -> str:
        """Estimate pressure level from context."""
        ctx = event.match_context

        # Chase scenario
        if ctx.target and ctx.required_rate:
            if ctx.required_rate > 12:
                return "critical"
            elif ctx.required_rate > 8:
                return "high"

        # Wicket situation
        if ctx.current_wickets >= 7:
            return "high"
        elif ctx.current_wickets >= 5:
            return "medium"

        return "medium"
