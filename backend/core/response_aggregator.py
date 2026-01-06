"""Response Aggregator - 핸들러 결과를 통합 응답으로 집계.

이 모듈은 다양한 핸들러의 결과를 수집하고
통합된 UnifiedResponse 형식으로 변환합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseType(str, Enum):
    """응답 유형 열거형"""
    QUICK_QA = "quick_qa"
    PLANNING = "planning"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    FEEDBACK_NEEDED = "feedback_needed"


@dataclass
class HandlerResult:
    """핸들러 실행 결과"""
    content: str                                    # 사용자 응답 텍스트
    artifacts: List[Dict[str, Any]] = field(default_factory=list)  # 생성된 파일들
    plan_file: Optional[str] = None                 # 저장된 계획 파일 경로
    metadata: Dict[str, Any] = field(default_factory=dict)  # 추가 메타데이터
    success: bool = True                            # 성공 여부
    error: Optional[str] = None                     # 에러 메시지


@dataclass
class UnifiedResponse:
    """통합 응답 구조

    모든 응답 타입에서 동일한 구조로 반환되는 통합 응답 객체입니다.
    """
    response_type: str                              # 응답 유형
    content: str                                    # 사용자 친화적 응답 텍스트
    artifacts: List[Dict[str, Any]]                 # 생성된 아티팩트 목록
    plan_file: Optional[str] = None                 # 저장된 계획 파일 경로
    analysis: Optional[Dict[str, Any]] = None       # Supervisor 분석 결과
    next_actions: List[str] = field(default_factory=list)  # 제안된 다음 행동
    metadata: Dict[str, Any] = field(default_factory=dict)  # 추가 메타데이터
    success: bool = True                            # 성공 여부
    error: Optional[str] = None                     # 에러 메시지

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "response_type": self.response_type,
            "content": self.content,
            "artifacts": self.artifacts,
            "plan_file": self.plan_file,
            "analysis": self.analysis,
            "next_actions": self.next_actions,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error
        }

    @classmethod
    def from_error(cls, error: str, response_type: str = "error") -> "UnifiedResponse":
        """에러 응답 생성"""
        return cls(
            response_type=response_type,
            content=f"오류가 발생했습니다: {error}",
            artifacts=[],
            success=False,
            error=error
        )


@dataclass
class StreamUpdate:
    """스트리밍 업데이트"""
    agent: str                                      # 에이전트 이름
    update_type: str                                # 업데이트 유형 (thinking, artifact, completed, error)
    status: str                                     # 상태 (running, completed, error)
    message: str                                    # 메시지
    data: Optional[Dict[str, Any]] = None           # 추가 데이터
    timestamp: Optional[str] = None                 # 타임스탬프
    streaming_content: Optional[str] = None         # 실시간 상세 출력 (진행 중인 작업 내용)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = {
            "agent": self.agent,
            "type": self.update_type,
            "status": self.status,
            "message": self.message
        }
        if self.data:
            result["data"] = self.data
        if self.timestamp:
            result["timestamp"] = self.timestamp
        if self.streaming_content:
            result["streaming_content"] = self.streaming_content
        return result


class ResponseAggregator:
    """핸들러 결과를 UnifiedResponse로 집계

    이 클래스는 다양한 핸들러의 결과를 수집하고
    통합된 형식으로 변환하는 역할을 합니다.
    """

    def aggregate(
        self,
        result: HandlerResult,
        analysis: Dict[str, Any]
    ) -> UnifiedResponse:
        """핸들러 결과와 분석 결과를 통합 응답으로 집계

        Args:
            result: 핸들러 실행 결과
            analysis: Supervisor 분석 결과

        Returns:
            UnifiedResponse: 통합 응답 객체
        """
        response_type = analysis.get("response_type", ResponseType.QUICK_QA)

        # analysis 정보 정리
        analysis_summary = {
            "complexity": analysis.get("complexity"),
            "task_type": analysis.get("task_type"),
            "required_agents": analysis.get("required_agents", []),
            "confidence": analysis.get("confidence_score", 0.0),
            "workflow_strategy": analysis.get("workflow_strategy")
        }

        # 다음 행동 제안
        next_actions = self._suggest_next_actions(response_type, result)

        return UnifiedResponse(
            response_type=response_type,
            content=result.content,
            artifacts=result.artifacts,
            plan_file=result.plan_file,
            analysis=analysis_summary,
            next_actions=next_actions,
            metadata=result.metadata,
            success=result.success,
            error=result.error
        )

    def _suggest_next_actions(
        self,
        response_type: str,
        result: HandlerResult
    ) -> List[str]:
        """응답 타입과 결과에 따른 다음 행동 제안

        Args:
            response_type: 응답 타입
            result: 핸들러 결과

        Returns:
            List[str]: 제안된 다음 행동 목록
        """
        actions = []

        if response_type == ResponseType.QUICK_QA:
            actions.append("추가 질문하기")

        elif response_type == ResponseType.PLANNING:
            actions.append("코드 생성 시작")
            actions.append("계획 수정 요청")
            if result.plan_file:
                actions.append("계획 파일 확인")

        elif response_type == ResponseType.CODE_GENERATION:
            if result.artifacts:
                actions.append("테스트 실행")
                actions.append("코드 리뷰 요청")
            actions.append("추가 기능 구현")
            actions.append("코드 수정 요청")

        elif response_type == ResponseType.CODE_REVIEW:
            actions.append("수정 사항 적용")
            actions.append("추가 리뷰 요청")

        elif response_type == ResponseType.DEBUGGING:
            actions.append("수정 사항 적용")
            actions.append("테스트 실행")

        return actions

    def aggregate_stream_updates(
        self,
        updates: List[StreamUpdate],
        analysis: Dict[str, Any]
    ) -> UnifiedResponse:
        """스트리밍 업데이트 목록을 최종 응답으로 집계

        Args:
            updates: 스트리밍 업데이트 목록
            analysis: Supervisor 분석 결과

        Returns:
            UnifiedResponse: 통합 응답 객체
        """
        # 아티팩트 수집
        artifacts = []
        for update in updates:
            if update.data and update.data.get("artifacts"):
                artifacts.extend(update.data["artifacts"])

        # 최종 메시지 찾기 (마지막 completed 업데이트)
        content = ""
        for update in reversed(updates):
            if update.status == "completed" and update.message:
                content = update.message
                break

        if not content:
            content = self._generate_summary_from_updates(updates, artifacts)

        result = HandlerResult(
            content=content,
            artifacts=artifacts,
            metadata={
                "update_count": len(updates),
                "agents_used": list(set(u.agent for u in updates))
            }
        )

        return self.aggregate(result, analysis)

    def _generate_summary_from_updates(
        self,
        updates: List[StreamUpdate],
        artifacts: List[Dict[str, Any]]
    ) -> str:
        """업데이트 목록에서 요약 생성"""
        if not artifacts:
            return "작업이 완료되었습니다."

        files = [a.get("filename", "unknown") for a in artifacts]
        return f"다음 파일들이 생성되었습니다: {', '.join(files)}"
