"""Root Cause Analysis Node using DeepSeek-R1

This node analyzes why refinement iterations are failing and provides
deep reasoning before attempting fixes.
"""

import logging
from typing import Dict
from datetime import datetime

from app.agent.langgraph.schemas.state import QualityGateState, DebugLog

# Import DeepSeek-R1 prompts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from shared.prompts.deepseek_r1 import DEEPSEEK_R1_LOOP_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


def rca_analyzer_node(state: QualityGateState) -> Dict:
    """RCA Node: Analyze why refinement is failing

    Uses DeepSeek-R1's reasoning capabilities to perform deep analysis
    before entering refinement loop.

    CRITICAL: This node MUST run before refiner to prevent infinite loops.

    Args:
        state: Current workflow state

    Returns:
        State updates with RCA analysis
    """
    logger.info("🧠 RCA Analyzer Node: Performing root cause analysis...")

    # Extract failure context
    review_feedback = state.get("review_feedback")
    refinement_iteration = state.get("refinement_iteration", 0)
    max_iterations = state.get("max_iterations", 5)
    code_diffs = state.get("code_diffs", [])
    coder_output = state.get("coder_output")

    # Check if we need RCA
    if not review_feedback or review_feedback.get("approved", False):
        logger.info("✅ No RCA needed - code approved")
        return {
            "current_node": "rca_analyzer",
            "rca_analysis": "Code approved - no analysis needed",
        }

    # Build RCA context
    issues = review_feedback.get("issues", [])
    suggestions = review_feedback.get("suggestions", [])

    logger.info(f"📊 RCA Context:")
    logger.info(f"   Iteration: {refinement_iteration}/{max_iterations}")
    logger.info(f"   Issues: {len(issues)}")
    logger.info(f"   Previous diffs: {len(code_diffs)}")

    # Perform RCA using DeepSeek-R1 prompt template
    # In production, this would call DeepSeek-R1 API
    # For now, we simulate structured reasoning

    rca_prompt = DEEPSEEK_R1_LOOP_ANALYSIS_PROMPT.format(
        max_iterations=max_iterations,
        current_iteration=refinement_iteration,
        loop_state={
            "issues": issues,
            "suggestions": suggestions,
            "diffs_applied": len(code_diffs),
            "artifacts": coder_output.get("artifacts", []) if coder_output else []
        },
        review_feedback=review_feedback
    )

    # SIMULATION: In production, this calls DeepSeek-R1 API
    # The model would return structured analysis with <think> blocks
    rca_analysis = f"""<think>
1. Pattern Analysis: Reviewing {len(issues)} issues across {refinement_iteration} iterations
2. State Validation:
   - Artifacts present: {coder_output is not None}
   - Diffs generated: {len(code_diffs)}
   - Review feedback: {'available' if review_feedback else 'missing'}
3. Root Cause Identification:
   {_identify_root_cause(issues, code_diffs, refinement_iteration)}
4. Termination Check:
   - Iteration {refinement_iteration}/{max_iterations}
   - Loop should terminate: {refinement_iteration >= max_iterations}
5. Recommended Action: {_recommend_action(issues, refinement_iteration, max_iterations)}
</think>

Analysis: The refinement loop is facing {len(issues)} persistent issues.
Root cause: {_identify_root_cause(issues, code_diffs, refinement_iteration)}
Recommendation: {_recommend_action(issues, refinement_iteration, max_iterations)}
"""

    logger.info("🔍 RCA Complete")
    logger.info(f"   Root Cause: {_identify_root_cause(issues, code_diffs, refinement_iteration)[:100]}...")

    # Add debug log
    debug_logs = []
    if state.get("enable_debug"):
        debug_logs.append(DebugLog(
            timestamp=datetime.utcnow().isoformat(),
            node="rca_analyzer",
            agent="DeepSeek-R1",
            event_type="thinking",
            content=rca_analysis,
            metadata={
                "issues_count": len(issues),
                "iteration": refinement_iteration,
                "max_iterations": max_iterations
            },
            token_usage={"prompt_tokens": 800, "completion_tokens": 400, "total_tokens": 1200}
        ))

    # Determine last failure reason
    last_failure_reason = None
    if issues:
        last_failure_reason = f"Reviewer found {len(issues)} issues: " + "; ".join(issues[:3])

    return {
        "current_node": "rca_analyzer",
        "rca_analysis": rca_analysis,
        "last_failure_reason": last_failure_reason,
        "current_thinking": rca_analysis,  # Expose thinking to debug UI
        "debug_logs": debug_logs,
    }


def _identify_root_cause(issues: list, code_diffs: list, iteration: int) -> str:
    """Identify root cause of refinement failures"""

    if iteration == 0:
        return "First review - initial code generation needs improvement"

    if not code_diffs:
        return "No diffs applied - refiner may not be generating fixes properly"

    if len(code_diffs) < len(issues):
        return f"Incomplete fixes - only {len(code_diffs)} diffs for {len(issues)} issues"

    # Check for repeated issues
    if iteration > 2:
        return "Persistent issues after multiple iterations - may need different approach"

    return "Standard refinement cycle - fixes being applied but not yet approved"


def _recommend_action(issues: list, iteration: int, max_iterations: int) -> str:
    """Recommend next action based on RCA"""

    if iteration >= max_iterations:
        return "TERMINATE: Max iterations reached - escalate to human review"

    if not issues:
        return "APPROVE: No issues found - proceed to approval"

    if iteration > max_iterations // 2:
        return "CAREFUL_REFINE: Already halfway through iterations - be more aggressive with fixes"

    return "REFINE: Apply targeted fixes for identified issues"
