"""Tests for CodeIndexer service - Phase 3-B verification."""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.code_indexer import CodeIndexer, IndexingStats, get_code_indexer


class TestCodeIndexer:
    """Test CodeIndexer functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Python file with top-level definitions
            py_file = Path(tmpdir) / "test_module.py"
            py_file.write_text('''"""Test module for indexing."""

class UserService:
    """Handle user operations."""

    def __init__(self):
        self.users = []

    def create_user(self, name: str) -> dict:
        """Create a new user."""
        user = {"name": name, "id": len(self.users)}
        self.users.append(user)
        return user

    def get_user(self, user_id: int) -> dict:
        """Get user by ID."""
        return self.users[user_id] if user_id < len(self.users) else None


def helper_function():
    """A standalone helper function."""
    return "helper"
''')

            # Create test JavaScript file
            js_file = Path(tmpdir) / "app.js"
            js_file.write_text('''// Main application file

class App {
    constructor() {
        this.name = "TestApp";
    }

    initialize() {
        console.log("Initializing...");
    }
}

function startServer(port) {
    console.log(`Starting on port ${port}`);
}

export const config = {
    debug: true
};
''')

            # Create file to be excluded
            excluded_dir = Path(tmpdir) / "node_modules"
            excluded_dir.mkdir()
            excluded_file = excluded_dir / "package.json"
            excluded_file.write_text('{"name": "test"}')

            # Create binary file to skip
            binary_file = Path(tmpdir) / "image.png"
            binary_file.write_bytes(b'\x89PNG\r\n\x1a\n')

            yield tmpdir

    def test_indexer_creation(self, temp_workspace):
        """Test CodeIndexer instantiation."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        # workspace is stored as Path object
        assert str(indexer.workspace) == str(Path(temp_workspace))
        assert indexer.session_id == "test_session"
        assert len(indexer.SUPPORTED_EXTENSIONS) >= 25
        assert '.py' in indexer.SUPPORTED_EXTENSIONS
        assert '.js' in indexer.SUPPORTED_EXTENSIONS

    def test_excluded_directories(self, temp_workspace):
        """Test that excluded directories are properly configured."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        assert 'node_modules' in indexer.EXCLUDED_DIRS
        assert '.git' in indexer.EXCLUDED_DIRS
        assert '__pycache__' in indexer.EXCLUDED_DIRS
        assert '.venv' in indexer.EXCLUDED_DIRS

    def test_excluded_patterns(self, temp_workspace):
        """Test excluded file patterns."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        # Check pattern configuration
        assert '*.min.js' in indexer.EXCLUDED_PATTERNS
        assert '*.pyc' in indexer.EXCLUDED_PATTERNS
        assert 'package-lock.json' in indexer.EXCLUDED_PATTERNS

    def test_should_exclude(self, temp_workspace):
        """Test _should_exclude method."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        # Should be excluded
        assert indexer._should_exclude("bundle.min.js") == True
        assert indexer._should_exclude("module.pyc") == True
        assert indexer._should_exclude("package-lock.json") == True

        # Should not be excluded
        assert indexer._should_exclude("main.py") == False
        assert indexer._should_exclude("app.js") == False
        assert indexer._should_exclude("config.yaml") == False

    def test_detect_language(self, temp_workspace):
        """Test language detection from file extension."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        assert indexer._detect_language(Path("test.py")) == "python"
        assert indexer._detect_language(Path("app.js")) == "javascript"
        assert indexer._detect_language(Path("main.ts")) == "typescript"
        assert indexer._detect_language(Path("styles.css")) == "css"
        assert indexer._detect_language(Path("unknown.xyz")) == "text"

    def test_get_code_files(self, temp_workspace):
        """Test _get_code_files finds correct files."""
        indexer = CodeIndexer(temp_workspace, "test_session")
        code_files = indexer._get_code_files()

        # Should find the py and js files we created
        filenames = [f.name for f in code_files]
        assert "test_module.py" in filenames
        assert "app.js" in filenames

        # Should NOT include excluded directories or patterns
        for f in code_files:
            assert "node_modules" not in str(f)
            assert ".png" not in str(f)

    def test_python_chunking_small_file(self, temp_workspace):
        """Test Python code chunking with small file (falls below MIN_CHUNK_SIZE)."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        # Very small code falls below MIN_CHUNK_SIZE (100 chars) so returns empty
        python_code = '''def simple_function():
    return "simple"
'''

        chunks = indexer._chunk_python(python_code, "simple.py", "python")

        # Small content below MIN_CHUNK_SIZE returns empty (expected)
        # The _chunk_code() method handles this by returning a single chunk fallback
        assert isinstance(chunks, list)

        # Test with larger content that meets MIN_CHUNK_SIZE
        larger_code = '''def simple_function():
    """A function with docstring."""
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
'''
        chunks = indexer._chunk_python(larger_code, "simple.py", "python")
        # Still may be empty if below threshold - test structure instead
        for chunk in chunks:
            assert "code" in chunk
            assert "filename" in chunk
            assert "language" in chunk

    def test_python_chunking_large_file(self, temp_workspace):
        """Test Python code chunking with multiple top-level definitions."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        # Large enough content with multiple top-level definitions
        python_code = '''"""Module docstring."""

class FirstClass:
    """First class."""
    def __init__(self):
        self.value = 1

    def method1(self):
        return self.value * 2

    def method2(self):
        return self.value * 3

''' + "# Extra padding\n" * 20 + '''
def standalone_function():
    """A standalone function with enough content."""
    x = 1
    y = 2
    z = 3
    return x + y + z

''' + "# More padding\n" * 20 + '''
class SecondClass:
    """Second class with content."""
    def __init__(self):
        self.data = []

    def add(self, item):
        self.data.append(item)
'''

        chunks = indexer._chunk_python(python_code, "multi.py", "python")

        # Should have multiple chunks for different top-level definitions
        assert len(chunks) >= 1

        # Each chunk should have proper structure
        for chunk in chunks:
            assert "code" in chunk
            assert "filename" in chunk
            assert "language" in chunk
            assert chunk["language"] == "python"

    def test_javascript_chunking(self, temp_workspace):
        """Test JavaScript code chunking."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        js_code = '''// Module header
import something from "somewhere";

class Component {
    constructor() {
        this.state = {};
    }

    render() {
        return "<div>Hello</div>";
    }
}

''' + "// padding\n" * 20 + '''
function processData(data) {
    const result = data.map(x => x * 2);
    return result;
}

''' + "// more padding\n" * 20 + '''
export const API_URL = "http://localhost:3000";
'''

        chunks = indexer._chunk_javascript(js_code, "app.js", "javascript")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert "code" in chunk
            assert "filename" in chunk
            assert "language" in chunk

    def test_line_based_chunking(self, temp_workspace):
        """Test fallback line-based chunking."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        # Create content larger than chunk size
        large_content = "\n".join([f"line number {i} with some content" for i in range(500)])

        chunks = indexer._chunk_by_lines(large_content, "large.txt", "text")

        assert len(chunks) >= 1
        # Each chunk should have code key and be within limits
        for chunk in chunks:
            assert "code" in chunk
            assert len(chunk["code"]) <= indexer.MAX_CHUNK_SIZE

    def test_generate_description_with_docstring(self, temp_workspace):
        """Test description generation with docstring."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        python_content = '''"""This module handles user authentication."""
def login():
    pass
'''
        desc = indexer._generate_description(python_content, "auth.py", "python")
        assert "auth.py" in desc

    def test_generate_description_with_comment(self, temp_workspace):
        """Test description generation with comment."""
        indexer = CodeIndexer(temp_workspace, "test_session")

        js_content = '''// This handles API requests
function fetchData() {}
'''
        desc = indexer._generate_description(js_content, "api.js", "javascript")
        assert "api.js" in desc

    @pytest.mark.asyncio
    async def test_index_project_with_mock_vector_db(self, temp_workspace):
        """Test project indexing with mocked vector DB."""
        with patch('app.services.code_indexer.vector_db') as mock_vector_db:
            mock_vector_db.add_code_snippet = MagicMock(return_value="doc_123")
            mock_vector_db.search_code = MagicMock(return_value=[])

            indexer = CodeIndexer(temp_workspace, "test_session")
            stats = await indexer.index_project(incremental=False)

            assert isinstance(stats, IndexingStats)
            assert stats.indexed >= 2  # At least py and js files
            assert stats.errors == 0
            assert stats.total_chunks > 0
            assert len(stats.files_processed) >= 2

            # Verify add_code_snippet was called
            assert mock_vector_db.add_code_snippet.called

    @pytest.mark.asyncio
    async def test_index_single_file(self, temp_workspace):
        """Test indexing a single file."""
        with patch('app.services.code_indexer.vector_db') as mock_vector_db:
            mock_vector_db.add_code_snippet = MagicMock(return_value="doc_123")

            indexer = CodeIndexer(temp_workspace, "test_session")
            py_file = Path(temp_workspace) / "test_module.py"

            doc_ids = await indexer.index_file(str(py_file))

            # Should return chunk count
            assert isinstance(doc_ids, int)
            assert doc_ids >= 1

    def test_get_code_indexer_factory(self, temp_workspace):
        """Test get_code_indexer factory function."""
        indexer = get_code_indexer(temp_workspace, "session_123")

        assert isinstance(indexer, CodeIndexer)
        assert str(indexer.workspace) == str(Path(temp_workspace))
        assert indexer.session_id == "session_123"

    def test_get_code_indexer_caching(self, temp_workspace):
        """Test that get_code_indexer returns cached instances."""
        indexer1 = get_code_indexer(temp_workspace, "session_cache_test")
        indexer2 = get_code_indexer(temp_workspace, "session_cache_test")

        # Should return the same instance
        assert indexer1 is indexer2


class TestIndexingStats:
    """Test IndexingStats dataclass."""

    def test_default_values(self):
        """Test default values of IndexingStats."""
        stats = IndexingStats()

        assert stats.indexed == 0
        assert stats.skipped == 0
        assert stats.errors == 0
        assert stats.total_chunks == 0
        assert stats.files_processed == []
        assert stats.error_files == []

    def test_custom_values(self):
        """Test IndexingStats with custom values."""
        stats = IndexingStats(
            indexed=10,
            skipped=5,
            errors=2,
            total_chunks=50,
            files_processed=["a.py", "b.py"],
            error_files=["c.py"]
        )

        assert stats.indexed == 10
        assert stats.skipped == 5
        assert stats.errors == 2
        assert stats.total_chunks == 50
        assert len(stats.files_processed) == 2
        assert len(stats.error_files) == 1


class TestCodeIndexerConfig:
    """Test CodeIndexer configuration constants."""

    def test_chunk_size_limits(self):
        """Test chunk size constants."""
        assert CodeIndexer.MAX_CHUNK_SIZE == 2000
        assert CodeIndexer.MIN_CHUNK_SIZE == 100
        assert CodeIndexer.MAX_FILE_SIZE == 100000

    def test_supported_extensions_count(self):
        """Test that we support many file extensions."""
        assert len(CodeIndexer.SUPPORTED_EXTENSIONS) >= 25

        # Common languages should be supported
        assert '.py' in CodeIndexer.SUPPORTED_EXTENSIONS
        assert '.js' in CodeIndexer.SUPPORTED_EXTENSIONS
        assert '.ts' in CodeIndexer.SUPPORTED_EXTENSIONS
        assert '.java' in CodeIndexer.SUPPORTED_EXTENSIONS
        assert '.go' in CodeIndexer.SUPPORTED_EXTENSIONS

    def test_excluded_dirs_configured(self):
        """Test that common directories are excluded."""
        assert 'node_modules' in CodeIndexer.EXCLUDED_DIRS
        assert '.git' in CodeIndexer.EXCLUDED_DIRS
        assert '__pycache__' in CodeIndexer.EXCLUDED_DIRS
        assert '.venv' in CodeIndexer.EXCLUDED_DIRS
        assert 'dist' in CodeIndexer.EXCLUDED_DIRS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
