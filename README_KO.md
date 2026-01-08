# TestCodeAgent - AI 코딩 어시스턴트

Claude Code, OpenAI Codex와 유사한 **통합 워크플로우 아키텍처**를 구현한 프로덕션 레디 AI 코딩 어시스턴트입니다.

[English Documentation](README.md)

---

## 개요

TestCodeAgent는 엔터프라이즈급 AI 기반 코딩 어시스턴트로 다음 기능을 제공합니다:

- **지능형 코드 생성** - 계획 및 리뷰를 포함한 다단계 코드 생성
- **멀티 모델 지원** - DeepSeek-R1, Qwen3-Coder, GPT-OSS 등
- **에이전트 도구** - 파일, Git, 코드, 웹, 샌드박스 작업을 위한 20개 전문 도구
- **네트워크 모드** - 폐쇄망 환경을 위한 온라인/오프라인 모드
- **샌드박스 실행** - Docker 기반 격리 코드 실행

---

## 아키텍처

```
사용자 요청
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    통합 채팅 엔드포인트                            │
│                    POST /chat/unified                            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedAgentManager                           │
│  - 세션 컨텍스트 관리                                              │
│  - Supervisor 분석 요청                                           │
│  - 응답 타입별 라우팅                                             │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SupervisorAgent                               │
│  - 요청 분석 (Reasoning LLM)                                     │
│  - 응답 타입 결정                                                 │
│  - 복잡도 평가                                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    ├─► QUICK_QA ─────────► 직접 LLM 응답
    ├─► PLANNING ─────────► PlanningHandler (계획 생성 + 파일 저장)
    ├─► CODE_GENERATION ──► CodeGenerationHandler (워크플로우 실행)
    ├─► CODE_REVIEW ──────► CodeReviewHandler
    └─► DEBUGGING ────────► DebuggingHandler
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ResponseAggregator                            │
│  - UnifiedResponse 생성                                          │
│  - 다음 행동 제안                                                 │
│  - 컨텍스트 DB 저장                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 주요 기능

### 핵심 기능

| 기능 | 설명 |
|------|------|
| **통합 워크플로우** | 지능형 라우팅이 포함된 단일 진입점 |
| **멀티 모델 지원** | DeepSeek-R1, Qwen3-Coder, GPT-OSS 자동 감지 |
| **컨텍스트 영속성** | 대화 및 작업 컨텍스트 DB 저장 |
| **실시간 스트리밍** | 코드 생성 과정 실시간 표시 |
| **한국어 지원** | 동사 어간 기반 네이티브 한국어 NLP |

### 에이전트 도구 (20개)

| 단계 | 도구 수 | 설명 |
|------|---------|------|
| **Phase 1** | 14개 | 파일, Git, 코드, 검색 작업 |
| **Phase 2** | 2개 | HTTP 요청, 파일 다운로드 (네트워크 모드) |
| **Phase 2.5** | 3개 | 코드 포맷팅, 셸 명령, Docstring 생성 |
| **Phase 4** | 1개 | 샌드박스 실행 (Docker 기반 격리) |

### 네트워크 모드 시스템

| 모드 | 설명 | EXTERNAL_API 도구 |
|------|------|-------------------|
| `online` | 모든 도구 사용 가능 | 활성화 |
| `offline` | 폐쇄망/보안 모드 | 차단 |

---

## 빠른 시작

### 사전 요구사항

1. **vLLM 서버** (앱 시작 전 실행 필요):
   ```bash
   # 터미널 1: 추론 모델
   vllm serve deepseek-ai/DeepSeek-R1 --port 8001

   # 터미널 2: 코딩 모델
   vllm serve Qwen/Qwen3-8B-Coder --port 8002
   ```

2. **Python 3.12+** 및 **Node.js 20+**

3. **Docker** (샌드박스 실행용)

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/TestCodeAgent.git
cd TestCodeAgent

# 2. 환경 설정
cp .env.example .env
# .env 파일을 원하는 설정으로 수정

# 3. 백엔드 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. 프론트엔드 설정
cd ../frontend
npm install

# 5. (선택) 격리 실행용 샌드박스 이미지 다운로드
docker pull ghcr.io/agent-infra/sandbox:latest
```

### 애플리케이션 실행

```bash
# 터미널 1: 백엔드
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 2: 프론트엔드
cd frontend
npm run dev
```

