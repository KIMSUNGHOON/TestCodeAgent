# Agentic Coder CLI Migration Plan

**작성일**: 2026-01-08
**목적**: Agentic Coder를 FastAPI 웹앱에서 Interactive CLI 도구로 변환
**참고**: anthropics/claude-code architecture

---

## 📊 현재 상태 분석

### 현재 아키텍처 (FastAPI + React)

```
Agentic Coder/
├── backend/                     # FastAPI 서버
│   ├── app/
│   │   ├── api/                # REST API 엔드포인트
│   │   ├── agent/              # LangGraph 워크플로우
│   │   │   ├── langgraph/      # 동적 워크플로우, 노드
│   │   │   ├── handlers/       # 작업 핸들러
│   │   │   └── unified_agent_manager.py
│   │   ├── core/               # Supervisor, config
│   │   └── utils/              # ContextManager, 유틸리티
│   └── tests/
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── components/         # UI 컴포넌트
│   │   ├── api/                # API 클라이언트
│   │   └── types/              # TypeScript 타입
│   └── public/
└── shared/                      # 공유 프롬프트
    └── prompts/
```

**장점**:
- ✅ 완성된 LangGraph agent 시스템
- ✅ Phase 2 Context Management (압축, 필터링)
- ✅ 파일 생성/수정/삭제 기능
- ✅ 스트리밍 UI

**단점**:
- ❌ 웹 서버 실행 필요 (FastAPI + React dev server)
- ❌ 터미널에서 직접 사용 불가
- ❌ 프로젝트 디렉토리에서 바로 실행 어려움

---

## 🎯 목표 아키텍처 (Interactive CLI)

### Claude Code 스타일 CLI

```
agentic-coder                    # 글로벌 CLI 도구
├── bin/
│   └── agentic-coder           # 실행 파일 (entry point)
├── cli/
│   ├── __main__.py             # CLI 진입점
│   ├── terminal_ui.py          # Rich/Textual 기반 TUI
│   ├── session_manager.py      # 세션 관리
│   └── command_parser.py       # 명령어 파싱
├── agent/                       # 기존 agent 시스템 재사용
│   └── (기존 langgraph 코드)
├── core/                        # 기존 core 재사용
│   └── (기존 supervisor 코드)
└── utils/                       # 기존 utils 재사용
    ├── context_manager.py
    └── repository_embedder.py
```

**설치 및 사용**:
```bash
# 설치
pip install agentic-coder

# 사용
cd /path/to/my-project
agentic-coder

# 또는
agentic-coder "Create a FastAPI hello world app"
```

---

## 🏗️ 아키텍처 설계

### 1. CLI Entry Point

**파일**: `cli/__main__.py`

```python
#!/usr/bin/env python3
"""Agentic Coder CLI Entry Point"""

import sys
import argparse
from cli.terminal_ui import TerminalUI
from cli.session_manager import SessionManager

def main():
    parser = argparse.ArgumentParser(
        description="Agentic Coder - AI-powered coding assistant"
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Initial prompt (optional, starts interactive mode if not provided)"
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=".",
        help="Workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--session-id",
        "-s",
        help="Resume existing session"
    )
    parser.add_argument(
        "--model",
        "-m",
        default="deepseek-r1:14b",
        help="LLM model to use"
    )

    args = parser.parse_args()

    # Initialize session
    session_mgr = SessionManager(
        workspace=args.workspace,
        session_id=args.session_id
    )

    # Start terminal UI
    ui = TerminalUI(session_mgr, model=args.model)

    # One-shot mode or interactive mode
    if args.prompt:
        prompt_text = " ".join(args.prompt)
        ui.execute_one_shot(prompt_text)
    else:
        ui.start_interactive()

if __name__ == "__main__":
    main()
```

### 2. Terminal UI (Rich/Textual)

**라이브러리 선택**: `rich` (가볍고 빠름) 또는 `textual` (풀 TUI)

**파일**: `cli/terminal_ui.py`

