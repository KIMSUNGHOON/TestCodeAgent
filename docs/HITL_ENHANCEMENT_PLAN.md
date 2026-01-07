# HITL (Human-In-The-Loop) Enhancement Plan v2.0

**버전**: 2.0
**작성일**: 2026-01-07 (수정)
**목표**: 기존 시스템과 호환되는 진정한 HITL 워크플로우 구현

> **중요**: 이 계획은 기존 시스템에 **영향을 주지 않고** 새로운 HITL 기능을 **옵션으로 추가**합니다.

---

## 1. 현재 시스템 상태 (2026-01-07 기준)

### 1.1 이미 구현된 주요 기능 (Requirement.md 기반)

#### 완성도 높은 Streaming UI
- ✅ 실시간 진행 상황 표시 (Issue 2 해결됨)
- ✅ Agent별 상태 메시지 (`getAgentStatusMessage()`)
- ✅ Streaming content 전달 (`streaming_content` 필드)
- ✅ Live output 업데이트
- ✅ Token usage 실시간 표시
- ✅ 확장/축소 토글 기능

#### 완성도 높은 Artifact 관리
- ✅ Workspace에 파일 자동 저장 (Issue 3 해결됨)
- ✅ FileTreeViewer (Windows 스타일 트리 구조)
- ✅ 코드 뷰어 팝업
- ✅ ZIP 다운로드
- ✅ 기존 파일 modify (버전닝 제거됨)

#### 강력한 대화 컨텍스트 관리
- ✅ 이전 대화 히스토리 전달 (`_build_enriched_message()`)
- ✅ 이전 plan 재사용 로직
- ✅ Markdown 렌더링 및 코드 구문 강조

#### 견고한 HITL 인프라
- ✅ HITLManager (WebSocket, 비동기, 타임아웃)
- ✅ human_approval_node (LangGraph 통합)
- ✅ HITL API Routes (REST + WebSocket)
- ✅ HITLModal (5가지 체크포인트 타입)

#### DeepSeek-R1 최적화
- ✅ `<think>` 태그 처리 (모든 파싱 함수)
- ✅ RTX 3090 + Ollama 병렬 설정 (`MAX_PARALLEL_AGENTS=2`)
- ✅ 모델별 프롬프트 엔지니어링 준비

#### 크로스 플랫폼 호환성
- ✅ Windows/Linux/MacOS 경로 처리
- ✅ OS별 기본 workspace (`getDefaultWorkspace()`)
- ✅ 환경 변수 우선 참조

### 1.2 현재 HITL 시스템의 특징

**장점**:
- 완전한 pause/resume 메커니즘
- 다양한 체크포인트 타입 (approval, review, edit, choice, confirm)
- WebSocket 실시간 통신

**현재 한계**:
1. **정적 트리거**: 특정 노드에 도달해야만 HITL 발생 (예: human_approval_node)
2. **모달 기반 UI**: 대화 흐름과 분리된 별도 팝업
3. **수동 인터럽트 없음**: 사용자가 실행 중 임의로 일시 정지 불가
4. **AI 주도 질문 없음**: Agent가 스스로 불확실성 감지 시 질문 생성 불가

---

## 2. 개선 목표 (사용자 요구사항 기반)

> "프롬프트 입력창을 통해서 중간에 다이나믹하게 Human In The Loop을 통해서 피드백을 받는것입니다."

> "reasoning을 통해서 스스로 feedback을 받을것인지. 아니면 항상 인터럽트가 가능하게 할 것인지."

### 2.1 핵심 요구사항

1. **AI-Driven HITL**: Agent가 reasoning 중 불확실성 감지 시 자동으로 질문 생성
2. **User-Driven HITL**: 사용자가 워크플로우 실행 중 언제든지 Pause 버튼으로 중단
3. **통합 채팅 UI**: 별도 모달이 아닌 채팅창에서 자연스럽게 피드백
4. **기존 시스템 보호**: 기본 동작은 변경 없음, 새 기능은 옵션으로 활성화

---

## 3. 설계 원칙 (기존 시스템 보호)

### 3.1 호환성 보장 전략

#### 원칙 1: Feature Flag 기반 점진적 도입
```python
# .env 설정
ENABLE_DYNAMIC_HITL=false  # 기본값: 비활성화
ENABLE_PAUSE_BUTTON=false  # 기본값: 비활성화
ENABLE_INLINE_HITL_UI=false  # 기본값: 비활성화
```

