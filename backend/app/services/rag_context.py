"""RAG Context Builder - 질의에 맞는 컨텍스트 구성

사용자 질문에 관련된 코드를 벡터 검색하여
LLM에게 제공할 컨텍스트를 구성합니다.
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.services.vector_db import vector_db, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """RAG 검색 결과 컨텍스트"""
    formatted_context: str
    results_count: int
    files_referenced: List[str]
    avg_relevance: float
    search_query: str


class RAGContextBuilder:
    """사용자 질문에 맞는 RAG 컨텍스트를 구성하는 서비스

    벡터 검색을 통해 관련 코드를 찾고,
    LLM이 이해하기 쉬운 형태로 포맷팅합니다.
    """

    # 기본 설정
    DEFAULT_N_RESULTS: int = 5
    DEFAULT_MIN_RELEVANCE: float = 0.5  # 최소 관련성 (cosine distance 기준)
    MAX_CONTEXT_LENGTH: int = 8000  # 최대 컨텍스트 길이 (토큰 절약)

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

    def enrich_query(
        self,
        user_request: str,
        n_results: int = DEFAULT_N_RESULTS,
        min_relevance: float = DEFAULT_MIN_RELEVANCE
    ) -> Tuple[str, RAGContext]:
        """사용자 요청을 RAG 컨텍스트로 보강

        Args:
            user_request: 원본 사용자 요청
            n_results: 최대 결과 수
            min_relevance: 최소 관련성

        Returns:
            Tuple[str, RAGContext]: (보강된 요청, RAG 컨텍스트)
        """
        rag_context = self.build_context(
            query=user_request,
            n_results=n_results,
            min_relevance=min_relevance
        )

        if rag_context.formatted_context:
            enriched_request = f"{user_request}\n\n{rag_context.formatted_context}"
            return enriched_request, rag_context

        return user_request, rag_context


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