```python
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

class TerminalUI:
    """Interactive terminal UI using Rich"""

    def __init__(self, session_manager, model: str):
        self.console = Console()
        self.session_mgr = session_manager
        self.model = model

    def start_interactive(self):
        """Start interactive REPL mode"""
        self.console.print(Panel(
            "[bold green]Agentic Coder Interactive Mode[/bold green]\n"
            "Type your request or /help for commands",
            title="🤖 Agentic Coder"
        ))

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

                if not user_input.strip():
                    continue

                # Handle special commands
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                    continue

                # Execute workflow
                self.execute_workflow(user_input)

            except KeyboardInterrupt:
                if Prompt.ask("\nExit? (y/n)", default="n") == "y":
                    break
            except EOFError:
                break

    def execute_workflow(self, prompt: str):
        """Execute agent workflow with streaming UI"""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("[cyan]Processing...", total=None)

            # Stream workflow execution
            for update in self.session_mgr.execute_stream(prompt):
                # Update progress bar
                agent = update.get("agent", "")
                message = update.get("message", "")
                progress.update(task, description=f"[cyan]{agent}: {message}")

                # Display streaming content
                if update.get("streaming_content"):
                    self.console.print(
                        Markdown(update["streaming_content"]),
                        style="dim"
                    )

                # Display final results
                if update.get("type") == "completed":
                    self.display_results(update)

    def display_results(self, result):
        """Display workflow results"""
        artifacts = result.get("artifacts", [])

        if artifacts:
            self.console.print(f"\n[bold green]✅ Created {len(artifacts)} files:[/bold green]")
            for artifact in artifacts:
                action_color = {
                    "created": "green",
                    "modified": "yellow",
                    "deleted": "red"
                }.get(artifact.get("action"), "white")

                self.console.print(
                    f"  [{action_color}]{artifact['action'].upper()}[/{action_color}] "
                    f"{artifact['filename']}"
                )

    def handle_command(self, command: str):
        """Handle slash commands"""
        cmd_parts = command[1:].split()
        cmd_name = cmd_parts[0] if cmd_parts else ""

        if cmd_name == "help":
            self.show_help()
        elif cmd_name == "status":
            self.show_status()
        elif cmd_name == "clear":
            self.console.clear()
        elif cmd_name == "exit":
            raise KeyboardInterrupt
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")

    def show_help(self):
        """Show help message"""
        help_text = """
## Available Commands

- `/help` - Show this help message
- `/status` - Show current session status
- `/clear` - Clear screen
- `/exit` - Exit Agentic Coder

## Usage Examples

```
You: Create a FastAPI hello world app
You: Add error handling to main.py
You: Review the code for bugs
```
        """
        self.console.print(Markdown(help_text))
```

### 3. Session Manager

**파일**: `cli/session_manager.py`

```python
import os
from pathlib import Path
from typing import Iterator, Dict, Any

from app.agent.langgraph.dynamic_workflow import DynamicWorkflowManager
from app.core.supervisor import Supervisor
from app.core.config import settings

class SessionManager:
    """Manages agent workflow sessions"""

    def __init__(self, workspace: str, session_id: str = None):
        self.workspace = Path(workspace).resolve()
        self.session_id = session_id or self._generate_session_id()
        self.conversation_history = []

        # Initialize workflow manager (기존 코드 재사용)
        self.workflow_mgr = DynamicWorkflowManager()
        self.supervisor = Supervisor()

    def execute_stream(self, user_request: str) -> Iterator[Dict[str, Any]]:
        """Execute workflow with streaming updates"""

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_request
        })

        # Execute workflow (기존 LangGraph 시스템 활용)
        async for update in self.workflow_mgr.execute_streaming_workflow(
            user_request=user_request,
            workspace_root=str(self.workspace),
            conversation_history=self.conversation_history
        ):
            yield update

        # Add response to history
        # (워크플로우 완료 후 응답 추가)

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import time
        return f"session-{int(time.time())}"
```

---

## 📋 구현 단계 (Phases)

### Phase 1: CLI 기본 구조 (1-2일)
**목표**: 최소 기능 CLI 도구 생성

#### Todo List
- [ ] 1.1. 프로젝트 구조 생성
  - [ ] `cli/` 디렉토리 생성
  - [ ] `bin/agentic-coder` 실행 스크립트 생성
  - [ ] `setup.py` 또는 `pyproject.toml` 작성

- [ ] 1.2. CLI Entry Point 구현
  - [ ] `cli/__main__.py` 작성
  - [ ] argparse 기반 명령어 파싱
  - [ ] 기본 --help, --version 구현

- [ ] 1.3. 기본 Terminal UI
  - [ ] `rich` 라이브러리 설치
  - [ ] 단순 REPL 모드 구현
  - [ ] 사용자 입력/출력 처리

