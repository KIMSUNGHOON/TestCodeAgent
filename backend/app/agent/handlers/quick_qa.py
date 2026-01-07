"""QuickQA Handler - 간단한 질문-답변 처리.

이 핸들러는 코드 생성이나 복잡한 분석이 필요 없는
간단한 질문에 대해 직접 LLM 응답을 제공합니다.
"""
import logging
from typing import Dict, Any, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.agent.handlers.base import BaseHandler, HandlerResult, StreamUpdate
from shared.utils.token_utils import estimate_tokens, create_token_usage
from shared.utils.language_utils import detect_language, get_language_instruction

logger = logging.getLogger(__name__)


# QuickQA용 시스템 프롬프트 (언어 지시어는 동적으로 추가됨)
QUICK_QA_BASE_PROMPT = """You are a helpful coding assistant. Answer questions clearly and concisely.

When answering:
- Be direct and informative
- Use code examples when helpful
- If you don't know something, say so

Do not:
- Generate complete applications or systems
- Create implementation plans
- Start coding unless specifically asked for a code example
"""


def get_quick_qa_prompt(user_message: str, project_name: str = "") -> str:
    """Generate QuickQA prompt with proper language instruction and project context.

    Args:
        user_message: User's input message for language detection
        project_name: Project name for context

    Returns:
        System prompt with language instruction and project context
    """
    language = detect_language(user_message)
    language_instruction = get_language_instruction(language)

    # 프로젝트 컨텍스트 추가
    project_context = ""
    if project_name:
        project_context = f"""
[PROJECT CONTEXT]
You are working on a project named "{project_name}".
When referring to files or code, consider the context of this project.
[/PROJECT CONTEXT]

"""

    return language_instruction + project_context + QUICK_QA_BASE_PROMPT


class QuickQAHandler(BaseHandler):
    """간단한 질문-답변 처리 핸들러

    코드 생성이나 복잡한 분석 없이 직접 LLM 응답을 제공합니다.
    """

    def __init__(self):
        """QuickQAHandler 초기화"""
        super().__init__()

        # Coding LLM 사용 (더 빠른 응답)
        self.llm = ChatOpenAI(
            base_url=settings.vllm_coding_endpoint,
            model=settings.coding_model,
            temperature=0.7,
            max_tokens=2048,
            api_key="not-needed",
        )

        self.logger.info("QuickQAHandler initialized")

    async def execute(
        self,
        user_message: str,
        analysis: Dict[str, Any],
        context: Any
    ) -> HandlerResult:
        """질문-답변 처리 실행

        Args:
            user_message: 사용자 질문
            analysis: Supervisor 분석 결과
            context: 대화 컨텍스트

        Returns:
            HandlerResult: 처리 결과
        """
        try:
            # 프로젝트 이름 추출
            import os
            project_name = ""
            if context and hasattr(context, 'workspace') and context.workspace:
                project_name = os.path.basename(context.workspace)

            # 메시지 구성 (언어 감지 및 프로젝트 컨텍스트 적용)
            system_prompt = get_quick_qa_prompt(user_message, project_name)
            messages = [SystemMessage(content=system_prompt)]

            # 이전 대화 컨텍스트 추가 (있는 경우)
            if context and hasattr(context, 'to_langchain_messages'):
                history = context.to_langchain_messages()
                messages.extend(history[-6:])  # 최근 6개 메시지만

            # 현재 질문 추가
            messages.append(HumanMessage(content=user_message))

            # LLM 호출
            self.logger.info(f"QuickQA processing: {user_message[:50]}...")
            response = await self.llm.ainvoke(messages)

            # 응답 정리 (think 태그 제거)
            content = self._strip_think_tags(response.content)

            # 토큰 사용량 추출 (가능한 경우)
            metadata = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                metadata["tokens"] = {
                    "input": response.usage_metadata.get("input_tokens", 0),
                    "output": response.usage_metadata.get("output_tokens", 0)
                }

            self.logger.info("QuickQA completed successfully")

            return HandlerResult(
                content=content,
                artifacts=[],
                metadata=metadata,
                success=True
            )

        except Exception as e:
            self.logger.error(f"QuickQA error: {e}")
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
        """스트리밍 질문-답변 처리

        Args:
            user_message: 사용자 질문
            analysis: Supervisor 분석 결과
            context: 대화 컨텍스트

        Yields:
            StreamUpdate: 스트리밍 업데이트
        """
        yield StreamUpdate(
            agent="QuickQAHandler",
            update_type="thinking",
            status="running",
            message="응답 생성 중..."
        )

        try:
            # 프로젝트 이름 추출
            import os
            project_name = ""
            if context and hasattr(context, 'workspace') and context.workspace:
                project_name = os.path.basename(context.workspace)

            # 메시지 구성 (언어 감지 및 프로젝트 컨텍스트 적용)
            system_prompt = get_quick_qa_prompt(user_message, project_name)
            messages = [SystemMessage(content=system_prompt)]

            # 이전 대화 컨텍스트 추가 (있는 경우)
            if context and hasattr(context, 'to_langchain_messages'):
                history = context.to_langchain_messages()
                messages.extend(history[-6:])

            # 현재 질문 추가
            messages.append(HumanMessage(content=user_message))

            # 프롬프트 텍스트 (토큰 계산용)
            prompt_text = system_prompt + "\n" + user_message

            # 스트리밍 LLM 호출
            self.logger.info(f"QuickQA streaming: {user_message[:50]}...")
            response_content = ""
            last_update_len = 0

            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    response_content += chunk.content

                    # 100자마다 진행 상황 업데이트
                    if len(response_content) - last_update_len >= 100:
                        last_update_len = len(response_content)

                        # 실시간 토큰 추정
                        current_token_usage = {
                            "prompt_tokens": estimate_tokens(prompt_text),
                            "completion_tokens": estimate_tokens(response_content),
                            "total_tokens": estimate_tokens(prompt_text) + estimate_tokens(response_content)
                        }

                        yield StreamUpdate(
                            agent="QuickQAHandler",
                            update_type="streaming",
                            status="running",
                            message=f"응답 생성 중... ({len(response_content)} 자)",
                            streaming_content=response_content[-500:] if len(response_content) > 500 else response_content,
                            data={"token_usage": current_token_usage}
                        )

            # 응답 정리 (think 태그 제거)
            content = self._strip_think_tags(response_content)

            # 최종 토큰 사용량
            token_usage = create_token_usage(prompt_text, content)

            yield StreamUpdate(
                agent="QuickQAHandler",
                update_type="completed",
                status="completed",
                message=content[:200],
                streaming_content=content,
                data={
                    "full_content": content,
                    "token_usage": token_usage
                }
            )

            self.logger.info("QuickQA streaming completed successfully")

        except Exception as e:
            self.logger.error(f"QuickQA stream error: {e}")
            yield StreamUpdate(
                agent="QuickQAHandler",
                update_type="error",
                status="error",
                message=str(e)
            )
