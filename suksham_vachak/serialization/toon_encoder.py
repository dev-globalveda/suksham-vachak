"""TOON encoder for cricket context data.

TOON (Token-Oriented Object Notation) provides ~50% token savings
compared to plain text when passing cricket context to LLMs.

Since the toon-format library's encoder is not yet implemented,
we provide a custom implementation following TOON principles:
- Short keys for token efficiency
- No quotes around simple strings
- Compact nested structure with indentation
- Arrays with length prefix
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from suksham_vachak.context.models import RichContext

# Schema explanation for system prompt - helps LLM understand TOON format
CRICKET_TOON_SCHEMA = """
TOON Format Schema (Token-Oriented Object Notation):
- Fields use short keys: M=match, B=batter, W=bowler, P=partnership
- Arrays use [N] length prefix
- Nested objects use indentation
- Values are unquoted unless containing special characters

Example:
M
  teams [2] India, Australia
  score 145/3
  overs 23.4
  phase middle
B
  name V Kohli
  runs 52
  balls 45
  SR 115.6
"""


def _format_overs(overs: float) -> str:
    """Format overs as string (e.g., 23.4)."""
    whole = int(overs)
    balls = round((overs - whole) * 10)
    if balls == 0:
        return str(whole)
    return f"{whole}.{balls}"


def _needs_quoting(s: str) -> bool:
    """Check if a string value needs quoting in TOON format."""
    if not s:
        return True
    # Quote if contains special characters that could confuse parsing
    special_chars = {"\n", "\t", ":", "[", "]", "{", "}", ",", '"', "'"}
    return any(c in s for c in special_chars) or s.startswith(" ") or s.endswith(" ")


def _format_value(value: Any) -> str:
    """Format a primitive value for TOON output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    # String
    s = str(value)
    if _needs_quoting(s):
        # Escape quotes and wrap
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _encode_dict(data: dict[str, Any], indent: int = 0) -> str:
    """Encode a dictionary to TOON format."""
    lines: list[str] = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_encode_dict(value, indent + 1))  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}[0]:")
            elif all(isinstance(item, dict) for item in value):  # pyright: ignore[reportUnknownVariableType]
                # List of objects
                lines.append(f"{prefix}{key}[{len(value)}]:")  # pyright: ignore[reportUnknownArgumentType]
                for item in value:  # pyright: ignore[reportUnknownVariableType]
                    lines.append(_encode_dict(item, indent + 1))  # pyright: ignore[reportUnknownArgumentType]
            else:
                # Simple list of values
                formatted_items = ", ".join(_format_value(item) for item in value)  # pyright: ignore[reportUnknownVariableType]
                lines.append(f"{prefix}{key}[{len(value)}]: {formatted_items}")  # pyright: ignore[reportUnknownArgumentType]
        else:
            lines.append(f"{prefix}{key}: {_format_value(value)}")

    return "\n".join(lines)


def encode(data: dict[str, Any]) -> str:
    """Encode a dictionary to TOON format.

    Custom implementation following TOON principles since the
    toon-format library's encoder is not yet implemented.

    Args:
        data: Dictionary to encode

    Returns:
        TOON-formatted string
    """
    return _encode_dict(data)


def decode(toon_str: str) -> dict[str, Any]:
    """Decode a TOON string back to a dictionary.

    Basic implementation for testing purposes.

    Args:
        toon_str: TOON-formatted string

    Returns:
        Decoded dictionary
    """
    result: dict[str, Any] = {}
    stack: list[tuple[dict[str, Any], int]] = [(result, -1)]
    current_dict = result

    for line in toon_str.split("\n"):
        if not line.strip():
            continue

        # Calculate indent level
        stripped = line.lstrip()
        indent = (len(line) - len(stripped)) // 2

        # Pop stack if indent decreased
        while stack and indent <= stack[-1][1]:
            stack.pop()
            if stack:
                current_dict, _ = stack[-1]

        # Parse the line
        if ":" in stripped:
            # Check for array notation
            if "[" in stripped and "]:" in stripped:
                # Array line: key[N]: values or key[N]:
                bracket_start = stripped.index("[")
                bracket_end = stripped.index("]")
                key = stripped[:bracket_start]
                # Note: count is parsed but not used (arrays populate from child lines)
                _ = int(stripped[bracket_start + 1 : bracket_end])
                rest = stripped[bracket_end + 2 :].strip()  # After ']:' or ']: '

                if rest:
                    # Simple array with inline values
                    values = [_parse_value(v.strip()) for v in rest.split(",")]
                    current_dict[key] = values
                else:
                    # Array of objects (will be populated by child lines)
                    current_dict[key] = []
            elif stripped.endswith(":"):
                # Nested object
                key = stripped[:-1].strip()
                new_dict: dict[str, Any] = {}
                current_dict[key] = new_dict
                stack.append((new_dict, indent))
                current_dict = new_dict
            else:
                # Key-value pair
                colon_pos = stripped.index(":")
                key = stripped[:colon_pos].strip()
                value_str = stripped[colon_pos + 1 :].strip()
                current_dict[key] = _parse_value(value_str)

    return result


