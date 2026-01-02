"""Persona definitions for commentary generation."""

from .base import CommentaryStyle, Persona
from .benaud import BENAUD
from .greig import GREIG

__all__ = [
    "BENAUD",
    "GREIG",
    "CommentaryStyle",
    "Persona",
]
