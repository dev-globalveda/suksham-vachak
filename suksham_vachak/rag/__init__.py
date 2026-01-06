"""RAG module for cricket commentary - Déjà Vu Engine.

Provides historical context retrieval for "reminds me of..." commentary.
Uses ChromaDB for vector storage and Voyage API for embeddings.
"""

from .config import RAGConfig
from .models import CricketMoment, MomentSource, MomentType, RetrievedMoment
from .retriever import DejaVuRetriever

__all__ = [
    "CricketMoment",
    "DejaVuRetriever",
    "MomentSource",
    "MomentType",
    "RAGConfig",
    "RetrievedMoment",
]


def create_retriever(config: RAGConfig | None = None) -> DejaVuRetriever:
    """Create a configured DejaVu retriever.

    Args:
        config: RAG configuration. Uses defaults if not provided.

    Returns:
        Configured retriever instance.

    Raises:
        ImportError: If chromadb is not installed.
        ValueError: If VOYAGE_API_KEY is not set.
    """
    from .embeddings import VoyageEmbeddingClient
    from .store import MomentVectorStore

    if config is None:
        config = RAGConfig.default()

    embedding_client = VoyageEmbeddingClient(model=config.voyage_model)
    store = MomentVectorStore(
        embedding_client=embedding_client,
        persist_directory=config.vector_db_path,
    )

    return DejaVuRetriever(
        store=store,
        max_callbacks=config.max_callbacks,
        min_similarity=config.min_similarity,
    )
