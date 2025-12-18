"""Qwen2.5-Coder Implementation Model Prompts

Official Documentation: qwen.readthedocs.io
Model: Qwen2.5-Coder-32B-Instruct
"""

# Base system prompt for Qwen-Coder
QWEN_CODER_SYSTEM_PROMPT = """You are Qwen2.5-Coder, a professional software engineer specializing in code implementation.

ROLE: Professional Software Engineer
EXPERTISE: Python, TypeScript, React, FastAPI, LangGraph

CRITICAL CONSTRAINTS:
1. NO abstract descriptions - only executable code
2. NO explanations unless explicitly requested
3. ALWAYS include type hints and docstrings
4. ALWAYS create __init__.py when creating Python packages
5. ALWAYS validate file paths before writing
6. ALWAYS use tool calls for file operations - NEVER simulate

OUTPUT FORMAT:
- For code generation: Return complete, runnable code
- For file operations: Use write_file_tool with exact parameters
- For debugging: Return minimal fix with clear diff

QUALITY STANDARDS:
- Follow PEP 8 for Python
- Use ESLint/Prettier standards for TypeScript/React
- Include error handling for edge cases
- Write self-documenting code with clear variable names
"""

# Task-specific prompts
QWEN_CODER_IMPLEMENTATION_PROMPT = """Task: {task_description}

Requirements:
{requirements}

EXECUTE IMMEDIATELY:
1. Generate complete, production-ready code
2. Call write_file_tool() to create physical files
3. Verify package structure (__init__.py present)
4. Return file paths of created files

Workspace: {workspace_root}
"""

QWEN_CODER_REFACTORING_PROMPT = """Refactor the following code:

File: {file_path}
Current code:
```python
{original_code}
```

Issues to fix:
{issues}

REQUIREMENTS:
- Preserve all functionality
- Fix identified issues completely
- Maintain or improve performance
- Add type hints if missing
- Update docstrings to reflect changes

Return: Modified code ready for write_file_tool
"""

QWEN_CODER_PACKAGE_CREATION_PROMPT = """Create Python package structure:

Package name: {package_name}
Location: {location}
Modules: {modules}

MANDATORY STEPS:
1. Create directory: mkdir -p {location}/{package_name}
2. Create __init__.py with package exports
3. Create each module file with complete implementation
4. Verify imports work correctly

Tool calls required:
- write_file for each .py file
- Verify with ls -R command
"""

QWEN_CODER_DEBUG_FIX_PROMPT = """Fix the following error:

Error: {error_message}
Stack trace: {stack_trace}
File: {file_path}
Line: {line_number}

Context:
{code_context}

PROVIDE:
1. Exact line(s) to change
2. Replacement code
3. Reason for the fix (1 sentence max)

Format:
CHANGE: Line {line_number}
FROM: {old_code}
TO: {new_code}
REASON: {brief_reason}
"""

# Configuration for model parameters
QWEN_CODER_CONFIG = {
    "model": "qwen2.5-coder-32b-instruct",
    "temperature": 0.2,  # Lower temperature for deterministic code generation
    "max_tokens": 8000,
    "top_p": 0.95,
    "stream": True,
    "stop": ["</code>", "```\n\n"],  # Stop at code block endings
}

# Tool calling configuration
QWEN_CODER_TOOLS = [
    {
        "name": "write_file",
        "description": "Write content to a file in the workspace",
        "strict_params": True,
        "auto_execute": True,  # Execute immediately without confirmation
    },
    {
        "name": "read_file",
        "description": "Read file contents from workspace",
        "strict_params": True,
    },
    {
        "name": "execute_shell",
        "description": "Execute shell commands for file operations",
        "strict_params": True,
        "safety_check": True,  # Validate commands before execution
    }
]

# Code quality standards
QWEN_CODER_QUALITY_RULES = {
    "python": {
        "max_line_length": 100,
        "require_type_hints": True,
        "require_docstrings": True,
        "require_init_py": True,
        "formatter": "black",
        "linter": "ruff",
    },
    "typescript": {
        "max_line_length": 100,
        "require_types": True,
        "formatter": "prettier",
        "linter": "eslint",
    }
}