접속 주소: http://localhost:5173

### Mock 모드 (vLLM 없이 테스트)

```bash
./RUN_MOCK.sh  # Linux/Mac
RUN_MOCK.bat   # Windows
```

---

## 환경 설정

### 환경 변수

```bash
# LLM 설정
LLM_ENDPOINT=http://localhost:8001/v1
LLM_MODEL=deepseek-ai/DeepSeek-R1

# 작업별 모델
VLLM_REASONING_ENDPOINT=http://localhost:8001/v1
VLLM_CODING_ENDPOINT=http://localhost:8002/v1
REASONING_MODEL=deepseek-ai/DeepSeek-R1
CODING_MODEL=Qwen/Qwen3-8B-Coder

# 네트워크 모드 (online/offline)
NETWORK_MODE=online

# 샌드박스 설정
SANDBOX_IMAGE=ghcr.io/agent-infra/sandbox:latest
SANDBOX_HOST=localhost
SANDBOX_PORT=8080
SANDBOX_TIMEOUT=60
```

전체 설정 옵션은 [.env.example](.env.example)을 참조하세요.

---

## 에이전트 도구

### 도구 카테고리

| 카테고리 | 도구 | 네트워크 타입 |
|----------|------|---------------|
| **FILE** | read_file, write_file, search_files, list_directory | LOCAL |
| **GIT** | git_status, git_diff, git_log, git_branch, git_commit | LOCAL |
| **CODE** | execute_python, run_tests, lint_code, format_code, shell_command, generate_docstring, sandbox_execute | LOCAL |
| **SEARCH** | code_search, web_search | LOCAL / EXTERNAL_API |
| **WEB** | http_request, download_file | EXTERNAL_API / EXTERNAL_DOWNLOAD |

### 네트워크 모드별 도구 가용성

| 도구 | 온라인 | 오프라인 | 단계 |
|------|--------|----------|------|
| read_file | ✅ | ✅ | 1 |
| write_file | ✅ | ✅ | 1 |
| git_* (5개) | ✅ | ✅ | 1 |
| code_search | ✅ | ✅ | 1 |
| web_search | ✅ | ❌ | 1 |
| http_request | ✅ | ❌ | 2 |
| download_file | ✅ | ✅ | 2 |
| format_code | ✅ | ✅ | 2.5 |
| shell_command | ✅ | ✅ | 2.5 |
| generate_docstring | ✅ | ✅ | 2.5 |
| sandbox_execute | ✅ | ✅ | 4 |

### 샌드박스 실행

격리된 Docker 컨테이너에서 코드 실행:

```python
from app.tools.registry import ToolRegistry

registry = ToolRegistry()
sandbox = registry.get_tool("sandbox_execute")

# Python 실행
result = await sandbox.execute(
    code="print('Hello, World!')",
    language="python",
    timeout=60
)

# 셸 실행
result = await sandbox.execute(
    code="ls -la && cat /etc/os-release",
    language="shell"
)
```

**오프라인 설정:**
```bash
# 이미지 한 번 다운로드 (인터넷 필요)
docker pull ghcr.io/agent-infra/sandbox:latest

# 이미지가 로컬에 캐시됨 - 이후 오프라인에서도 동작
```

---

## API 엔드포인트

### 통합 채팅 (Non-streaming)

```
POST /chat/unified
```

```json
{
  "message": "Python으로 계산기 만들어줘",
  "session_id": "session-123",
  "workspace": "/home/user/workspace"
}
```

**응답:**
```json
{
  "response_type": "code_generation",
  "content": "## 코드 생성 완료\n\n...",
  "artifacts": [...],
  "next_actions": ["테스트 실행", "코드 리뷰 요청"],
  "session_id": "session-123",
  "success": true
}
```

### 통합 채팅 (Streaming)

```
POST /chat/unified/stream
```

---

## 프로젝트 구조

