"""Script to embed claude-code repository into vector database

Usage:
    python backend/scripts/embed_claude_code.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import chromadb
from app.utils.repository_embedder import RepositoryEmbedder
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main function to embed claude-code repository"""

    # Initialize ChromaDB client
    logger.info("🚀 Initializing ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")

    # Create embedder
    embedder = RepositoryEmbedder(client, collection_name="code_repositories")
    embedder.initialize_collection()

    # Embed claude-code repository
    repo_path = "/tmp/claude-code"

    if not Path(repo_path).exists():
        logger.error(f"❌ Repository not found at {repo_path}")
        logger.info("Please clone it first:")
        logger.info("cd /tmp && git clone --depth 1 https://github.com/anthropics/claude-code.git")
        return

    logger.info(f"📂 Embedding repository from: {repo_path}")

    stats = embedder.embed_repository(
        repo_path=repo_path,
        repo_name="anthropics/claude-code",
        max_files=None  # Embed all files
    )

    logger.info("\n" + "="*60)
    logger.info("✅ Embedding Complete!")
    logger.info("="*60)
    logger.info(f"📊 Statistics:")
    logger.info(f"   - Files processed: {stats['files_processed']}")
    logger.info(f"   - Chunks created: {stats['chunks_created']}")
    logger.info(f"   - Files skipped: {stats['files_skipped']}")
    logger.info(f"   - Total characters: {stats['total_characters']:,}")
    logger.info("="*60)

    # Test search
    logger.info("\n🔍 Testing search functionality...")

    test_queries = [
        "How do plugins work?",
        "What are slash commands?",
        "Agent implementation",
        "Hook system",
    ]

    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        results = embedder.search(query, n_results=3)

        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            content_preview = result['content'][:150].replace('\n', ' ')
            logger.info(
                f"  [{i}] {metadata['file_path']} "
                f"(chunk {metadata['chunk_index'] + 1}/{metadata['total_chunks']})"
            )
            logger.info(f"      {content_preview}...")

    logger.info("\n✅ All done! Vector DB is ready for use.")
    logger.info(f"📍 Database location: ./chroma_db")


if __name__ == "__main__":
    main()