- 새 기능은 **명시적으로 활성화**해야만 동작
- 기본 설정에서는 **기존 동작 그대로 유지**
- 사용자가 원하면 개별 기능을 하나씩 테스트 가능

#### 원칙 2: 기존 코드 경로 유지
```python
# 기존 코드는 그대로, 새 로직은 조건부로 추가
if settings.enable_dynamic_hitl:
    # 새 HITL 로직
    hitl_request = self._parse_dynamic_hitl(agent_output)
    if hitl_request:
        yield hitl_request
else:
    # 기존 동작 유지 (아무 변화 없음)
    pass
```

#### 원칙 3: Backward Compatible API
- 기존 API 엔드포인트는 변경 없음
- 새 엔드포인트는 별도 추가 (`/hitl/dynamic`, `/workflow/pause`)
- 프론트엔드도 기존 UI와 신규 UI 병행 사용 가능

#### 원칙 4: 점진적 Rollout
```
Phase 0: 기존 시스템 완전 보호 (기본값)
  ↓
Phase 1: AI-Driven HITL 테스트 (opt-in)
  ↓
Phase 2: User-Driven Pause 테스트 (opt-in)
  ↓
Phase 3: 통합 채팅 UI 테스트 (opt-in)
  ↓
Phase 4: 안정화 후 기본값 변경 고려
```

### 3.2 기존 시스템 영향도 최소화

| 컴포넌트 | 기존 동작 | 새 기능 활성화 시 | 영향도 |
|---------|---------|-----------------|-------|
| HITLManager | 변경 없음 | 새 메서드 추가만 | ⭕ 없음 |
| human_approval_node | 변경 없음 | Feature flag로 분기 | ⭕ 없음 |
| UnifiedAgentManager | 변경 없음 | 조건부 파싱 추가 | ⭕ 없음 |
| WorkflowInterface | 변경 없음 | 새 컴포넌트 조건부 렌더 | ⭕ 없음 |

---

## 4. 아키텍처 설계 (기존 시스템 확장)

### 4.1 AI-Driven HITL (동적 질문 생성)

**목표**: Agent가 스스로 불확실성 감지하고 HITL 요청 생성

#### 4.1.1 프롬프트 강화 (Opt-in)

**새 파일**: `backend/app/agent/prompts/hitl_guidelines.py`

```python
DYNAMIC_HITL_GUIDELINES = """
[OPTIONAL] If you need user input, you can request feedback:

**HITL_REQUEST:**
- **Type**: question | choice | confirm
- **Title**: Brief title
- **Question**: Your question
- **Context**: Why you need this input

Example:
**HITL_REQUEST:**
- **Type**: question
- **Title**: Project Directory Name
- **Question**: What should I name the project directory?
- **Context**: This determines folder structure.

When to request input:
1. Unclear requirements
2. Critical decisions (project names, file paths)
3. Security-sensitive operations
4. Multiple valid approaches

IMPORTANT: Only use HITL_REQUEST if absolutely necessary.
"""
```

#### 4.1.2 동적 HITL 파서 (신규 컴포넌트)

**새 파일**: `backend/app/hitl/dynamic_parser.py`

```python
class DynamicHITLParser:
    """Parse agent output for dynamic HITL requests"""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        if not enabled:
            logger.info("[DynamicHITL] Disabled - parser will no-op")

    def parse(self, output: str, workflow_id: str, agent_id: str) -> Optional[HITLRequest]:
        """Parse HITL_REQUEST markers from agent output

        Returns:
            HITLRequest if found and enabled, None otherwise
        """
        if not self.enabled:
            return None

        # Parse markdown-style HITL_REQUEST block
        match = re.search(r'\*\*HITL_REQUEST:\*\*(.+?)(?=\n\n|\Z)', output, re.DOTALL)
        if not match:
            return None

        # Extract fields
        request_text = match.group(1)
        type_match = re.search(r'Type:\s*(\w+)', request_text)
        title_match = re.search(r'Title:\s*(.+)', request_text)
        question_match = re.search(r'Question:\s*(.+)', request_text)

        # Create HITLRequest
        return HITLRequest(
            workflow_id=workflow_id,
            stage_id=agent_id,
            agent_id=agent_id,
            checkpoint_type=HITLCheckpointType(type_match.group(1)),
            title=title_match.group(1).strip(),
            description=question_match.group(1).strip(),
            content=HITLContent(summary="Dynamic question from agent"),
            priority="high"
        )
```

