"""Query claude-code repository via RAG system

Usage:
    python backend/scripts/query_claude_code.py "How do plugins work?"
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import chromadb
from app.utils.repository_embedder import RepositoryEmbedder


def query(question: str, n_results: int = 5):
    """Query the claude-code repository

    Args:
        question: Question to ask
        n_results: Number of results to return
    """
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path="./chroma_db")

    # Create embedder
    embedder = RepositoryEmbedder(client, collection_name="code_repositories")
    embedder.initialize_collection()

    # Search
    results = embedder.search(
        query=question,
        n_results=n_results,
        repo_filter="anthropics/claude-code"
    )

    print(f"\n🔍 Query: '{question}'\n")
    print("="*80)

    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        content = result['content']

        print(f"\n[{i}] 📄 {metadata['file_path']}")
        print(f"    Chunk {metadata['chunk_index'] + 1}/{metadata['total_chunks']}")
        if result['distance']:
            print(f"    Distance: {result['distance']:.4f}")
        print(f"\n{content}\n")
        print("-"*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/query_claude_code.py '<question>'")
        print("\nExamples:")
        print("  python backend/scripts/query_claude_code.py 'How do CLI tools work?'")
        print("  python backend/scripts/query_claude_code.py 'What is the plugin architecture?'")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    query(question)