- [ ] 1.4. Session Manager 기본 구현
  - [ ] 세션 ID 생성
  - [ ] 워크스페이스 경로 관리
  - [ ] 대화 히스토리 저장

- [ ] 1.5. 기존 Agent 시스템 연동
  - [ ] DynamicWorkflowManager import
  - [ ] Supervisor 연동
  - [ ] 간단한 요청 처리 테스트

#### 완료 조건
```bash
$ agentic-coder
🤖 Agentic Coder Interactive Mode
You: Hello
AI: Hello! How can I help you today?
```

---

### Phase 2: 스트리밍 UI 구현 (2-3일)
**목표**: 실시간 agent 진행 상황 표시

#### Todo List
- [ ] 2.1. Rich Progress 통합
  - [ ] SpinnerColumn, BarColumn 구현
  - [ ] Agent별 진행 상황 표시
  - [ ] 다중 agent 동시 표시

- [ ] 2.2. Streaming Content 표시
  - [ ] Markdown 렌더링
  - [ ] Code syntax highlighting
  - [ ] 실시간 스트림 업데이트

- [ ] 2.3. Artifact 결과 표시
  - [ ] 파일 트리 뷰
  - [ ] 생성/수정/삭제 표시
  - [ ] 색상 코딩 (green/yellow/red)

#### 완료 조건
```
You: Create a Python calculator

[Supervisor] 요청 분석 중...
[Planning] 계획 수립 중... (1,234 chars)
  ## 구현 계획
  1. 기본 연산 함수
  2. 메인 인터페이스

[Coder] 코드 생성 중...
✅ Created 2 files:
  [green]CREATED[/green] calculator.py
  [green]CREATED[/green] test_calculator.py
```

---

### Phase 3: 고급 기능 (3-4일)
**목표**: Slash commands, 설정, 플러그인 기반 확장

#### Todo List
- [ ] 3.1. Slash Commands 구현
  - [ ] `/help` - 도움말
  - [ ] `/status` - 세션 상태
  - [ ] `/clear` - 화면 지우기
  - [ ] `/history` - 대화 히스토리
  - [ ] `/context` - 현재 컨텍스트 표시
  - [ ] `/files` - 생성된 파일 목록

- [ ] 3.2. 설정 시스템
  - [ ] `.agentic-coder/settings.json` 지원
  - [ ] 모델 설정 (Qwen, DeepSeek, GPT-OSS)
  - [ ] workspace 기본 경로
  - [ ] 커스텀 프롬프트

- [ ] 3.3. 세션 저장/복원
  - [ ] 세션 자동 저장
  - [ ] `--session-id`로 이전 세션 복원
  - [ ] 대화 히스토리 저장

- [ ] 3.4. 파일 미리보기
  - [ ] 생성된 파일 내용 미리보기
  - [ ] Syntax highlighting
  - [ ] diff 표시 (수정된 파일)

#### 완료 조건
```bash
$ agentic-coder --session-id session-123 --model qwen-coder

🤖 Resuming session-123

You: /history
[1] User: Create a calculator
[2] AI: Created calculator.py, test_calculator.py

You: /files
📄 calculator.py (200 lines)
📄 test_calculator.py (50 lines)

You: /context
## Key Context
- Files: calculator.py, test_calculator.py
- Recent: Calculator implementation
```

---

### Phase 4: 패키징 및 배포 (1-2일)
**목표**: pip로 설치 가능한 패키지 생성

#### Todo List
- [ ] 4.1. setup.py / pyproject.toml 완성
  - [ ] 의존성 정의
  - [ ] Entry point 설정
  - [ ] 메타데이터 (version, author 등)

- [ ] 4.2. 설치 스크립트
  - [ ] `install.sh` (Linux/MacOS)
  - [ ] `install.ps1` (Windows)
  - [ ] Docker 이미지 (선택)

- [ ] 4.3. 문서 작성
  - [ ] README.md (CLI 사용법)
  - [ ] INSTALL.md (설치 가이드)
  - [ ] CLI_GUIDE.md (상세 가이드)

- [ ] 4.4. 테스트
  - [ ] 설치 테스트 (clean 환경)
  - [ ] Cross-platform 테스트
  - [ ] CI/CD 설정 (선택)