def _parse_value(value_str: str) -> Any:
    """Parse a TOON value string to Python type."""
    if not value_str:
        return ""
    if value_str == "null":
        return None
    if value_str == "true":
        return True
    if value_str == "false":
        return False
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1].replace('\\"', '"')
    # Try numeric
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        return value_str


def _build_context_dict(ctx: RichContext) -> dict[str, Any]:
    """Build the dictionary structure for TOON encoding.

    Uses short keys for token efficiency:
    - M: Match situation
    - E: Event (current ball)
    - B: Batter context
    - W: Bowler (wicket-taker) context
    - P: Pressure
    - N: Narrative state
    """
    data: dict[str, Any] = {
        "M": {  # Match
            "teams": [ctx.match.batting_team, ctx.match.bowling_team],
            "score": f"{ctx.match.total_runs}/{ctx.match.total_wickets}",
            "overs": _format_overs(ctx.match.overs_completed),
            "phase": ctx.match.phase.value,
            "CRR": round(ctx.match.current_run_rate, 2),
        },
        "E": {  # Event
            "type": ctx.event.event_type.value,
            "ball": ctx.event.ball_number,
            "batter": ctx.event.batter,
            "bowler": ctx.event.bowler,
            "runs": ctx.event.runs_total,
        },
        "B": {  # Batter context
            "name": ctx.batter.name,
            "runs": ctx.batter.runs_scored,
            "balls": ctx.batter.balls_faced,
            "SR": round(ctx.batter.strike_rate, 1),
            "4s": ctx.batter.fours,
            "6s": ctx.batter.sixes,
        },
        "W": {  # Bowler context
            "name": ctx.bowler.name,
            "overs": _format_overs(ctx.bowler.overs_bowled),
            "runs": ctx.bowler.runs_conceded,
            "wkts": ctx.bowler.wickets,
            "econ": round(ctx.bowler.economy, 2),
        },
        "P": {  # Pressure
            "level": ctx.pressure.value,
            "score": round(ctx.pressure_score, 2),
        },
        "N": {  # Narrative
            "story": ctx.narrative.current_storyline,
            "tension": round(ctx.narrative.tension_level, 2),
            "momentum": ctx.narrative.momentum.value,
        },
        "tone": ctx.suggested_tone,
        "length": ctx.suggested_length,
    }

    # Add optional fields only if present
    _add_chase_context(data, ctx)
    _add_event_and_player_extras(data, ctx)

    return data


def _add_chase_context(data: dict[str, Any], ctx: RichContext) -> None:
    """Add chase-related fields to match context if applicable."""
    if ctx.match.target is not None:
        data["M"]["target"] = ctx.match.target
    if ctx.match.required_rate is not None:
        data["M"]["RRR"] = round(ctx.match.required_rate, 2)
    if ctx.match.runs_required is not None:
        data["M"]["need"] = ctx.match.runs_required
    if ctx.match.balls_remaining is not None:
        data["M"]["balls_left"] = ctx.match.balls_remaining


def _add_event_and_player_extras(data: dict[str, Any], ctx: RichContext) -> None:
    """Add optional event, player, and narrative fields."""
    # Batter milestones
    if ctx.batter.approaching_milestone:
        data["B"]["milestone"] = ctx.batter.approaching_milestone

    # Wicket info
    if ctx.event.is_wicket:
        data["E"]["wicket"] = ctx.event.wicket_type or "out"
        if ctx.event.fielder:
            data["E"]["fielder"] = ctx.event.fielder

    # Bowler hat-trick
    if ctx.bowler.is_on_hat_trick:
        data["W"]["hat_trick"] = True

    # Narrative callbacks (limit to 3 for token efficiency)
    if ctx.narrative.callbacks_available:
        data["N"]["callbacks"] = ctx.narrative.callbacks_available[:3]

    # Partnership if significant
    if ctx.partnership.runs > 0:
        data["PR"] = {  # Partnership
            "runs": ctx.partnership.runs,
            "balls": ctx.partnership.balls,
        }


def encode_rich_context(ctx: RichContext) -> str:
    """Encode RichContext to TOON format for token-efficient LLM prompts.

    Args:
        ctx: The RichContext object containing full match situation

    Returns:
        TOON-formatted string (~50% fewer tokens than plain text)
    """
    data = _build_context_dict(ctx)
    return encode(data)
