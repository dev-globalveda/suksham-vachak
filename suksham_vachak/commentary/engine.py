"""Commentary engine for generating cricket commentary."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from suksham_vachak.logging import get_logger
from suksham_vachak.parser import CricketEvent, EventType
from suksham_vachak.personas import Persona

from .prompts import build_event_prompt, build_rich_context_prompt, build_system_prompt
from .providers import BaseLLMProvider, LLMResponse, create_llm_provider

logger = get_logger(__name__)

if TYPE_CHECKING:
    from suksham_vachak.context import ContextBuilder, RichContext


@dataclass
class Commentary:
    """Generated commentary for a cricket event."""

    text: str
    event: CricketEvent
    persona: Persona
    language: str = "en"
    used_llm: bool = False
    llm_response: LLMResponse | None = None
    rich_context: RichContext | None = None  # Enhanced context when available


@dataclass
class WordLimits:
    """Word limits for different event types based on minimalism."""

    wicket: int = 3
    boundary: int = 3
    dot_ball: int = 1
    single: int = 1
    other: int = 2


# Word limits for high-minimalism personas (like Benaud)
MINIMALIST_LIMITS = WordLimits(wicket=3, boundary=3, dot_ball=1, single=1, other=2)

# Word limits for verbose personas
VERBOSE_LIMITS = WordLimits(wicket=25, boundary=20, dot_ball=10, single=8, other=15)


def _get_word_limit(event: CricketEvent, persona: Persona) -> int:
    """Get the word limit for an event based on persona's minimalism."""
    limits = MINIMALIST_LIMITS if persona.is_minimalist else VERBOSE_LIMITS

    if event.event_type == EventType.WICKET:
        return limits.wicket
    if event.event_type in (EventType.BOUNDARY_FOUR, EventType.BOUNDARY_SIX):
        return limits.boundary
    if event.event_type == EventType.DOT_BALL:
        return limits.dot_ball
    if event.event_type in (EventType.SINGLE, EventType.DOUBLE, EventType.TRIPLE):
        return limits.single
    return limits.other


def _enforce_word_limit(text: str, limit: int) -> str:
    """Enforce word limit on generated text.

    For minimalist personas, truncate to the limit.
    This is a safety net - the LLM should already be brief.
    """
    if not text:
        return text

    words = text.split()
    if len(words) <= limit:
        return text

    # Truncate and add period if needed
    truncated = " ".join(words[:limit])
    if not truncated.endswith((".", "!", "?")):
        truncated += "."
    return truncated


