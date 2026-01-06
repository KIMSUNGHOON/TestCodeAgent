"""Planning Handler - 개발 계획 수립 처리.

이 핸들러는 사용자의 요청을 분석하고 개발 계획을 수립합니다.
복잡한 작업의 경우 계획을 파일로 저장할 수 있습니다.
"""
import logging
import re
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.agent.handlers.base import BaseHandler, HandlerResult, StreamUpdate

logger = logging.getLogger(__name__)


def _get_planning_system_prompt(model_type: str) -> str:
    """모델 타입에 따른 시스템 프롬프트 반환"""

    base_prompt = """You are an expert software architect and development planner.

Your task is to analyze user requests and create detailed, actionable development plans.

When creating a plan:
1. Break down the task into clear, manageable steps
2. Identify potential challenges and solutions
3. Consider best practices and design patterns
4. Suggest appropriate technologies and libraries
5. Estimate relative complexity of each component

Output format:
- Use clear markdown formatting
- Number your steps
- Include code structure suggestions where helpful
- Provide rationale for key decisions

Language: Respond in the same language as the user's request."""

    if model_type == "deepseek":
        return f"""<think>
Before responding, analyze:
1. What is the user trying to build?
2. What are the key components needed?
3. What challenges might arise?
4. What's the best architecture?
</think>

{base_prompt}"""
    else:
        return base_prompt


