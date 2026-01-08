# Agentic Coder CLI Implementation - Detailed Todos

**기준일**: 2026-01-08
**연관 문서**: `CLI_MIGRATION_PLAN.md`

---

## 📋 Phase 1: CLI 기본 구조 (예상 1-2일)

### Todo 1.1: 프로젝트 구조 생성

- [ ] **T1.1.1** `backend/cli/` 디렉토리 생성
  ```bash
  mkdir -p backend/cli
  touch backend/cli/__init__.py
  ```

- [ ] **T1.1.2** `backend/cli/__main__.py` 생성
  - CLI entry point
  - argparse 기반 명령어 파싱
  - 기본 옵션: --workspace, --session-id, --model, --help, --version

- [ ] **T1.1.3** `bin/agentic-coder` 실행 스크립트 생성
  ```bash
  mkdir -p bin
  ```
  ```python
  #!/usr/bin/env python3
  import sys
  from backend.cli.__main__ import main
  sys.exit(main())
  ```

- [ ] **T1.1.4** `setup.py` 또는 `pyproject.toml` 작성
  - Entry point: `agentic-coder = backend.cli.__main__:main`
  - Dependencies: rich, click, prompt-toolkit
  - Version: 1.0.0

### Todo 1.2: Session Manager 구현

- [ ] **T1.2.1** `backend/cli/session_manager.py` 생성
  - `SessionManager` 클래스
  - 세션 ID 생성 (`session-{timestamp}`)
  - 워크스페이스 경로 관리
  - 대화 히스토리 관리 (리스트)

- [ ] **T1.2.2** Session persistence
  - `.agentic-coder/sessions/` 디렉토리 사용
  - JSON 형식으로 대화 히스토리 저장
  - 세션 복원 기능

- [ ] **T1.2.3** DynamicWorkflowManager 연동
  - `from app.agent.langgraph.dynamic_workflow import DynamicWorkflowManager`
  - `execute_streaming_workflow()` 호출
  - conversation_history 전달

### Todo 1.3: 기본 Terminal UI

- [ ] **T1.3.1** `backend/cli/terminal_ui.py` 생성
  - `TerminalUI` 클래스
  - Rich Console 초기화
  - 기본 REPL 루프

- [ ] **T1.3.2** 사용자 입력 처리
  - `Prompt.ask()` 사용
  - KeyboardInterrupt 처리 (Ctrl+C)
  - EOFError 처리 (Ctrl+D)

- [ ] **T1.3.3** 기본 출력
  - 환영 메시지 (`Panel`)
  - 사용자 입력/AI 응답 표시
  - 에러 메시지 표시

### Todo 1.4: 기본 동작 테스트

- [ ] **T1.4.1** 로컬 개발 모드 테스트
  ```bash
  cd backend
  python -m cli
  ```

- [ ] **T1.4.2** 간단한 요청 테스트
  ```
  You: Hello
  AI: (Supervisor 응답)
  ```

- [ ] **T1.4.3** 세션 저장/복원 테스트
  ```bash
  python -m cli --session-id test-123
  ```

---

## 📋 Phase 2: 스트리밍 UI 구현 (예상 2-3일)

### Todo 2.1: Progress Bar 구현

- [ ] **T2.1.1** Rich Progress 통합
  ```python
  from rich.progress import Progress, SpinnerColumn, TextColumn
  ```

- [ ] **T2.1.2** Agent별 진행 상황 표시
  - Supervisor: "요청 분석 중..."
  - Planning: "계획 수립 중... (N chars)"
  - Coder: "코드 생성 중..."
  - Reviewer: "코드 리뷰 중..."

- [ ] **T2.1.3** 다중 agent 동시 표시 (선택)
  - 병렬 agent 실행 시 각각 표시
  - Task ID 관리

### Todo 2.2: Streaming Content 표시

- [ ] **T2.2.1** Markdown 렌더링
  ```python
  from rich.markdown import Markdown
  console.print(Markdown(streaming_content))
  ```

- [ ] **T2.2.2** Code syntax highlighting
  - `rich.syntax.Syntax` 사용
  - 언어 자동 감지

- [ ] **T2.2.3** 실시간 업데이트
  - `Live` 컨텍스트 사용
  - 스트림 데이터 실시간 렌더링

### Todo 2.3: Artifact 결과 표시

