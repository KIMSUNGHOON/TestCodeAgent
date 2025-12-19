"""Architect Agent Node - Project Structure & Design

This agent analyzes requirements and designs:
- Project directory structure
- Module/file organization
- API schemas and endpoints
- Data models
- Technology stack decisions
- Dependency graph

Uses DeepSeek-R1 for reasoning about architecture decisions.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.agent.langgraph.schemas.state import QualityGateState, DebugLog

logger = logging.getLogger(__name__)


# Architecture Design Prompt
ARCHITECT_SYSTEM_PROMPT = """You are an Expert Software Architect with 20+ years of experience.

Your role is to analyze requirements and design a comprehensive project structure BEFORE any code is written.

CRITICAL RESPONSIBILITIES:
1. Analyze the user's requirements thoroughly
2. Design optimal directory/file structure
3. Define module boundaries and responsibilities
4. Specify API endpoints and schemas
5. Define data models
6. Choose appropriate technology stack
7. Consider scalability, maintainability, and security

OUTPUT FORMAT (JSON):
```json
{
    "project_name": "project-name",
    "description": "Brief description",
    "tech_stack": {
        "language": "python/typescript/etc",
        "framework": "fastapi/react/etc",
        "database": "postgresql/mongodb/etc",
        "other": ["redis", "celery"]
    },
    "directory_structure": {
        "src/": {
            "description": "Main source code",
            "subdirs": {
                "api/": "API endpoints",
                "models/": "Data models",
                "services/": "Business logic",
                "utils/": "Utility functions"
            }
        },
        "tests/": "Test files",
        "docs/": "Documentation"
    },
    "files_to_create": [
        {
            "path": "src/main.py",
            "purpose": "Application entry point",
            "dependencies": ["src/api/routes.py"],
            "priority": 1
        }
    ],
    "api_endpoints": [
        {
            "method": "POST",
            "path": "/api/users",
            "description": "Create new user",
            "request_schema": {"name": "string", "email": "string"},
            "response_schema": {"id": "integer", "name": "string"}
        }
    ],
    "data_models": [
        {
            "name": "User",
            "fields": {"id": "int", "name": "str", "email": "str"},
            "relationships": []
        }
    ],
    "implementation_phases": [
        {
            "phase": 1,
            "name": "Core Setup",
            "files": ["src/main.py", "src/config.py"],
            "description": "Set up project foundation"
        },
        {
            "phase": 2,
            "name": "Data Layer",
            "files": ["src/models/user.py", "src/db/connection.py"],
            "description": "Implement data models"
        }
    ],
    "parallel_tasks": [
        {
            "group": "api_endpoints",
            "tasks": ["src/api/users.py", "src/api/auth.py"],
            "can_parallelize": true,
            "reason": "Independent API modules"
        }
    ],
    "estimated_complexity": "moderate",
    "estimated_files": 15,
    "requires_human_review": true,
    "review_reason": "Architecture decisions need validation"
}
```

IMPORTANT:
- Be thorough but practical
- Consider real-world best practices
- Identify what can be parallelized
- Flag anything that needs human review
"""

ARCHITECT_USER_PROMPT = """Analyze the following request and design a complete project architecture:

USER REQUEST:
{user_request}

WORKSPACE: {workspace_root}

SUPERVISOR ANALYSIS:
- Task Type: {task_type}
- Complexity: {complexity}
- Required Agents: {required_agents}