#### 완료 조건
```bash
# 설치
$ pip install agentic-coder

# 사용
$ agentic-coder --version
Agentic Coder v1.0.0

$ agentic-coder --help
usage: agentic-coder [-h] [--workspace WORKSPACE] [--session-id SESSION_ID] ...
```

---

## 🔧 기술 스택

### 필수 라이브러리
```
rich>=13.0.0           # Terminal UI
click>=8.0.0           # CLI framework (alternative to argparse)
prompt-toolkit>=3.0.0  # Advanced input handling
python-dotenv>=1.0.0   # Environment variables
```

### 선택 라이브러리
```
textual>=0.40.0        # Full TUI (advanced alternative to rich)
questionary>=2.0.0     # Interactive prompts
halo>=0.0.31          # Spinners
```

---

## 🎨 UI/UX 디자인

### 컬러 스킴
```python
COLORS = {
    "user": "bold cyan",
    "ai": "bold green",
    "supervisor": "blue",
    "coder": "yellow",
    "reviewer": "magenta",
    "created": "green",
    "modified": "yellow",
    "deleted": "red",
    "error": "bold red",
    "warning": "yellow",
    "info": "cyan",
}
```

### ASCII Art 로고 (선택)
```
╔════════════════════════════════════════════╗
║                                            ║
║   ████████╗███████╗███████╗████████╗      ║
║   ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝      ║
║      ██║   █████╗  ███████╗   ██║         ║
║      ██║   ██╔══╝  ╚════██║   ██║         ║
║      ██║   ███████╗███████║   ██║         ║
║      ╚═╝   ╚══════╝╚══════╝   ╚═╝         ║
║                                            ║
║   🤖 Agentic Coder - AI Coding Assistant  ║
║                                            ║
╚════════════════════════════════════════════╝
```

---

## 📈 마이그레이션 전략

### 병행 운영
- ✅ 웹 버전 유지 (FastAPI + React)
- ✅ CLI 버전 신규 추가
- ✅ 동일한 backend agent 시스템 공유

### 코드 재사용
```
backend/
├── app/
│   ├── agent/          # ✅ CLI와 웹 모두 사용
│   ├── core/           # ✅ CLI와 웹 모두 사용
│   ├── utils/          # ✅ CLI와 웹 모두 사용
│   ├── api/            # ⚠️  웹 전용
│   └── cli/            # 🆕 CLI 전용
frontend/               # ⚠️  웹 전용
```

### 점진적 전환
1. Phase 1-2: CLI 기본 기능 (웹과 병행)
2. Phase 3: CLI 고급 기능 (사용자 피드백)
3. Phase 4: 안정화 및 배포
4. (선택) Phase 5: 웹 버전 deprecate 또는 유지

---

## 🚀 빠른 시작 (Quick Start)

개발 환경에서 CLI 테스트:

```bash
# 1. 개발 모드로 CLI 실행
cd backend
python -m cli "Create a hello world app"

# 2. Interactive 모드
python -m cli

# 3. 특정 워크스페이스에서 실행
python -m cli --workspace /path/to/project
```

---

## 📚 참고 자료

- **anthropics/claude-code**: Plugin 기반 아키텍처 참고
- **Phase 2 Context Manager**: 이미 구현된 컨텍스트 관리 재사용
- **LangGraph Dynamic Workflow**: 기존 agent 시스템 활용
- **Rich Documentation**: https://rich.readthedocs.io/
- **Click Documentation**: https://click.palletsprojects.com/

---

## ✅ 성공 지표

CLI 마이그레이션이 성공적이려면:

1. **설치 간편성**: `pip install agentic-coder` 한 줄로 설치
2. **사용 편의성**: `agentic-coder` 실행만으로 작동
3. **반응성**: 실시간 agent 진행 상황 확인
4. **안정성**: 기존 agent 시스템의 모든 기능 유지
5. **확장성**: 새로운 slash command 쉽게 추가 가능

---

## 🎯 다음 단계

1. ✅ 이 문서 검토 및 피드백
2. ⏭️ Phase 1 구현 시작 (CLI 기본 구조)
3. ⏭️ 프로토타입 테스트
4. ⏭️ 사용자 피드백 수집
5. ⏭️ Phase 2-4 순차 진행

---

**문서 버전**: v1.0.0
**최종 수정**: 2026-01-08
