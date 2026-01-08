"""RAG Context Builder - 질의에 맞는 컨텍스트 구성 (Phase 6 Enhanced)

사용자 질문에 관련된 코드와 이전 대화를 벡터 검색하여
LLM에게 제공할 컨텍스트를 구성합니다.

Phase 6 Enhancements:
- 확장된 대화 검색 결과 (3 → 5개)
- 압축된 히스토리 통합
- 토큰 버짓 인식
- MAX_CONTEXT_LENGTH 증가
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from app.services.vector_db import vector_db, SearchResult
from app.services.conversation_indexer import get_conversation_indexer, ConversationSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """RAG 검색 결과 컨텍스트 (Phase 6 Enhanced)"""
    formatted_context: str
    results_count: int
    files_referenced: List[str]
    avg_relevance: float
    search_query: str
    # 대화 컨텍스트 (Phase 3-D)
    conversation_results: int = 0
    conversation_context: str = ""
    # Phase 6: 토큰 정보
    estimated_tokens: int = 0
    compressed_history: Optional[str] = None


class RAGContextBuilder:
    """사용자 질문에 맞는 RAG 컨텍스트를 구성하는 서비스 (Phase 6 Enhanced)

    벡터 검색을 통해 관련 코드를 찾고,
    LLM이 이해하기 쉬운 형태로 포맷팅합니다.

    Phase 6 Enhancements:
    - Expanded conversation search (3 → 5 results)
    - Compressed history integration
    - Token budget awareness
    """

    # Phase 6: 확장된 기본 설정
    DEFAULT_N_RESULTS: int = 7              # Phase 6: 5 → 7
    DEFAULT_CONVERSATION_RESULTS: int = 5   # Phase 6: 3 → 5
    DEFAULT_MIN_RELEVANCE: float = 0.5      # 최소 관련성 (cosine distance 기준)
    MAX_CONTEXT_LENGTH: int = 12000         # Phase 6: 8000 → 12000 (토큰 절약)

    def __init__(self, session_id: str):
        """RAGContextBuilder 초기화

        Args:
            session_id: 세션 ID (검색 범위 제한용)
        """
        self.session_id = session_id
        self.logger = logging.getLogger(f"{__name__}.{session_id[:8]}")

    def build_context(
        self,
        query: str,
        n_results: int = DEFAULT_N_RESULTS,
        min_relevance: float = DEFAULT_MIN_RELEVANCE,
        language: Optional[str] = None
    ) -> RAGContext:
        """질문에 관련된 코드 컨텍스트 생성

        Args:
            query: 사용자 질문 또는 검색 쿼리
            n_results: 최대 결과 수
            min_relevance: 최소 관련성 점수 (0-1, 높을수록 엄격)
            language: 언어 필터 (선택적)

        Returns:
            RAGContext: 포맷된 컨텍스트 정보
        """
        self.logger.debug(f"Building RAG context for: {query[:50]}...")

        # 벡터 검색 실행
        try:
            results = vector_db.search_code(
                query=query,
                session_id=self.session_id,
                language=language,
                n_results=n_results * 2  # 필터링 여유분
            )
        except Exception as e:
            self.logger.warning(f"Vector search failed: {e}")
            return RAGContext(
                formatted_context="",
                results_count=0,
                files_referenced=[],
                avg_relevance=0.0,
                search_query=query
            )

        if not results:
            self.logger.debug("No search results found")
            return RAGContext(
                formatted_context="",
                results_count=0,
                files_referenced=[],
                avg_relevance=0.0,
                search_query=query
            )

        # 관련성 필터링 (cosine distance: 0=동일, 2=반대)
        # distance < (1 - min_relevance) 는 관련성 > min_relevance
        max_distance = 1 - min_relevance
        relevant = [r for r in results if r.distance <= max_distance][:n_results]

        if not relevant:
            self.logger.debug(f"No results above relevance threshold {min_relevance}")
            return RAGContext(
                formatted_context="",
                results_count=0,
                files_referenced=[],
                avg_relevance=0.0,
                search_query=query
            )

        # 컨텍스트 포맷팅
        formatted_context, files = self._format_results(relevant)

        # 평균 관련성 계산
        avg_relevance = 1 - (sum(r.distance for r in relevant) / len(relevant))

        self.logger.info(
            f"RAG context built: {len(relevant)} results, "
            f"avg relevance: {avg_relevance:.2%}, "
            f"files: {files[:3]}..."
        )

        return RAGContext(
            formatted_context=formatted_context,
            results_count=len(relevant),
            files_referenced=files,
            avg_relevance=avg_relevance,
            search_query=query
        )

    def _format_results(self, results: List[SearchResult]) -> Tuple[str, List[str]]:
        """검색 결과를 LLM 컨텍스트로 포맷팅

        Args:
            results: 검색 결과 목록

        Returns:
            Tuple[str, List[str]]: (포맷된 컨텍스트, 참조 파일 목록)
        """
        context_parts = ["## Relevant Code from Project\n"]
        files_referenced = []
        current_length = 0

        for i, result in enumerate(results, 1):
            filename = result.metadata.get('filename', 'unknown')
            language = result.metadata.get('language', 'text')
            description = result.metadata.get('description', '')
            relevance = round((1 - result.distance) * 100, 1)

            # 코드 내용 추출 (document에서 코드 부분만)
            code = self._extract_code_from_document(result.content)

            # 길이 체크
            entry_length = len(filename) + len(code) + 100
            if current_length + entry_length > self.MAX_CONTEXT_LENGTH:
                self.logger.debug(f"Context truncated at result {i}")
                break

            context_parts.append(f"""
