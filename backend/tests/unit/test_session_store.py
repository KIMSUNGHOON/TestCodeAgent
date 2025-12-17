"""Unit tests for thread-safe SessionStore"""

import pytest
import asyncio
from app.core.session_store import SessionStore, get_session_store


class TestSessionStore:
    """Test suite for SessionStore class"""

    @pytest.fixture
    def store(self):
        """Create a fresh SessionStore for each test"""
        return SessionStore()

    @pytest.mark.asyncio
    async def test_get_set_framework(self, store):
        """Test getting and setting framework"""
        # Default should be standard
        framework = await store.get_framework("session1")
        assert framework == "standard"

        # Set to deepagents
        await store.set_framework("session1", "deepagents")
        framework = await store.get_framework("session1")
        assert framework == "deepagents"

        # Set back to standard
        await store.set_framework("session1", "standard")
        framework = await store.get_framework("session1")
        assert framework == "standard"

    @pytest.mark.asyncio
    async def test_invalid_framework(self, store):
        """Test that invalid framework raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            await store.set_framework("session1", "invalid")

        assert "Invalid framework" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_set_workspace(self, store):
        """Test getting and setting workspace"""
        # Default should be returned
        workspace = await store.get_workspace("session1", default="/default/workspace")
        assert workspace == "/default/workspace"

        # Set custom workspace
        await store.set_workspace("session1", "/custom/workspace")
        workspace = await store.get_workspace("session1")
        assert workspace == "/custom/workspace"

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, store):
        """Test that sessions are isolated"""
        await store.set_framework("session1", "standard")
        await store.set_framework("session2", "deepagents")
        await store.set_workspace("session1", "/workspace1")
        await store.set_workspace("session2", "/workspace2")

        # Verify isolation
        assert await store.get_framework("session1") == "standard"
        assert await store.get_framework("session2") == "deepagents"
        assert await store.get_workspace("session1") == "/workspace1"
        assert await store.get_workspace("session2") == "/workspace2"

    @pytest.mark.asyncio
    async def test_delete_session(self, store):
        """Test deleting session data"""
        await store.set_framework("session1", "deepagents")
        await store.set_workspace("session1", "/workspace1")

        # Delete session
        await store.delete_session("session1")

        # Should return defaults
        assert await store.get_framework("session1") == "standard"
        assert await store.get_workspace("session1", "/default") == "/default"

    @pytest.mark.asyncio
    async def test_get_session_info(self, store):
        """Test getting session information"""
        await store.set_framework("session1", "deepagents")
        await store.set_workspace("session1", "/workspace1")

        info = await store.get_session_info("session1")
        assert info["session_id"] == "session1"
        assert info["framework"] == "deepagents"
        assert info["workspace"] == "/workspace1"
        assert info["exists"] is True

    @pytest.mark.asyncio
    async def test_list_sessions(self, store):
        """Test listing active sessions"""
        await store.set_framework("session1", "standard")
        await store.set_workspace("session2", "/workspace2")
        await store.set_framework("session3", "deepagents")

        sessions = await store.list_sessions()
        assert len(sessions) == 3
        assert "session1" in sessions
        assert "session2" in sessions
        assert "session3" in sessions

    @pytest.mark.asyncio
    async def test_len(self, store):
        """Test __len__ method"""
        assert len(store) == 0

        await store.set_framework("session1", "standard")
        assert len(store) == 1

        await store.set_workspace("session2", "/workspace2")
        assert len(store) == 2

        await store.delete_session("session1")
        assert len(store) == 1


class TestSessionStoreConcurrency:
    """Test thread safety and concurrency"""

    @pytest.mark.asyncio
    async def test_concurrent_writes_same_session(self):
        """Test that concurrent writes to same session are thread-safe"""
        store = SessionStore()

        async def set_framework(session_id, framework):
            await store.set_framework(session_id, framework)
            await asyncio.sleep(0.001)  # Simulate some work

        # Concurrent writes to same session
        tasks = [
            set_framework("session1", "standard" if i % 2 == 0 else "deepagents")
            for i in range(100)
        ]

        await asyncio.gather(*tasks)

        # Should have one of the values
        result = await store.get_framework("session1")
        assert result in ("standard", "deepagents")

    @pytest.mark.asyncio
    async def test_concurrent_reads_writes(self):
        """Test concurrent reads and writes"""
        store = SessionStore()
        await store.set_framework("session1", "standard")

        async def reader(session_id):
            for _ in range(10):
                framework = await store.get_framework(session_id)
                assert framework in ("standard", "deepagents")
                await asyncio.sleep(0.001)

        async def writer(session_id, framework):
            for _ in range(10):
                await store.set_framework(session_id, framework)
                await asyncio.sleep(0.001)

        # Run readers and writers concurrently
        tasks = [
            reader("session1"),
            reader("session1"),
            writer("session1", "deepagents"),
            writer("session1", "standard"),
        ]

        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_concurrent_different_sessions(self):
        """Test that different sessions can be accessed in parallel"""
        store = SessionStore()

        async def set_data(session_id, framework, workspace):
            await store.set_framework(session_id, framework)
            await store.set_workspace(session_id, workspace)

        # Different sessions should not block each other
        tasks = [
            set_data(f"session{i}", "standard" if i % 2 == 0 else "deepagents", f"/workspace{i}")
            for i in range(50)
        ]

        await asyncio.gather(*tasks)

        # Verify all sessions
        for i in range(50):
            expected_framework = "standard" if i % 2 == 0 else "deepagents"
            expected_workspace = f"/workspace{i}"

            assert await store.get_framework(f"session{i}") == expected_framework
            assert await store.get_workspace(f"session{i}") == expected_workspace


class TestGetSessionStore:
    """Test singleton pattern"""

    def test_singleton(self):
        """Test that get_session_store returns same instance"""
        store1 = get_session_store()
        store2 = get_session_store()
        assert store1 is store2

    @pytest.mark.asyncio
    async def test_singleton_persistence(self):
        """Test that data persists across get_session_store calls"""
        store1 = get_session_store()
        await store1.set_framework("test_session", "deepagents")

        store2 = get_session_store()
        framework = await store2.get_framework("test_session")
        assert framework == "deepagents"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
