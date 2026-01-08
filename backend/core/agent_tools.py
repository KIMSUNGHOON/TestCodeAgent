"""Agent Tools Definition for Tool Use Pattern

This module defines all agents as OpenAI-compatible function tools,
enabling LLM-driven dynamic workflow orchestration.

Instead of hardcoded workflow types (QUICK_QA, CODE_GENERATION, etc.),
the LLM freely decides which agents to call and in what order.
"""

from typing import List, Dict, Any


# ============================================
# Agent Tool Definitions
# ============================================

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "ask_human",
            "description": (
                "Ask the human user a question when you need clarification, "
                "important decisions, or confirmation. Use this when:\n"
                "- Request is ambiguous or unclear\n"
                "- Multiple valid approaches exist\n"
                "- Important decision with significant impact\n"
                "- Potentially dangerous operation needs confirmation\n"
                "- Low confidence in your analysis"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Clear, concise question to ask the user"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you're asking - provide context for the user"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of suggested answers (for multiple choice)"
                    }
                },
                "required": ["question", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "architect_agent",
            "description": (
                "Design project structure and architecture. Use this agent to:\n"
                "- Plan folder/file structure\n"
                "- Design system architecture\n"
                "- Identify technical components and dependencies\n"
                "- Create high-level implementation plan\n"
                "- Recommend design patterns and best practices"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "Detailed project requirements and constraints"
                    },
                    "architecture_style": {
                        "type": "string",
                        "enum": ["monolithic", "microservices", "layered", "modular"],
                        "description": "Preferred architecture style (optional)"
                    },
                    "constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technical constraints (e.g., 'must use FastAPI', 'no external dependencies')"
                    }
                },
                "required": ["requirements"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "coder_agent",
            "description": (
                "Generate actual implementation code. Use this agent to:\n"
                "- Write production-ready code\n"
                "- Implement features based on architecture\n"
                "- Create multiple files with proper structure\n"
                "- Follow security best practices automatically\n"
                "- Include error handling and type hints"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Clear description of what code to generate"
                    },
                    "architecture": {
                        "type": "object",
                        "description": "Architecture plan from architect_agent (optional but recommended)"
                    },
                    "existing_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of existing files to consider (for modifications)"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reviewer_agent",
            "description": (
                "Review code for quality, bugs, and security issues. Use this to:\n"
                "- Check for logic errors and bugs\n"
                "- Identify security vulnerabilities (SQL injection, XSS, etc.)\n"
                "- Verify code follows best practices\n"
                "- Suggest improvements and optimizations\n"
                "- Validate error handling and edge cases"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to review (or specify files)"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files to review from workspace"
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["security", "performance", "correctness", "maintainability", "all"]
                        },
                        "description": "Specific review focus (default: all)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "refiner_agent",
            "description": (
                "Fix issues and refine code based on review feedback. Use this to:\n"
                "- Fix bugs identified by reviewer\n"
                "- Address security vulnerabilities\n"
                "- Improve code quality\n"
                "- Apply suggested optimizations\n"
                "- Refactor for better maintainability"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Original code to refine"
                    },
                    "review_feedback": {
                        "type": "object",
                        "description": "Feedback from reviewer_agent"
                    },
                    "issues_to_fix": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific issues to address"
                    }
                },
                "required": ["review_feedback"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "qa_tester_agent",
            "description": (
                "Generate and run tests for code. Use this to:\n"
                "- Create unit tests\n"
                "- Create integration tests\n"
                "- Execute tests and report results\n"
                "- Verify code correctness\n"
                "- Check edge case handling"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to test"
                    },
                    "test_type": {
                        "type": "string",
                        "enum": ["unit", "integration", "both"],
                        "description": "Type of tests to generate"
                    },
                    "execute_tests": {
                        "type": "boolean",
                        "description": "Whether to execute tests (default: true)"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "security_auditor_agent",
            "description": (
                "Perform deep security analysis. Use this for:\n"
                "- OWASP Top 10 vulnerability scanning\n"
                "- Authentication/authorization review\n"
                "- Input validation checking\n"
                "- Cryptography usage review\n"
                "- Dependency vulnerability checking\n"
                "Use this for critical/production code or when user explicitly requests security audit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to audit"
                    },
                    "focus": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "injection",
                                "authentication",
                                "xss",
                                "csrf",
                                "sensitive_data",
                                "all"
                            ]
                        },
                        "description": "Specific security focus areas"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": (
                "Mark the task as complete and provide final response to user. "
                "Call this when you have finished all necessary work and are ready to respond. "
                "This will end the workflow and return the final result to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of what was accomplished"
                    },
                    "response": {
                        "type": "string",
                        "description": "Final response message to the user"
                    },
                    "files_created": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files created/modified"
                    }
                },
                "required": ["summary", "response"]
            }
        }
    }
]


# ============================================
# Helper Functions
# ============================================

def get_agent_tools() -> List[Dict[str, Any]]:
    """Get all agent tools for LLM Tool Use"""
    return AGENT_TOOLS


def get_tool_names() -> List[str]:
    """Get list of all available tool names"""
    return [tool["function"]["name"] for tool in AGENT_TOOLS]


def get_tool_by_name(name: str) -> Dict[str, Any]:
    """Get tool definition by name"""
    for tool in AGENT_TOOLS:
        if tool["function"]["name"] == name:
            return tool
    raise ValueError(f"Tool '{name}' not found")
