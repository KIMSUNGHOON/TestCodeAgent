# LLM 모델 변경 개선 계획

## 📋 개요

현재 Agentic Coder는 두 개의 LLM 모델을 사용합니다:
- **Reasoning Model**: DeepSeek-R1 (분석, 계획 수립)
- **Coding Model**: Qwen-Coder (코드 생성, 리뷰)

단일 모델(예: `gpt-oss-120b`)로 변경할 경우의 영향도와 개선 방안을 정리합니다.

---

## 🔍 현재 구조 분석

### 1. 설정 구조 (`backend/app/core/config.py`)

```python
class Settings(BaseSettings):
    # 현재: 두 개의 엔드포인트
    vllm_reasoning_endpoint: str = "http://localhost:8001/v1"
    vllm_coding_endpoint: str = "http://localhost:8002/v1"

    # 현재: 두 개의 모델
    reasoning_model: str = "deepseek-ai/DeepSeek-R1"
    coding_model: str = "Qwen/Qwen3-8B-Coder"
```

### 2. 모델별 프롬프트 (`shared/prompts/`)

| 파일 | 모델 | 특징 |
|------|------|------|
| `deepseek_r1.py` | DeepSeek-R1 | `<think></think>` 태그 필수 |
| `qwen_coder.py` | Qwen-Coder | 코드 블록 중심, 낮은 temperature |

### 3. 모델 사용처

| 컴포넌트 | 사용 모델 | 파일 위치 |
|----------|----------|-----------|
| Supervisor | DeepSeek-R1 | `backend/core/supervisor.py` |
| Coder | Qwen-Coder | `backend/app/agent/langgraph/nodes/coder.py` |
| Reviewer | Qwen-Coder | `backend/app/agent/langgraph/nodes/reviewer.py` |
| Refiner | (없음 - 시뮬레이션) | `backend/app/agent/langgraph/nodes/refiner.py` |

---

## ❓ 핵심 질문에 대한 답변

### Q1: 단일 모델 사용 시 변경사항

단일 모델(예: `gpt-oss-120b`)로 변경 시:

| 항목 | 현재 | 변경 후 | 영향도 |
|------|------|---------|--------|
| 엔드포인트 | 2개 | 1개 | 🟢 낮음 |
| 모델 설정 | 2개 | 1개 | 🟢 낮음 |
| 프롬프트 | 모델별 분리 | **통합 필요** | 🔴 높음 |
| 파라미터 | 모델별 최적화 | **재조정 필요** | 🟡 중간 |

### Q2: System Prompt 변경 필요성

**예, 변경이 필요합니다.**

현재 프롬프트의 모델 특화 요소:

```python
# DeepSeek-R1 전용 (다른 모델에서 작동 안 함)
DEEPSEEK_R1_SYSTEM_PROMPT = """
CRITICAL CONSTRAINTS:
1. ALWAYS use <think></think> tags...  # ❌ GPT 계열에서 미지원
"""

# Qwen-Coder 전용
QWEN_CODER_CONFIG = {
    "stop": ["</code>", "```\n\n"],  # 모델별 종료 토큰 다름
}
```

**해결 방안: 모델 추상화 계층 도입**

### Q3: DeepAgent 구조 변경 필요성

**부분적 변경 필요:**

| 영역 | 변경 필요 | 이유 |
|------|----------|------|
| 워크플로우 (LangGraph) | ❌ 불필요 | 모델 독립적 설계 |
| 노드 (Coder, Reviewer) | ⚠️ 수정 필요 | 엔드포인트/프롬프트 참조 변경 |
| 프롬프트 시스템 | ✅ 재설계 필요 | 모델별 어댑터 패턴 적용 |
| 설정 (Config) | ✅ 재설계 필요 | 단일 모델 지원 구조로 |

---

## 🎯 개선 방향

### Phase 1: 모델 추상화 계층 도입 (우선순위: 높음)

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  (Supervisor, Coder, Reviewer, Refiner, etc.)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  LLM Provider Interface                      │
│  - generate(prompt, task_type)                              │
│  - stream(prompt, task_type)                                │
│  - get_config(task_type)                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ DeepSeek R1 │  │ Qwen Coder  │  │  GPT-OSS    │
│   Adapter   │  │   Adapter   │  │   Adapter   │
└─────────────┘  └─────────────┘  └─────────────┘
```

### Phase 2: 통합 프롬프트 시스템

```python
# 새로운 구조: shared/prompts/base.py
class BasePromptTemplate:
    """모델 독립적 프롬프트 템플릿"""

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @abstractmethod
    def format_reasoning(self, content: str) -> str:
        """모델에 맞는 reasoning 포맷으로 변환"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict:
        """모델 응답을 표준 형식으로 파싱"""
        pass


# 모델별 구현
class DeepSeekAdapter(BasePromptTemplate):
    def format_reasoning(self, content: str) -> str:
        return f"<think>{content}</think>"

class GPTAdapter(BasePromptTemplate):
    def format_reasoning(self, content: str) -> str:
        return f"Let me think step by step:\n{content}"
```

### Phase 3: 설정 통합

```python
# 개선된 config.py
class Settings(BaseSettings):
    # 통합 엔드포인트 (또는 여러 개 지원)
    llm_endpoint: str = "http://localhost:8001/v1"

    # 단일 모델 또는 태스크별 모델 지정
    llm_model: str = "gpt-oss-120b"

    # 선택적: 태스크별 모델 오버라이드
    reasoning_model: Optional[str] = None  # None이면 llm_model 사용
    coding_model: Optional[str] = None     # None이면 llm_model 사용

    # 모델 타입 (프롬프트 어댑터 선택용)
    model_type: Literal["deepseek", "qwen", "gpt", "claude", "generic"] = "generic"
```

