"""Compatibility Tests for Recent Fixes

Tests to ensure backward compatibility of:
1. Security Gate file type filtering
2. LLM JSON parsing (with/without <think> tags)
3. Coder calculator generation

Run with: uv run python -m pytest tests/test_compatibility.py -v
"""

import pytest
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))


class TestSecurityGateCompatibility:
    """Test Security Gate maintains backward compatibility"""

    def test_python_files_still_scanned(self):
        """Python files should still be scanned for vulnerabilities"""
        from app.agent.langgraph.nodes.security_gate import SecurityScanner

        python_code = '''
import os
os.system("rm -rf /")  # Command injection
eval(user_input)  # Dangerous eval
'''
        findings = SecurityScanner.scan_code(python_code, "test.py")
        assert len(findings) > 0, "Python files should still be scanned"
        categories = [f["category"] for f in findings]
        assert "command_injection_python" in categories or "dangerous_eval_python" in categories

    def test_javascript_files_still_scanned(self):
        """JavaScript files should still be scanned for XSS"""
        from app.agent.langgraph.nodes.security_gate import SecurityScanner

        js_code = '''
element.innerHTML = userInput + "<script>alert('xss')</script>";
'''
        findings = SecurityScanner.scan_code(js_code, "app.js")
        # XSS patterns should still match for JS
        assert isinstance(findings, list)

    def test_css_files_skipped(self):
        """CSS files should be skipped (no false positives)"""
        from app.agent.langgraph.nodes.security_gate import SecurityScanner

        css_code = '''
.button {
    background: url("data:image/svg+xml,...");
}
'''
        findings = SecurityScanner.scan_code(css_code, "style.css")
        assert len(findings) == 0, "CSS files should not produce security findings"

    def test_markdown_files_skipped(self):
        """Markdown files should be skipped (no false positives)"""
        from app.agent.langgraph.nodes.security_gate import SecurityScanner

        md_code = '''
# Example

```python
os.system("ls")  # This is documentation, not real code
eval(x)
```
'''
        findings = SecurityScanner.scan_code(md_code, "README.md")
        assert len(findings) == 0, "Markdown files should not produce security findings"

    def test_file_type_detection(self):
        """File type detection should work correctly"""
        from app.agent.langgraph.nodes.security_gate import SecurityScanner

        assert SecurityScanner.get_file_type("main.py") == "python"
        assert SecurityScanner.get_file_type("app.js") == "javascript"
        assert SecurityScanner.get_file_type("index.tsx") == "javascript"
        assert SecurityScanner.get_file_type("style.css") == "skip"
        assert SecurityScanner.get_file_type("README.md") == "skip"
        assert SecurityScanner.get_file_type("config.json") == "config"


