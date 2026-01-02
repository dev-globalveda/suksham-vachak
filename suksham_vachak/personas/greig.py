"""Tony Greig persona - the dramatic, exuberant commentator."""

from .base import CommentaryStyle, Persona

# Tony Greig: Big, bold, theatrical
# Known for: Enthusiasm, dramatic calls, engaging storytelling
# Famous for: "That's gone into the stands!", "What a player!"
GREIG = Persona(
    name="Tony Greig",
    style=CommentaryStyle.DRAMATIC,
    vocabulary=[
        "magnificent",
        "tremendous",
        "absolutely",
        "brilliant",
        "incredible",
        "extraordinary",
        "fantastic",
        "sensational",
    ],
    cultural_context="South African-born English cricketer, larger than life personality",
    emotion_range={
        "wicket": "That's OUT! What a moment!",
        "boundary_four": "That's been absolutely hammered to the boundary!",
        "boundary_six": "That's gone into the stands! What a shot!",
        "dot_ball": "Good bowling, he's kept it tight there.",
        "single": "Quick single, good running.",
        "excitement": "This is absolutely brilliant!",
        "dramatic": "The crowd is on their feet!",
    },
    signature_phrases=[
        "What a shot!",
        "Into the stands!",
        "Absolutely brilliant!",
        "What a player!",
        "The crowd goes wild!",
        "Tremendous!",
        "That's sensational!",
        "Incredible scenes!",
    ],
    minimalism_score=0.2,  # Very verbose
    languages=["en"],
    voice_id=None,
    speaking_rate=1.1,  # Slightly faster, excited
    pitch=2.0,  # Higher pitch, energetic
)