### [{i}] {filename} (Relevance: {relevance}%)
{f"> {description}" if description else ""}

```{language}
{code}
```
""")
            files_referenced.append(filename)
            current_length += entry_length

        return "\n".join(context_parts), files_referenced

    def _extract_code_from_document(self, document: str) -> str:
        """문서에서 코드 부분만 추출

        add_code_snippet에서 저장한 형식:
        "{description}\n\nFilename: {filename}\nLanguage: {language}\n\n{code}"

        Args:
            document: 전체 문서 내용

        Returns:
            str: 추출된 코드
        """
        # 마지막 두 줄 바꿈 이후가 코드
        parts = document.split('\n\n')
        if len(parts) >= 3:
            return parts[-1]  # 마지막 부분이 코드
        return document

    def search_conversation(
        self,
        query: str,
        n_results: int = None,  # Phase 6: Use DEFAULT_CONVERSATION_RESULTS
        min_relevance: float = 0.4
    ) -> Tuple[str, List[ConversationSearchResult]]:
        """이전 대화에서 관련 내용 검색 (Phase 6 Enhanced)

        Phase 6: 기본 결과 수 3 → 5개로 확장

        Args:
            query: 검색 쿼리
            n_results: 최대 결과 수 (기본: 5)
            min_relevance: 최소 관련성

        Returns:
            Tuple[str, List]: (포맷된 컨텍스트, 검색 결과)
        """
        # Phase 6: 기본값 적용
        if n_results is None:
            n_results = self.DEFAULT_CONVERSATION_RESULTS

        try:
            indexer = get_conversation_indexer(self.session_id)
            results = indexer.search_conversation(
                query=query,
                n_results=n_results,
                min_relevance=min_relevance
            )

            if not results:
                return "", []

            formatted = indexer.format_search_results(results)
            return formatted, results

        except Exception as e:
            self.logger.warning(f"Conversation search failed: {e}")
            return "", []

    def enrich_query(
        self,
        user_request: str,
        n_results: int = None,  # Phase 6: Use class default
        min_relevance: float = None,
        include_conversation: bool = True,
        compressed_history: Optional[List[Dict]] = None  # Phase 6: 압축된 히스토리
    ) -> Tuple[str, RAGContext]:
        """사용자 요청을 RAG 컨텍스트로 보강 (Phase 6 Enhanced)

        코드 검색과 대화 검색을 모두 수행하여
        관련 컨텍스트를 사용자 요청에 추가합니다.

        Phase 6 Enhancements:
        - 확장된 대화 검색 (3 → 5개)
        - 압축된 히스토리 통합 지원
        - 토큰 추정 추가

        Args:
            user_request: 원본 사용자 요청
            n_results: 최대 결과 수 (기본: 7)
            min_relevance: 최소 관련성 (기본: 0.5)
            include_conversation: 대화 검색 포함 여부
            compressed_history: Phase 6 - 압축된 대화 히스토리

        Returns:
            Tuple[str, RAGContext]: (보강된 요청, RAG 컨텍스트)
        """
        # Phase 6: 기본값 적용
        if n_results is None:
            n_results = self.DEFAULT_N_RESULTS
        if min_relevance is None:
            min_relevance = self.DEFAULT_MIN_RELEVANCE

        # 1. 코드 검색
        rag_context = self.build_context(
            query=user_request,
            n_results=n_results,
            min_relevance=min_relevance
        )

        # 2. 대화 검색 (선택적) - Phase 6: 확장된 결과 수 (3 → 5)
        conv_context = ""
        conv_results = 0
        if include_conversation:
            conv_context, conv_search_results = self.search_conversation(
                query=user_request,
                n_results=self.DEFAULT_CONVERSATION_RESULTS,  # Phase 6: 5개
                min_relevance=0.4
            )
            conv_results = len(conv_search_results)

            # RAGContext에 대화 정보 추가
            rag_context.conversation_results = conv_results
            rag_context.conversation_context = conv_context

        # 3. 컨텍스트 결합
        context_parts = []

        # Phase 6: 압축된 히스토리 추가
        if compressed_history:
            compressed_content = self._format_compressed_history(compressed_history)
            if compressed_content:
                context_parts.append(compressed_content)
                rag_context.compressed_history = compressed_content

        if rag_context.formatted_context:
            context_parts.append(rag_context.formatted_context)

        if conv_context:
            context_parts.append(conv_context)

        if context_parts:
            combined_context = "\n\n".join(context_parts)
            enriched_request = f"{user_request}\n\n{combined_context}"

            # Phase 6: 토큰 추정
            rag_context.estimated_tokens = len(combined_context) // 4  # 대략적 추정

            self.logger.info(
                f"Query enriched: {rag_context.results_count} code results, "
                f"{conv_results} conversation results, "
                f"~{rag_context.estimated_tokens} tokens"
            )
            return enriched_request, rag_context

        return user_request, rag_context

    def _format_compressed_history(self, compressed_history: List[Dict]) -> str:
        """압축된 히스토리를 포맷팅 (Phase 6)

        Args:
            compressed_history: 압축된 메시지 리스트

        Returns:
            str: 포맷된 히스토리 문자열
        """
        if not compressed_history:
            return ""

        parts = ["## Compressed Conversation History\n"]

        for msg in compressed_history:
            if msg.get("is_compressed"):
                # 압축된 요약 메시지
                parts.append(msg.get("content", ""))
            else:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")[:500]  # 제한된 미리보기
                if len(msg.get("content", "")) > 500:
                    content += "..."
                parts.append(f"**{role}**: {content}\n")

        return "\n".join(parts)


# 캐시된 빌더 인스턴스
_builders: Dict[str, RAGContextBuilder] = {}


def get_rag_builder(session_id: str) -> RAGContextBuilder:
    """RAGContextBuilder 인스턴스 가져오기 (캐시됨)

    Args:
        session_id: 세션 ID

    Returns:
        RAGContextBuilder: 빌더 인스턴스
    """
    if session_id not in _builders:
        _builders[session_id] = RAGContextBuilder(session_id)
    return _builders[session_id]