#### 4.1.3 통합 지점 (Feature Flag 보호)

**수정 파일**: `backend/app/agent/unified_agent_manager.py`

```python
class UnifiedAgentManager:
    def __init__(self):
        # ... 기존 코드 ...

        # 새 컴포넌트 (feature flag로 제어)
        self.dynamic_hitl_parser = DynamicHITLParser(
            enabled=settings.enable_dynamic_hitl
        )

    async def _stream_response(self, ...):
        # ... 기존 코드 ...

        async for update in handler.execute_stream(...):
            # 기존 로직은 그대로
            yield update

            # 새 로직 (조건부만 실행)
            if settings.enable_dynamic_hitl and update.get("agent_output"):
                hitl_req = self.dynamic_hitl_parser.parse(
                    output=update["agent_output"],
                    workflow_id=session_id,
                    agent_id=update.get("agent", "unknown")
                )
                if hitl_req:
                    # HITL 요청 발견 → 워크플로우 일시 정지
                    yield {
                        "update_type": "hitl_request",
                        "data": {"hitl_request": hitl_req.model_dump()},
                        "status": "awaiting_approval"
                    }
                    # Wait for response...
```

### 4.2 User-Driven Pause/Resume (실시간 인터럽트)

**목표**: 사용자가 워크플로우 실행 중 언제든지 일시 정지

#### 4.2.1 새 API 엔드포인트

**수정 파일**: `backend/app/api/routes/langgraph_routes.py`

```python
@router.post("/workflow/pause/{workflow_id}")
async def pause_workflow(workflow_id: str):
    """User-initiated workflow pause

    IMPORTANT: Only works if ENABLE_PAUSE_BUTTON=true

    Returns:
        400 if feature disabled
        200 with pause confirmation if enabled
    """
    if not settings.enable_pause_button:
        raise HTTPException(
            status_code=400,
            detail="Pause feature is not enabled. Set ENABLE_PAUSE_BUTTON=true"
        )

    # Set workflow status to 'paused_by_user'
    # ... pause logic ...

    return {
        "success": True,
        "workflow_id": workflow_id,
        "status": "paused",
        "message": "Workflow paused. Send feedback to resume."
    }
```

#### 4.2.2 프론트엔드 Pause 버튼 (조건부 렌더)

**수정 파일**: `frontend/src/components/WorkflowStatusPanel.tsx`

```tsx
const WorkflowStatusPanel = ({ sessionId, status, onPause }) => {
  const [pauseEnabled, setPauseEnabled] = useState(false);

  useEffect(() => {
    // Check if pause feature is enabled
    apiClient.getConfig().then(config => {
      setPauseEnabled(config.enable_pause_button);
    });
  }, []);

  return (
    <div className="workflow-status-panel">
      {/* 기존 UI 그대로 */}

      {/* Pause 버튼 (조건부 표시) */}
      {pauseEnabled && status === 'running' && (
        <button onClick={onPause} className="pause-button">
          ⏸️ Pause
        </button>
      )}
    </div>
  );
};
```

### 4.3 통합 채팅 + HITL UI (선택적 사용)

**목표**: 별도 모달 대신 채팅창에 HITL 요청 표시

#### 4.3.1 새 메시지 타입

**수정 파일**: `frontend/src/types/api.ts`

```typescript
interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;

  // 새 필드 (optional, 기존 코드 영향 없음)
  type?: 'text' | 'hitl_request';
  hitl_request?: HITLRequest;
  timestamp: number;
}
```

#### 4.3.2 InlineHITLRequest 컴포넌트 (신규)

**새 파일**: `frontend/src/components/InlineHITLRequest.tsx`

```tsx
interface InlineHITLRequestProps {
  request: HITLRequest;
  onRespond: (response: HITLResponse) => void;
}

const InlineHITLRequest = ({ request, onRespond }: InlineHITLRequestProps) => {
  const [answer, setAnswer] = useState('');

  return (
    <div className="inline-hitl-request bg-blue-900/20 border border-blue-600 rounded-lg p-4 my-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-blue-400">❓</span>
        <strong className="text-blue-300">{request.title}</strong>
      </div>

      <p className="text-gray-300 mb-3">{request.description}</p>

      {/* Question type */}
      {request.checkpoint_type === 'question' && (
        <div>
          <input
            type="text"
            value={answer}
            onChange={e => setAnswer(e.target.value)}
            placeholder="Type your answer..."
            className="w-full px-3 py-2 bg-gray-800 rounded"
          />
          <button
            onClick={() => onRespond({
              request_id: request.request_id,
              action: HITLAction.APPROVE,
              feedback: answer
            })}
            className="mt-2 px-4 py-2 bg-blue-600 rounded"
          >
            Submit
          </button>
        </div>
      )}

      {/* Choice type */}
      {request.checkpoint_type === 'choice' && (
        <div className="space-y-2">
          {request.content.options?.map(opt => (
            <button
              key={opt.option_id}
              onClick={() => onRespond({
                request_id: request.request_id,
                action: HITLAction.SELECT,
                selected_option: opt.option_id
              })}
              className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded"
            >
              {opt.title}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
```

