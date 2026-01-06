"""ChromaDB vector store for cricket moments.

Provides persistent storage and semantic search for historical
cricket moments used in RAG retrieval.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import CricketMoment, MomentSource, RetrievedMoment

if TYPE_CHECKING:
    from .embeddings import VoyageEmbeddingClient


class MomentVectorStore:
    """ChromaDB-based vector store for cricket moments.

    Optimized for:
    - Raspberry Pi deployment (lightweight, persistent storage)
    - Hybrid retrieval (semantic + metadata filtering)
    - Curated moment prioritization
    """

    COLLECTION_NAME = "cricket_moments"

    def __init__(
        self,
        embedding_client: VoyageEmbeddingClient,
        persist_directory: str | Path | None = None,
        in_memory: bool = False,
    ) -> None:
        """Initialize vector store.

        Args:
            embedding_client: Voyage embedding client for vectors.
            persist_directory: Directory for persistent storage.
            in_memory: If True, use in-memory storage (for testing).
        """
        # Import chromadb here to make it optional
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            msg = "chromadb not installed. Run: poetry install --extras rag"
            raise ImportError(msg) from e

        self.embedding_client = embedding_client

        if in_memory:
            self._client = chromadb.Client()
        else:
            persist_path = Path(persist_directory) if persist_directory else Path("data/vector_db")
            persist_path.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Cricket moments for RAG retrieval"},
        )

    def add_moment(self, moment: CricketMoment) -> None:
        """Add a single moment to the store."""
        self.add_moments([moment])

    def add_moments(self, moments: list[CricketMoment]) -> None:
        """Add multiple moments to the store.

        Generates embeddings for all moments and stores them
        with their metadata.
        """
        if not moments:
            return

        # Generate embeddings
        texts = [m.to_embedding_text() for m in moments]
        embeddings = self.embedding_client.embed_documents(texts)

        # Prepare for ChromaDB
        ids = [m.moment_id for m in moments]
        metadatas = [m.to_metadata() for m in moments]
        documents = [m.description for m in moments]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        curated_boost: float = 1.5,
    ) -> list[RetrievedMoment]:
        """Query for similar moments.

        Args:
            query_text: Text describing the current situation.
            n_results: Maximum number of results.
            where: ChromaDB metadata filter.
            curated_boost: Score multiplier for curated moments.

        Returns:
            List of retrieved moments sorted by relevance.
        """
        # Generate query embedding
        query_embedding = self.embedding_client.embed_query(query_text)

        # Query ChromaDB - fetch extra for re-ranking
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        # Convert to RetrievedMoment objects
        retrieved = []
        for i, _moment_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]  # type: ignore[index]
            document = results["documents"][0][i]  # type: ignore[index]
            distance = results["distances"][0][i]  # type: ignore[index]

            # Convert distance to similarity (ChromaDB uses L2 distance)
            similarity = 1.0 / (1.0 + distance)

            # Boost curated moments
            if metadata["source"] == MomentSource.CURATED.value:
                similarity *= curated_boost

            # Apply priority boost
            similarity *= metadata.get("priority", 1.0)

            moment = CricketMoment.from_metadata(metadata, document)
            retrieved.append(RetrievedMoment(moment=moment, similarity_score=similarity))

        # Sort by score and limit
        retrieved.sort(key=lambda x: x.similarity_score, reverse=True)
        return retrieved[:n_results]

    def query_by_player(
        self,
        player_name: str,
        n_results: int = 3,
    ) -> list[RetrievedMoment]:
        """Find moments involving a specific player."""
        query_text = f"cricket moment involving {player_name}"

        return self.query(
            query_text=query_text,
            n_results=n_results,
            where={"primary_player": {"$eq": player_name}},
        )

    def query_by_situation(
        self,
        phase: str,
        pressure_level: str,
        match_format: str,
        n_results: int = 3,
    ) -> list[RetrievedMoment]:
        """Find moments in similar match situations."""
        query_text = f"{match_format} match {phase} phase {pressure_level} pressure moment"

        return self.query(
            query_text=query_text,
            n_results=n_results,
            where={
                "$and": [
                    {"phase": {"$eq": phase}},
                    {"pressure_level": {"$eq": pressure_level}},
                ]
            },
        )

    def delete_moment(self, moment_id: str) -> None:
        """Delete a moment by ID."""
        self._collection.delete(ids=[moment_id])

    def clear(self) -> None:
        """Clear all moments from the store."""
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Cricket moments for RAG retrieval"},
        )

    @property
    def count(self) -> int:
        """Get number of moments in store."""
        return self._collection.count()
