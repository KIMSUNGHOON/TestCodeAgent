"""Context Manager for .ai_context.json persistence

Handles loading and saving workflow state to enable context resumption.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages .ai_context.json for stateful workflow persistence"""

    def __init__(self, workspace_root: str):
        """Initialize context manager

        Args:
            workspace_root: Absolute path to workspace root
        """
        self.workspace_root = Path(workspace_root)
        self.context_file = self.workspace_root / ".ai_context.json"

    def load_context(self) -> Optional[Dict]:
        """Load existing context from .ai_context.json

        Returns:
            Context dict if file exists, None otherwise
        """
        try:
            if not self.context_file.exists():
                logger.info(f"No existing context found at {self.context_file}")
                return None

            with open(self.context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)

            logger.info(f"✅ Loaded context from {self.context_file}")
            logger.info(f"   Last updated: {context.get('last_updated', 'unknown')}")
            logger.info(f"   Project: {context.get('project_name', 'unknown')}")

            return context

        except Exception as e:
            logger.error(f"❌ Failed to load context: {e}")
            return None

    def save_context(
        self,
        context: Dict,
        merge: bool = True
    ) -> bool:
        """Save context to .ai_context.json

        Args:
            context: Context dict to save
            merge: If True, merge with existing context

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Load existing context if merging
            if merge and self.context_file.exists():
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                # Merge (new context takes precedence)
                existing.update(context)
                context = existing

            # Update timestamp
            context['last_updated'] = datetime.utcnow().isoformat()

            # Write to file
            self.context_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Saved context to {self.context_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save context: {e}")
            return False

    def add_workflow_execution(
        self,
        workflow_type: str,
        status: str,
        duration_ms: float,
        artifacts: List[str],
        notes: Optional[str] = None
    ) -> bool:
        """Add workflow execution record to context

        Args:
            workflow_type: Type of workflow executed
            status: Workflow status (completed, failed, etc.)
            duration_ms: Execution duration in milliseconds
            artifacts: List of files created/modified
            notes: Optional notes about execution

        Returns:
            True if saved successfully
        """
        try:
            context = self.load_context() or {}

            # Initialize workflow_history if not exists
            if 'workflow_history' not in context:
                context['workflow_history'] = []

            # Add execution record
            execution = {
                'timestamp': datetime.utcnow().isoformat(),
                'workflow_type': workflow_type,
                'status': status,
                'duration_ms': duration_ms,
                'artifacts': artifacts,
                'notes': notes
            }

            context['workflow_history'].append(execution)

            # Keep only last 50 executions
            context['workflow_history'] = context['workflow_history'][-50:]

            return self.save_context(context, merge=False)

        except Exception as e:
            logger.error(f"❌ Failed to add workflow execution: {e}")
            return False

    def update_next_tasks(self, tasks: List[Dict]) -> bool:
        """Update recommended next tasks in context

        Args:
            tasks: List of task dicts with keys: priority, task, rationale, estimated_effort

        Returns:
            True if saved successfully
        """
        try:
            context = self.load_context() or {}
            context['next_recommended_tasks'] = tasks
            return self.save_context(context, merge=False)

        except Exception as e:
            logger.error(f"❌ Failed to update next tasks: {e}")
            return False

    def get_recent_changes(self, limit: int = 10) -> List[Dict]:
        """Get recent changes from context

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of recent change dicts
        """
        context = self.load_context()
        if not context:
            return []

        changes = context.get('recent_changes', [])
        return changes[-limit:]

    def get_known_issues(self) -> List[Dict]:
        """Get known issues from context

        Returns:
            List of known issue dicts
        """
        context = self.load_context()
        if not context:
            return []

        return context.get('known_issues', [])
