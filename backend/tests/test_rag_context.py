"""Tests for RAGContextBuilder - Phase 3-C verification."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.rag_context import (
    RAGContextBuilder,
    RAGContext,
    get_rag_builder
)
from app.services.vector_db import SearchResult


class TestRAGContextBuilder:
    """Test RAGContextBuilder functionality."""

    @pytest.fixture
    def mock_search_results(self):
        """Create mock search results."""
        return [
            SearchResult(
                id="doc1",
                content="user management\n\nFilename: user_service.py\nLanguage: python\n\nclass UserService:\n    def create_user(self, name):\n        pass",
                metadata={
                    "filename": "user_service.py",
                    "language": "python",
                    "session_id": "test_session",
                    "description": "User service module"
                },
                distance=0.3  # 70% relevance
            ),
            SearchResult(
                id="doc2",
                content="authentication\n\nFilename: auth.py\nLanguage: python\n\ndef login(username, password):\n    pass",
                metadata={
                    "filename": "auth.py",
                    "language": "python",
                    "session_id": "test_session",
                    "description": "Authentication module"
                },
                distance=0.4  # 60% relevance
            ),
            SearchResult(
                id="doc3",
                content="database\n\nFilename: db.py\nLanguage: python\n\nclass Database:\n    pass",
                metadata={
                    "filename": "db.py",
                    "language": "python",
                    "session_id": "test_session"
                },
                distance=0.6  # 40% relevance - should be filtered at 0.5 threshold
            )
        ]

    def test_builder_creation(self):
        """Test RAGContextBuilder instantiation."""
        builder = RAGContextBuilder("test_session")

        assert builder.session_id == "test_session"
        assert builder.DEFAULT_N_RESULTS == 5
        assert builder.DEFAULT_MIN_RELEVANCE == 0.5

    def test_build_context_with_results(self, mock_search_results):
        """Test building context from search results."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            mock_db.search_code.return_value = mock_search_results

            builder = RAGContextBuilder("test_session")
            context = builder.build_context("user management", min_relevance=0.5)

            assert isinstance(context, RAGContext)
            assert context.results_count == 2  # Only 2 above 0.5 relevance
            assert "user_service.py" in context.files_referenced
            assert "auth.py" in context.files_referenced
            assert "db.py" not in context.files_referenced  # Filtered out
            assert context.avg_relevance > 0.5
            assert "Relevant Code from Project" in context.formatted_context

    def test_build_context_empty_results(self):
        """Test building context with no search results."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            mock_db.search_code.return_value = []

            builder = RAGContextBuilder("test_session")
            context = builder.build_context("nonexistent query")

            assert context.results_count == 0
            assert context.formatted_context == ""
            assert context.files_referenced == []
            assert context.avg_relevance == 0.0

    def test_build_context_all_filtered(self, mock_search_results):
        """Test when all results are below relevance threshold."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            # All results have low relevance
            low_relevance_results = [
                SearchResult(
                    id="doc1",
                    content="content",
                    metadata={"filename": "test.py", "language": "python"},
                    distance=0.9  # Only 10% relevance
                )
            ]
            mock_db.search_code.return_value = low_relevance_results

            builder = RAGContextBuilder("test_session")
            context = builder.build_context("query", min_relevance=0.5)

            assert context.results_count == 0
            assert context.formatted_context == ""

    def test_format_results(self, mock_search_results):
        """Test formatting of search results."""
        builder = RAGContextBuilder("test_session")

        # Only include high relevance results
        relevant_results = [r for r in mock_search_results if r.distance <= 0.5]
        formatted, files = builder._format_results(relevant_results)

        assert "user_service.py" in formatted
        assert "auth.py" in formatted
        assert "Relevance:" in formatted
        assert "```python" in formatted
        assert len(files) == 2

    def test_extract_code_from_document(self):
        """Test code extraction from stored document format."""
        builder = RAGContextBuilder("test_session")

        document = "Description here\n\nFilename: test.py\nLanguage: python\n\nclass TestClass:\n    pass"
        code = builder._extract_code_from_document(document)

        assert "class TestClass" in code

    def test_enrich_query_with_results(self, mock_search_results):
        """Test query enrichment with RAG context."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            mock_db.search_code.return_value = mock_search_results[:2]  # High relevance only

            builder = RAGContextBuilder("test_session")
            enriched, context = builder.enrich_query("How do I create a user?")

            assert "How do I create a user?" in enriched
            assert "Relevant Code from Project" in enriched
            assert context.results_count >= 1

    def test_enrich_query_no_results(self):
        """Test query enrichment with no results."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            mock_db.search_code.return_value = []

            builder = RAGContextBuilder("test_session")
            enriched, context = builder.enrich_query("unrelated query")

            assert enriched == "unrelated query"
            assert context.results_count == 0

    def test_context_length_limit(self):
        """Test that context respects MAX_CONTEXT_LENGTH."""
        builder = RAGContextBuilder("test_session")
        builder.MAX_CONTEXT_LENGTH = 500  # Set low limit for testing

        # Create large results
        large_results = [
            SearchResult(
                id=f"doc{i}",
                content="x" * 200 + f"\n\nFilename: large{i}.py\nLanguage: python\n\n" + "y" * 200,
                metadata={"filename": f"large{i}.py", "language": "python"},
                distance=0.2
            )
            for i in range(10)
        ]

        formatted, files = builder._format_results(large_results)

        # Should be truncated
        assert len(formatted) < 500 + 500  # Some buffer for formatting

    def test_search_error_handling(self):
        """Test graceful handling of search errors."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            mock_db.search_code.side_effect = Exception("Search failed")

            builder = RAGContextBuilder("test_session")
            context = builder.build_context("query")

            assert context.results_count == 0
            assert context.formatted_context == ""


class TestRAGContext:
    """Test RAGContext dataclass."""

    def test_rag_context_creation(self):
        """Test RAGContext dataclass."""
        context = RAGContext(
            formatted_context="## Code\n```python\npass\n```",
            results_count=3,
            files_referenced=["a.py", "b.py", "c.py"],
            avg_relevance=0.75,
            search_query="test query"
        )

        assert context.results_count == 3
        assert len(context.files_referenced) == 3
        assert context.avg_relevance == 0.75
        assert context.search_query == "test query"


class TestGetRAGBuilder:
    """Test get_rag_builder factory function."""

    def test_get_rag_builder_returns_instance(self):
        """Test factory returns RAGContextBuilder instance."""
        builder = get_rag_builder("session_123")
        assert isinstance(builder, RAGContextBuilder)
        assert builder.session_id == "session_123"

    def test_get_rag_builder_caches_instance(self):
        """Test that factory caches instances."""
        builder1 = get_rag_builder("session_cache_test")
        builder2 = get_rag_builder("session_cache_test")
        assert builder1 is builder2

    def test_get_rag_builder_different_sessions(self):
        """Test different sessions get different instances."""
        builder1 = get_rag_builder("session_a")
        builder2 = get_rag_builder("session_b")
        assert builder1 is not builder2


class TestRAGIntegration:
    """Integration tests for RAG context in agent workflow."""

    @pytest.mark.asyncio
    async def test_rag_enrichment_in_agent_manager(self):
        """Test RAG enrichment works in UnifiedAgentManager."""
        with patch('app.services.rag_context.vector_db') as mock_db:
            mock_db.search_code.return_value = [
                SearchResult(
                    id="test",
                    content="Test code",
                    metadata={"filename": "test.py", "language": "python"},
                    distance=0.3
                )
            ]

            # Import and test the enrichment function directly
            from app.agent.unified_agent_manager import UnifiedAgentManager

            manager = UnifiedAgentManager.__new__(UnifiedAgentManager)
            manager.supervisor = MagicMock()

            enriched, context = await manager._enrich_with_rag(
                "How do I use this?",
                "test_session"
            )

            assert "How do I use this?" in enriched
            assert context is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
