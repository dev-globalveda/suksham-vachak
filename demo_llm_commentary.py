#!/usr/bin/env python3
"""Demo script: End-to-end LLM-powered cricket commentary with rich context.

This script demonstrates the full pipeline:
1. Parse a match from Cricsheet JSON
2. Build rich context for each delivery
3. Generate LLM commentary with situational awareness

Usage:
    python demo_llm_commentary.py [--match-id MATCH_ID] [--persona PERSONA] [--moments N] [--rag] [--tts PROVIDER]

Examples:
    python demo_llm_commentary.py
    python demo_llm_commentary.py --persona greig --moments 5
    python demo_llm_commentary.py --match-id 1000881 --persona benaud
    python demo_llm_commentary.py --rag  # Enable RAG historical context
    python demo_llm_commentary.py --tts google  # Generate audio with Google TTS
    python demo_llm_commentary.py --tts azure   # Generate audio with Azure TTS
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from suksham_vachak.commentary import CommentaryEngine
from suksham_vachak.context import ContextBuilder
from suksham_vachak.parser import CricsheetParser
from suksham_vachak.personas import BENAUD, DOSHI, GREIG

# Optional RAG imports (only available if installed with: poetry install --extras rag)
try:
    from suksham_vachak.rag import RAGConfig, create_retriever

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Optional TTS imports (only available if installed with: poetry install --extras tts)
try:
    from suksham_vachak.tts import TTSConfig, TTSEngine

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# Load environment variables from .env file (must be before using env vars)
load_dotenv()

# Data directory
DATA_DIR = Path("data/cricsheet_sample")

# Persona registry
PERSONAS = {
    "benaud": BENAUD,
    "greig": GREIG,
    "doshi": DOSHI,
}


def print_header(text: str) -> None:
    """Print a styled header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_context_summary(context) -> None:
    """Print a summary of the rich context."""
    print("\n  📊 Context Summary:")
    print(f"     Phase: {context.match.phase.value}")
    print(f"     Pressure: {context.pressure.value} ({context.pressure_score:.2f})")
    print(f"     Momentum: {context.narrative.momentum.value}")
    print(f"     Storyline: {context.narrative.current_storyline}")
    if context.narrative.key_subplot:
        print(f"     Subplot: {context.narrative.key_subplot}")
    print(f"     Suggested tone: {context.suggested_tone}")
    # Show Memory Lane if RAG returned historical parallels
    if context.narrative.callbacks_available:
        history = [c for c in context.narrative.callbacks_available if c.startswith("History:")]
        if history:
            print("\n  🧠 Memory Lane:")
            for h in history[:2]:
                print(f"     {h}")


