"""API routes for Suksham Vachak frontend."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from suksham_vachak.commentary import CommentaryEngine, OllamaProvider
from suksham_vachak.context import ContextBuilder
from suksham_vachak.logging import get_logger
from suksham_vachak.parser import CricsheetParser, EventType
from suksham_vachak.personas import BENAUD, DOSHI, GREIG
from suksham_vachak.tts import AudioFormat
from suksham_vachak.tts.prosody import ProsodyController

logger = get_logger(__name__)


def _check_llm_availability() -> dict[str, bool]:
    """Check which LLM providers are available."""
    availability = {
        "claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "ollama": False,
    }

    # Check if Ollama is running
    try:
        ollama = OllamaProvider()
        availability["ollama"] = ollama.is_available()
    except Exception as e:
        logger.debug("Ollama availability check failed", error=str(e))

    return availability


# Check LLM availability at startup
LLM_AVAILABILITY = _check_llm_availability()
LLM_AVAILABLE = LLM_AVAILABILITY["claude"] or LLM_AVAILABILITY["ollama"]

router = APIRouter(prefix="/api", tags=["api"])

# Data directory
DATA_DIR = Path("data/cricsheet_sample")

# Persona registry
PERSONAS = {
    "benaud": BENAUD,
    "greig": GREIG,
    "doshi": DOSHI,
}

PERSONA_INFO = {
    "benaud": {
        "id": "benaud",
        "name": "Richie Benaud",
        "tagline": "The Master of Silence",
        "style": "Minimalist",
        "accent": "Australian",
        "language": "en",
        "description": "Less is more. Let the pictures tell the story.",
        "color": "#F5F5DC",  # Cream/beige - elegant
        "accentColor": "#8B7355",  # Warm brown
    },
    "greig": {
        "id": "greig",
        "name": "Tony Greig",
        "tagline": "The Showman",
        "style": "Dramatic",
        "accent": "British",
        "language": "en",
        "description": "Every ball is an event. Every wicket is theatre.",
        "color": "#DC143C",  # Crimson - bold
        "accentColor": "#FFFFFF",  # White
    },
    "doshi": {
        "id": "doshi",
        "name": "Sushil Doshi",
        "tagline": "हिंदी की आवाज़",
        "style": "Passionate",
        "accent": "Hindi",
        "language": "hi",
        "description": "The voice of Hindi cricket. Emotion in every word.",
        "color": "#FF9933",  # Saffron - warm
        "accentColor": "#138808",  # Green
    },
}


class CommentaryRequest(BaseModel):
    """Request for commentary generation."""

    match_id: str
    ball_number: str
    persona_id: str
    language: str = "en"  # "en" or "hi"
    use_llm: bool = True  # Use LLM for generation (falls back to templates if unavailable)
    llm_provider: str = "auto"  # "auto", "claude", or "ollama"


class CommentaryResponse(BaseModel):
    """Response with generated commentary."""

    text: str
    audio_base64: str | None
    audio_format: str
    persona_id: str
    event_type: str
    duration_seconds: float


@router.get("/matches")
async def list_matches() -> list[dict[str, Any]]:
    """List all available matches."""
    matches = []

    for json_file in sorted(DATA_DIR.glob("*.json")):
        try:
            parser = CricsheetParser(json_file)
            info = parser.match_info

            matches.append({
                "id": info.match_id,
                "teams": list(info.teams),
                "date": info.dates[0] if info.dates else "Unknown",
                "venue": info.venue or "Unknown",
                "format": info.format.value,
                "winner": info.outcome_winner,
                "file": json_file.name,
            })
        except Exception as e:
            logger.warning("Failed to parse match", file=json_file.name, error=str(e))
            continue

    return matches


@router.get("/matches/{match_id}")
async def get_match(match_id: str) -> dict[str, Any]:
    """Get match details."""
    json_file = DATA_DIR / f"{match_id}.json"

    if not json_file.exists():
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    parser = CricsheetParser(json_file)
    info = parser.match_info

    return {
        "id": info.match_id,
        "teams": list(info.teams),
        "date": info.dates[0] if info.dates else "Unknown",
        "venue": info.venue or "Unknown",
        "format": info.format.value,
        "winner": info.outcome_winner,
        "toss": {
            "winner": info.toss_winner,
            "decision": info.toss_decision,
        },
    }


@router.get("/matches/{match_id}/moments")
async def get_key_moments(match_id: str) -> list[dict[str, Any]]:
    """Get key moments (wickets, sixes, milestones) from a match."""
    json_file = DATA_DIR / f"{match_id}.json"

    if not json_file.exists():
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    parser = CricsheetParser(json_file)
    moments = []

    # Get key moments from both innings
    for innings_num in [1, 2]:
        try:
            key_events = parser.get_key_moments(innings_number=innings_num)

            for event in key_events:
                moment = {
                    "id": event.event_id,
                    "ball_number": event.ball_number,
                    "innings": innings_num,
                    "event_type": event.event_type.value,
                    "batter": event.batter,
                    "bowler": event.bowler,
                    "runs": event.runs_total,
                    "score": f"{event.match_context.current_score}/{event.match_context.current_wickets}",
                    "description": _get_moment_description(event),
                    "is_wicket": event.is_wicket,
                    "is_boundary": event.is_boundary,
                }

                if event.is_wicket:
                    moment["wicket_type"] = event.wicket_type
                    moment["fielder"] = event.fielder

                moments.append(moment)
        except Exception as e:
            logger.warning("Failed to get moments from innings", innings=innings_num, error=str(e))
            continue

    return moments


def _get_moment_description(event) -> str:
    """Generate a human-readable description of a moment."""
    if event.is_wicket:
        if event.wicket_type == "caught":
            return f"{event.batter} c {event.fielder} b {event.bowler}"
        elif event.wicket_type == "bowled":
            return f"{event.batter} b {event.bowler}"
        elif event.wicket_type == "lbw":
            return f"{event.batter} lbw b {event.bowler}"
        elif event.wicket_type == "run out":
            return f"{event.batter} run out ({event.fielder})"
        elif event.wicket_type == "stumped":
            return f"{event.batter} st {event.fielder} b {event.bowler}"
        else:
            return f"{event.batter} out ({event.wicket_type})"

    if event.event_type == EventType.BOUNDARY_SIX:
        return f"{event.batter} hits {event.bowler} for SIX!"

    if event.event_type == EventType.BOUNDARY_FOUR:
        return f"{event.batter} hits {event.bowler} for FOUR"

    return f"{event.batter} vs {event.bowler}"


@router.get("/personas")
async def list_personas() -> list[dict[str, Any]]:
    """List all available personas."""
    return list(PERSONA_INFO.values())


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str) -> dict[str, Any]:
    """Get persona details."""
    if persona_id not in PERSONA_INFO:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    return PERSONA_INFO[persona_id]


@router.post("/commentary", response_model=CommentaryResponse)
async def generate_commentary(request: CommentaryRequest) -> CommentaryResponse:  # noqa: C901
    """Generate commentary for a specific moment."""
    # Validate inputs
    json_file = DATA_DIR / f"{request.match_id}.json"
    if not json_file.exists():
        raise HTTPException(status_code=404, detail=f"Match {request.match_id} not found")

    if request.persona_id not in PERSONAS:
        raise HTTPException(status_code=404, detail=f"Persona {request.persona_id} not found")

    persona = PERSONAS[request.persona_id]

    # Find the specific event and build context
    parser = CricsheetParser(json_file)
    target_event = None
    target_innings = None

    for innings_num in [1, 2]:
        try:
            for event in parser.parse_innings(innings_number=innings_num):
                if event.ball_number == request.ball_number:
                    target_event = event
                    target_innings = innings_num
                    break
            if target_event:
                break
        except Exception as e:
            logger.warning("Failed to parse innings", innings=innings_num, error=str(e))
            continue

    if not target_event:
        raise HTTPException(status_code=404, detail=f"Ball {request.ball_number} not found in match {request.match_id}")

    # Build context by processing events up to the target
    context_builder = ContextBuilder(parser.match_info)

    # Process all events up to and including target to build proper context
    for event in parser.parse_innings(innings_number=target_innings):
        context_builder.build(event)
        if event.ball_number == request.ball_number:
            break

    # Determine if we should use LLM
    use_llm = request.use_llm and LLM_AVAILABLE

    # Generate commentary with context (supports auto-detection of Ollama/Claude)
    engine = CommentaryEngine(
        use_llm=use_llm,
        llm_provider=request.llm_provider,
        context_builder=context_builder,
    )
    commentary = engine.generate(target_event, persona)

    # Get the text - LLM generates in persona's language naturally
    text = commentary.text

    # Determine target language for TTS
    target_language = request.language

    # If LLM didn't generate text or LLM is disabled, use fallbacks
    if not text:
        emotion_key = _event_type_to_emotion(target_event.event_type)

        if target_language == "hi":
            hindi_phrases = {
                "wicket": "आउट! और गया!",
                "boundary_six": "छक्का! क्या मारा है!",
                "boundary_four": "चौका! शानदार शॉट!",
                "dot_ball": "",
                "single": "एक रन",
                "dramatic": "क्या बात है!",
            }
            text = hindi_phrases.get(emotion_key, "शानदार!")
        else:
            if persona.name == "Richie Benaud":
                english_fallbacks = {
                    "wicket": "Gone.",
                    "boundary_six": "That's huge.",
                    "boundary_four": "Lovely shot.",
                    "dramatic": "Marvellous.",
                }
            else:
                english_fallbacks = {
                    "wicket": "That's OUT! What a moment!",
                    "boundary_six": "That's gone all the way! SIX!",
                    "boundary_four": "FOUR! Cracking shot!",
                    "dramatic": "This is extraordinary!",
                }
            text = english_fallbacks.get(emotion_key, "What a delivery.")

    # Generate audio
    audio_base64 = None
    duration = 0.0

    try:
        if text:
            # Generate SSML
            controller = ProsodyController()
            ssml = controller.apply_prosody(text, persona, target_event.event_type)

            from suksham_vachak.tts.google import GoogleTTSProvider

            provider = GoogleTTSProvider()

            # Get voice based on persona AND target language
            voice_id = provider.get_voice_for_persona(persona.name, target_language)

            # Set language code
            if target_language == "hi":
                language_code = "hi-IN"
            else:
                # Use Australian accent for Benaud, British for Greig
                language_code = "en-AU" if persona.name == "Richie Benaud" else "en-GB"

            result = provider.synthesize(
                text=ssml, voice_id=voice_id, language=language_code, ssml=True, audio_format=AudioFormat.MP3
            )

            audio_base64 = base64.b64encode(result.audio_bytes).decode("utf-8")
            duration = result.duration_seconds or 0.0

    except Exception:
        # Audio generation failed, continue without audio
        logger.exception("Audio generation failed", persona=request.persona_id)

    return CommentaryResponse(
        text=text,
        audio_base64=audio_base64,
        audio_format="mp3",
        persona_id=request.persona_id,
        event_type=target_event.event_type.value,
        duration_seconds=duration,
    )


def _event_type_to_emotion(event_type: EventType) -> str:
    """Map event type to emotion key."""
    mapping = {
        EventType.WICKET: "wicket",
        EventType.BOUNDARY_FOUR: "boundary_four",
        EventType.BOUNDARY_SIX: "boundary_six",
        EventType.DOT_BALL: "dot_ball",
        EventType.SINGLE: "single",
    }
    return mapping.get(event_type, "dramatic")


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint with LLM status."""
    # Refresh LLM availability
    llm_status = _check_llm_availability()
    return {
        "status": "ok",
        "service": "suksham-vachak",
        "llm": {
            "available": llm_status["claude"] or llm_status["ollama"],
            "claude": llm_status["claude"],
            "ollama": llm_status["ollama"],
        },
    }


@router.get("/llm/status")
async def llm_status() -> dict[str, Any]:
    """Get detailed LLM provider status."""
    status = _check_llm_availability()

    providers = []
    if status["ollama"]:
        try:
            ollama = OllamaProvider()
            models = ollama.list_models()
            providers.append({
                "name": "ollama",
                "available": True,
                "models": models,
                "default_model": "qwen2.5:7b",
            })
        except Exception as e:
            providers.append({
                "name": "ollama",
                "available": False,
                "error": str(e),
            })
    else:
        providers.append({
            "name": "ollama",
            "available": False,
            "hint": "Start with: ollama serve && ollama pull qwen2.5:7b",
        })

    providers.append({
        "name": "claude",
        "available": status["claude"],
        "models": ["haiku", "sonnet", "opus"] if status["claude"] else [],
        "hint": None if status["claude"] else "Set ANTHROPIC_API_KEY environment variable",
    })

    return {
        "any_available": status["claude"] or status["ollama"],
        "providers": providers,
        "recommended": "ollama" if status["ollama"] else "claude" if status["claude"] else None,
    }
