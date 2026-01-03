"""Sushil Doshi persona - the voice of Hindi cricket commentary."""

from .base import CommentaryStyle, Persona

# Sushil Doshi: The legendary Hindi commentator
# Known for: Poetic Hindi, dramatic flair, emotional connection
# Famous calls in Hindi that resonate with millions
DOSHI = Persona(
    name="Sushil Doshi",
    style=CommentaryStyle.DRAMATIC,
    vocabulary=[
        "गजब",  # Amazing
        "शानदार",  # Splendid
        "बेहतरीन",  # Excellent
        "कमाल",  # Wonderful
        "धमाका",  # Blast
        "जबरदस्त",  # Tremendous
    ],
    cultural_context="Hindi heartland cricket passion, emotional storytelling",
    emotion_range={
        "wicket": "आउट! और गया!",  # Out! And he's gone!
        "boundary_four": "चौका! शानदार शॉट!",  # Four! Splendid shot!
        "boundary_six": "छक्का! क्या मारा है!",  # Six! What a hit!
        "dot_ball": "",  # Silence
        "single": "एक रन",  # One run
        "appeal": "अपील! बड़ी अपील!",  # Appeal! Big appeal!
        "milestone": "शतक! क्या पारी!",  # Century! What an innings!
        "dramatic": "क्या बात है!",  # What a moment!
        "excitement": "गजब! कमाल!",  # Amazing! Wonderful!
    },
    signature_phrases=[
        "आउट! और गया!",
        "क्या बात है!",
        "गजब!",
        "शानदार!",
        "कमाल का खेल!",
        "बड़ा शॉट!",
    ],
    minimalism_score=0.6,  # Slightly more expressive, but still punchy
    languages=["hi"],
    voice_id="hi-IN-Wavenet-C",  # Male Hindi voice
    speaking_rate=0.9,  # Slightly slower, more deliberate
    pitch=-3.0,  # Deeper voice for gravitas
)
