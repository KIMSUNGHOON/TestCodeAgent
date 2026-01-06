"""Context Store - 대화 컨텍스트 영속성 관리.

이 모듈은 세션별 대화 컨텍스트를 관리하고
DB와 메모리 캐시 간의 동기화를 담당합니다.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

# 최대 메시지 수 (컨텍스트 오버플로우 방지)
MAX_MESSAGES = 50
# LLM에 전달할 최근 메시지 수
RECENT_MESSAGES_FOR_LLM = 20
# 컨텍스트 요약용 최근 메시지 수
RECENT_MESSAGES_FOR_CONTEXT = 10
# 최대 아티팩트 수
MAX_ARTIFACTS = 20


@dataclass
class ConversationContext:
    """대화 컨텍스트

    세션별 대화 기록, 아티팩트, 분석 결과를 관리합니다.
    """
    session_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    workspace: Optional[str] = None
    last_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str):
        """메시지 추가

        Args:
            role: 역할 (user, assistant, system)
            content: 메시지 내용
        """
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # 최대 메시지 수 제한
        if len(self.messages) > MAX_MESSAGES:
            self.messages = self.messages[-MAX_MESSAGES:]

        self.updated_at = datetime.now()

    def add_artifact(self, artifact: Dict[str, Any]):
        """아티팩트 추가

        Args:
            artifact: 아티팩트 정보 (filename, language, content 등)
        """
        # 중복 제거 (같은 파일명이면 업데이트)
        filename = artifact.get("filename")
        if filename:
            self.artifacts = [a for a in self.artifacts if a.get("filename") != filename]

        artifact["added_at"] = datetime.now().isoformat()
        self.artifacts.append(artifact)

        # 최대 아티팩트 수 제한
        if len(self.artifacts) > MAX_ARTIFACTS:
            self.artifacts = self.artifacts[-MAX_ARTIFACTS:]

        self.updated_at = datetime.now()

    def to_langchain_messages(self) -> List:
        """LangChain 메시지 형식으로 변환

        Returns:
            List: LangChain 메시지 객체 리스트
        """
        messages = []
        for msg in self.messages[-RECENT_MESSAGES_FOR_LLM:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

        return messages

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (Supervisor 컨텍스트용)

        Returns:
            Dict: 컨텍스트 딕셔너리
        """
        return {
            "session_id": self.session_id,
            "messages": self.messages[-RECENT_MESSAGES_FOR_CONTEXT:],
            "artifacts": self.artifacts[-5:],
            "workspace": self.workspace,
            "last_analysis": self.last_analysis
        }

    def get_conversation_summary(self) -> str:
        """대화 요약 생성

        Returns:
            str: 대화 요약 문자열
        """
        if not self.messages:
            return "새 대화입니다."

        recent = self.messages[-5:]
        summary_parts = []

        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]  # 처음 100자만
            if len(msg.get("content", "")) > 100:
                content += "..."
            summary_parts.append(f"[{role}] {content}")

        return "\n".join(summary_parts)

    def get_artifact_summary(self) -> str:
        """아티팩트 요약 생성

        Returns:
            str: 아티팩트 요약 문자열
        """
        if not self.artifacts:
            return "생성된 파일이 없습니다."

        summaries = []
        for artifact in self.artifacts[-5:]:
            filename = artifact.get("filename", "unknown")
            language = artifact.get("language", "unknown")
            summaries.append(f"- {filename} ({language})")

        return "\n".join(summaries)


