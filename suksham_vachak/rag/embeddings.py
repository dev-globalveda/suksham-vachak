"""Voyage API embedding client for RAG.

Voyage provides high-quality embeddings optimized for retrieval tasks.
https://www.voyageai.com/
"""

from __future__ import annotations

import os
from typing import ClassVar

import httpx


class VoyageEmbeddingClient:
    """Client for Voyage API embeddings.

    Voyage provides high-quality embeddings that work well for
    semantic similarity and retrieval tasks.
    """

    BASE_URL: ClassVar[str] = "https://api.voyageai.com/v1"
    DEFAULT_MODEL: ClassVar[str] = "voyage-2"  # Good balance of quality/speed
    LITE_MODEL: ClassVar[str] = "voyage-lite-02-instruct"  # Faster, smaller

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        """Initialize Voyage client.

        Args:
            api_key: Voyage API key. Falls back to VOYAGE_API_KEY env var.
            model: Embedding model to use.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY not provided and not in environment")

        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def embed_texts(
        self,
        texts: list[str],
        input_type: str = "document",
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.
            input_type: "document" for indexing, "query" for retrieval.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        response = self._client.post(
            "/embeddings",
            json={
                "input": texts,
                "model": self.model,
                "input_type": input_type,
            },
        )
        response.raise_for_status()

        data = response.json()
        # Sort by index to preserve order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]

    def embed_text(self, text: str, input_type: str = "document") -> list[float]:
        """Generate embedding for a single text."""
        embeddings = self.embed_texts([text], input_type)
        return embeddings[0]

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a query (retrieval).

        Uses input_type="query" which optimizes the embedding
        for retrieval tasks.
        """
        return self.embed_text(query, input_type="query")

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """Generate embeddings for documents (indexing).

        Uses input_type="document" which optimizes the embedding
        for being retrieved.
        """
        return self.embed_texts(documents, input_type="document")

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> VoyageEmbeddingClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