#### 4.3.3 WorkflowInterface 통합 (조건부)

**수정 파일**: `frontend/src/components/WorkflowInterface.tsx`

```tsx
const WorkflowInterface = ({ ... }) => {
  const [inlineHitlEnabled, setInlineHitlEnabled] = useState(false);

  useEffect(() => {
    apiClient.getConfig().then(config => {
      setInlineHitlEnabled(config.enable_inline_hitl_ui);
    });
  }, []);

  // ... 기존 코드 ...

  return (
    <div>
      {conversationHistory.map(turn => (
        <div key={turn.timestamp}>
          {/* 기존 메시지 렌더링 */}
          <div>{turn.content}</div>

          {/* HITL 요청 (조건부 렌더) */}
          {inlineHitlEnabled && turn.type === 'hitl_request' && turn.hitl_request && (
            <InlineHITLRequest
              request={turn.hitl_request}
              onRespond={handleHitlResponse}
            />
          )}

          {/* 기존 Modal도 유지 (폴백) */}
          {!inlineHitlEnabled && turn.hitl_request && (
            <HITLModal {...turn.hitl_request} />
          )}
        </div>
      ))}
    </div>
  );
};
```

---

## 5. 구현 계획 (단계별, 기존 시스템 보호)

### Phase 0: 사전 작업 (안전장치 설치)

**목표**: 기존 시스템 보호 장치 마련

**작업 항목**:
1. ✅ Feature flags 추가 (`.env.example`)
   ```env
   # Dynamic HITL Features (Experimental)
   ENABLE_DYNAMIC_HITL=false
   ENABLE_PAUSE_BUTTON=false
   ENABLE_INLINE_HITL_UI=false
   ```

2. ✅ Config 클래스에 feature flags 추가
   ```python
   # backend/app/core/config.py
   class Settings(BaseSettings):
       # ... 기존 설정 ...

       # HITL Enhancement Flags (v2.0)
       enable_dynamic_hitl: bool = False
       enable_pause_button: bool = False
       enable_inline_hitl_ui: bool = False
   ```

3. ✅ Frontend config API 추가
   ```python
   # backend/app/api/routes/config_routes.py (NEW)
   @router.get("/config/features")
   async def get_feature_flags():
       return {
           "enable_dynamic_hitl": settings.enable_dynamic_hitl,
           "enable_pause_button": settings.enable_pause_button,
           "enable_inline_hitl_ui": settings.enable_inline_hitl_ui
       }
   ```

4. ✅ 기존 시스템 회귀 테스트 작성
   ```python
   # tests/test_hitl_compatibility.py (NEW)
   def test_hitl_backward_compatibility():
       """기존 HITL 시스템이 변경 없이 동작하는지 확인"""
       # ... test cases ...
   ```

**예상 기간**: 1일

**핵심 파일**:
- `.env.example` (신규 flag 추가)
- `backend/app/core/config.py` (Settings 확장)
- `backend/app/api/routes/config_routes.py` (신규)
- `tests/test_hitl_compatibility.py` (신규)

### Phase 1: AI-Driven HITL (Opt-in 테스트)

**목표**: Agent가 스스로 HITL 요청 생성 (기본값: 비활성화)

**작업 항목**:
1. ✅ DynamicHITLParser 구현
   - `backend/app/hitl/dynamic_parser.py` (신규)
   - enabled 파라미터로 no-op 가능

2. ✅ Agent 프롬프트 가이드라인 추가
   - `backend/app/agent/prompts/hitl_guidelines.py` (신규)
   - 기존 프롬프트는 변경 없음

3. ✅ UnifiedAgentManager 통합 (조건부)
   - `_stream_response()`에 조건부 파싱 추가
   - `if settings.enable_dynamic_hitl:` 분기

