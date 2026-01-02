"""Generic LLM Prompts - Model Agnostic

Compatible with: GPT, Claude, Llama, Mistral, and other general-purpose LLMs.
Use when specific model adapters are not available.
"""

# Base system prompt for generic models
GENERIC_SYSTEM_PROMPT = """You are an expert software engineering AI assistant.

CAPABILITIES:
- Code generation and implementation
- Code review and quality assessment
- Architecture design and planning
- Bug fixing and debugging
- Security analysis

GUIDELINES:
1. For complex problems, think through the problem step by step before providing a solution
2. Provide clear, executable code with proper error handling
3. Include type hints and documentation where appropriate
4. Follow best practices for the language/framework being used
5. Be concise but thorough in explanations

OUTPUT QUALITY:
- Code should be production-ready
- Include error handling for edge cases
- Follow established coding conventions
"""

# Task-specific prompts
GENERIC_REASONING_PROMPT = """Analyze the following request step by step:

REQUEST: {user_request}

CONTEXT: {context}

ANALYSIS STEPS:
1. Understand the core requirements
2. Identify complexity and challenges
3. Determine the best approach
4. List required components/agents
5. Estimate effort and iterations needed

Provide your analysis in JSON format:
{{
    "complexity": "simple|moderate|complex|critical",
    "task_type": "implementation|review|testing|security_audit|general",
    "required_agents": ["agent1", "agent2"],
    "workflow_strategy": "description of approach",
    "max_iterations": number,
    "requires_human_approval": true/false,
    "reasoning": "explanation of decisions"
}}
"""

GENERIC_CODE_GENERATION_PROMPT = """Generate production-ready code for the following request:

REQUEST: {user_request}
TASK TYPE: {task_type}

REQUIREMENTS:
- Complete, working code that can be executed immediately
- Include all necessary files with proper structure
- Use appropriate language features and best practices
- Include error handling and input validation

Respond in JSON format:
{{
    "files": [
        {{
            "filename": "path/to/file.py",
            "content": "complete file content",
            "language": "python",
            "description": "brief description of this file's purpose"
        }}
    ]
}}
"""

GENERIC_CODE_REVIEW_PROMPT = """Review the following code for quality and correctness:

ORIGINAL REQUEST: {user_request}

CODE TO REVIEW:
{code_summary}

REVIEW CRITERIA:
1. Code correctness - Does it fulfill the requirements?
2. Error handling - Are edge cases covered?
3. Security - Any vulnerabilities?
4. Performance - Any obvious inefficiencies?
5. Maintainability - Is the code clean and well-structured?

Respond in JSON format:
{{
    "approved": true/false,
    "quality_score": 0.0 to 1.0,
    "issues": ["list of issues found"],
    "suggestions": ["list of improvements"],
    "critique": "overall assessment"
}}
"""

GENERIC_REFINER_PROMPT = """Fix the following issues in the code:

ISSUES TO FIX:
{issues}

SUGGESTIONS TO IMPLEMENT:
{suggestions}

CURRENT QUALITY SCORE: {quality_score:.0%}
TARGET SCORE: 80%+

For each issue, provide a targeted fix. Return the modified code that addresses all issues while maintaining existing functionality.
"""

# Configuration for generic models
GENERIC_CONFIG = {
    "temperature": 0.3,  # Balanced between creativity and consistency
    "max_tokens": 4096,
    "top_p": 0.95,
    "stream": True,
}

# Model-specific configurations (can be overridden)
MODEL_CONFIGS = {
    "gpt-4": {
        "temperature": 0.2,
        "max_tokens": 8192,
        "stop": None,
    },
    "gpt-3.5-turbo": {
        "temperature": 0.3,
        "max_tokens": 4096,
        "stop": None,
    },
    "claude-3": {
        "temperature": 0.2,
        "max_tokens": 8192,
        "stop": None,
    },
    "llama-3": {
        "temperature": 0.3,
        "max_tokens": 4096,
        "stop": ["</s>", "[INST]"],
    },
    "mistral": {
        "temperature": 0.3,
        "max_tokens": 4096,
        "stop": ["</s>", "[INST]"],
    },
    "gpt-oss-120b": {
        "temperature": 0.2,
        "max_tokens": 8192,
        "stop": None,
    },
}


def get_model_config(model_name: str) -> dict:
    """Get configuration for a specific model, with fallback to generic."""
    # Check for exact match
    if model_name in MODEL_CONFIGS:
        return {**GENERIC_CONFIG, **MODEL_CONFIGS[model_name]}

    # Check for partial match (e.g., "gpt-4-turbo" matches "gpt-4")
    for key in MODEL_CONFIGS:
        if key in model_name.lower():
            return {**GENERIC_CONFIG, **MODEL_CONFIGS[key]}

    # Return generic config as fallback
    return GENERIC_CONFIG
