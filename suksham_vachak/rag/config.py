"""RAG configuration for Déjà Vu Engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class RAGConfig:
    """Configuration for RAG system."""

    # Embedding settings
    voyage_model: str = "voyage-2"

    # ChromaDB settings
    vector_db_path: str = "data/vector_db"
    collection_name: str = "cricket_moments"

    # Retrieval settings
    max_callbacks: int = 2
    min_similarity: float = 0.3
    curated_boost: float = 1.5

    # Data paths
    cricsheet_data_dir: str = "data/cricsheet_sample"
    curated_moments_file: str = "data/curated/iconic_moments.yaml"

    @classmethod
    def from_yaml(cls, path: str | Path) -> RAGConfig:
        """Load config from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data.get("rag", {}))

    @classmethod
    def default(cls) -> RAGConfig:
        """Return default configuration."""
        return cls()
