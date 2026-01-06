"""CLI for RAG ingestion and management.

Usage:
    python -m suksham_vachak.rag.cli ingest
    python -m suksham_vachak.rag.cli stats
    python -m suksham_vachak.rag.cli clear
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import RAGConfig


def ingest_all(config: RAGConfig) -> None:
    """Ingest all moments into vector store."""
    from .embeddings import VoyageEmbeddingClient
    from .ingestion import CricsheetIngester, CuratedIngester
    from .store import MomentVectorStore

    print("Initializing RAG components...")
    print(f"  Vector DB: {config.vector_db_path}")
    print(f"  Voyage model: {config.voyage_model}")

    embedding_client = VoyageEmbeddingClient(model=config.voyage_model)
    store = MomentVectorStore(
        embedding_client=embedding_client,
        persist_directory=config.vector_db_path,
    )

    # Ingest curated moments first (higher priority)
    print("\nIngesting curated moments...")
    curated_path = Path(config.curated_moments_file)
    if curated_path.exists():
        curated_ingester = CuratedIngester(config.curated_moments_file)
        curated_moments = curated_ingester.ingest()
        if curated_moments:
            store.add_moments(curated_moments)
            print(f"  Added {len(curated_moments)} curated iconic moments")
    else:
        print(f"  Skipped: {config.curated_moments_file} not found")

    # Ingest Cricsheet data
    print("\nIngesting Cricsheet matches...")
    cricsheet_path = Path(config.cricsheet_data_dir)
    if cricsheet_path.exists():
        cricsheet_ingester = CricsheetIngester(config.cricsheet_data_dir)

        batch: list = []
        batch_size = 50
        total_count = 0

        for moment in cricsheet_ingester.ingest_all():
            batch.append(moment)
            if len(batch) >= batch_size:
                store.add_moments(batch)
                total_count += len(batch)
                print(f"  Added {total_count} moments...")
                batch = []

        # Add remaining
        if batch:
            store.add_moments(batch)
            total_count += len(batch)

        print(f"  Added {total_count} moments from matches")
    else:
        print(f"  Skipped: {config.cricsheet_data_dir} not found")

    print(f"\nComplete! Total moments in store: {store.count}")
    embedding_client.close()


def show_stats(config: RAGConfig) -> None:
    """Show vector store statistics."""
    from .embeddings import VoyageEmbeddingClient
    from .store import MomentVectorStore

    embedding_client = VoyageEmbeddingClient(model=config.voyage_model)
    store = MomentVectorStore(
        embedding_client=embedding_client,
        persist_directory=config.vector_db_path,
    )

    print(f"Vector Store: {config.vector_db_path}")
    print(f"Total moments: {store.count}")
    embedding_client.close()


def clear_store(config: RAGConfig) -> None:
    """Clear all moments from vector store."""
    from .embeddings import VoyageEmbeddingClient
    from .store import MomentVectorStore

    embedding_client = VoyageEmbeddingClient(model=config.voyage_model)
    store = MomentVectorStore(
        embedding_client=embedding_client,
        persist_directory=config.vector_db_path,
    )

    store.clear()
    print("Vector store cleared.")
    embedding_client.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Déjà Vu Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m suksham_vachak.rag.cli ingest   # Ingest all moments
  python -m suksham_vachak.rag.cli stats    # Show store statistics
  python -m suksham_vachak.rag.cli clear    # Clear all moments
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/rag.yaml",
        help="Path to RAG config file",
    )
    parser.add_argument(
        "command",
        choices=["ingest", "clear", "stats"],
        help="Command to run",
    )

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    config = RAGConfig.from_yaml(config_path) if config_path.exists() else RAGConfig.default()

    # Execute command
    if args.command == "ingest":
        ingest_all(config)
    elif args.command == "stats":
        show_stats(config)
    elif args.command == "clear":
        clear_store(config)


if __name__ == "__main__":
    main()