```
TestCodeAgent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 진입점
│   │   ├── agent/
│   │   │   ├── unified_agent_manager.py
│   │   │   └── handlers/              # 응답 타입 핸들러
│   │   ├── tools/                     # 에이전트 도구 (20개)
│   │   │   ├── base.py                # BaseTool, ToolResult
│   │   │   ├── registry.py            # ToolRegistry
│   │   │   ├── file_tools.py          # 파일 작업
│   │   │   ├── git_tools.py           # Git 작업
│   │   │   ├── code_tools.py          # 코드 작업
│   │   │   ├── code_tools_phase25.py  # Phase 2.5 도구
│   │   │   ├── search_tools.py        # 검색 도구
│   │   │   ├── web_tools.py           # HTTP/다운로드 도구
│   │   │   ├── sandbox_tools.py       # 샌드박스 실행
│   │   │   └── performance.py         # 연결 풀, 캐싱
│   │   └── api/
│   │       └── main_routes.py         # API 엔드포인트
│   ├── core/
│   │   ├── supervisor.py              # SupervisorAgent
│   │   ├── response_aggregator.py     # UnifiedResponse
│   │   └── context_store.py           # 컨텍스트 저장소
│   └── shared/
│       └── llm/
│           ├── base.py                # LLMProvider 인터페이스
│           └── adapters/              # 모델별 어댑터
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── WorkflowInterface.tsx  # 통합 모드 UI
│       │   ├── NextActionsPanel.tsx   # 액션 버튼
│       │   └── PlanFileViewer.tsx     # 계획 파일 뷰어
│       └── api/
│           └── client.ts              # API 클라이언트
├── docs/                              # 문서
├── .env.example                       # 설정 템플릿
└── README.md                          # 메인 문서 (영문)
```

---

## 테스트

### 전체 테스트 실행

```bash
cd backend
pytest app/tools/tests/ -v

# 결과: 262 passed, 6 skipped
```

### 테스트 모듈

| 모듈 | 테스트 수 | 설명 |
|------|-----------|------|
| test_network_mode.py | 44 | 네트워크 모드 시스템 |
| test_web_tools_phase2.py | 41 | HTTP 및 다운로드 도구 |
| test_code_tools_phase25.py | 53 | 코드 포맷팅, 셸, docstring |
| test_sandbox_tools.py | 38 | 샌드박스 실행 |
| test_performance.py | 24 | 연결 풀, 캐싱 |
| test_e2e.py | 21 | E2E 통합 테스트 |
| test_integration.py | 17 | 도구 통합 |

---

## 문서

| 문서 | 설명 |
|------|------|
| [AGENT_TOOLS_PHASE2_README.md](docs/AGENT_TOOLS_PHASE2_README.md) | 에이전트 도구 전체 문서 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 아키텍처 상세 |
| [MOCK_MODE.md](docs/MOCK_MODE.md) | Mock 모드 테스트 가이드 |
| [CLI_PHASE3_USER_GUIDE.md](docs/CLI_PHASE3_USER_GUIDE.md) | CLI 인터페이스 가이드 |

---

## 개발 이력

### Phase 4 (현재) - 샌드박스 실행
- **SandboxExecuteTool** - Docker 기반 격리 코드 실행
- **AIO Sandbox 통합** - 사전 빌드된 개발 환경 사용
- **다중 언어 지원** - Python, Node.js, TypeScript, Shell
- **오프라인 지원** - 로컬 캐시된 Docker 이미지로 동작

### Phase 3 - 성능 최적화
- **연결 풀링** - 공유 HTTP 연결
- **결과 캐싱** - TTL 기반 LRU 캐시
- **진행률 추적** - 실시간 다운로드 진행률

### Phase 2.5 - 코드 도구
- **FormatCodeTool** - Black/autopep8/yapf 포맷팅
- **ShellCommandTool** - 블록리스트 기반 안전한 셸 실행
- **DocstringGeneratorTool** - Docstring 자동 생성

### Phase 2 - 네트워크 모드
- **네트워크 모드 시스템** - 온라인/오프라인 제어
- **HttpRequestTool** - REST API 호출
- **DownloadFileTool** - 진행률 포함 파일 다운로드

### Phase 1 - 기반
- 14개 핵심 도구 (파일, Git, 코드, 검색)
- 도구 레지스트리 시스템
- 기본 도구 실행 프레임워크

---

## 지원 LLM 모델

| 모델 | 특징 | 프롬프트 형식 |
|------|------|---------------|
| DeepSeek-R1 | 추론 모델 | `<think></think>` 태그 |
| Qwen3-Coder | 코딩 특화 | 표준 프롬프트 |
| GPT-OSS | OpenAI Harmony | 구조화된 추론 |

---

## 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 기여하기

1. 저장소 Fork
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

---

**관리**: TestCodeAgent Team
**최종 업데이트**: 2026-01-08
