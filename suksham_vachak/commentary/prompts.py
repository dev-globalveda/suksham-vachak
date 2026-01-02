"""Prompt templates for LLM-based commentary generation."""

from suksham_vachak.parser import CricketEvent, EventType
from suksham_vachak.personas import Persona

# System prompt template - establishes the commentator role
SYSTEM_PROMPT_TEMPLATE = """You are {name}, a legendary cricket commentator.

Your style: {style_description}

SIGNATURE PHRASES you use:
{signature_phrases}

CRITICAL WORD LIMIT RULES:
{word_limit_rules}

WHAT NOT TO DO:
- NEVER explain what happened. The audience can see the action.
- NEVER be verbose or use unnecessary words.
- NEVER start with "And" or "Well".
- NEVER describe the obvious.

BAD EXAMPLES (never do this):
{bad_examples}

GOOD EXAMPLES (do this):
{good_examples}

Remember: {key_reminder}"""

# Event prompt template - describes what happened
EVENT_PROMPT_TEMPLATE = """Match: {team1} vs {team2} at {venue}
Score: {score}/{wickets} ({overs} overs)
{chase_context}

Event: {event_description}

Your commentary{word_limit_reminder}:"""


def _get_word_limit_rules(persona: Persona) -> str:
    """Generate word limit rules based on minimalism score."""
    if persona.minimalism_score >= 0.9:
        return """- For wickets: 1-3 words MAXIMUM. Examples: "Gone.", "Bowled him."
- For sixes: 1-3 words MAXIMUM. Examples: "Magnificent.", "Six."
- For fours: 1-2 words MAXIMUM. Examples: "Four.", "Boundary."
- For dot balls: Stay SILENT (empty response) or 1 word maximum.
- For singles/doubles: Stay SILENT or 1 word maximum."""
    elif persona.minimalism_score >= 0.6:
        return """- For wickets: 1-8 words. Be concise but can add brief color.
- For sixes: 1-8 words. Can express measured excitement.
- For fours: 1-5 words.
- For dot balls: 0-3 words or silence.
- For singles: 0-3 words or silence."""
    else:
        return """- For wickets: 5-20 words. Describe the moment with feeling.
- For sixes: 5-20 words. Express the excitement fully.
- For fours: 3-15 words. Paint the picture.
- For dot balls: 0-10 words. Build the tension.
- For singles: 0-8 words. Keep the narrative flowing."""


def _get_bad_examples(persona: Persona) -> str:
    """Generate bad examples to avoid based on persona style."""
    if persona.is_minimalist:
        return """- "And the batsman has been clean bowled by an excellent delivery from the fast bowler!"
- "What a magnificent shot! The ball has sailed over the boundary for a maximum six runs!"
- "The batsman played forward but missed, and that's gone through to the keeper."
- "That's been dispatched to the boundary fence for four runs by the batsman.\""""
    else:
        return """- Single word responses like "Gone." (too brief for your style)
- Silence when something exciting happens
- Dry, emotionless descriptions"""


def _get_good_examples(persona: Persona, event_type: EventType | None = None) -> str:
    """Generate good examples based on persona."""
    phrases = persona.signature_phrases[:5] if persona.signature_phrases else []

    if persona.is_minimalist:
        examples = [
            '"Gone."',
            '"Magnificent."',
            '"Four."',
            '"Well played."',
            '""  (silence for dot balls)',
        ]
        if phrases:
            examples = [f'"{p}"' for p in phrases[:5]]
        return "\n".join(f"- {ex}" for ex in examples)
    else:
        return """- "What a moment this is! The crowd erupts!"
- "That's been timed to perfection, racing away to the boundary!"
- "He's taken him on and won that battle emphatically!\""""


def _get_style_description(persona: Persona) -> str:
    """Get a description of the persona's style."""
    style_map = {
        "minimalist": "Minimalist and elegant. Economy of words is your art. Silence speaks volumes.",
        "analytical": "Analytical and insightful. You explain the game with clarity and warmth.",
        "dramatic": "Dramatic and exuberant. You bring theater to cricket. Every moment is electric.",
        "philosophical": "Philosophical and mystical. You see deeper meaning in the game.",
        "technical": "Technical and precise. You focus on the craft and mechanics.",
    }
    return style_map.get(persona.style.value, "Professional and engaging.")


def _get_event_description(event: CricketEvent) -> str:
    """Generate a description of the cricket event."""
    if event.is_wicket:
        fielder_text = f" (caught by {event.fielder})" if event.fielder else ""
        return f"WICKET! {event.batter} is {event.wicket_type} by {event.bowler}{fielder_text}"

    if event.event_type == EventType.BOUNDARY_SIX:
        return f"SIX! {event.batter} hits {event.bowler} for a maximum"

    if event.event_type == EventType.BOUNDARY_FOUR:
        return f"FOUR! {event.batter} finds the boundary off {event.bowler}"

    if event.event_type == EventType.DOT_BALL:
        return f"Dot ball. {event.bowler} to {event.batter}, no run"

    if event.event_type in (EventType.SINGLE, EventType.DOUBLE, EventType.TRIPLE):
        runs = {EventType.SINGLE: 1, EventType.DOUBLE: 2, EventType.TRIPLE: 3}
        return f"{event.batter} takes {runs[event.event_type]} off {event.bowler}"

    if event.event_type == EventType.WIDE:
        return f"Wide ball from {event.bowler}"

    if event.event_type == EventType.NO_BALL:
        return f"No ball from {event.bowler}"

    return f"{event.batter} plays {event.bowler}"


def _get_chase_context(event: CricketEvent) -> str:
    """Get chase context if batting second."""
    ctx = event.match_context
    if ctx.target is not None:
        runs_needed = ctx.target - ctx.current_score
        return f"Chasing {ctx.target}. Need {runs_needed} more runs. RRR: {ctx.required_rate:.2f}"
    return ""


def _get_word_limit_reminder(persona: Persona, event: CricketEvent) -> str:
    """Get word limit reminder based on event type and persona."""
    if not persona.is_minimalist:
        return ""

    limits = {
        EventType.WICKET: " (1-3 words max)",
        EventType.BOUNDARY_SIX: " (1-3 words max)",
        EventType.BOUNDARY_FOUR: " (1-2 words max)",
        EventType.DOT_BALL: " (silence or 1 word)",
        EventType.SINGLE: " (silence or 1 word)",
        EventType.DOUBLE: " (silence or 1 word)",
        EventType.TRIPLE: " (1-2 words)",
    }
    return limits.get(event.event_type, "")


def build_system_prompt(persona: Persona) -> str:
    """Build the system prompt for a persona."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona.name,
        style_description=_get_style_description(persona),
        signature_phrases="\n".join(f'- "{p}"' for p in persona.signature_phrases[:8]),
        word_limit_rules=_get_word_limit_rules(persona),
        bad_examples=_get_bad_examples(persona),
        good_examples=_get_good_examples(persona),
        key_reminder="Brevity is your signature." if persona.is_minimalist else "Bring the excitement!",
    )


def build_event_prompt(event: CricketEvent, persona: Persona) -> str:
    """Build the user prompt for a specific event."""
    ctx = event.match_context
    return EVENT_PROMPT_TEMPLATE.format(
        team1=ctx.teams[0],
        team2=ctx.teams[1],
        venue=ctx.venue,
        score=ctx.current_score,
        wickets=ctx.current_wickets,
        overs=ctx.overs_completed,
        chase_context=_get_chase_context(event),
        event_description=_get_event_description(event),
        word_limit_reminder=_get_word_limit_reminder(persona, event),
    )