4. ✅ 새 체크포인트 타입 `dynamic_question` 추가
   - `backend/app/hitl/models.py` (enum 확장)

5. ✅ 테스트 케이스 작성
   ```python
   def test_dynamic_hitl_disabled_by_default():
       """기본 설정에서 dynamic HITL 동작하지 않음 확인"""
       assert settings.enable_dynamic_hitl == False

   def test_dynamic_hitl_parsing_when_enabled():
       """활성화 시에만 HITL 요청 파싱됨 확인"""
       parser = DynamicHITLParser(enabled=True)
       output = "**HITL_REQUEST:** ..."
       req = parser.parse(output, "wf-1", "agent-1")
       assert req is not None
   ```

**예상 기간**: 2일

**테스트 시나리오**:
```bash
# 1. 기본 설정 (비활성화)
$ # ENABLE_DYNAMIC_HITL=false (기본값)
$ # 워크플로우 실행 → 기존과 동일하게 동작, HITL 요청 생성 안됨

# 2. 활성화 테스트
$ # .env에 ENABLE_DYNAMIC_HITL=true 설정
$ # 워크플로우 실행 → Agent가 "HITL_REQUEST:" 출력 시 파싱됨
```

### Phase 2: User-Driven Pause/Resume (Opt-in 테스트)

**목표**: 사용자가 Pause 버튼으로 워크플로우 중단 (기본값: 비활성화)

**작업 항목**:
1. ✅ `/workflow/pause` API 엔드포인트 추가
   - `backend/app/api/routes/langgraph_routes.py`
   - Feature flag 체크 후 동작

2. ✅ Workflow 상태 관리 확장
   - `paused_by_user` 상태 추가
   - LangGraph checkpointing 활용

3. ✅ 프론트엔드 Pause 버튼 추가 (조건부)
   - `frontend/src/components/WorkflowStatusPanel.tsx`
   - `pauseEnabled` 상태로 조건부 렌더

4. ✅ Resume 로직 구현
   - 사용자 피드백 받은 후 정확히 이어서 실행

5. ✅ 테스트 케이스 작성
   ```python
   def test_pause_disabled_by_default():
       response = client.post("/workflow/pause/wf-1")
       assert response.status_code == 400  # Feature disabled

   def test_pause_when_enabled():
       settings.enable_pause_button = True
       response = client.post("/workflow/pause/wf-1")
       assert response.status_code == 200
   ```

**예상 기간**: 2일

**테스트 시나리오**:
```bash
# 1. 기본 설정 (버튼 없음)
$ # ENABLE_PAUSE_BUTTON=false (기본값)
$ # UI에 Pause 버튼 표시 안됨

# 2. 활성화 테스트
$ # .env에 ENABLE_PAUSE_BUTTON=true 설정
$ # Pause 버튼 표시 → 클릭 시 워크플로우 일시 정지
```

### Phase 3: 통합 채팅 + HITL UI (Opt-in 테스트)

**목표**: 채팅창에서 HITL 요청 표시 (기본값: 모달 사용)

**작업 항목**:
1. ✅ 새 메시지 타입 정의
   - `frontend/src/types/api.ts` (optional 필드 추가)

2. ✅ InlineHITLRequest 컴포넌트 구현
   - `frontend/src/components/InlineHITLRequest.tsx` (신규)

3. ✅ WorkflowInterface 통합 (조건부 렌더)
   - `inlineHitlEnabled` 상태로 분기
   - 기존 HITLModal도 유지 (폴백)

4. ✅ HITL 응답 처리 로직
   - 채팅 입력창으로 제출

5. ✅ 테스트 케이스 작성
   ```tsx
   test('renders HITLModal by default', () => {
     const { getByTestId } = render(<WorkflowInterface />);
     // inlineHitlEnabled=false → 모달 사용
     expect(getByTestId('hitl-modal')).toBeInTheDocument();
   });

   test('renders InlineHITLRequest when enabled', () => {
     mockConfig({ enable_inline_hitl_ui: true });
     const { getByTestId } = render(<WorkflowInterface />);
     expect(getByTestId('inline-hitl')).toBeInTheDocument();
   });
   ```

**예상 기간**: 3일

**테스트 시나리오**:
```bash
# 1. 기본 설정 (모달 사용)
$ # ENABLE_INLINE_HITL_UI=false (기본값)
$ # HITL 요청 → 별도 모달 팝업 (기존 방식)

# 2. 활성화 테스트
$ # .env에 ENABLE_INLINE_HITL_UI=true 설정
$ # HITL 요청 → 채팅창에 inline으로 표시
```