class ContextStore:
    """컨텍스트 저장소

    세션별 컨텍스트의 로드/저장을 관리합니다.
    메모리 캐시와 DB 영속성을 모두 지원합니다.
    """

    def __init__(self):
        """ContextStore 초기화"""
        self.cache: Dict[str, ConversationContext] = {}
        logger.info("ContextStore initialized")

    async def load(self, session_id: str) -> ConversationContext:
        """세션 컨텍스트 로드

        Args:
            session_id: 세션 ID

        Returns:
            ConversationContext: 컨텍스트 객체
        """
        # 1. 캐시 확인
        if session_id in self.cache:
            logger.debug(f"Context loaded from cache: {session_id}")
            return self.cache[session_id]

        # 2. DB 조회 (향후 구현)
        db_context = await self._load_from_db(session_id)
        if db_context:
            self.cache[session_id] = db_context
            logger.debug(f"Context loaded from DB: {session_id}")
            return db_context

        # 3. 신규 생성
        new_context = ConversationContext(session_id=session_id)
        self.cache[session_id] = new_context
        logger.info(f"New context created: {session_id}")
        return new_context

    async def save(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        analysis: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None
    ):
        """컨텍스트 저장

        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            assistant_response: 어시스턴트 응답
            analysis: Supervisor 분석 결과
            artifacts: 생성된 아티팩트 목록
        """
        context = await self.load(session_id)

        # 메시지 추가
        context.add_message("user", user_message)
        context.add_message("assistant", assistant_response)

        # 분석 결과 저장
        if analysis:
            context.last_analysis = analysis

        # 아티팩트 추가
        if artifacts:
            for artifact in artifacts:
                context.add_artifact(artifact)

        context.updated_at = datetime.now()

        # 캐시 업데이트
        self.cache[session_id] = context

        # DB 저장 (비동기, 향후 구현)
        await self._save_to_db(context)

        logger.debug(f"Context saved: {session_id}, messages={len(context.messages)}")

    async def update_workspace(self, session_id: str, workspace: str):
        """워크스페이스 경로 업데이트

        Args:
            session_id: 세션 ID
            workspace: 워크스페이스 경로
        """
        context = await self.load(session_id)
        context.workspace = workspace
        context.updated_at = datetime.now()
        self.cache[session_id] = context
        logger.debug(f"Workspace updated: {session_id} -> {workspace}")

    async def clear(self, session_id: str):
        """세션 컨텍스트 초기화

        Args:
            session_id: 세션 ID
        """
        if session_id in self.cache:
            del self.cache[session_id]

        # DB에서도 삭제 (향후 구현)
        await self._delete_from_db(session_id)

        logger.info(f"Context cleared: {session_id}")

    async def _load_from_db(self, session_id: str) -> Optional[ConversationContext]:
        """DB에서 컨텍스트 로드 (향후 구현)

        Args:
            session_id: 세션 ID

        Returns:
            Optional[ConversationContext]: 컨텍스트 또는 None
        """
        # TODO: SQLAlchemy 또는 다른 DB 연동 구현
        # 현재는 None 반환 (캐시만 사용)
        return None

    async def _save_to_db(self, context: ConversationContext):
        """DB에 컨텍스트 저장 (향후 구현)

        Args:
            context: 저장할 컨텍스트
        """
        # TODO: SQLAlchemy 또는 다른 DB 연동 구현
        # 현재는 캐시만 사용
        pass

    async def _delete_from_db(self, session_id: str):
        """DB에서 컨텍스트 삭제 (향후 구현)

        Args:
            session_id: 세션 ID
        """
        # TODO: SQLAlchemy 또는 다른 DB 연동 구현
        pass

    def get_stats(self) -> Dict[str, Any]:
        """저장소 통계 반환

        Returns:
            Dict: 통계 정보
        """
        return {
            "cached_sessions": len(self.cache),
            "sessions": [
                {
                    "session_id": sid,
                    "message_count": len(ctx.messages),
                    "artifact_count": len(ctx.artifacts),
                    "updated_at": ctx.updated_at.isoformat()
                }
                for sid, ctx in self.cache.items()
            ]
        }


# 싱글톤 인스턴스
_context_store: Optional[ContextStore] = None


def get_context_store() -> ContextStore:
    """ContextStore 싱글톤 인스턴스 반환

    Returns:
        ContextStore: 컨텍스트 저장소 인스턴스
    """
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store
