"""Unit tests for UnifiedAgentManager.

Tests core functionality without requiring external services.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional


# Test fixtures
@dataclass
class MockContext:
    """Mock conversation context for testing."""
    session_id: str = "test-session-123"
    workspace: str = "/test/workspace"
    messages: list = None
    conversation_history: list = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.conversation_history is None:
            self.conversation_history = []

    def to_langchain_messages(self):
        return self.messages


class TestUnifiedAgentManagerBasics:
    """Basic functionality tests for UnifiedAgentManager."""

    def test_artifact_save_path_safety(self):
        """Test that path traversal attacks are prevented."""
        # Test safe_parts extraction logic
        test_cases = [
            ("normal.py", ["normal.py"]),
            ("../etc/passwd", ["etc", "passwd"]),
            ("..\\windows\\system32", ["windows", "system32"]),
            ("./safe/path.py", ["safe", "path.py"]),
            ("path/to/file.py", ["path", "to", "file.py"]),
            ("path\\to\\file.py", ["path", "to", "file.py"]),
        ]

        for filename, expected_parts in test_cases:
            # Simulate path traversal prevention logic
            safe_parts = []
            for part in filename.replace("\\", "/").split("/"):
                if part and part != ".." and part != ".":
                    safe_parts.append(part)

            assert safe_parts == expected_parts, f"Failed for {filename}"

    def test_artifact_action_types(self):
        """Test valid artifact action types."""
        valid_actions = ["created", "modified", "deleted", "skipped_duplicate"]

        for action in valid_actions:
            artifact = {
                "filename": "test.py",
                "content": "print('hello')",
                "action": action
            }
            assert artifact["action"] in valid_actions

    def test_response_type_enum_values(self):
        """Test that response types are properly defined."""
        from app.agent.handlers.base import HandlerResult, StreamUpdate

        # Test HandlerResult creation
        result = HandlerResult(
            content="Test content",
            success=True,
            artifacts=[]
        )
        assert result.content == "Test content"
        assert result.success is True
        assert result.error is None

        # Test error result
        error_result = HandlerResult(
            content="",
            success=False,
            error="Test error"
        )
        assert error_result.success is False
        assert error_result.error == "Test error"

    def test_stream_update_to_dict(self):
        """Test StreamUpdate.to_dict() includes all required fields."""
        from app.agent.handlers.base import StreamUpdate

        update = StreamUpdate(
            agent="TestAgent",
            update_type="progress",
            status="running",
            message="Processing...",
            streaming_content="Some content",
            data={"artifacts": [{"filename": "test.py"}]}
        )

        result = update.to_dict()

        # Check required fields
        assert result["agent"] == "TestAgent"
        assert result["node"] == "TestAgent"  # Frontend compatibility
        assert result["type"] == "progress"
        assert result["update_type"] == "progress"
        assert result["status"] == "running"
        assert result["message"] == "Processing..."
        assert result["streaming_content"] == "Some content"

        # Check updates field for frontend compatibility
        assert "updates" in result
        assert result["updates"]["streaming_content"] == "Some content"
        assert result["updates"]["artifacts"] == [{"filename": "test.py"}]


class TestBaseHandlerMethods:
    """Test BaseHandler utility methods."""

    def setup_method(self):
        """Set up test fixtures."""
        # Import inside method to avoid import errors when module not found
        pass

    def test_get_project_name_with_workspace(self):
        """Test _get_project_name extracts project name correctly."""
        from app.agent.handlers.base import BaseHandler

        # Create a concrete implementation for testing
        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        # Test with workspace
        context = MockContext(workspace="/path/to/my_project")
        project_name = handler._get_project_name(context)
        assert project_name == "my_project"

        # Test with Windows path
        context = MockContext(workspace="C:\\Users\\test\\projects\\TestProject")
        project_name = handler._get_project_name(context)
        assert project_name == "TestProject"

    def test_get_project_name_without_workspace(self):
        """Test _get_project_name returns empty string without workspace."""
        from app.agent.handlers.base import BaseHandler

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        # Test with None context
        assert handler._get_project_name(None) == ""

        # Test with context without workspace
        context = MockContext(workspace=None)
        assert handler._get_project_name(context) == ""

        # Test with empty workspace
        context = MockContext(workspace="")
        assert handler._get_project_name(context) == ""

    def test_create_error_result(self):
        """Test _create_error_result creates proper HandlerResult."""
        from app.agent.handlers.base import BaseHandler, HandlerResult

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        # Test with Exception
        error = ValueError("Test error message")
        result = handler._create_error_result(error)

        assert isinstance(result, HandlerResult)
        assert result.success is False
        assert result.content == ""
        assert result.error == "Test error message"

    def test_create_error_update(self):
        """Test _create_error_update creates proper StreamUpdate."""
        from app.agent.handlers.base import BaseHandler, StreamUpdate

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        error = RuntimeError("Stream error")
        update = handler._create_error_update(error)

        assert isinstance(update, StreamUpdate)
        assert update.update_type == "error"
        assert update.status == "error"
        assert update.message == "Stream error"
        assert update.agent == "TestHandler"

    def test_create_progress_update(self):
        """Test _create_progress_update creates proper StreamUpdate."""
        from app.agent.handlers.base import BaseHandler, StreamUpdate

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        update = handler._create_progress_update(
            message="Processing...",
            streaming_content="Some output",
            data={"key": "value"}
        )

        assert isinstance(update, StreamUpdate)
        assert update.update_type == "progress"
        assert update.status == "running"
        assert update.message == "Processing..."
        assert update.streaming_content == "Some output"
        assert update.data == {"key": "value"}

    def test_create_completed_update(self):
        """Test _create_completed_update creates proper StreamUpdate."""
        from app.agent.handlers.base import BaseHandler, StreamUpdate

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        artifacts = [{"filename": "test.py", "content": "print('test')"}]
        update = handler._create_completed_update(
            message="Done!",
            content="Full content here",
            artifacts=artifacts,
            extra_data={"token_usage": {"total": 100}}
        )

        assert isinstance(update, StreamUpdate)
        assert update.update_type == "completed"
        assert update.status == "completed"
        assert update.message == "Done!"
        assert update.streaming_content == "Full content here"
        assert update.data["full_content"] == "Full content here"
        assert update.data["artifacts"] == artifacts
        assert update.data["token_usage"]["total"] == 100

    def test_strip_think_tags(self):
        """Test _strip_think_tags removes think blocks correctly."""
        from app.agent.handlers.base import BaseHandler

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        # Test with think tags
        text_with_think = "<think>This is thinking</think>This is output"
        result = handler._strip_think_tags(text_with_think)
        assert result == "This is output"

        # Test with multiline think tags
        text_multiline = "<think>\nMulti\nline\nthinking\n</think>\nClean output"
        result = handler._strip_think_tags(text_multiline)
        assert "Clean output" in result
        assert "thinking" not in result

        # Test without think tags
        clean_text = "No think tags here"
        result = handler._strip_think_tags(clean_text)
        assert result == "No think tags here"

        # Test with empty string
        assert handler._strip_think_tags("") == ""
        assert handler._strip_think_tags(None) == ""

    def test_extract_code_blocks(self):
        """Test _extract_code_blocks parses markdown correctly."""
        from app.agent.handlers.base import BaseHandler

        class TestHandler(BaseHandler):
            async def execute(self, user_message, analysis, context):
                pass

        handler = TestHandler()

        markdown = """