### Phase 4: 통합 테스트 및 문서화

**목표**: 모든 Phase 검증 및 사용자 가이드 작성

**작업 항목**:
1. ✅ 전체 통합 테스트
   ```python
   def test_all_features_enabled():
       """모든 HITL 기능 동시 활성화 테스트"""
       settings.enable_dynamic_hitl = True
       settings.enable_pause_button = True
       settings.enable_inline_hitl_ui = True
       # ... end-to-end test ...
   ```

2. ✅ 회귀 테스트 (기존 시스템)
   ```python
   def test_all_features_disabled():
       """모든 flag 비활성화 시 기존 동작 유지"""
       assert settings.enable_dynamic_hitl == False
       # ... 기존 워크플로우 테스트 ...
   ```

3. ✅ 사용자 가이드 작성
   - `docs/HITL_USER_GUIDE.md` (신규)
   - 각 기능 활성화 방법
   - 사용 예시

4. ✅ Requirement.md 업데이트
   - 작업 내역 추가

**예상 기간**: 2일

---

## 6. 기술적 고려사항 (DeepSeek-R1 특화)

### 6.1 DeepSeek-R1 `<think>` 태그 처리

**현재 상태**: 이미 모든 파싱 함수에서 `<think>` 제거됨 ✅

**HITL 파서에도 적용**:
```python
class DynamicHITLParser:
    def parse(self, output: str, ...):
        # Remove <think> tags first
        clean_output = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL)
        clean_output = re.sub(r'</?think>', '', clean_output)

        # Then parse HITL_REQUEST
        match = re.search(r'\*\*HITL_REQUEST:\*\*', clean_output)
        # ...
```

### 6.2 RTX 3090 + Ollama 환경 고려

**현재 설정**:
- `MAX_PARALLEL_AGENTS=2` (Ollama 순차 처리)
- DeepSeek-R1:14B 단일 모델

**HITL 영향**:
- HITL 대기 중에는 LLM 호출 없음 → 병목 없음
- 사용자 응답 후 즉시 재개 가능

### 6.3 크로스 플랫폼 호환성

**이미 구현됨**:
- Windows/Linux/MacOS 경로 처리 ✅
- `getDefaultWorkspace()` ✅

**HITL에서 추가 고려**:
- Pause 상태 저장 경로 (workspace 기준)
- 로그 파일 경로 (크로스 플랫폼)

---

## 7. 사용자 시나리오 (기능별)

### 시나리오 1: AI-Driven HITL (옵션 활성화 시)

```
# .env에 설정
ENABLE_DYNAMIC_HITL=true

User: "Create a REST API for user management"

Supervisor (reasoning):
  <think>
  User wants REST API.
  Need to know project name for directory structure.
  </think>

  **HITL_REQUEST:**
  - Type: question
  - Title: Project Name
  - Question: What should I name this project?
  - Context: This will create a folder like `user-api/`

[워크플로우 자동 일시 정지]

[채팅창 또는 모달에 질문 표시]

User (응답): "user-management-api"

Supervisor: "Creating project 'user-management-api'..."

[워크플로우 재개]
```

### 시나리오 2: User-Driven Pause (옵션 활성화 시)

```
# .env에 설정
ENABLE_PAUSE_BUTTON=true

User: "Implement authentication with JWT"

[워크플로우 시작: Supervisor → Architect → Coder]

[사용자가 Architect의 설계 내용을 보고 Pause 버튼 클릭]

System: "Workflow paused. What would you like to adjust?"

User (채팅): "Use refresh tokens with Redis"

Architect: "Revising architecture..."

[워크플로우 재개]
```

### 시나리오 3: 기본 설정 (모든 flag 비활성화)

```
# .env 기본값
ENABLE_DYNAMIC_HITL=false
ENABLE_PAUSE_BUTTON=false
ENABLE_INLINE_HITL_UI=false

User: "Create a calculator in Python"

[기존 워크플로우 그대로 실행]
- Supervisor 분석
- Planning 생성
- Coding 실행
- Review 완료

[HITL 없이 자동 완료 - 기존 동작 유지]
```

---

## 8. 테스트 전략 (필수)

### 8.1 단위 테스트