class PlanningHandler(BaseHandler):
    """개발 계획 수립 핸들러

    사용자 요청을 분석하고 개발 계획을 생성합니다.
    복잡한 작업은 계획 파일로 저장됩니다.
    """

    def __init__(self):
        """PlanningHandler 초기화"""
        super().__init__()

        # Reasoning LLM 사용 (더 깊은 분석)
        self.llm = ChatOpenAI(
            base_url=settings.vllm_reasoning_endpoint,
            model=settings.reasoning_model,
            temperature=0.7,
            max_tokens=4096,
            api_key="not-needed",
        )

        self.model_type = settings.get_reasoning_model_type
        self.logger.info(f"PlanningHandler initialized (model_type: {self.model_type})")

    async def execute(
        self,
        user_message: str,
        analysis: Dict[str, Any],
        context: Any
    ) -> HandlerResult:
        """계획 수립 실행

        Args:
            user_message: 사용자 요청
            analysis: Supervisor 분석 결과
            context: 대화 컨텍스트

        Returns:
            HandlerResult: 처리 결과 (계획 + 옵션으로 파일 저장)
        """
        try:
            # 시스템 프롬프트 구성
            system_prompt = _get_planning_system_prompt(self.model_type)

            # 컨텍스트 정보 추가
            context_info = self._build_context_info(analysis, context)

            # 사용자 프롬프트 구성
            user_prompt = f"""## 요청 분석
{context_info}

## 사용자 요청
{user_message}

## 작업
위 요청에 대한 상세한 개발 계획을 작성해주세요."""

            # LLM 호출
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            self.logger.info(f"Planning: {user_message[:50]}...")
            response = await self.llm.ainvoke(messages)

            # 응답 정리
            plan_content = self._strip_think_tags(response.content)

            # 사용자 친화적 응답 생성
            user_response = self._format_user_response(plan_content, analysis)

            # 복잡한 작업은 파일로 저장
            plan_file = None
            complexity = analysis.get("complexity", "simple")

            if complexity in ["complex", "critical"] and context and hasattr(context, 'workspace'):
                workspace = context.workspace
                if workspace:
                    plan_file = await self._save_plan_file(plan_content, workspace, user_message)

            # 메타데이터
            metadata = {
                "complexity": complexity,
                "plan_saved": plan_file is not None
            }

            self.logger.info(f"Planning completed (saved: {plan_file is not None})")

            return HandlerResult(
                content=user_response,
                artifacts=[],
                plan_file=plan_file,
                metadata=metadata,
                success=True
            )

        except Exception as e:
            self.logger.error(f"Planning error: {e}")
            return HandlerResult(
                content="",
                success=False,
                error=str(e)
            )

    async def execute_stream(
        self,
        user_message: str,
        analysis: Dict[str, Any],
        context: Any
    ) -> AsyncGenerator[StreamUpdate, None]:
        """스트리밍 계획 수립

        Args:
            user_message: 사용자 요청
            analysis: Supervisor 분석 결과
            context: 대화 컨텍스트

        Yields:
            StreamUpdate: 스트리밍 업데이트
        """
        yield StreamUpdate(
            agent="PlanningHandler",
            update_type="thinking",
            status="running",
            message="요청을 분석하고 있습니다..."
        )

        try:
            # 시스템 프롬프트 구성
            system_prompt = _get_planning_system_prompt(self.model_type)
            context_info = self._build_context_info(analysis, context)

            user_prompt = f"""## 요청 분석
{context_info}

## 사용자 요청
{user_message}

## 작업
위 요청에 대한 상세한 개발 계획을 작성해주세요."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # 스트리밍 LLM 호출
            plan_content = ""
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    plan_content += chunk.content

                    # 진행 상황 업데이트 (100자마다)
                    if len(plan_content) % 100 < 10:
                        yield StreamUpdate(
                            agent="PlanningHandler",
                            update_type="progress",
                            status="running",
                            message=f"계획 작성 중... ({len(plan_content)} 자)"
                        )

            # 정리 및 저장
            plan_content = self._strip_think_tags(plan_content)
            user_response = self._format_user_response(plan_content, analysis)

            plan_file = None
            complexity = analysis.get("complexity", "simple")

            if complexity in ["complex", "critical"] and context and hasattr(context, 'workspace'):
                workspace = context.workspace
                if workspace:
                    plan_file = await self._save_plan_file(plan_content, workspace, user_message)

            yield StreamUpdate(
                agent="PlanningHandler",
                update_type="completed",
                status="completed",
                message=user_response[:200],
                data={
                    "plan_file": plan_file,
                    "full_content": user_response
                }
            )

        except Exception as e:
            self.logger.error(f"Planning stream error: {e}")
            yield StreamUpdate(
                agent="PlanningHandler",
                update_type="error",
                status="error",
                message=str(e)
            )

    def _build_context_info(self, analysis: Dict[str, Any], context: Any) -> str:
        """컨텍스트 정보 문자열 생성"""
        parts = []

        # Supervisor 분석 정보
        if analysis:
            complexity = analysis.get("complexity", "unknown")
            task_type = analysis.get("task_type", "unknown")
            parts.append(f"- 복잡도: {complexity}")
            parts.append(f"- 작업 유형: {task_type}")

        # 이전 대화 요약 (있는 경우)
        if context and hasattr(context, 'get_conversation_summary'):
            summary = context.get_conversation_summary()
            if summary:
                parts.append(f"- 이전 대화: {summary[:200]}")

        # 기존 아티팩트 (있는 경우)
        if context and hasattr(context, 'get_artifact_summary'):
            artifacts = context.get_artifact_summary()
            if artifacts and artifacts != "생성된 파일이 없습니다.":
                parts.append(f"- 기존 파일:\n{artifacts}")

        return "\n".join(parts) if parts else "새 작업입니다."

    def _format_user_response(self, plan_content: str, analysis: Dict[str, Any]) -> str:
        """사용자 친화적 응답 생성

        Args:
            plan_content: 생성된 계획 내용
            analysis: 분석 결과

        Returns:
            str: 포맷된 응답
        """
        complexity = analysis.get("complexity", "simple")

        header = "## 개발 계획\n\n"
        footer = "\n\n---\n"

        if complexity in ["complex", "critical"]:
            footer += "이 계획이 적절한지 확인해주세요. 진행하려면 '코드 생성 시작'이라고 말씀해주세요."
        else:
            footer += "계획을 확인하고, 코드 생성을 원하시면 말씀해주세요."

        return header + plan_content + footer

    async def _save_plan_file(
        self,
        content: str,
        workspace: str,
        user_message: str
    ) -> Optional[str]:
        """계획을 마크다운 파일로 저장

        Args:
            content: 계획 내용
            workspace: 워크스페이스 경로
            user_message: 원본 요청 (파일명 생성용)

        Returns:
            Optional[str]: 저장된 파일 경로 또는 None
        """
        try:
            # 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 요청에서 키워드 추출 (파일명용)
            keywords = re.findall(r'[가-힣a-zA-Z]+', user_message)[:3]
            keyword_part = "_".join(keywords) if keywords else "plan"
            keyword_part = keyword_part[:30]  # 길이 제한

            filename = f"PLAN_{keyword_part}_{timestamp}.md"

            # 저장 경로
            plans_dir = Path(workspace) / ".plans"
            plans_dir.mkdir(parents=True, exist_ok=True)

            filepath = plans_dir / filename

            # 파일 내용 구성
            file_content = f"""# Development Plan

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Request**: {user_message[:200]}

---

{content}

---
*This plan was automatically generated. Review and modify as needed.*
"""

            # 저장
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(file_content)

            self.logger.info(f"Plan saved: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Failed to save plan file: {e}")
            return None
