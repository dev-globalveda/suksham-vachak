"""Parser for Cricsheet JSON match data."""

import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from suksham_vachak.logging import get_logger

from .events import CricketEvent, EventType, MatchContext, MatchFormat, MatchInfo

logger = get_logger(__name__)


def _parse_match_format(match_type: str) -> MatchFormat:
    """Convert Cricsheet match_type string to MatchFormat enum."""
    mapping = {
        "Test": MatchFormat.TEST,
        "ODI": MatchFormat.ODI,
        "T20": MatchFormat.T20,
        "IT20": MatchFormat.T20I,
        "T20I": MatchFormat.T20I,
    }
    return mapping.get(match_type, MatchFormat.T20)


def _get_extras_event_type(extras_type: str | None) -> EventType | None:
    """Get event type for extras, if applicable."""
    if extras_type is None:
        return None
    mapping: dict[str, EventType] = {
        "wide": EventType.WIDE,
        "noball": EventType.NO_BALL,
        "bye": EventType.BYE,
        "legbye": EventType.LEG_BYE,
    }
    return mapping.get(extras_type)


def _get_runs_event_type(runs_batter: int) -> EventType:
    """Get event type based on runs scored by batter."""
    mapping: dict[int, EventType] = {
        6: EventType.BOUNDARY_SIX,
        4: EventType.BOUNDARY_FOUR,
        3: EventType.TRIPLE,
        2: EventType.DOUBLE,
        1: EventType.SINGLE,
    }
    return mapping.get(runs_batter, EventType.DOT_BALL)


def _determine_event_type(
    runs_batter: int,
    is_wicket: bool,
    extras_type: str | None,
) -> EventType:
    """Determine the event type from delivery data."""
    if is_wicket:
        return EventType.WICKET

    extras_event = _get_extras_event_type(extras_type)
    if extras_event is not None:
        return extras_event

    return _get_runs_event_type(runs_batter)


def _parse_extras_type(extras_dict: dict[str, Any]) -> str | None:
    """Parse the extras type from a delivery's extras dictionary."""
    extras_keys = ["wides", "noballs", "byes", "legbyes"]
    key_to_type = {"wides": "wide", "noballs": "noball", "byes": "bye", "legbyes": "legbye"}
    for key in extras_keys:
        if key in extras_dict:
            return key_to_type[key]
    return None


def _parse_wicket_info(wickets: list[dict[str, Any]]) -> tuple[str | None, str | None, str | None]:
    """Parse wicket information from delivery data.

    Returns:
        Tuple of (wicket_type, wicket_player, fielder).
    """
    if not wickets:
        return None, None, None

    wicket_data = wickets[0]
    wicket_type: str | None = wicket_data.get("kind")
    wicket_player: str | None = wicket_data.get("player_out")
    fielder: str | None = None

    fielders = wicket_data.get("fielders", [])
    if fielders:
        fielder = fielders[0].get("name")

    return wicket_type, wicket_player, fielder