```python
# tests/test_dynamic_hitl_parser.py
def test_parser_disabled():
    parser = DynamicHITLParser(enabled=False)
    assert parser.parse("**HITL_REQUEST:**...") is None

def test_parser_enabled():
    parser = DynamicHITLParser(enabled=True)
    req = parser.parse("**HITL_REQUEST:**\n- Type: question\n...")
    assert req.checkpoint_type == HITLCheckpointType.QUESTION

# tests/test_pause_api.py
def test_pause_disabled():
    response = client.post("/workflow/pause/wf-1")
    assert response.status_code == 400

def test_pause_enabled():
    settings.enable_pause_button = True
    response = client.post("/workflow/pause/wf-1")
    assert response.status_code == 200
```

### 8.2 통합 테스트

```python
# tests/test_hitl_integration.py
def test_end_to_end_dynamic_hitl():
    """AI가 질문 → 사용자 응답 → 워크플로우 재개"""
    settings.enable_dynamic_hitl = True

    # 1. 워크플로우 시작
    response = client.post("/chat/unified/stream", json={...})

    # 2. HITL 요청 수신 확인
    assert "hitl_request" in response.text

    # 3. 사용자 응답 제출
    hitl_response = client.post("/hitl/respond/req-123", json={...})

    # 4. 워크플로우 재개 확인
    assert hitl_response.json()["success"] == True
```

### 8.3 회귀 테스트 (기존 시스템)

```python
# tests/test_hitl_backward_compat.py
def test_existing_workflow_unchanged():
    """모든 flag 비활성화 시 기존 동작 유지"""
    # 모든 feature flag를 false로 설정
    settings.enable_dynamic_hitl = False
    settings.enable_pause_button = False
    settings.enable_inline_hitl_ui = False

    # 기존 워크플로우 실행
    response = client.post("/chat/unified", json={
        "message": "Create a calculator",
        "session_id": "test-123"
    })

    # 기존과 동일한 응답 구조 확인
    assert response.status_code == 200
    assert "response_type" in response.json()
    assert "content" in response.json()
```

### 8.4 Frontend 테스트

```tsx
// frontend/src/components/__tests__/InlineHITL.test.tsx
describe('InlineHITLRequest', () => {
  test('renders only when enabled', () => {
    const { queryByTestId } = render(
      <WorkflowInterface config={{ enable_inline_hitl_ui: false }} />
    );
    expect(queryByTestId('inline-hitl')).toBeNull();
  });

  test('renders when enabled', () => {
    const { getByTestId } = render(
      <WorkflowInterface config={{ enable_inline_hitl_ui: true }} />
    );
    expect(getByTestId('inline-hitl')).toBeInTheDocument();
  });
});
```

---

## 9. 위험 요소 및 완화 전략

### 위험 1: LLM이 HITL 형식을 정확히 따르지 않음

**완화 전략**:
- 프롬프트에 명확한 예시 포함
- Few-shot learning 적용 (DeepSeek-R1 compatible)
- 파싱 실패 시 graceful fallback (기존 동작 유지)
- `enabled=False` 기본값으로 안전장치

### 위험 2: Feature flag 설정 실수로 예상치 못한 동작

**완화 전략**:
- 기본값은 모두 `false` (opt-in)
- `.env.example`에 명확한 주석
- Config API로 현재 설정 확인 가능
- 로그에 활성화된 기능 명시

### 위험 3: Pause 기능이 워크플로우 상태를 손상

**완화 전략**:
- LangGraph checkpointing 활용 (이미 구현됨)
- 상태 저장/복원 테스트 필수
- Graceful pause (현재 노드 완료 후)
- Resume 실패 시 에러 메시지 명확히

### 위험 4: 채팅 UI가 복잡한 HITL 요청에 부적합

**완화 전략**:
- 복잡한 요청 (코드 리뷰, 다중 선택)은 여전히 모달 사용
- `enable_inline_hitl_ui=false` 설정으로 모달 강제 사용 가능
- 사용자 선호도 설정 제공

---

## 10. 성공 지표

### 정량적 지표

1. **회귀 없음**: 모든 기존 테스트 통과율 100%
2. **동적 HITL 사용률**: 복잡한 요청의 20% 이상에서 AI가 자동으로 질문 생성
3. **Pause 사용률**: 활성화한 사용자의 15% 이상이 Pause 버튼 사용
4. **UI 선호도**: 채팅 기반 HITL vs 모달 사용 비율 측정

### 정성적 지표

