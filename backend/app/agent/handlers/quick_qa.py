"""QuickQA Handler - 간단한 질문-답변 처리.

이 핸들러는 코드 생성이나 복잡한 분석이 필요 없는
간단한 질문에 대해 직접 LLM 응답을 제공합니다.
"""
import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.agent.handlers.base import BaseHandler, HandlerResult

logger = logging.getLogger(__name__)


# QuickQA용 시스템 프롬프트
QUICK_QA_SYSTEM_PROMPT = """You are a helpful coding assistant. Answer questions clearly and concisely.

When answering:
- Be direct and informative
- Use code examples when helpful
- If you don't know something, say so
- For Korean questions, respond in Korean
- For English questions, respond in English

Do not:
- Generate complete applications or systems
- Create implementation plans
- Start coding unless specifically asked for a code example
"""


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
            # 메시지 구성
            messages = [SystemMessage(content=QUICK_QA_SYSTEM_PROMPT)]

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
