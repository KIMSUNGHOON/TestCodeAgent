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
from shared.utils.token_utils import estimate_tokens, create_token_usage
from shared.utils.language_utils import detect_language, get_language_instruction

logger = logging.getLogger(__name__)


def _get_planning_system_prompt(model_type: str, user_message: str = "", project_name: str = "") -> str:
    """모델 타입과 사용자 언어에 따른 시스템 프롬프트 반환

    Args:
        model_type: LLM 모델 타입
        user_message: 사용자 메시지 (언어 감지용)
        project_name: 프로젝트 이름 (컨텍스트용)

    Returns:
        시스템 프롬프트
    """
    # 언어 감지 및 지시어 생성
    language_instruction = ""
    if user_message:
        language = detect_language(user_message)
        language_instruction = get_language_instruction(language)

    # 프로젝트 컨텍스트 추가
    project_context = ""
    if project_name:
        project_context = f"""
[PROJECT CONTEXT]
You are working on a project named "{project_name}".
All generated files and code should be organized within this project's directory structure.
Use "{project_name}" as the root directory for file paths when suggesting file organization.
[/PROJECT CONTEXT]

"""

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
- Provide rationale for key decisions"""

    if model_type == "deepseek":
        return f"""{language_instruction}{project_context}<think>
Before responding, analyze:
1. What is the user trying to build?
2. What are the key components needed?
3. What challenges might arise?
4. What's the best architecture?
</think>

{base_prompt}"""
    else:
        return language_instruction + project_context + base_prompt


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
            # 프로젝트 이름 추출 (베이스 클래스 메서드 사용)
            project_name = self._get_project_name(context)

            # 시스템 프롬프트 구성 (언어 감지 및 프로젝트 컨텍스트 적용)
            system_prompt = _get_planning_system_prompt(self.model_type, user_message, project_name)

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
            return self._create_error_result(e)

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
        yield self._create_progress_update(
            message="요청을 분석하고 있습니다...",
            streaming_content="## 분석 시작\n- 요청 내용 파악 중...\n- 복잡도 평가 중..."
        )

        try:
            # 프로젝트 이름 추출 (베이스 클래스 메서드 사용)
            project_name = self._get_project_name(context)

            # 시스템 프롬프트 구성 (언어 감지 및 프로젝트 컨텍스트 적용)
            system_prompt = _get_planning_system_prompt(self.model_type, user_message, project_name)
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
            last_update_len = 0
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    plan_content += chunk.content

                    # 진행 상황 업데이트 (100자마다 또는 의미있는 변화가 있을 때)
                    if len(plan_content) - last_update_len >= 100:
                        last_update_len = len(plan_content)
                        # think 태그 제거한 미리보기 생성
                        preview = self._strip_think_tags(plan_content)
                        # 최근 500자만 streaming_content로 전달
                        preview_content = preview[-500:] if len(preview) > 500 else preview

                        # Real-time token estimation
                        current_token_usage = {
                            "prompt_tokens": estimate_tokens(f"{system_prompt}\n{user_prompt}"),
                            "completion_tokens": estimate_tokens(plan_content),
                            "total_tokens": estimate_tokens(f"{system_prompt}\n{user_prompt}") + estimate_tokens(plan_content)
                        }

                        yield StreamUpdate(
                            agent="PlanningHandler",
                            update_type="streaming",
                            status="running",
                            message=f"계획 작성 중... ({len(plan_content)} 자)",
                            streaming_content=preview_content,
                            data={"token_usage": current_token_usage}
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

            # Calculate token usage
            full_prompt = f"{system_prompt}\n{user_prompt}"
            token_usage = create_token_usage(full_prompt, plan_content)

            yield StreamUpdate(
                agent="PlanningHandler",
                update_type="completed",
                status="completed",
                message=user_response[:200],
                streaming_content=plan_content,
                data={
                    "plan_file": plan_file,
                    "full_content": user_response,
                    "token_usage": token_usage
                }
            )

        except Exception as e:
            yield self._create_error_update(e)

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