---

## 📝 구현 계획

### Stage 1: 기반 구조 구현 ✅ 완료

- [x] `shared/llm/base.py` - LLM Provider 인터페이스 정의
  - `BaseLLMProvider` 추상 클래스
  - `LLMConfig`, `LLMResponse` 데이터 클래스
  - `TaskType` enum (REASONING, CODING, REVIEW, REFINE, GENERAL)
  - `LLMProviderFactory` 팩토리 패턴
- [x] `shared/llm/adapters/` - 모델별 어댑터 구현
  - [x] `deepseek_adapter.py` - `<think>` 태그 지원
  - [x] `qwen_adapter.py` - 코딩 특화 설정
  - [x] `generic_adapter.py` - GPT, Claude, Llama, Mistral 지원
- [x] `backend/app/core/config.py` - 설정 구조 확장
  - `model_type`, `llm_endpoint`, `llm_model` 추가
  - `get_reasoning_endpoint`, `get_coding_endpoint` 프로퍼티

### Stage 2: 노드 리팩토링 ✅ 완료

- [x] `coder.py` - LLM Provider 인터페이스 사용으로 변경
  - `_get_code_generation_prompt()` 모델별 프롬프트 선택
- [x] `reviewer.py` - LLM Provider 어댑터 적용
  - `LLMProviderFactory.create()` 사용
- [x] `refiner.py` - 실제 LLM 호출 구현
  - `_apply_fix_with_llm()` 함수 추가
  - Fallback to heuristic 지원
- [ ] `supervisor.py` - 어댑터 패턴 적용 (선택적)

### Stage 3: 프롬프트 통합 ✅ 완료

- [x] `shared/prompts/generic.py` - 범용 프롬프트 템플릿
- [x] 어댑터 내 통합 프롬프트
  - 각 어댑터에 `SYSTEM_PROMPTS` 딕셔너리 포함
  - `format_prompt()`, `format_system_prompt()` 메서드

### Stage 4: 테스트 및 검증 ✅ 완료

- [x] 모듈 임포트 테스트
- [x] 단일 모델 모드 테스트 (`TestSingleModelMode` - 5 tests passed)
- [x] 멀티 모델 모드 테스트 (`TestMultiModelMode` - 6 tests passed)
- [x] Fallback 동작 검증 (`TestFallbackBehavior`, `TestRefinerFallback` - 7 tests passed)
- [x] Config 통합 테스트 (`TestConfigIntegration` - 3 tests passed)
- [x] Async 작업 테스트 (`TestAsyncOperations` - 2 tests passed)

**통합 테스트 결과: 28 passed, 0 failed**

테스트 파일: `backend/tests/integration/test_llm_provider.py`

---

## 🔧 즉시 적용 가능한 빠른 변경

단일 모델로 빠르게 전환하려면 아래 최소 변경만 수행:

### 1. Config 수정

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # 기존 유지 (하위 호환)
    vllm_reasoning_endpoint: str = "http://localhost:8001/v1"
    vllm_coding_endpoint: str = "http://localhost:8001/v1"  # 동일 엔드포인트

    # 단일 모델 사용
    reasoning_model: str = "gpt-oss-120b"
    coding_model: str = "gpt-oss-120b"  # 동일 모델

    # 모델 타입 추가 (프롬프트 선택용)
    model_type: str = "generic"
```

### 2. 범용 프롬프트 추가

```python
# shared/prompts/generic.py
GENERIC_SYSTEM_PROMPT = """You are an AI assistant specialized in software engineering.

For complex tasks, think through the problem step by step before providing a solution.
Provide clear, executable code with proper error handling.
"""
```

### 3. 노드에서 프롬프트 분기

```python
# coder.py 등에서
if settings.model_type == "deepseek":
    system_prompt = DEEPSEEK_R1_SYSTEM_PROMPT
elif settings.model_type == "qwen":
    system_prompt = QWEN_CODER_SYSTEM_PROMPT
else:
    system_prompt = GENERIC_SYSTEM_PROMPT
```

---

## ⚠️ 주의사항

1. **Reasoning 품질**: DeepSeek-R1의 `<think>` 태그는 reasoning 품질 향상에 기여. 다른 모델에서는 "step-by-step" 프롬프팅으로 대체 필요.

2. **코드 생성 품질**: 코딩 특화 모델(Qwen-Coder)에서 범용 모델로 전환 시 품질 저하 가능. 프롬프트 최적화 필요.

3. **비용/성능 트레이드오프**: 단일 대형 모델 vs 특화 소형 모델 비교 필요.

4. **Fallback 전략**: 모델 장애 시 다른 모델로 자동 전환 로직 고려.

---

## 📊 예상 효과

| 지표 | 현재 (2 모델) | 변경 후 (1 모델) |
|------|--------------|-----------------|
| 배포 복잡도 | 높음 (2 서버) | 낮음 (1 서버) |
| 유지보수 | 복잡 | 단순 |
| 비용 | 모델별 상이 | 통합 가능 |
| 특화 성능 | 높음 | 다소 낮을 수 있음 |

---

## 🗓️ 타임라인

| 단계 | 작업 | 예상 소요 |
|------|------|----------|
| 즉시 적용 | 설정 변경 + 범용 프롬프트 | 1시간 |
| Stage 1 | 기반 구조 | 1-2일 |
| Stage 2 | 노드 리팩토링 | 2-3일 |
| Stage 3 | 프롬프트 통합 | 1-2일 |
| Stage 4 | 테스트 | 1일 |
| **Total** | **완전한 추상화** | **5-8일** |

---

*Last Updated: 2026-01-05*
*Author: AI Assistant*
*Implementation Status: Stage 1-4 Complete ✅*