class CricsheetParser:
    """Parser for Cricsheet JSON format cricket match data."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize parser with path to JSON file.

        Args:
            file_path: Path to the Cricsheet JSON file.
        """
        self.file_path = Path(file_path)
        self._data: dict[str, Any] | None = None
        self._match_info: MatchInfo | None = None

    def _load(self) -> dict[str, Any]:
        """Load and cache the JSON data."""
        data = self._data
        if data is None:
            with open(self.file_path) as f:
                data = json.load(f)
            self._data = data
        return data

    @property
    def match_info(self) -> MatchInfo:
        """Get match metadata."""
        if self._match_info is not None:
            return self._match_info

        data = self._load()
        info: dict[str, Any] = data["info"]

        teams_list: list[str] = info["teams"]
        outcome: dict[str, Any] = info.get("outcome", {})
        by_info: dict[str, Any] = outcome.get("by", {})
        toss: dict[str, Any] = info.get("toss", {})

        self._match_info = MatchInfo(
            match_id=self.file_path.stem,
            teams=(teams_list[0], teams_list[1]),
            venue=str(info.get("venue", "Unknown")),
            city=info.get("city"),
            dates=info.get("dates", []),
            format=_parse_match_format(str(info.get("match_type", "T20"))),
            gender=str(info.get("gender", "male")),
            toss_winner=str(toss.get("winner", "")),
            toss_decision=str(toss.get("decision", "")),
            outcome_winner=outcome.get("winner"),
            outcome_by_runs=by_info.get("runs"),
            outcome_by_wickets=by_info.get("wickets"),
            player_of_match=info.get("player_of_match"),
            players=info.get("players", {}),
        )
        return self._match_info

    def _calculate_first_innings_total(self, data: dict[str, Any]) -> int:
        """Calculate total runs from first innings."""
        first_innings: dict[str, Any] = data["innings"][0]
        overs: list[dict[str, Any]] = first_innings.get("overs", [])
        total = 0
        for over in overs:
            deliveries: list[dict[str, Any]] = over.get("deliveries", [])
            for delivery in deliveries:
                runs: dict[str, Any] = delivery.get("runs", {})
                total += int(runs.get("total", 0))
        return total

    def _build_match_context(
        self,
        info: MatchInfo,
        innings_number: int,
        current_score: int,
        current_wickets: int,
        over_num: int,
        ball_in_over: int,
        target: int | None,
    ) -> MatchContext:
        """Build a MatchContext for a delivery."""
        overs_completed = over_num + (ball_in_over / 10)
        balls_bowled = over_num * 6 + ball_in_over
        current_rate = (current_score / balls_bowled * 6) if balls_bowled > 0 else 0.0

        required_rate: float | None = None
        if target is not None:
            runs_needed = target - current_score
            total_balls = 120 if info.format in (MatchFormat.T20, MatchFormat.T20I) else 300
            balls_remaining = total_balls - balls_bowled
            if balls_remaining > 0:
                required_rate = runs_needed / balls_remaining * 6

        return MatchContext(
            match_id=info.match_id,
            teams=info.teams,
            venue=info.venue,
            date=info.dates[0] if info.dates else "",
            format=info.format,
            innings=innings_number,
            current_score=current_score,
            current_wickets=current_wickets,
            overs_completed=overs_completed,
            target=target,
            required_rate=required_rate,
            current_rate=current_rate,
        )

    def parse_innings(self, innings_number: int = 1) -> Iterator[CricketEvent]:
        """Parse a specific innings and yield CricketEvent objects.

        Args:
            innings_number: 1-indexed innings number (1, 2, 3, 4 for Tests).

        Yields:
            CricketEvent objects for each delivery.
        """
        data = self._load()
        info = self.match_info
        innings_list: list[dict[str, Any]] = data.get("innings", [])

        if innings_number < 1 or innings_number > len(innings_list):
            return

        innings_data = innings_list[innings_number - 1]
        target = self._calculate_first_innings_total(data) + 1 if innings_number == 2 else None

        current_score = 0
        current_wickets = 0

        overs: list[dict[str, Any]] = innings_data.get("overs", [])
        for over_data in overs:
            over_num: int = over_data["over"]
            deliveries: list[dict[str, Any]] = over_data.get("deliveries", [])

            for ball_idx, delivery in enumerate(deliveries, start=1):
                runs_data: dict[str, Any] = delivery.get("runs", {})
                runs_batter = int(runs_data.get("batter", 0))
                runs_extras = int(runs_data.get("extras", 0))
                runs_total = int(runs_data.get("total", 0))

                extras_dict: dict[str, Any] = delivery.get("extras", {})
                extras_type = _parse_extras_type(extras_dict)

                wickets: list[dict[str, Any]] = delivery.get("wickets", [])
                is_wicket = len(wickets) > 0
                wicket_type, wicket_player, fielder = _parse_wicket_info(wickets)

                current_score += runs_total
                if is_wicket:
                    current_wickets += 1

                match_context = self._build_match_context(
                    info,
                    innings_number,
                    current_score,
                    current_wickets,
                    over_num,
                    ball_idx,
                    target,
                )

                event = CricketEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=_determine_event_type(runs_batter, is_wicket, extras_type),
                    ball_number=f"{over_num}.{ball_idx}",
                    batter=str(delivery.get("batter", "")),
                    bowler=str(delivery.get("bowler", "")),
                    non_striker=str(delivery.get("non_striker", "")),
                    runs_batter=runs_batter,
                    runs_extras=runs_extras,
                    runs_total=runs_total,
                    is_boundary=runs_batter in (4, 6),
                    is_wicket=is_wicket,
                    match_context=match_context,
                    wicket_type=wicket_type,
                    wicket_player=wicket_player,
                    fielder=fielder,
                    extras_type=extras_type,
                )

                yield event

    def parse_all_innings(self) -> Iterator[CricketEvent]:
        """Parse all innings in the match.

        Yields:
            CricketEvent objects for each delivery across all innings.
        """
        data = self._load()
        innings_list: list[dict[str, Any]] = data.get("innings", [])
        num_innings = len(innings_list)

        for innings_num in range(1, num_innings + 1):
            yield from self.parse_innings(innings_num)

    def get_key_moments(self, innings_number: int = 1) -> list[CricketEvent]:
        """Get key moments (wickets, boundaries, milestones) from an innings.

        Args:
            innings_number: 1-indexed innings number.

        Returns:
            List of significant CricketEvent objects.
        """
        key_events: list[CricketEvent] = []
        for event in self.parse_innings(innings_number):
            is_milestone = event.match_context.current_score > 0 and event.match_context.current_score % 50 == 0
            if event.is_wicket or event.is_boundary or is_milestone:
                key_events.append(event)

        return key_events