def run_demo(  # noqa: C901
    match_id: str | None = None,
    persona_name: str = "benaud",
    num_moments: int = 3,
    use_llm: bool = True,
    use_rag: bool = False,
    tts_provider: str | None = None,
) -> None:
    """Run the end-to-end demo."""
    # Find a match file
    if match_id:
        match_file = DATA_DIR / f"{match_id}.json"
        if not match_file.exists():
            print(f"❌ Match {match_id} not found in {DATA_DIR}")
            sys.exit(1)
    else:
        match_files = list(DATA_DIR.glob("*.json"))
        if not match_files:
            print(f"❌ No match files found in {DATA_DIR}")
            sys.exit(1)
        match_file = match_files[0]

    # Get persona
    persona = PERSONAS.get(persona_name.lower())
    if not persona:
        print(f"❌ Unknown persona: {persona_name}. Available: {list(PERSONAS.keys())}")
        sys.exit(1)

    print_header("🏏 Suksham Vachak - LLM Commentary Demo")

    # Parse match
    print(f"\n📁 Loading match: {match_file.name}")
    parser = CricsheetParser(match_file)
    info = parser.match_info

    print(f"   {info.teams[0]} vs {info.teams[1]}")
    print(f"   📍 {info.venue}")
    print(f"   📅 {info.dates[0] if info.dates else 'Unknown'}")
    print(f"   🏆 Format: {info.format.value}")

    # Initialize RAG retriever (optional)
    rag_retriever = None
    if use_rag:
        if not RAG_AVAILABLE:
            print("❌ RAG not available. Install with: poetry install --extras rag")
            sys.exit(1)
        print("\n🧠 Initializing RAG Déjà Vu Engine...")
        try:
            config = RAGConfig.default()
            rag_retriever = create_retriever(config)
            print("   ✅ RAG retriever initialized")
            print(f"   📚 Vector store: {config.vector_db_path}")
        except Exception as e:
            print(f"❌ Failed to initialize RAG: {e}")
            sys.exit(1)

    # Initialize context builder
    context_builder = ContextBuilder(info, rag_retriever=rag_retriever)

    # Initialize commentary engine
    print(f"\n🎙️ Commentator: {persona.name}")
    print(f"   Style: {persona.style.value}")
    print(f"   Minimalism: {persona.minimalism_score:.0%}")

    try:
        engine = CommentaryEngine(
            use_llm=use_llm,
            context_builder=context_builder,
        )
        if use_llm:
            print("   ✅ LLM client initialized")
    except ValueError as e:
        print(f"   ⚠️ LLM not available: {e}")
        print("   Falling back to template-based commentary")
        engine = CommentaryEngine(use_llm=False, context_builder=context_builder)

    # Initialize TTS engine (optional)
    tts_engine = None
    audio_segments = []
    if tts_provider:
        if not TTS_AVAILABLE:
            print(f"❌ TTS not available. Install with: poetry install --extras tts-{tts_provider}")
            sys.exit(1)
        print(f"\n🔊 Initializing TTS Engine ({tts_provider})...")
        try:
            tts_config = TTSConfig(provider=tts_provider)
            tts_engine = TTSEngine(tts_config)
            print("   ✅ TTS engine initialized")
            print(f"   📁 Audio cache: {tts_config.cache_dir}")
        except Exception as e:
            print(f"❌ Failed to initialize TTS: {e}")
            sys.exit(1)

    # Get key moments
    print_header("🎯 Key Moments Commentary")

    key_moments = parser.get_key_moments(innings_number=1)[:num_moments]

    if not key_moments:
        print("No key moments found in innings 1, trying innings 2...")
        key_moments = parser.get_key_moments(innings_number=2)[:num_moments]

    if not key_moments:
        print("No key moments found. Using first few deliveries instead.")
        key_moments = list(parser.parse_innings(1))[:num_moments]

    # Process events to build context
    print("\n📈 Processing match to build context...")
    all_events = list(parser.parse_innings(1))

    # Find ball numbers of key moments (more reliable than event_id)
    key_moment_balls = {m.ball_number for m in key_moments}

    for event in all_events:
        # Build context for each event (this updates internal state)
        context = context_builder.build(event)

        # Generate commentary only for key moments
        if event.ball_number in key_moment_balls:
            print(f"\n{'─' * 50}")
            print(
                f"⚡ Ball {event.ball_number}: {event.match_context.current_score}/{event.match_context.current_wickets}"
            )
            print(f"   {event.bowler} to {event.batter}")

            # Show what happened
            if event.is_wicket:
                print(f"   🔴 WICKET! {event.wicket_type}")
            elif event.runs_batter == 6:
                print("   🟢 SIX!")
            elif event.runs_batter == 4:
                print("   🟢 FOUR!")
            else:
                print(f"   Runs: {event.runs_total}")

            # Show context summary
            print_context_summary(context)

            # Generate commentary
            commentary = engine.generate(event, persona)

            print(f"\n  🎙️ {persona.name}:")
            if commentary.text:
                print(f'     "{commentary.text}"')
            else:
                print("     [Silence - letting the moment speak]")

            if commentary.used_llm and commentary.llm_response:
                print(f"\n     📊 Tokens: {commentary.llm_response.total_tokens}")

            # Synthesize audio if TTS enabled
            if tts_engine and commentary.text:
                try:
                    segment = tts_engine.synthesize_commentary(commentary, persona)
                    audio_segments.append(segment)
                    print(f"     🔊 Audio: {segment.duration_seconds:.1f}s")
                except Exception as e:
                    print(f"     ⚠️ TTS failed: {e}")

    # Save audio files if TTS was used
    if tts_engine and audio_segments:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        print_header("🔊 Saving Audio Files")
        for i, segment in enumerate(audio_segments, 1):
            output_file = output_dir / f"commentary_{i:02d}.{segment.format.value}"
            tts_engine.save_audio(segment, output_file)
            print(f"   {i}. {output_file} ({segment.duration_seconds:.1f}s)")

        # Concatenate all segments
        if len(audio_segments) > 1:
            concat_file = output_dir / f"full_commentary.{audio_segments[0].format.value}"
            tts_engine.concatenate_segments(audio_segments, concat_file)
            print(f"\n   📼 Combined: {concat_file}")

    # Summary
    print_header("📊 Demo Complete")
    print(f"\n   Moments commentated: {len(key_moments)}")
    print(f"   Persona: {persona.name}")
    print(f"   LLM used: {engine.use_llm}")
    print(f"   RAG enabled: {use_rag}")
    print(f"   TTS enabled: {tts_provider or 'No'}")

    if engine.use_llm:
        print("\n   💡 The commentary was generated by Claude with rich match context!")
        print("      Context includes: pressure, momentum, narrative, player form, etc.")
        if use_rag:
            print("      + Historical parallels from the Déjà Vu Engine!")
        if tts_provider:
            print(f"      + Audio generated with {tts_provider.title()} TTS!")
    else:
        print("\n   💡 Using template-based commentary (set ANTHROPIC_API_KEY for LLM)")


def main() -> None:
    """Parse args and run demo."""
    parser = argparse.ArgumentParser(description="Demo: LLM-powered cricket commentary with rich context")
    parser.add_argument(
        "--match-id",
        type=str,
        help="Match ID to use (defaults to first available)",
    )
    parser.add_argument(
        "--persona",
        type=str,
        default="benaud",
        choices=["benaud", "greig", "doshi"],
        help="Commentary persona (default: benaud)",
    )
    parser.add_argument(
        "--moments",
        type=int,
        default=3,
        help="Number of key moments to commentate (default: 3)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM, use templates only",
    )
    parser.add_argument(
        "--rag",
        action="store_true",
        help="Enable RAG historical context (requires VOYAGE_API_KEY)",
    )
    parser.add_argument(
        "--tts",
        type=str,
        choices=["google", "azure"],
        help="Enable TTS with specified provider (requires credentials)",
    )

    args = parser.parse_args()

    run_demo(
        match_id=args.match_id,
        persona_name=args.persona,
        num_moments=args.moments,
        use_llm=not args.no_llm,
        use_rag=args.rag,
        tts_provider=args.tts,
    )


if __name__ == "__main__":
    main()
