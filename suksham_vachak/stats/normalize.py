"""Player name normalization for consistent identification."""

from __future__ import annotations

import re


def normalize_player_id(name: str) -> str:
    """Convert player name to a normalized ID.

    Cricsheet data has inconsistent name formats:
    - "V Kohli", "Virat Kohli", "VK"
    - "MS Dhoni", "M.S. Dhoni", "Mahendra Singh Dhoni"

    This function creates a deterministic ID by:
    1. Converting to lowercase
    2. Removing punctuation (periods, apostrophes)
    3. Replacing spaces with underscores
    4. Removing extra whitespace

    Examples:
        >>> normalize_player_id("V Kohli")
        'v_kohli'
        >>> normalize_player_id("M.S. Dhoni")
        'ms_dhoni'
        >>> normalize_player_id("Shaheen Shah Afridi")
        'shaheen_shah_afridi'
        >>> normalize_player_id("D'Arcy Short")
        'darcy_short'

    Args:
        name: Player name as it appears in source data.

    Returns:
        Normalized player ID suitable for database keys.
    """
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower()

    # Remove periods (M.S. Dhoni -> MS Dhoni)
    normalized = normalized.replace(".", "")

    # Remove apostrophes (D'Arcy -> DArcy)
    normalized = normalized.replace("'", "")

    # Remove other common punctuation
    normalized = re.sub(r"[^\w\s]", "", normalized)

    # Replace multiple spaces with single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Strip leading/trailing whitespace
    normalized = normalized.strip()

    # Replace spaces with underscores
    normalized = normalized.replace(" ", "_")

    return normalized


def normalize_display_name(name: str) -> str:
    """Clean up display name while preserving format.

    Fixes common issues like extra spaces, inconsistent capitalization.

    Args:
        name: Raw player name from source data.

    Returns:
        Cleaned display name.
    """
    if not name:
        return ""

    # Fix multiple spaces
    cleaned = re.sub(r"\s+", " ", name)

    # Strip whitespace
    cleaned = cleaned.strip()

    return cleaned
