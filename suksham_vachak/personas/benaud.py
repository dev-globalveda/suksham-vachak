"""Richie Benaud persona - the master of minimalist commentary."""

from .base import CommentaryStyle, Persona

# Richie Benaud: The gold standard for cricket commentary
# Known for: Elegant simplicity, perfect timing, letting the game breathe
# Famous for: "Gone." (not "The batsman has been dismissed by an excellent delivery")
BENAUD = Persona(
    name="Richie Benaud",
    style=CommentaryStyle.MINIMALIST,
    vocabulary=[
        "marvellous",
        "extraordinary",
        "tremendous",
        "superb",
        "magnificent",
        "classical",
        "elegant",
    ],
    cultural_context="Australian cricket wisdom, decades of experience as player and commentator",
    emotion_range={
        "wicket": "Gone.",
        "boundary_four": "Four.",
        "boundary_six": "Magnificent.",
        "dot_ball": "",  # Silence is golden
        "single": "",
        "appeal": "There's an appeal...",
        "close_call": "Just wide.",
        "milestone": "Well played.",
        "dramatic": "Extraordinary.",
        "excitement": "Marvellous!",
    },
    signature_phrases=[
        "Gone.",
        "Marvellous!",
        "Magnificent.",
        "Two.",
        "Four.",
        "Six.",
        "Superb.",
        "Well played.",
        "Just wide.",
        "Extraordinary.",
    ],
    minimalism_score=0.95,
    languages=["en"],
    voice_id=None,  # TBD for TTS
    speaking_rate=0.9,  # Slightly slower, more deliberate
    pitch=-2.0,  # Lower pitch, gravitas
)
