"""Conversation Indexer - 대화 내용 벡터 색인 서비스.

이전 대화 내용을 벡터DB에 색인하여
관련 대화를 시맨틱 검색할 수 있게 합니다.
"""
import logging
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from app.services.vector_db import vector_db, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class ConversationSearchResult:
    """대화 검색 결과"""
    content: str
    role: str
    turn_number: int
    relevance: float
    timestamp: str


class ConversationIndexer:
    """대화 내용을 벡터DB에 색인하는 서비스

    세션별 대화 기록을 벡터화하여 저장하고,
    관련 대화를 시맨틱 검색할 수 있게 합니다.
    """

    # 최소 메시지 길이 (너무 짧은 메시지는 색인하지 않음)
    MIN_MESSAGE_LENGTH: int = 20

    # 최대 색인할 메시지 길이
    MAX_MESSAGE_LENGTH: int = 2000

    def __init__(self, session_id: str):
        """ConversationIndexer 초기화

        Args:
            session_id: 세션 ID
        """
        self.session_id = session_id
        self.logger = logging.getLogger(f"{__name__}.{session_id[:8]}")
        self._turn_counter = 0

    def index_message(
        self,
        message: str,
        role: str,
        turn_number: Optional[int] = None,
        timestamp: Optional[str] = None
    ) -> Optional[str]:
        """개별 메시지를 벡터DB에 색인

        Args:
            message: 메시지 내용
            role: 역할 (user, assistant)
            turn_number: 턴 번호 (없으면 자동 증가)
            timestamp: 타임스탬프 (없으면 현재 시간)

        Returns:
            Optional[str]: 생성된 문서 ID (색인 실패시 None)
        """
        # 너무 짧은 메시지는 스킵
        if len(message.strip()) < self.MIN_MESSAGE_LENGTH:
            self.logger.debug(f"Message too short to index: {len(message)} chars")
            return None

        # 턴 번호 설정
        if turn_number is None:
            self._turn_counter += 1
            turn_number = self._turn_counter
        else:
            self._turn_counter = max(self._turn_counter, turn_number)

        # 타임스탬프 설정
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # 메시지 길이 제한
        content = message[:self.MAX_MESSAGE_LENGTH]
        if len(message) > self.MAX_MESSAGE_LENGTH:
            content += "... (truncated)"

        try:
            # 고유 ID 생성
            doc_id = self._generate_doc_id(content, turn_number)

            # 검색 가능한 문서 텍스트 생성
            doc_text = f"[{role.upper()}] {content}"

            # 메타데이터
            metadata = {
                "type": "conversation",
                "role": role,
                "session_id": self.session_id,
                "turn": turn_number,
                "timestamp": timestamp
            }

            # 벡터DB에 추가
            vector_db.add_documents(
                documents=[doc_text],
                ids=[doc_id],
                metadatas=[metadata]
            )

            self.logger.debug(
                f"Indexed message: turn={turn_number}, role={role}, "
                f"length={len(content)}"
            )
            return doc_id

        except Exception as e:
            self.logger.warning(f"Failed to index message: {e}")
            return None

    def index_conversation(
        self,
        messages: List[Dict[str, str]],
        start_turn: int = 1
    ) -> int:
        """여러 메시지를 한 번에 색인

        Args:
            messages: 메시지 목록 [{"role": str, "content": str}, ...]
            start_turn: 시작 턴 번호

        Returns:
            int: 색인된 메시지 수
        """
        indexed_count = 0

        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")

            doc_id = self.index_message(
                message=content,
                role=role,
                turn_number=start_turn + i,
                timestamp=timestamp
            )

            if doc_id:
                indexed_count += 1

        self.logger.info(
            f"Indexed {indexed_count}/{len(messages)} messages "
            f"for session {self.session_id}"
        )
        return indexed_count

    def search_conversation(
        self,
        query: str,
        n_results: int = 5,
        min_relevance: float = 0.4
    ) -> List[ConversationSearchResult]:
        """이전 대화에서 관련 내용 검색

        Args:
            query: 검색 쿼리
            n_results: 최대 결과 수
            min_relevance: 최소 관련성 (0-1)

        Returns:
            List[ConversationSearchResult]: 검색 결과 목록
        """
        try:
            # 벡터 검색 (conversation 타입만)
            results = vector_db.search(
                query=query,
                n_results=n_results * 2,  # 필터링 여유분
                filter_metadata={
                    "session_id": self.session_id,
                    "type": "conversation"
                }
            )

            # 관련성 필터링
            max_distance = 1 - min_relevance
            search_results = []

            for result in results:
                if result.distance <= max_distance:
                    # [ROLE] content 형식에서 content 추출
                    content = result.content
                    if content.startswith("["):
                        content = content.split("] ", 1)[-1]

                    search_results.append(ConversationSearchResult(
                        content=content,
                        role=result.metadata.get("role", "unknown"),
                        turn_number=result.metadata.get("turn", 0),
                        relevance=1 - result.distance,
                        timestamp=result.metadata.get("timestamp", "")
                    ))

            # 관련성 높은 순으로 정렬
            search_results.sort(key=lambda x: x.relevance, reverse=True)

            return search_results[:n_results]

        except Exception as e:
            self.logger.warning(f"Conversation search failed: {e}")
            return []

    def format_search_results(
        self,
        results: List[ConversationSearchResult]
    ) -> str:
        """검색 결과를 LLM 컨텍스트로 포맷팅

        Args:
            results: 검색 결과 목록

        Returns:
            str: 포맷된 컨텍스트 문자열
        """
        if not results:
            return ""

        parts = ["## Relevant Previous Conversations\n"]

        for i, result in enumerate(results, 1):
            role_label = "User" if result.role == "user" else "Assistant"
            relevance_pct = round(result.relevance * 100, 1)

            parts.append(
                f"### [{i}] Turn {result.turn_number} ({role_label}) "
                f"- Relevance: {relevance_pct}%\n"
                f"> {result.content[:500]}{'...' if len(result.content) > 500 else ''}\n"
            )

        return "\n".join(parts)

    def clear_session(self):
        """세션의 모든 대화 색인 삭제"""
        try:
            vector_db.delete_by_session(self.session_id)
            self._turn_counter = 0
            self.logger.info(f"Cleared conversation index for session: {self.session_id}")
        except Exception as e:
            self.logger.warning(f"Failed to clear conversation index: {e}")

    def _generate_doc_id(self, content: str, turn_number: int) -> str:
        """문서 ID 생성

        Args:
            content: 메시지 내용
            turn_number: 턴 번호

        Returns:
            str: 고유 문서 ID
        """
        data = f"{self.session_id}:conv:{turn_number}:{content[:100]}"
        return hashlib.md5(data.encode()).hexdigest()


# 캐시된 인덱서 인스턴스
_indexers: Dict[str, ConversationIndexer] = {}


def get_conversation_indexer(session_id: str) -> ConversationIndexer:
    """ConversationIndexer 인스턴스 가져오기 (캐시됨)

    Args:
        session_id: 세션 ID

    Returns:
        ConversationIndexer: 인덱서 인스턴스
    """
    if session_id not in _indexers:
        _indexers[session_id] = ConversationIndexer(session_id)
    return _indexers[session_id]