Here is some code:

```python
def hello():
    print('Hello')
```

And more:

```javascript
console.log('test');
```
"""

        blocks = handler._extract_code_blocks(markdown)

        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert "def hello():" in blocks[0]["code"]
        assert blocks[1]["language"] == "javascript"
        assert "console.log" in blocks[1]["code"]


class TestSupervisorResponseType:
    """Test Supervisor response type detection methods."""

    def test_quick_qa_detection(self):
        """Test _is_quick_qa_request detects Q&A patterns."""
        from core.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(use_api=False)

        # Korean Q&A patterns
        assert supervisor._is_quick_qa_request("python이 뭐야") is True
        assert supervisor._is_quick_qa_request("차이점이 뭐야") is True
        assert supervisor._is_quick_qa_request("왜 이게 필요해") is True

        # English Q&A patterns
        assert supervisor._is_quick_qa_request("what is python") is True
        assert supervisor._is_quick_qa_request("explain how this works") is True

        # Should not match with code intent
        assert supervisor._is_quick_qa_request("뭐야 만들어줘") is False

    def test_planning_detection(self):
        """Test _is_planning_request detects planning patterns."""
        from core.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(use_api=False)

        # Korean planning patterns
        assert supervisor._is_planning_request("계획을 세워줘") is True
        assert supervisor._is_planning_request("아키텍처 설계") is True

        # English planning patterns
        assert supervisor._is_planning_request("design a system") is True
        assert supervisor._is_planning_request("what's the best architecture") is True
        assert supervisor._is_planning_request("how should i approach this") is True

        # Should not match unrelated
        assert supervisor._is_planning_request("hello world") is False

    def test_code_review_detection(self):
        """Test _is_code_review_request detects review patterns."""
        from core.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(use_api=False)

        # Korean review patterns with code keyword
        assert supervisor._is_code_review_request("코드 리뷰해줘") is True
        assert supervisor._is_code_review_request("코드 검토") is True

        # English review patterns with code keyword
        assert supervisor._is_code_review_request("review this code") is True
        assert supervisor._is_code_review_request("analyze the code") is True

        # Should not match without code keyword
        assert supervisor._is_code_review_request("리뷰해줘") is False
        assert supervisor._is_code_review_request("review this") is False

    def test_debugging_detection(self):
        """Test _is_debugging_request detects debug patterns."""
        from core.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(use_api=False)

        # Korean debug patterns
        assert supervisor._is_debugging_request("에러가 나요") is True
        assert supervisor._is_debugging_request("버그 수정") is True
        assert supervisor._is_debugging_request("왜 안돼") is True

        # English debug patterns
        assert supervisor._is_debugging_request("fix this error") is True
        assert supervisor._is_debugging_request("debug the issue") is True
        assert supervisor._is_debugging_request("it doesn't work") is True

        # Should not match unrelated
        assert supervisor._is_debugging_request("hello") is False

    def test_code_generation_detection(self):
        """Test _is_code_generation_request detects code patterns."""
        from core.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(use_api=False)

        # Korean code generation patterns
        assert supervisor._is_code_generation_request("만들어줘") is True
        assert supervisor._is_code_generation_request("구현해주세요") is True
        assert supervisor._is_code_generation_request("코드 작성") is True

        # English code generation patterns
        assert supervisor._is_code_generation_request("create a function") is True
        assert supervisor._is_code_generation_request("implement this feature") is True
        assert supervisor._is_code_generation_request("write the code") is True

        # Should not match unrelated
        assert supervisor._is_code_generation_request("hello") is False

    def test_determine_response_type_integration(self):
        """Test _determine_response_type routes correctly."""
        from core.supervisor import SupervisorAgent, ResponseType

        supervisor = SupervisorAgent(use_api=False)

        # Q&A should return QUICK_QA
        assert supervisor._determine_response_type("what is python") == ResponseType.QUICK_QA

        # Planning should return PLANNING
        assert supervisor._determine_response_type("design the architecture") == ResponseType.PLANNING

        # Code review should return CODE_REVIEW
        assert supervisor._determine_response_type("review this code") == ResponseType.CODE_REVIEW

        # Debug should return DEBUGGING
        assert supervisor._determine_response_type("fix this error") == ResponseType.DEBUGGING

        # Code generation should return CODE_GENERATION
        assert supervisor._determine_response_type("create a function") == ResponseType.CODE_GENERATION


class TestContextConfig:
    """Test ContextConfig constants."""

    def test_context_config_values(self):
        """Test ContextConfig has expected values."""
        from app.utils.context_manager import ContextConfig

        # Summary limits
        assert ContextConfig.MAX_FILES_IN_SUMMARY == 10
        assert ContextConfig.MAX_ERRORS_IN_SUMMARY == 5
        assert ContextConfig.MAX_DECISIONS_IN_SUMMARY == 5

        # Extraction limits
        assert ContextConfig.MAX_FILES_EXTRACTED == 20
        assert ContextConfig.MAX_ERRORS_EXTRACTED == 10
        assert ContextConfig.MAX_DECISIONS_EXTRACTED == 10
        assert ContextConfig.MAX_PREFERENCES_EXTRACTED == 5

        # Text limits
        assert ContextConfig.MAX_SENTENCE_LENGTH == 200
        assert ContextConfig.MAX_CONTENT_LENGTH == 1000

        # Agent filtering
        assert ContextConfig.RECENT_MESSAGES_FOR_AGENT == 5

        # Prompt formatting
        assert ContextConfig.MAX_CONTENT_IN_PROMPT == 1000
        assert ContextConfig.MAX_FILES_IN_PROMPT == 10


# Run tests
if __name__ == "__main__":
    print("Running UnifiedAgentManager tests...")

    # Run basic tests
    test_basics = TestUnifiedAgentManagerBasics()
    test_basics.test_artifact_save_path_safety()
    print("  [PASS] test_artifact_save_path_safety")

    test_basics.test_artifact_action_types()
    print("  [PASS] test_artifact_action_types")

    test_basics.test_response_type_enum_values()
    print("  [PASS] test_response_type_enum_values")

    test_basics.test_stream_update_to_dict()
    print("  [PASS] test_stream_update_to_dict")

    # Run BaseHandler tests
    test_handler = TestBaseHandlerMethods()
    test_handler.test_get_project_name_with_workspace()
    print("  [PASS] test_get_project_name_with_workspace")

    test_handler.test_get_project_name_without_workspace()
    print("  [PASS] test_get_project_name_without_workspace")

    test_handler.test_create_error_result()
    print("  [PASS] test_create_error_result")

    test_handler.test_create_error_update()
    print("  [PASS] test_create_error_update")

    test_handler.test_create_progress_update()
    print("  [PASS] test_create_progress_update")

    test_handler.test_create_completed_update()
    print("  [PASS] test_create_completed_update")

    test_handler.test_strip_think_tags()
    print("  [PASS] test_strip_think_tags")

    test_handler.test_extract_code_blocks()
    print("  [PASS] test_extract_code_blocks")

    # Run ContextConfig tests
    test_config = TestContextConfig()
    test_config.test_context_config_values()
    print("  [PASS] test_context_config_values")

    print("\nAll tests passed!")
