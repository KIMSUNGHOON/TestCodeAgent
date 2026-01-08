"""Repository Embedder and Vector DB Manager

Phase 3 RAG Implementation:
- Embeds git repositories into vector database
- Provides semantic search over code and documentation
- Integrates with ContextManager for enhanced context retrieval
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import hashlib

logger = logging.getLogger(__name__)


class RepositoryEmbedder:
    """Embeds repository files into vector database"""

    def __init__(self, chroma_client, collection_name: str = "code_repositories"):
        """Initialize repository embedder

        Args:
            chroma_client: ChromaDB client instance
            collection_name: Name of the collection to store embeddings
        """
        self.client = chroma_client
        self.collection_name = collection_name
        self.collection = None

    def initialize_collection(self):
        """Initialize or get existing ChromaDB collection"""
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"📚 Using existing collection: {self.collection_name}")
        except Exception:
            # Create new collection if doesn't exist
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Code repositories for RAG context"}
            )
            logger.info(f"📚 Created new collection: {self.collection_name}")

    def should_embed_file(self, file_path: str) -> bool:
        """Check if file should be embedded

        Args:
            file_path: Path to file

        Returns:
            True if file should be embedded
        """
        # Skip common non-text files
        skip_extensions = {
            '.pyc', '.pyo', '.so', '.dll', '.dylib',
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
            '.mp4', '.avi', '.mov', '.mp3', '.wav',
            '.zip', '.tar', '.gz', '.bz2',
            '.pdf', '.doc', '.docx',
            '.lock', '.sum',
        }

        # Skip common directories
        skip_dirs = {
            '__pycache__', 'node_modules', '.git', '.venv', 'venv',
            'dist', 'build', '.next', '.nuxt', 'target',
        }

        file_path_obj = Path(file_path)

        # Check if any parent directory should be skipped
        if any(skip_dir in file_path_obj.parts for skip_dir in skip_dirs):
            return False

        # Check file extension
        if file_path_obj.suffix in skip_extensions:
            return False

        return True

    def chunk_text(
        self,
        text: str,
        max_chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """Split text into overlapping chunks

        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters

        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chunk_size

            # Try to break at newline
            if end < len(text):
                newline_pos = text.rfind('\n', start, end)
                if newline_pos > start + max_chunk_size // 2:
                    end = newline_pos

            chunk = text[start:end]
            chunks.append(chunk)

            start = end - overlap

        return chunks

    def embed_repository(
        self,
        repo_path: str,
        repo_name: str,
        max_files: Optional[int] = None
    ) -> Dict[str, int]:
        """Embed entire repository into vector database

        Args:
            repo_path: Path to repository
            repo_name: Name identifier for repository
            max_files: Maximum number of files to embed (for testing)

        Returns:
            Dictionary with statistics (files_processed, chunks_created, etc.)
        """
        if not self.collection:
            self.initialize_collection()

        stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "files_skipped": 0,
            "total_characters": 0,
        }

        documents = []
        metadatas = []
        ids = []

        file_count = 0

        # Walk through repository
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, repo_path)

                # Check if should embed
                if not self.should_embed_file(file_path):
                    stats["files_skipped"] += 1
                    continue

                # Read file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Failed to read {relative_path}: {e}")
                    stats["files_skipped"] += 1
                    continue

                # Skip empty files
                if not content.strip():
                    stats["files_skipped"] += 1
                    continue

                # Determine file type
                file_ext = Path(filename).suffix
                file_type = self._get_file_type(file_ext)

                # Chunk content
                chunks = self.chunk_text(content)

                # Create documents and metadata
                for i, chunk in enumerate(chunks):
                    # Generate unique ID
                    chunk_id = hashlib.md5(
                        f"{repo_name}:{relative_path}:{i}".encode()
                    ).hexdigest()

                    documents.append(chunk)
                    metadatas.append({
                        "repo": repo_name,
                        "file_path": relative_path,
                        "file_type": file_type,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    })
                    ids.append(chunk_id)

                    stats["chunks_created"] += 1

                stats["files_processed"] += 1
                stats["total_characters"] += len(content)

                file_count += 1
                if max_files and file_count >= max_files:
                    break

            if max_files and file_count >= max_files:
                break

        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            self.collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )

            logger.info(
                f"📥 Added batch {i // batch_size + 1}: "
                f"{len(batch_docs)} chunks"
            )

        logger.info(
            f"✅ Embedded {repo_name}: "
            f"{stats['files_processed']} files, "
            f"{stats['chunks_created']} chunks, "
            f"{stats['files_skipped']} skipped"
        )

        return stats

    def _get_file_type(self, extension: str) -> str:
        """Determine file type from extension

        Args:
            extension: File extension (e.g., '.py', '.ts')

        Returns:
            File type category
        """
        type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.sh': 'shell',
            '.bash': 'shell',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
        }
        return type_map.get(extension.lower(), 'text')

    def search(
        self,
        query: str,
        n_results: int = 5,
        repo_filter: Optional[str] = None,
        file_type_filter: Optional[str] = None
    ) -> List[Dict]:
        """Search for relevant code chunks

        Args:
            query: Search query
            n_results: Number of results to return
            repo_filter: Optional repository name filter
            file_type_filter: Optional file type filter

        Returns:
            List of search results with metadata
        """
        if not self.collection:
            self.initialize_collection()

        # Build where clause for filtering
        where = {}
        if repo_filter:
            where["repo"] = repo_filter
        if file_type_filter:
            where["file_type"] = file_type_filter

        # Query collection
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where if where else None
        )

        # Format results
        formatted_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None,
                })

        return formatted_results