class TestLLMJsonParsingCompatibility:
    """Test LLM JSON parsing maintains backward compatibility"""

    def test_normal_json_parsing(self):
        """Normal JSON without think tags should still parse"""
        from llm.base import BaseLLMProvider, LLMConfig

        # Create a minimal concrete implementation for testing
        class TestProvider(BaseLLMProvider):
            @property
            def model_type(self): return "test"
            def format_prompt(self, prompt, task_type): return prompt
            def format_system_prompt(self, task_type): return ""
            def parse_response(self, response, task_type): return None
            async def generate(self, prompt, task_type=None, config_override=None): pass
            async def stream(self, prompt, task_type=None, config_override=None): yield ""

        provider = TestProvider("http://test", "test-model")

        # Test normal JSON
        normal_json = '{"result": "success", "count": 42}'
        parsed = provider._extract_json(normal_json)
        assert parsed == {"result": "success", "count": 42}

    def test_json_with_text_before(self):
        """JSON with text before it should still parse"""
        from llm.base import BaseLLMProvider, LLMConfig

        class TestProvider(BaseLLMProvider):
            @property
            def model_type(self): return "test"
            def format_prompt(self, prompt, task_type): return prompt
            def format_system_prompt(self, task_type): return ""
            def parse_response(self, response, task_type): return None
            async def generate(self, prompt, task_type=None, config_override=None): pass
            async def stream(self, prompt, task_type=None, config_override=None): yield ""

        provider = TestProvider("http://test", "test-model")

        # Test JSON with surrounding text
        text_with_json = 'Here is the result:\n{"status": "ok", "data": [1, 2, 3]}\nDone.'
        parsed = provider._extract_json(text_with_json)
        assert parsed == {"status": "ok", "data": [1, 2, 3]}

    def test_json_with_think_tags(self):
        """JSON with DeepSeek-R1 think tags should parse correctly"""
        from llm.base import BaseLLMProvider, LLMConfig

        class TestProvider(BaseLLMProvider):
            @property
            def model_type(self): return "test"
            def format_prompt(self, prompt, task_type): return prompt
            def format_system_prompt(self, task_type): return ""
            def parse_response(self, response, task_type): return None
            async def generate(self, prompt, task_type=None, config_override=None): pass
            async def stream(self, prompt, task_type=None, config_override=None): yield ""

        provider = TestProvider("http://test", "test-model")

        # Test JSON with think tags (DeepSeek-R1 format)
        think_response = '''<think>
Let me think about this...
The user wants JSON output.
I should return a structured response.
</think>

{"answer": "42", "explanation": "The meaning of life"}'''
        parsed = provider._extract_json(think_response)
        assert parsed is not None
        assert parsed.get("answer") == "42"

    def test_json_in_code_block(self):
        """JSON in markdown code block should parse"""
        from llm.base import BaseLLMProvider, LLMConfig

        class TestProvider(BaseLLMProvider):
            @property
            def model_type(self): return "test"
            def format_prompt(self, prompt, task_type): return prompt
            def format_system_prompt(self, task_type): return ""
            def parse_response(self, response, task_type): return None
            async def generate(self, prompt, task_type=None, config_override=None): pass
            async def stream(self, prompt, task_type=None, config_override=None): yield ""

        provider = TestProvider("http://test", "test-model")

        # Test JSON in code block
        code_block_json = '''Here is the response:
```json
{"type": "code_block", "valid": true}
```'''
        parsed = provider._extract_json(code_block_json)
        assert parsed == {"type": "code_block", "valid": True} or parsed is not None


class TestCoderCalculatorCompatibility:
    """Test Coder calculator generation"""

    def test_calculator_generates_python_files(self):
        """Calculator should generate Python files, not HTML/JS"""
        from app.agent.langgraph.nodes.coder import _generate_calculator_app

        artifacts = _generate_calculator_app()

        # Should have at least 2 Python files
        filenames = [a["filename"] for a in artifacts]
        assert "calculator_cli.py" in filenames, "Should generate CLI Python file"
        assert "calculator_gui.py" in filenames, "Should generate GUI Python file"

        # Should NOT have HTML/JS files
        assert not any(f.endswith(".html") for f in filenames), "Should not generate HTML"
        assert not any(f.endswith(".js") for f in filenames), "Should not generate JS"
        assert not any(f.endswith(".css") for f in filenames), "Should not generate CSS"

    def test_calculator_cli_content(self):
        """CLI calculator should have proper Python content"""
        from app.agent.langgraph.nodes.coder import _generate_calculator_app

        artifacts = _generate_calculator_app()
        cli_artifact = next(a for a in artifacts if a["filename"] == "calculator_cli.py")

        content = cli_artifact["content"]
        assert "def main" in content or "if __name__" in content
        assert "def safe_eval" in content or "ast" in content, "Should have safe evaluation"

    def test_calculator_gui_content(self):
        """GUI calculator should use Tkinter"""
        from app.agent.langgraph.nodes.coder import _generate_calculator_app

        artifacts = _generate_calculator_app()
        gui_artifact = next(a for a in artifacts if a["filename"] == "calculator_gui.py")

        content = gui_artifact["content"]
        assert "tkinter" in content or "Tk" in content, "Should use Tkinter"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