1. **기존 사용자 불편 없음**: 기본 설정에서 기존과 동일한 경험
2. **점진적 도입 가능**: 각 기능을 독립적으로 활성화 가능
3. **문서 명확성**: 사용자가 각 기능을 이해하고 설정 가능

---

## 11. 다음 단계

### 즉시 (Phase 0)
1. ✅ Feature flags 추가 (`.env`, `config.py`)
2. ✅ Config API 엔드포인트 추가
3. ✅ 회귀 테스트 작성

### 1주차 (Phase 1)
1. ✅ DynamicHITLParser 구현
2. ✅ 프롬프트 가이드라인 추가
3. ✅ 단위 테스트 작성
4. ✅ Opt-in 테스트

### 2주차 (Phase 2)
1. ✅ Pause API 구현
2. ✅ 프론트엔드 버튼 추가
3. ✅ 통합 테스트

### 3주차 (Phase 3)
1. ✅ InlineHITLRequest 컴포넌트
2. ✅ WorkflowInterface 통합
3. ✅ UI 테스트

### 4주차 (Phase 4)
1. ✅ 전체 통합 테스트
2. ✅ 사용자 가이드 작성
3. ✅ Requirement.md 업데이트

---

## 12. 결론

### 핵심 차별점 (v2.0)

1. **기존 시스템 완전 보호**
   - Feature flag로 새 기능 opt-in
   - 기본 동작 변경 없음
   - 회귀 테스트 보장

2. **점진적 도입 가능**
   - 각 기능을 독립적으로 테스트
   - 단계별 rollout
   - 언제든지 rollback 가능

3. **현재 환경 최적화**
   - DeepSeek-R1 `<think>` 태그 처리
   - RTX 3090 + Ollama 환경 고려
   - 크로스 플랫폼 호환성 유지

4. **테스트 중심 개발**
   - 단위/통합/회귀 테스트 필수
   - 모든 Phase마다 테스트
   - 기존 기능 보호 검증

### 최종 목표

> **"기존 시스템에 영향 없이, 진정한 HITL 워크플로우를 옵션으로 제공"**

사용자는:
- 기본 설정에서 기존과 동일한 경험
- 원하는 기능만 선택적으로 활성화
- 언제든지 이전 동작으로 복귀 가능

---

## 부록 A: 파일 체크리스트

### Phase 0 (사전 작업)

| 파일 | 변경 유형 | 내용 |
|-----|---------|------|
| `.env.example` | 수정 | Feature flags 추가 |
| `backend/app/core/config.py` | 수정 | Settings 확장 |
| `backend/app/api/routes/config_routes.py` | 신규 | Config API |
| `tests/test_hitl_compatibility.py` | 신규 | 회귀 테스트 |

### Phase 1 (AI-Driven HITL)

| 파일 | 변경 유형 | 내용 |
|-----|---------|------|
| `backend/app/hitl/dynamic_parser.py` | 신규 | HITL 파서 |
| `backend/app/agent/prompts/hitl_guidelines.py` | 신규 | 프롬프트 가이드라인 |
| `backend/app/agent/unified_agent_manager.py` | 수정 | 조건부 파싱 추가 |
| `backend/app/hitl/models.py` | 수정 | 체크포인트 타입 확장 |
| `tests/test_dynamic_hitl_parser.py` | 신규 | 단위 테스트 |

### Phase 2 (User-Driven Pause)

| 파일 | 변경 유형 | 내용 |
|-----|---------|------|
| `backend/app/api/routes/langgraph_routes.py` | 수정 | Pause API |
| `backend/app/agent/langgraph/enhanced_workflow.py` | 수정 | 상태 관리 |
| `frontend/src/components/WorkflowStatusPanel.tsx` | 수정 | Pause 버튼 |
| `tests/test_pause_api.py` | 신규 | API 테스트 |

### Phase 3 (통합 채팅 UI)

| 파일 | 변경 유형 | 내용 |
|-----|---------|------|
| `frontend/src/types/api.ts` | 수정 | 타입 정의 |
| `frontend/src/components/InlineHITLRequest.tsx` | 신규 | Inline 컴포넌트 |
| `frontend/src/components/WorkflowInterface.tsx` | 수정 | 조건부 렌더 |
| `tests/InlineHITL.test.tsx` | 신규 | UI 테스트 |

---

**문서 버전**: 2.0
**최종 검토일**: 2026-01-07
**승인 대기 중**: 사용자 확인 후 Phase 0 시작
