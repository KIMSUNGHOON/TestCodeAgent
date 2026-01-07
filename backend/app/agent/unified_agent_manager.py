"""Unified Agent Manager - 통합 에이전트 매니저.

이 모듈은 모든 요청을 Supervisor를 통해 분석하고
적절한 핸들러로 라우팅하는 중앙 컴포넌트입니다.

Claude Code / OpenAI Codex 방식의 통합 워크플로우를 구현합니다:
User Prompt → Supervisor → Handler → Response
"""
import logging
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, Union, AsyncGenerator, List
from datetime import datetime

from core.supervisor import SupervisorAgent
from core.response_aggregator import (
    ResponseAggregator,
    UnifiedResponse,
    ResponseType,
    StreamUpdate
)
from core.context_store import ContextStore, ConversationContext, get_context_store
from app.agent.handlers import (
    QuickQAHandler,
    PlanningHandler,
    CodeGenerationHandler,
    HandlerResult
)

logger = logging.getLogger(__name__)


class UnifiedAgentManager:
    """통합 에이전트 매니저

    모든 사용자 요청을 Supervisor를 통해 분석하고
    응답 타입에 따라 적절한 핸들러로 라우팅합니다.

    Flow:
    1. 컨텍스트 로드
    2. Supervisor 분석
    3. 응답 타입별 핸들러 실행
    4. 응답 집계
    5. 컨텍스트 저장

    Attributes:
        supervisor: Supervisor 에이전트
        context_store: 컨텍스트 저장소
        response_aggregator: 응답 집계기
        handlers: 응답 타입별 핸들러 딕셔너리
    """

    def __init__(self):
        """UnifiedAgentManager 초기화"""
        # Supervisor 초기화 (API 모드)
        self.supervisor = SupervisorAgent(use_api=True)

        # 컨텍스트 저장소
        self.context_store = get_context_store()

        # 응답 집계기
        self.response_aggregator = ResponseAggregator()

        # 응답 타입별 핸들러
        self.handlers = {
            ResponseType.QUICK_QA: QuickQAHandler(),
            ResponseType.PLANNING: PlanningHandler(),
            ResponseType.CODE_GENERATION: CodeGenerationHandler(),
            # CODE_REVIEW와 DEBUGGING은 CodeGenerationHandler 재사용
            ResponseType.CODE_REVIEW: CodeGenerationHandler(),
            ResponseType.DEBUGGING: CodeGenerationHandler(),
        }

        logger.info("UnifiedAgentManager initialized")

    async def process_request(
        self,
        session_id: str,
        user_message: str,
        workspace: Optional[str] = None,
        stream: bool = False
    ) -> Union[UnifiedResponse, AsyncGenerator[StreamUpdate, None]]:
        """통합 요청 처리

        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            workspace: 워크스페이스 경로 (옵션)
            stream: 스트리밍 모드 여부

        Returns:
            Union[UnifiedResponse, AsyncGenerator]: 통합 응답 또는 스트리밍 제너레이터
        """
        logger.info(f"Processing request: session={session_id}, stream={stream}")
        start_time = datetime.now()

        try:
            # 1. 컨텍스트 로드
            context = await self.context_store.load(session_id)

            # 워크스페이스 업데이트 (있는 경우)
            if workspace:
                await self.context_store.update_workspace(session_id, workspace)
                context.workspace = workspace

            # 2. Supervisor 분석
            logger.info("Running Supervisor analysis...")
            analysis = await self._analyze_request(user_message, context)

            response_type = analysis.get("response_type", ResponseType.QUICK_QA)
            logger.info(f"Response type determined: {response_type}")

            # 3. 핸들러 선택
            handler = self.handlers.get(response_type)
            if not handler:
                handler = self.handlers[ResponseType.QUICK_QA]
                logger.warning(f"Unknown response type: {response_type}, using QuickQA")

            # 4. 핸들러 실행
            if stream:
                # 스트리밍 모드
                return self._stream_response(
                    handler, user_message, analysis, context, session_id
                )
            else:
                # 비스트리밍 모드
                result = await handler.execute(user_message, analysis, context)

                # 5. 응답 집계
                response = self.response_aggregator.aggregate(result, analysis)

                # 6. 컨텍스트 저장
                await self.context_store.save(
                    session_id=session_id,
                    user_message=user_message,
                    assistant_response=response.content,
                    analysis=response.analysis,
                    artifacts=response.artifacts
                )

                # 메타데이터 추가
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                response.metadata = response.metadata or {}
                response.metadata["latency_ms"] = int(elapsed_ms)
                response.metadata["session_id"] = session_id

                logger.info(f"Request completed in {elapsed_ms:.0f}ms")
                return response

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return UnifiedResponse.from_error(str(e))

    async def _analyze_request(
        self,
        user_message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Supervisor를 통한 요청 분석

        Args:
            user_message: 사용자 메시지
            context: 대화 컨텍스트

        Returns:
            Dict[str, Any]: 분석 결과
        """
        # 컨텍스트를 Supervisor에 전달
        context_dict = context.to_dict() if context else None

        # Supervisor 동기 분석 사용 (비동기 버전은 스트리밍용)
        analysis = self.supervisor.analyze_request(user_message, context_dict)

        return analysis

    async def _stream_response(
        self,
        handler,
        user_message: str,
        analysis: Dict[str, Any],
        context: ConversationContext,
        session_id: str
    ) -> AsyncGenerator[StreamUpdate, None]:
        """스트리밍 응답 생성

        Args:
            handler: 핸들러 인스턴스
            user_message: 사용자 메시지
            analysis: Supervisor 분석 결과
            context: 대화 컨텍스트
            session_id: 세션 ID

        Yields:
            StreamUpdate: 스트리밍 업데이트
        """
        # Supervisor 분석 결과 전송
        yield StreamUpdate(
            agent="Supervisor",
            update_type="analysis",
            status="completed",
            message=f"분석 완료: {analysis.get('response_type', 'unknown')}",
            streaming_content=f"요청 분석 결과:\n- 응답 유형: {analysis.get('response_type', 'unknown')}\n- 복잡도: {analysis.get('complexity', 'unknown')}\n- 작업 유형: {analysis.get('task_type', 'unknown')}",
            data={
                "response_type": analysis.get("response_type"),
                "complexity": analysis.get("complexity"),
                "task_type": analysis.get("task_type")
            }
        )

        # 핸들러 스트리밍 실행
        artifacts = []
        final_content = ""
        plan_file = None
        workspace = context.workspace if context else None

        async for update in handler.execute_stream(user_message, analysis, context):
            # 아티팩트가 있으면 workspace에 저장
            if update.data and update.data.get("artifacts") and workspace:
                saved_artifacts = []
                for artifact in update.data["artifacts"]:
                    if artifact.get("content") and not artifact.get("saved"):
                        save_result = await self._save_artifact_to_workspace(artifact, workspace)
                        artifact.update(save_result)
                    saved_artifacts.append(artifact)
                update.data["artifacts"] = saved_artifacts

            yield update

            # 최종 결과 수집
            if update.update_type == "completed" and update.data:
                if update.data.get("artifacts"):
                    artifacts.extend(update.data["artifacts"])
                if update.data.get("full_content"):
                    final_content = update.data["full_content"]
                if update.data.get("plan_file"):
                    plan_file = update.data["plan_file"]

        # 컨텍스트 저장
        await self.context_store.save(
            session_id=session_id,
            user_message=user_message,
            assistant_response=final_content or "응답 완료",
            analysis=analysis,
            artifacts=artifacts
        )

        # 다음 행동 제안 생성
        next_actions = self._suggest_next_actions(
            analysis.get("response_type", ResponseType.QUICK_QA),
            artifacts,
            plan_file
        )

        # 저장된 파일 목록 생성
        saved_files = [
            f"✓ {a.get('filename')} ({a.get('saved_path', '저장됨')})"
            for a in artifacts if a.get("saved")
        ]
        saved_summary = "\n".join(saved_files) if saved_files else "생성된 파일 없음"

        # 최종 완료 업데이트
        yield StreamUpdate(
            agent="UnifiedAgentManager",
            update_type="done",
            status="completed",
            message="모든 처리가 완료되었습니다.",
            streaming_content=f"## 작업 완료\n\n### 생성된 파일 ({len(artifacts)}개)\n{saved_summary}",
            data={
                "session_id": session_id,
                "artifact_count": len(artifacts),
                "artifacts": artifacts,
                "next_actions": next_actions,
                "plan_file": plan_file
            }
        )

    async def _save_artifact_to_workspace(
        self,
        artifact: Dict[str, Any],
        workspace: str
    ) -> Dict[str, Any]:
        """Artifact를 워크스페이스에 저장

        동일한 파일이 존재할 경우 내용 비교 후:
        - 동일 내용: 덮어쓰지 않고 기존 파일 유지
        - 다른 내용: 버전 번호를 붙여서 새 파일로 저장 (예: file_v2.py)

        Args:
            artifact: 저장할 artifact 정보 (filename, content, language)
            workspace: 워크스페이스 경로

        Returns:
            Dict: 저장 결과 (saved, saved_path, saved_at, error, action)
        """
        try:
            filename = artifact.get("filename", "code.py")
            content = artifact.get("content", "")

            if not content:
                return {
                    "saved": False,
                    "saved_path": None,
                    "saved_at": None,
                    "error": "Empty content",
                    "action": None
                }

            # 경로 정리 (보안: 경로 탈출 방지)
            # 파일명에서 상위 디렉토리 이동 방지
            safe_parts = []
            for part in filename.replace("\\", "/").split("/"):
                if part and part != ".." and part != ".":
                    safe_parts.append(part)

            if not safe_parts:
                safe_parts = ["code.py"]

            safe_filename = "/".join(safe_parts)
            file_path = Path(workspace) / safe_filename

            # 부모 디렉토리 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)

            action = "created"  # 기본 액션

            # 파일이 이미 존재하는 경우 처리
            if file_path.exists():
                try:
                    # 기존 파일 내용 읽기
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        existing_content = await f.read()

                    # 내용이 동일하면 저장 건너뛰기
                    if existing_content.strip() == content.strip():
                        logger.info(f"Skipped duplicate artifact: {file_path}")
                        return {
                            "saved": True,
                            "saved_path": str(file_path),
                            "saved_at": datetime.now().isoformat(),
                            "error": None,
                            "action": "skipped_duplicate"
                        }

                    # 내용이 다르면 버전 번호 추가
                    file_path = self._get_versioned_path(file_path)
                    action = "created_new_version"
                    logger.info(f"Creating new version: {file_path}")

                except Exception as read_error:
                    logger.warning(f"Could not read existing file for comparison: {read_error}")
                    # 읽기 실패 시 버전 번호 추가하여 안전하게 저장
                    file_path = self._get_versioned_path(file_path)
                    action = "created_new_version"

            # 파일 저장
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            logger.info(f"Saved artifact to: {file_path} (action: {action})")

            return {
                "saved": True,
                "saved_path": str(file_path),
                "saved_at": datetime.now().isoformat(),
                "error": None,
                "action": action
            }

        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
            return {
                "saved": False,
                "saved_path": None,
                "saved_at": None,
                "error": str(e),
                "action": None
            }

    def _get_versioned_path(self, file_path: Path) -> Path:
        """파일이 이미 존재할 경우 버전 번호가 포함된 새 경로 생성

        크로스 플랫폼 호환: Windows/Linux/MacOS 모두 지원

        Args:
            file_path: 원본 파일 경로

        Returns:
            Path: 버전 번호가 포함된 새 파일 경로 (예: file_v2.py)
        """
        stem = file_path.stem  # 확장자 제외한 파일명
        suffix = file_path.suffix  # 확장자
        parent = file_path.parent

        # 버전 번호 찾기 (file_v2.py 형식 지원)
        import re
        version_match = re.match(r'^(.+)_v(\d+)$', stem)

        if version_match:
            base_stem = version_match.group(1)
            current_version = int(version_match.group(2))
        else:
            base_stem = stem
            current_version = 1

        # 다음 버전 번호로 새 경로 생성
        version = current_version + 1
        new_path = parent / f"{base_stem}_v{version}{suffix}"

        # 해당 버전도 존재하면 다음 버전 찾기
        while new_path.exists():
            version += 1
            new_path = parent / f"{base_stem}_v{version}{suffix}"

            # 무한 루프 방지 (최대 100개 버전)
            if version > 100:
                # 타임스탬프 기반 fallback
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_path = parent / f"{base_stem}_{timestamp}{suffix}"
                break

        return new_path

    async def get_context(self, session_id: str) -> ConversationContext:
        """세션 컨텍스트 조회

        Args:
            session_id: 세션 ID

        Returns:
            ConversationContext: 컨텍스트 객체
        """
        return await self.context_store.load(session_id)

    async def clear_context(self, session_id: str):
        """세션 컨텍스트 초기화

        Args:
            session_id: 세션 ID
        """
        await self.context_store.clear(session_id)
        logger.info(f"Context cleared: {session_id}")

    def get_stats(self) -> Dict[str, Any]:
        """매니저 통계 조회

        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            "context_store": self.context_store.get_stats(),
            "handlers": list(self.handlers.keys()),
            "supervisor_model": self.supervisor.model_type
        }

    def _suggest_next_actions(
        self,
        response_type: str,
        artifacts: List[Dict[str, Any]],
        plan_file: Optional[str]
    ) -> List[str]:
        """응답 타입과 결과에 따른 다음 행동 제안

        Args:
            response_type: 응답 타입
            artifacts: 생성된 아티팩트
            plan_file: 계획 파일 경로

        Returns:
            List[str]: 제안된 다음 행동 목록
        """
        actions = []

        if response_type == ResponseType.QUICK_QA:
            actions.append("추가 질문하기")

        elif response_type == ResponseType.PLANNING:
            actions.append("코드 생성 시작")
            actions.append("계획 수정 요청")
            if plan_file:
                actions.append("계획 파일 확인")

        elif response_type == ResponseType.CODE_GENERATION:
            if artifacts:
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


# 싱글톤 인스턴스
_unified_manager: Optional[UnifiedAgentManager] = None


def get_unified_agent_manager() -> UnifiedAgentManager:
    """UnifiedAgentManager 싱글톤 인스턴스 반환

    Returns:
        UnifiedAgentManager: 통합 에이전트 매니저 인스턴스
    """
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedAgentManager()
    return _unified_manager