- [ ] **T2.3.1** 파일 목록 표시
  - Tree 구조 (선택)
  - 플랫 리스트 (기본)

- [ ] **T2.3.2** 액션별 색상 코딩
  - Created: `[green]CREATED[/green]`
  - Modified: `[yellow]MODIFIED[/yellow]`
  - Deleted: `[red]DELETED[/red]`

- [ ] **T2.3.3** 파일 크기 및 라인 수 표시 (선택)

### Todo 2.4: 통합 테스트

- [ ] **T2.4.1** 실제 워크플로우 실행
  ```
  You: Create a Python calculator
  ```

- [ ] **T2.4.2** 스트리밍 출력 확인
  - Agent 진행 상황 표시
  - 중간 결과 표시
  - 최종 artifact 표시

- [ ] **T2.4.3** 에러 처리 테스트
  - 네트워크 에러
  - LLM timeout
  - 파일 쓰기 실패

---

## 📋 Phase 3: 고급 기능 (예상 3-4일)

### Todo 3.1: Slash Commands

- [ ] **T3.1.1** Command parser 구현
  ```python
  def handle_command(self, command: str):
      cmd_parts = command[1:].split()
      cmd_name = cmd_parts[0]
  ```

- [ ] **T3.1.2** `/help` 구현
  - 사용 가능한 명령어 목록
  - 사용 예시
  - Markdown 형식

- [ ] **T3.1.3** `/status` 구현
  - 현재 세션 ID
  - 워크스페이스 경로
  - 대화 개수
  - 생성된 파일 개수

- [ ] **T3.1.4** `/clear` 구현
  - `console.clear()` 호출

- [ ] **T3.1.5** `/history` 구현
  - 대화 히스토리 표시
  - 페이지네이션 (선택)

- [ ] **T3.1.6** `/context` 구현
  - 현재 컨텍스트 정보
  - 추출된 파일명, 에러, 결정사항
  - ContextManager 활용

- [ ] **T3.1.7** `/files` 구현
  - 생성된 파일 목록
  - 파일 크기, 라인 수

- [ ] **T3.1.8** `/exit` 또는 `/quit` 구현
  - 세션 저장
  - 종료 확인

### Todo 3.2: 설정 시스템

- [ ] **T3.2.1** `.agentic-coder/settings.json` 지원
  ```json
  {
    "model": "deepseek-r1:14b",
    "default_workspace": ".",
    "auto_save_session": true,
    "display_thinking": false
  }
  ```

- [ ] **T3.2.2** 설정 로드 및 병합
  - 프로젝트 설정 > 글로벌 설정 > 기본값

- [ ] **T3.2.3** 모델 설정
  - Qwen, DeepSeek, GPT-OSS 선택
  - 엔드포인트 설정

### Todo 3.3: 세션 관리

- [ ] **T3.3.1** 자동 저장
  - 각 대화 후 세션 저장
  - `.agentic-coder/sessions/{session-id}.json`

- [ ] **T3.3.2** 세션 복원
  - `--session-id` 옵션으로 복원
  - 대화 히스토리 불러오기

- [ ] **T3.3.3** 세션 목록 보기 (선택)
  - `/sessions` 명령어
  - 최근 세션 목록

### Todo 3.4: 파일 미리보기

- [ ] **T3.4.1** 생성된 파일 내용 표시
  - `/preview <filename>` 명령어
  - Syntax highlighting

- [ ] **T3.4.2** Diff 표시 (수정된 파일)
  - 변경 전/후 비교
  - `difflib` 사용

- [ ] **T3.4.3** 파일 트리 뷰 (선택)
  - Rich Tree 사용
  - 폴더 구조 표시

---

## 📋 Phase 4: 패키징 및 배포 (예상 1-2일)

### Todo 4.1: 패키지 설정

- [ ] **T4.1.1** `setup.py` 완성
  ```python
  setup(
      name="agentic-coder",
      version="1.0.0",
      packages=find_packages(),
      entry_points={
          "console_scripts": [
              "agentic-coder=backend.cli.__main__:main"
          ]
      },
      install_requires=[
          "rich>=13.0.0",
          "click>=8.0.0",
          ...
      ]
  )
  ```

- [ ] **T4.1.2** `pyproject.toml` (선택, 대안)
  - Poetry 또는 Flit 사용
  - 의존성 관리

- [ ] **T4.1.3** `MANIFEST.in`
  - 포함할 파일 지정
  - 프롬프트, 설정 파일 등