Please provide a comprehensive architecture design in the JSON format specified.
Think step by step about:
1. What is the user actually trying to build?
2. What are the core components needed?
3. How should files be organized?
4. What can be built in parallel?
5. What needs human review before proceeding?
"""


def architect_node(state: QualityGateState) -> Dict:
    """Architect Node: Design project structure before implementation

    This node runs AFTER supervisor but BEFORE coders.
    It creates a blueprint for the entire project.

    Args:
        state: Current workflow state

    Returns:
        State updates with architecture design
    """
    start_time = time.time()
    logger.info("🏗️ Architect Node: Designing project structure...")

    user_request = state["user_request"]
    workspace_root = state["workspace_root"]
    supervisor_analysis = state.get("supervisor_analysis", {})
    enable_debug = state.get("enable_debug", True)

    debug_logs: List[DebugLog] = []

    # Add start log
    if enable_debug:
        debug_logs.append(DebugLog(
            timestamp=datetime.utcnow().isoformat(),
            node="architect",
            agent="ArchitectAgent",
            event_type="thinking",
            content="Starting architecture design...",
            metadata={"phase": "start"},
            token_usage=None
        ))

    # Build the prompt
    prompt = ARCHITECT_USER_PROMPT.format(
        user_request=user_request,
        workspace_root=workspace_root,
        task_type=supervisor_analysis.get("task_type", "implementation"),
        complexity=supervisor_analysis.get("complexity", "moderate"),
        required_agents=supervisor_analysis.get("required_agents", [])
    )

    # For now, generate a rule-based architecture
    # TODO: Integrate with DeepSeek-R1 for intelligent design
    architecture = _generate_architecture(user_request, workspace_root, supervisor_analysis)

    # Calculate execution time
    execution_time = time.time() - start_time

    # Add completion log
    if enable_debug:
        debug_logs.append(DebugLog(
            timestamp=datetime.utcnow().isoformat(),
            node="architect",
            agent="ArchitectAgent",
            event_type="result",
            content=f"Architecture design complete: {architecture['estimated_files']} files planned",
            metadata={
                "files_count": architecture["estimated_files"],
                "phases": len(architecture.get("implementation_phases", [])),
                "parallel_groups": len(architecture.get("parallel_tasks", [])),
                "execution_time_seconds": round(execution_time, 2)
            },
            token_usage=None
        ))

    logger.info(f"✅ Architecture Design Complete:")
    logger.info(f"   Project: {architecture['project_name']}")
    logger.info(f"   Files: {architecture['estimated_files']}")
    logger.info(f"   Phases: {len(architecture.get('implementation_phases', []))}")
    logger.info(f"   Parallel Groups: {len(architecture.get('parallel_tasks', []))}")
    logger.info(f"   Execution Time: {execution_time:.2f}s")

    return {
        "current_node": "architect",
        "architecture_design": architecture,
        "files_to_create": architecture.get("files_to_create", []),
        "implementation_phases": architecture.get("implementation_phases", []),
        "parallel_tasks": architecture.get("parallel_tasks", []),
        "requires_architecture_review": architecture.get("requires_human_review", False),
        "debug_logs": debug_logs,
        "agent_execution_times": {"architect": round(execution_time, 2)},
    }


def _generate_architecture(
    user_request: str,
    workspace_root: str,
    supervisor_analysis: Dict
) -> Dict[str, Any]:
    """Generate architecture based on request analysis

    This is a rule-based fallback. Will be enhanced with LLM integration.
    """
    request_lower = user_request.lower()

    # Detect project type
    if any(word in request_lower for word in ["web app", "website", "frontend"]):
        return _web_app_architecture(user_request, workspace_root)
    elif any(word in request_lower for word in ["api", "backend", "server", "rest"]):
        return _api_architecture(user_request, workspace_root)
    elif any(word in request_lower for word in ["cli", "command line", "script"]):
        return _cli_architecture(user_request, workspace_root)
    elif any(word in request_lower for word in ["library", "package", "module"]):
        return _library_architecture(user_request, workspace_root)
    else:
        return _default_architecture(user_request, workspace_root)


def _web_app_architecture(user_request: str, workspace_root: str) -> Dict[str, Any]:
    """Generate web application architecture"""
    return {
        "project_name": "web-app",
        "description": "Full-stack web application",
        "tech_stack": {
            "language": "typescript",
            "framework": "react",
            "backend": "fastapi",
            "database": "postgresql",
            "other": ["tailwindcss", "vite"]
        },
        "directory_structure": {
            "frontend/": {
                "description": "React frontend application",
                "subdirs": {
                    "src/components/": "React components",
                    "src/pages/": "Page components",
                    "src/hooks/": "Custom hooks",
                    "src/api/": "API client",
                    "src/types/": "TypeScript types"
                }
            },
            "backend/": {
                "description": "FastAPI backend",
                "subdirs": {
                    "app/api/": "API routes",
                    "app/models/": "Data models",
                    "app/services/": "Business logic",
                    "app/db/": "Database"
                }
            }
        },
        "files_to_create": [
            {"path": "backend/app/main.py", "purpose": "Backend entry", "priority": 1},
            {"path": "backend/app/api/routes.py", "purpose": "API routes", "priority": 2},
            {"path": "backend/app/models/base.py", "purpose": "Base models", "priority": 2},
            {"path": "frontend/src/App.tsx", "purpose": "React app", "priority": 1},
            {"path": "frontend/src/components/Layout.tsx", "purpose": "Layout", "priority": 2},
            {"path": "frontend/package.json", "purpose": "Dependencies", "priority": 1},
        ],
        "implementation_phases": [
            {"phase": 1, "name": "Project Setup", "files": ["package.json", "main.py"], "description": "Initialize projects"},
            {"phase": 2, "name": "Backend Core", "files": ["routes.py", "models/"], "description": "Backend API"},
            {"phase": 3, "name": "Frontend Core", "files": ["App.tsx", "components/"], "description": "Frontend UI"},
            {"phase": 4, "name": "Integration", "files": ["api/client.ts"], "description": "Connect frontend to backend"},
        ],
        "parallel_tasks": [
            {"group": "setup", "tasks": ["backend/main.py", "frontend/App.tsx"], "can_parallelize": True, "reason": "Independent projects"},
            {"group": "components", "tasks": ["Layout.tsx", "Header.tsx", "Footer.tsx"], "can_parallelize": True, "reason": "Independent components"},
        ],
        "estimated_complexity": "complex",
        "estimated_files": 15,
        "requires_human_review": True,
        "review_reason": "Full-stack architecture needs validation"
    }


def _api_architecture(user_request: str, workspace_root: str) -> Dict[str, Any]:
    """Generate API/Backend architecture"""
    return {
        "project_name": "api-server",
        "description": "RESTful API server",
        "tech_stack": {
            "language": "python",
            "framework": "fastapi",
            "database": "postgresql",
            "other": ["sqlalchemy", "pydantic", "uvicorn"]
        },
        "directory_structure": {
            "app/": {
                "description": "Main application",
                "subdirs": {
                    "api/routes/": "API endpoints",
                    "models/": "SQLAlchemy models",
                    "schemas/": "Pydantic schemas",
                    "services/": "Business logic",
                    "db/": "Database configuration"
                }
            },
            "tests/": {"description": "Test files"},
            "docs/": {"description": "API documentation"}
        },
        "files_to_create": [
            {"path": "app/main.py", "purpose": "Application entry", "priority": 1},
            {"path": "app/config.py", "purpose": "Configuration", "priority": 1},
            {"path": "app/db/database.py", "purpose": "DB connection", "priority": 2},
            {"path": "app/models/base.py", "purpose": "Base model", "priority": 2},
            {"path": "app/api/routes/__init__.py", "purpose": "Routes init", "priority": 2},
            {"path": "app/schemas/base.py", "purpose": "Base schemas", "priority": 2},
            {"path": "requirements.txt", "purpose": "Dependencies", "priority": 1},
        ],
        "implementation_phases": [
            {"phase": 1, "name": "Setup", "files": ["main.py", "config.py", "requirements.txt"], "description": "Project foundation"},
            {"phase": 2, "name": "Database", "files": ["db/database.py", "models/"], "description": "Data layer"},
            {"phase": 3, "name": "API", "files": ["api/routes/", "schemas/"], "description": "API endpoints"},
            {"phase": 4, "name": "Services", "files": ["services/"], "description": "Business logic"},
        ],
        "parallel_tasks": [
            {"group": "models", "tasks": ["models/user.py", "models/item.py"], "can_parallelize": True, "reason": "Independent models"},
            {"group": "routes", "tasks": ["routes/users.py", "routes/items.py"], "can_parallelize": True, "reason": "Independent endpoints"},
        ],
        "estimated_complexity": "moderate",
        "estimated_files": 12,
        "requires_human_review": True,
        "review_reason": "API design needs review"
    }


def _cli_architecture(user_request: str, workspace_root: str) -> Dict[str, Any]:
    """Generate CLI tool architecture"""
    return {
        "project_name": "cli-tool",
        "description": "Command-line interface tool",
        "tech_stack": {
            "language": "python",
            "framework": "click",
            "other": ["rich", "typer"]
        },
        "directory_structure": {
            "src/": {
                "description": "Source code",
                "subdirs": {
                    "commands/": "CLI commands",
                    "utils/": "Utilities"
                }
            },
            "tests/": {"description": "Tests"}
        },
        "files_to_create": [
            {"path": "src/main.py", "purpose": "Entry point", "priority": 1},
            {"path": "src/cli.py", "purpose": "CLI setup", "priority": 1},
            {"path": "src/commands/__init__.py", "purpose": "Commands", "priority": 2},
            {"path": "setup.py", "purpose": "Package setup", "priority": 1},
        ],
        "implementation_phases": [
            {"phase": 1, "name": "Setup", "files": ["main.py", "cli.py", "setup.py"], "description": "CLI foundation"},
            {"phase": 2, "name": "Commands", "files": ["commands/"], "description": "Implement commands"},
        ],
        "parallel_tasks": [
            {"group": "commands", "tasks": ["commands/init.py", "commands/run.py"], "can_parallelize": True, "reason": "Independent commands"},
        ],
        "estimated_complexity": "simple",
        "estimated_files": 6,
        "requires_human_review": False,
        "review_reason": ""
    }


def _library_architecture(user_request: str, workspace_root: str) -> Dict[str, Any]:
    """Generate library/package architecture"""
    return {
        "project_name": "python-library",
        "description": "Reusable Python library",
        "tech_stack": {
            "language": "python",
            "framework": "none",
            "other": ["pytest", "sphinx"]
        },
        "directory_structure": {
            "src/": {"description": "Library source"},
            "tests/": {"description": "Test suite"},
            "docs/": {"description": "Documentation"}
        },
        "files_to_create": [
            {"path": "src/__init__.py", "purpose": "Package init", "priority": 1},
            {"path": "src/core.py", "purpose": "Core functionality", "priority": 1},
            {"path": "tests/test_core.py", "purpose": "Core tests", "priority": 2},
            {"path": "setup.py", "purpose": "Package setup", "priority": 1},
            {"path": "README.md", "purpose": "Documentation", "priority": 3},
        ],
        "implementation_phases": [
            {"phase": 1, "name": "Setup", "files": ["setup.py", "__init__.py"], "description": "Package setup"},
            {"phase": 2, "name": "Core", "files": ["core.py"], "description": "Core implementation"},
            {"phase": 3, "name": "Tests", "files": ["tests/"], "description": "Test coverage"},
        ],
        "parallel_tasks": [],
        "estimated_complexity": "simple",
        "estimated_files": 5,
        "requires_human_review": False,
        "review_reason": ""
    }


def _default_architecture(user_request: str, workspace_root: str) -> Dict[str, Any]:
    """Default architecture for general projects"""
    return {
        "project_name": "project",
        "description": "General Python project",
        "tech_stack": {
            "language": "python",
            "framework": "none",
            "other": []
        },
        "directory_structure": {
            "src/": {"description": "Source code"},
            "tests/": {"description": "Tests"}
        },
        "files_to_create": [
            {"path": "src/main.py", "purpose": "Entry point", "priority": 1},
            {"path": "src/utils.py", "purpose": "Utilities", "priority": 2},
            {"path": "requirements.txt", "purpose": "Dependencies", "priority": 1},
        ],
        "implementation_phases": [
            {"phase": 1, "name": "Setup", "files": ["main.py", "requirements.txt"], "description": "Project setup"},
            {"phase": 2, "name": "Implementation", "files": ["src/"], "description": "Core implementation"},
        ],
        "parallel_tasks": [],
        "estimated_complexity": "simple",
        "estimated_files": 3,
        "requires_human_review": False,
        "review_reason": ""
    }
