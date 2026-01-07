"""Tests for ConversationIndexer - Phase 3-D verification."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.conversation_indexer import (
    ConversationIndexer,
    ConversationSearchResult,
    get_conversation_indexer
)
from app.services.vector_db import SearchResult


class TestConversationIndexer:
    """Test ConversationIndexer functionality."""

    def test_indexer_creation(self):
        """Test ConversationIndexer instantiation."""
        indexer = ConversationIndexer("test_session")

        assert indexer.session_id == "test_session"
        assert indexer.MIN_MESSAGE_LENGTH == 20
        assert indexer.MAX_MESSAGE_LENGTH == 2000
        assert indexer._turn_counter == 0

    def test_index_message_short_message(self):
        """Test that short messages are skipped."""
        indexer = ConversationIndexer("test_session")

        # Message too short
        result = indexer.index_message("Hi", role="user")
        assert result is None

    def test_index_message_success(self):
        """Test successful message indexing."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.add_documents = MagicMock()

            indexer = ConversationIndexer("test_session")
            doc_id = indexer.index_message(
                "This is a longer test message that should be indexed",
                role="user",
                turn_number=1
            )

            assert doc_id is not None
            assert mock_db.add_documents.called

            # Check the call arguments
            call_args = mock_db.add_documents.call_args
            docs = call_args.kwargs.get('documents') or call_args[1].get('documents')
            metadatas = call_args.kwargs.get('metadatas') or call_args[1].get('metadatas')

            assert "[USER]" in docs[0]
            assert metadatas[0]["type"] == "conversation"
            assert metadatas[0]["role"] == "user"
            assert metadatas[0]["turn"] == 1

    def test_index_message_auto_turn(self):
        """Test automatic turn numbering."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.add_documents = MagicMock()

            indexer = ConversationIndexer("test_session")

            # First message - auto turn 1
            indexer.index_message("First message that is long enough", role="user")
            assert indexer._turn_counter == 1

            # Second message - auto turn 2
            indexer.index_message("Second message that is long enough", role="assistant")
            assert indexer._turn_counter == 2

    def test_index_message_truncation(self):
        """Test message truncation for long messages."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.add_documents = MagicMock()

            indexer = ConversationIndexer("test_session")
            indexer.MAX_MESSAGE_LENGTH = 50

            long_message = "x" * 100
            indexer.index_message(long_message, role="user")

            call_args = mock_db.add_documents.call_args
            docs = call_args.kwargs.get('documents') or call_args[1].get('documents')

            # Should be truncated
            assert "truncated" in docs[0]

    def test_index_conversation_batch(self):
        """Test batch indexing of multiple messages."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.add_documents = MagicMock()

            indexer = ConversationIndexer("test_session")

            messages = [
                {"role": "user", "content": "This is the first user message in the conversation"},
                {"role": "assistant", "content": "This is the assistant response to the user"},
                {"role": "user", "content": "Follow up question from the user about something"}
            ]

            indexed_count = indexer.index_conversation(messages)

            assert indexed_count == 3
            assert mock_db.add_documents.call_count == 3

    def test_search_conversation(self):
        """Test conversation search."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.search.return_value = [
                SearchResult(
                    id="conv1",
                    content="[USER] How do I create a user?",
                    metadata={
                        "type": "conversation",
                        "role": "user",
                        "session_id": "test_session",
                        "turn": 1,
                        "timestamp": "2026-01-08T10:00:00"
                    },
                    distance=0.3
                ),
                SearchResult(
                    id="conv2",
                    content="[ASSISTANT] To create a user, use the create_user method",
                    metadata={
                        "type": "conversation",
                        "role": "assistant",
                        "session_id": "test_session",
                        "turn": 2,
                        "timestamp": "2026-01-08T10:01:00"
                    },
                    distance=0.4
                )
            ]

            indexer = ConversationIndexer("test_session")
            results = indexer.search_conversation("user creation", min_relevance=0.5)

            assert len(results) == 2
            assert isinstance(results[0], ConversationSearchResult)
            assert results[0].role == "user"
            assert results[0].turn_number == 1
            assert results[0].relevance > 0.5

    def test_search_conversation_filtering(self):
        """Test that low relevance results are filtered."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.search.return_value = [
                SearchResult(
                    id="conv1",
                    content="[USER] Relevant message",
                    metadata={"type": "conversation", "role": "user", "turn": 1},
                    distance=0.3  # 70% relevance
                ),
                SearchResult(
                    id="conv2",
                    content="[USER] Irrelevant message",
                    metadata={"type": "conversation", "role": "user", "turn": 2},
                    distance=0.8  # 20% relevance
                )
            ]

            indexer = ConversationIndexer("test_session")
            results = indexer.search_conversation("query", min_relevance=0.5)

            # Only high relevance result should be included
            assert len(results) == 1
            assert results[0].relevance >= 0.5

    def test_format_search_results(self):
        """Test formatting of search results."""
        indexer = ConversationIndexer("test_session")

        results = [
            ConversationSearchResult(
                content="How do I create a user?",
                role="user",
                turn_number=1,
                relevance=0.75,
                timestamp="2026-01-08T10:00:00"
            ),
            ConversationSearchResult(
                content="Use the create_user method",
                role="assistant",
                turn_number=2,
                relevance=0.65,
                timestamp="2026-01-08T10:01:00"
            )
        ]

        formatted = indexer.format_search_results(results)

        assert "Relevant Previous Conversations" in formatted
        assert "Turn 1" in formatted
        assert "User" in formatted
        assert "Assistant" in formatted
        assert "75" in formatted  # Relevance percentage

    def test_format_empty_results(self):
        """Test formatting with no results."""
        indexer = ConversationIndexer("test_session")
        formatted = indexer.format_search_results([])
        assert formatted == ""

    def test_clear_session(self):
        """Test clearing session index."""
        with patch('app.services.conversation_indexer.vector_db') as mock_db:
            mock_db.delete_by_session = MagicMock()

            indexer = ConversationIndexer("test_session")
            indexer._turn_counter = 10

            indexer.clear_session()

            mock_db.delete_by_session.assert_called_once_with("test_session")
            assert indexer._turn_counter == 0

    def test_generate_doc_id(self):
        """Test document ID generation."""
        indexer = ConversationIndexer("test_session")

        id1 = indexer._generate_doc_id("content1", 1)
        id2 = indexer._generate_doc_id("content2", 1)
        id3 = indexer._generate_doc_id("content1", 1)

        # Different content = different ID
        assert id1 != id2
        # Same content and turn = same ID
        assert id1 == id3


class TestConversationSearchResult:
    """Test ConversationSearchResult dataclass."""

    def test_creation(self):
        """Test dataclass creation."""
        result = ConversationSearchResult(
            content="Test content",
            role="user",
            turn_number=5,
            relevance=0.85,
            timestamp="2026-01-08T10:00:00"
        )

        assert result.content == "Test content"
        assert result.role == "user"
        assert result.turn_number == 5
        assert result.relevance == 0.85


class TestGetConversationIndexer:
    """Test get_conversation_indexer factory function."""

    def test_returns_instance(self):
        """Test factory returns ConversationIndexer instance."""
        indexer = get_conversation_indexer("session_123")
        assert isinstance(indexer, ConversationIndexer)
        assert indexer.session_id == "session_123"

    def test_caches_instance(self):
        """Test that factory caches instances."""
        indexer1 = get_conversation_indexer("cache_test_session")
        indexer2 = get_conversation_indexer("cache_test_session")
        assert indexer1 is indexer2

    def test_different_sessions(self):
        """Test different sessions get different instances."""
        indexer1 = get_conversation_indexer("session_a")
        indexer2 = get_conversation_indexer("session_b")
        assert indexer1 is not indexer2


class TestRAGContextBuilderConversation:
    """Test RAGContextBuilder conversation search integration."""

    def test_enrich_query_with_conversation(self):
        """Test query enrichment includes conversation search."""
        with patch('app.services.rag_context.vector_db') as mock_code_db:
            with patch('app.services.rag_context.get_conversation_indexer') as mock_get_indexer:
                # Mock code search
                mock_code_db.search_code.return_value = []

                # Mock conversation search
                mock_indexer = MagicMock()
                mock_indexer.search_conversation.return_value = [
                    ConversationSearchResult(
                        content="Previous relevant conversation",
                        role="user",
                        turn_number=1,
                        relevance=0.7,
                        timestamp=""
                    )
                ]
                mock_indexer.format_search_results.return_value = "## Relevant Conversations\n..."
                mock_get_indexer.return_value = mock_indexer

                from app.services.rag_context import RAGContextBuilder

                builder = RAGContextBuilder("test_session")
                enriched, context = builder.enrich_query(
                    "How do I do this?",
                    include_conversation=True
                )

                assert context.conversation_results == 1
                assert "Relevant Conversations" in enriched or context.conversation_context != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