### Todo 4.2: 설치 스크립트

- [ ] **T4.2.1** `install.sh` (Linux/MacOS)
  ```bash
  #!/bin/bash
  pip install agentic-coder
  ```

- [ ] **T4.2.2** `install.ps1` (Windows)
  ```powershell
  pip install agentic-coder
  ```

- [ ] **T4.2.3** Docker 이미지 (선택)
  ```dockerfile
  FROM python:3.11-slim
  RUN pip install agentic-coder
  ENTRYPOINT ["agentic-coder"]
  ```

### Todo 4.3: 문서 작성

- [ ] **T4.3.1** `README_CLI.md` 작성
  - CLI 사용법
  - 설치 방법
  - 예제

- [ ] **T4.3.2** `INSTALL.md` 작성
  - 상세 설치 가이드
  - 문제 해결 (Troubleshooting)

- [ ] **T4.3.3** `CLI_GUIDE.md` 작성
  - 모든 slash command 설명
  - 고급 사용법
  - 팁 & 트릭

- [ ] **T4.3.4** 기존 `README.md` 업데이트
  - CLI 버전 추가
  - 웹 버전과 CLI 버전 비교

### Todo 4.4: 테스트

- [ ] **T4.4.1** Clean 환경 설치 테스트
  ```bash
  python -m venv test_env
  source test_env/bin/activate
  pip install .
  agentic-coder --version
  ```

- [ ] **T4.4.2** Cross-platform 테스트
  - Linux
  - MacOS (가능하다면)
  - Windows (가능하다면)

- [ ] **T4.4.3** CI/CD 설정 (선택)
  - GitHub Actions
  - 자동 빌드 및 테스트

---

## 📋 Phase 5: 고급 기능 (선택, 예상 2-3일)

### Todo 5.1: Plugin 시스템 (claude-code 스타일)

- [ ] **T5.1.1** `.agentic-coder/plugins/` 지원
  - Plugin discovery
  - Plugin loading

- [ ] **T5.1.2** Custom slash command
  - Markdown 기반 정의
  - 동적 로딩

- [ ] **T5.1.3** Custom agent
  - Agent 정의 파일
  - 전문 에이전트 추가

### Todo 5.2: RAG 통합

- [ ] **T5.2.1** Vector DB 쿼리
  - `/ask <question>` 명령어
  - claude-code 레포지토리 검색

- [ ] **T5.2.2** 컨텍스트 보강
  - 관련 문서 자동 검색
  - ContextManager 통합

### Todo 5.3: TUI (Textual)

- [ ] **T5.3.1** Textual로 마이그레이션 (선택)
  - Full-screen TUI
  - 분할 창 (대화/파일 트리)
  - 마우스 지원

---

## 🔄 진행 상황 추적

### 진행률
- [ ] Phase 1: 0% (0/12 tasks)
- [ ] Phase 2: 0% (0/9 tasks)
- [ ] Phase 3: 0% (0/20 tasks)
- [ ] Phase 4: 0% (0/13 tasks)
- [ ] Phase 5: 0% (0/7 tasks)

### 총 진행률
**0/61 tasks** completed (0%)

---

## 🎯 우선순위

### High Priority (Phase 1-2)
- **P0**: CLI entry point, Session manager
- **P1**: Basic terminal UI, REPL
- **P2**: Streaming progress, Artifact display

### Medium Priority (Phase 3)
- **P3**: Slash commands (/help, /status, /history)
- **P4**: Settings system
- **P5**: Session persistence

### Low Priority (Phase 4-5)
- **P6**: Packaging, Documentation
- **P7**: Plugin system (선택)
- **P8**: RAG integration (선택)
- **P9**: Full TUI (선택)

---

## 📌 참고 사항

### 코드 재사용

기존 Agentic Coder backend 코드를 최대한 재사용:
- ✅ `app/agent/` - 모든 LangGraph agent
- ✅ `app/core/` - Supervisor, config
- ✅ `app/utils/` - ContextManager, RepositoryEmbedder
- 🆕 `cli/` - CLI 전용 코드만 추가

### 병행 운영

웹 버전(FastAPI + React)과 CLI 버전을 동시에 유지:
- 사용자 선택 가능
- 동일한 backend agent 시스템 공유
- 점진적 마이그레이션

---

**문서 버전**: v1.0.0
**최종 수정**: 2026-01-08