class CommentaryEngine:
    """Engine for generating cricket commentary from events.

    Supports both template-based and LLM-based generation.
    The key principle: respect the persona's minimalism_score.
    Higher scores = fewer words. Benaud (0.95) gets "Gone.", not paragraphs.
    """

    # Verbose templates for low-minimalism personas
    VERBOSE_TEMPLATES: ClassVar[dict[EventType, list[str]]] = {
        EventType.WICKET: [
            "And that's the end of {batter}! {wicket_type} by {bowler}. What a moment!",
            "{batter} has to go! Caught {wicket_type} off {bowler}'s bowling.",
            "The batsman is OUT! {batter} falls to {bowler}.",
        ],
        EventType.BOUNDARY_FOUR: [
            "That's been dispatched to the boundary! Four runs for {batter}.",
            "Wonderful shot! {batter} finds the gap and it races away for four.",
            "FOUR! {batter} times that beautifully off {bowler}.",
        ],
        EventType.BOUNDARY_SIX: [
            "That's gone all the way! A massive six from {batter}!",
            "SIX! {batter} has launched {bowler} into the stands!",
            "Maximum! What a strike from {batter}!",
        ],
        EventType.DOT_BALL: [
            "Good delivery from {bowler}, no run.",
            "Dot ball. {bowler} keeps it tight.",
            "{batter} defends solidly.",
        ],
        EventType.SINGLE: [
            "Quick single taken by {batter}.",
            "They scamper through for one.",
            "Pushed into the gap for a single.",
        ],
        EventType.DOUBLE: [
            "Good running! They come back for two.",
            "Two runs, well run by the batsmen.",
        ],
        EventType.TRIPLE: [
            "Excellent running! They've taken three.",
            "Three runs, superb athleticism.",
        ],
        EventType.WIDE: [
            "That's called wide. Extra run to the batting side.",
            "Wide ball from {bowler}.",
        ],
        EventType.NO_BALL: [
            "No ball called! Free hit coming up.",
            "That's a no ball from {bowler}.",
        ],
        EventType.BYE: [
            "Byes taken there.",
            "The keeper can't gather it, bye runs.",
        ],
        EventType.LEG_BYE: [
            "Leg byes signaled by the umpire.",
            "Off the pads, leg bye.",
        ],
    }

    # Minimal templates for high-minimalism personas (Benaud-style)
    MINIMAL_TEMPLATES: ClassVar[dict[EventType, list[str]]] = {
        EventType.WICKET: ["Gone.", "Out.", "Bowled him."],
        EventType.BOUNDARY_FOUR: ["Four.", "Boundary."],
        EventType.BOUNDARY_SIX: ["Six.", "Magnificent.", "Maximum."],
        EventType.DOT_BALL: ["", ".", "No run."],  # Often silence
        EventType.SINGLE: ["One.", "Single."],
        EventType.DOUBLE: ["Two."],
        EventType.TRIPLE: ["Three."],
        EventType.WIDE: ["Wide."],
        EventType.NO_BALL: ["No ball."],
        EventType.BYE: ["Bye."],
        EventType.LEG_BYE: ["Leg bye."],
    }

    def __init__(
        self,
        default_language: str = "en",
        use_llm: bool = False,
        llm_client: BaseLLMProvider | None = None,
        llm_provider: str = "auto",
        context_builder: ContextBuilder | None = None,
    ) -> None:
        """Initialize the commentary engine.

        Args:
            default_language: Default language for commentary generation.
            use_llm: Whether to use LLM for generation. Falls back to templates if False.
            llm_client: Pre-configured LLM provider. If use_llm=True and not provided,
                        creates one based on llm_provider setting.
            llm_provider: Which LLM provider to use when auto-creating:
                         - "auto": Try Ollama first, fall back to Claude
                         - "ollama": Use local Ollama server
                         - "claude": Use Anthropic Claude API
            context_builder: Optional ContextBuilder for rich context generation.
                            When provided, LLM prompts include enhanced situational context.
        """
        self.default_language = default_language
        self.use_llm = use_llm
        self._llm_provider = llm_client
        self._llm_provider_name = llm_provider
        self.context_builder = context_builder

        # Cache system prompts per persona to avoid rebuilding
        self._system_prompt_cache: dict[str, str] = {}

    @property
    def llm_client(self) -> BaseLLMProvider | None:
        """Get or create the LLM provider.

        Uses auto-detection by default: tries Ollama first, falls back to Claude.
        """
        if self.use_llm and self._llm_provider is None:
            try:
                self._llm_provider = create_llm_provider(self._llm_provider_name)  # type: ignore[arg-type]
                logger.info(
                    "Created LLM provider",
                    provider=self._llm_provider.provider_name,
                    model=self._llm_provider.model_name,
                )
            except ValueError as e:
                logger.warning("Failed to create LLM provider, using templates", error=str(e))
                self.use_llm = False
                return None
        return self._llm_provider

    def generate(
        self,
        event: CricketEvent,
        persona: Persona,
        language: str | None = None,
    ) -> Commentary:
        """Generate commentary for a cricket event.

        Args:
            event: The cricket event to commentate on.
            persona: The persona to use for commentary style.
            language: Language code (defaults to engine's default).

        Returns:
            Commentary object with generated text.
        """
        lang = language or self.default_language
        log = logger.bind(
            event_id=event.event_id,
            event_type=event.event_type.value,
            persona=persona.name,
            language=lang,
        )

        # Build rich context if context builder is available
        rich_context: RichContext | None = None
        if self.context_builder is not None:
            rich_context = self.context_builder.build(event)
            log.debug("Built rich context for event")

        # Try LLM first if enabled
        if self.use_llm and self.llm_client is not None:
            log.debug("Generating commentary with LLM")
            return self._generate_with_llm(event, persona, lang, rich_context)

        # Fall back to template-based generation
        log.debug("Generating commentary with templates")
        return self._generate_with_templates(event, persona, lang, rich_context)

    def _generate_with_llm(
        self,
        event: CricketEvent,
        persona: Persona,
        language: str,
        rich_context: RichContext | None = None,
    ) -> Commentary:
        """Generate commentary using the LLM."""
        # Get or build system prompt (cached per persona)
        system_prompt = self._get_system_prompt(persona)

        # Build event-specific user prompt
        # Use rich context prompt if available, otherwise basic event prompt
        if rich_context is not None:
            user_prompt = build_rich_context_prompt(rich_context, persona)
        else:
            user_prompt = build_event_prompt(event, persona)

        # Determine max tokens based on minimalism
        max_tokens = 20 if persona.is_minimalist else 100

        # Call LLM (type guard - we checked use_llm and llm_client above)
        client = self.llm_client
        if client is None:
            return self._generate_with_templates(event, persona, language, rich_context)

        llm_response = client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )

        # Enforce word limit client-side as safety net
        word_limit = _get_word_limit(event, persona)
        text = _enforce_word_limit(llm_response.text, word_limit)

        # Track recently used phrases to avoid repetition
        if self.context_builder is not None and text:
            self.context_builder.add_phrase_to_avoid(text)

        return Commentary(
            text=text,
            event=event,
            persona=persona,
            language=language,
            used_llm=True,
            llm_response=llm_response,
            rich_context=rich_context,
        )

    def _get_system_prompt(self, persona: Persona) -> str:
        """Get cached system prompt for a persona."""
        if persona.name not in self._system_prompt_cache:
            self._system_prompt_cache[persona.name] = build_system_prompt(persona)
        return self._system_prompt_cache[persona.name]

    def _generate_with_templates(
        self,
        event: CricketEvent,
        persona: Persona,
        language: str,
        rich_context: RichContext | None = None,
    ) -> Commentary:
        """Generate commentary using templates."""
        # Check if persona has a direct emotion mapping for this event type
        text = self._get_persona_phrase(event, persona)

        if text is None:
            # Fall back to templates based on minimalism score
            text = self._get_template_commentary(event, persona)

        return Commentary(
            text=text,
            event=event,
            persona=persona,
            language=language,
            used_llm=False,
            llm_response=None,
            rich_context=rich_context,
        )

    def _get_persona_phrase(self, event: CricketEvent, persona: Persona) -> str | None:
        """Get a direct phrase from persona's emotion_range if available."""
        emotion_key = self._event_to_emotion(event)
        phrase = persona.get_phrase_for_emotion(emotion_key)

        # Return the phrase if it exists (even empty string for silence)
        if phrase is not None:
            return phrase

        return None

    def _event_to_emotion(self, event: CricketEvent) -> str:
        """Map event type to emotion key for persona lookup."""
        mapping: dict[EventType, str] = {
            EventType.WICKET: "wicket",
            EventType.BOUNDARY_FOUR: "boundary_four",
            EventType.BOUNDARY_SIX: "boundary_six",
            EventType.DOT_BALL: "dot_ball",
            EventType.SINGLE: "single",
            EventType.DOUBLE: "single",  # Same as single
            EventType.TRIPLE: "single",
            EventType.WIDE: "dot_ball",
            EventType.NO_BALL: "dot_ball",
            EventType.BYE: "single",
            EventType.LEG_BYE: "single",
        }
        return mapping.get(event.event_type, "neutral")

    def _get_template_commentary(self, event: CricketEvent, persona: Persona) -> str:
        """Get template-based commentary based on minimalism score."""
        if persona.is_minimalist:
            templates = self.MINIMAL_TEMPLATES.get(event.event_type, [""])
        else:
            templates = self.VERBOSE_TEMPLATES.get(event.event_type, [""])

        template = random.choice(templates)  # noqa: S311
        return self._format_template(template, event)

    def _format_template(self, template: str, event: CricketEvent) -> str:
        """Format a template with event data."""
        if not template:
            return ""

        wicket_type = event.wicket_type or "dismissed"

        return template.format(
            batter=event.batter,
            bowler=event.bowler,
            non_striker=event.non_striker,
            runs=event.runs_total,
            wicket_type=wicket_type,
            fielder=event.fielder or "",
        )

    def generate_for_key_moments(
        self,
        events: list[CricketEvent],
        persona: Persona,
        language: str | None = None,
    ) -> list[Commentary]:
        """Generate commentary for a list of key moments.

        Args:
            events: List of cricket events (typically key moments).
            persona: The persona to use.
            language: Language code.

        Returns:
            List of Commentary objects.
        """
        return [self.generate(event, persona, language) for event in events]
