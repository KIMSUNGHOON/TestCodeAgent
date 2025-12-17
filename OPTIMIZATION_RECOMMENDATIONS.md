# H100 GPU 최적화 권장사항

## 현재 하드웨어 구성
- **GPU 0**: NVIDIA H100 96GB NVL (DeepSeek-R1)
- **GPU 1**: NVIDIA H100 96GB NVL (Qwen3-Coder)

## 최적화 전략

### 1. 병렬 처리 수 증가

#### 현재 설정
```python
max_parallel_agents = 10  # workflow_manager.py:531
```

#### 권장 설정
```python
max_parallel_agents = 25  # H100 + vLLM의 성능을 고려
```

**예상 효과:**
- 코딩 작업 처리 속도 2-2.5배 향상
- GPU 1 활용도 증가 (40% → 80%+)
- 전체 워크플로우 완료 시간 30-40% 단축

**적용 방법:**
```bash
# backend/app/agent/langchain/workflow_manager.py 수정
sed -i 's/self.max_parallel_agents = 10/self.max_parallel_agents = 25/' \
  backend/app/agent/langchain/workflow_manager.py
```

---

### 2. 세션 간 파이프라이닝

#### 개념
여러 사용자 세션이 동시에 실행될 때 GPU 활용도 극대화:

```
Session A: [Planning@GPU0] → [Coding@GPU1] → [Review@GPU1]
Session B:                    [Planning@GPU0] → [Coding@GPU1] → [Review@GPU1]
                                            ↑ 이 시점에 GPU0 유휴
```

#### 구현 방안

**Option A: 다중 세션 자동 파이프라이닝**
```python
# 새로운 SessionScheduler 추가
class SessionScheduler:
    def __init__(self):
        self.gpu0_queue = asyncio.Queue()  # DeepSeek-R1 작업
        self.gpu1_queue = asyncio.Queue()  # Qwen3-Coder 작업

    async def schedule_planning(self, session_id, task):
        # GPU0에 Planning 작업 큐잉
        await self.gpu0_queue.put((session_id, task))

    async def schedule_coding(self, session_id, task):
        # GPU1에 Coding 작업 큐잉 (병렬 처리)
        await self.gpu1_queue.put((session_id, task))
```

**Option B: Review 단계도 병렬화**
```python
# Review를 DeepSeek-R1에서 수행하도록 분리
class OptimizedWorkflow:
    def __init__(self):
        self.review_llm = ChatOpenAI(
            base_url=settings.vllm_reasoning_endpoint,  # GPU 0 사용
            model=settings.reasoning_model
        )
```

**예상 효과:**
- GPU 0 활용도 증가 (20% → 60%+)
- 다중 사용자 환경에서 처리량 3배 향상
- GPU 유휴 시간 최소화

---

### 3. vLLM 서버 최적화 설정

#### 추천 vLLM 서버 실행 파라미터

**GPU 0 (DeepSeek-R1) - 추론 최적화:**
```bash
vllm serve deepseek-ai/DeepSeek-R1 \
  --port 8001 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768 \
  --max-num-seqs 16 \
  --max-num-batched-tokens 65536 \
  --enable-chunked-prefill \
  --tensor-parallel-size 1
```

**GPU 1 (Qwen3-Coder) - 처리량 최적화:**
```bash
vllm serve Qwen/Qwen3-8B-Coder \
  --port 8002 \
  --gpu-memory-utilization 0.95 \
  --max-model-len 32768 \
  --max-num-seqs 64 \
  --max-num-batched-tokens 131072 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --tensor-parallel-size 1
```

**주요 파라미터 설명:**
- `--max-num-seqs`: 동시 처리 시퀀스 수 (높일수록 처리량 증가)
- `--max-num-batched-tokens`: 배치당 최대 토큰 수
- `--enable-chunked-prefill`: 긴 프롬프트 효율적 처리
- `--enable-prefix-caching`: 반복되는 시스템 프롬프트 캐싱
- `--gpu-memory-utilization`: GPU 메모리 활용률 (0.9-0.95 권장)

**예상 효과:**
- GPU 1에서 25개 동시 요청 처리 가능
- 시스템 프롬프트 캐싱으로 10-15% 속도 향상
- Chunked prefill로 긴 컨텍스트 처리 효율 증가

---

### 4. 적응형 배치 크기 조정

#### 현재 로직
```python
# workflow_manager.py:1609-1617
if self.adaptive_parallelism:
    optimal_parallel = min(len(grouped_checklist), self.max_parallel_agents)
    if len(grouped_checklist) <= 5:
        optimal_parallel = len(grouped_checklist)
```

#### 개선된 로직
```python
# H100 성능을 고려한 적응형 조정
def calculate_optimal_parallel(self, task_count: int) -> int:
    """Calculate optimal parallelism based on H100 capabilities."""
    # H100 기준 권장 동시 처리 수
    H100_RECOMMENDED_PARALLEL = 25

    if task_count <= 10:
        # 소규모 작업: 모두 병렬 처리
        return task_count
    elif task_count <= 20:
        # 중규모 작업: 적극적 병렬화
        return min(task_count, H100_RECOMMENDED_PARALLEL)
    else:
        # 대규모 작업: 최대 병렬도 유지
        return H100_RECOMMENDED_PARALLEL
```

**예상 효과:**
- 작은 프로젝트: 즉시 완료 (모든 작업 동시 실행)
- 중간 프로젝트: 25개 작업 동시 처리로 빠른 완료
- 큰 프로젝트: 안정적인 배치 처리

---

### 5. 성능 모니터링 및 메트릭

#### 추가 권장 메트릭
```python
class PerformanceMetrics:
    """Track GPU utilization and workflow performance."""

    def __init__(self):
        self.gpu0_utilization = []  # DeepSeek-R1 활용도
        self.gpu1_utilization = []  # Qwen3-Coder 활용도
        self.parallel_task_count = []  # 동시 실행 작업 수
        self.task_latency = []  # 작업별 지연 시간

    async def log_metrics(self):
        """Log current GPU utilization."""
        # nvidia-smi를 통한 GPU 모니터링
        # vLLM metrics endpoint 활용
        pass
```

#### vLLM 메트릭 활용
```python
# vLLM은 /metrics 엔드포인트 제공
async def get_vllm_metrics():
    gpu0_metrics = await fetch("http://localhost:8001/metrics")
    gpu1_metrics = await fetch("http://localhost:8002/metrics")

    return {
        "gpu0_throughput": gpu0_metrics["throughput"],
        "gpu1_throughput": gpu1_metrics["throughput"],
        "gpu0_queue_size": gpu0_metrics["queue_size"],
        "gpu1_queue_size": gpu1_metrics["queue_size"]
    }
```

---

## 우선순위별 적용 계획

### Phase 1: 즉시 적용 (10분)
1. ✅ `max_parallel_agents` 10 → 25로 증가
2. ✅ vLLM 서버 재시작 (최적화된 파라미터)

**예상 효과:** 처리 속도 2배 향상

### Phase 2: 단기 (1일)
3. 🔄 적응형 배치 크기 로직 개선
4. 🔄 성능 메트릭 수집 시스템 추가

**예상 효과:** 추가 20% 성능 향상, 모니터링 가능

### Phase 3: 중기 (1주)
5. 🚀 세션 간 파이프라이닝 구현
6. 🚀 Review 단계 GPU 0으로 분리

**예상 효과:** 다중 사용자 환경에서 3배 처리량 증가

---

## 성능 비교 (예상)

### 단일 세션 워크플로우 (20개 작업)

| 구성 | Planning | Coding | Review | 총 시간 |
|------|----------|--------|--------|---------|
| **현재** | 10초 | 40초 (10개 병렬) | 15초 | **65초** |
| **Phase 1** | 10초 | 16초 (25개 병렬) | 15초 | **41초** (37% 단축) |
| **Phase 3** | 10초 | 16초 (25개 병렬) | 15초 | **41초** (37% 단축) |

### 다중 세션 (3개 동시 실행)

| 구성 | GPU 0 활용도 | GPU 1 활용도 | 총 처리 시간 |
|------|--------------|--------------|--------------|
| **현재** | 20% | 60% | **195초** (65초 × 3) |
| **Phase 1** | 20% | 80% | **123초** (41초 × 3) |
| **Phase 3** | 65% | 85% | **70초** (파이프라이닝) |

---

## 구현 코드 예시

### 1. max_parallel_agents 증가
```python
# backend/app/agent/langchain/workflow_manager.py:531
self.max_parallel_agents = 25  # H100 최적화
```

### 2. 개선된 적응형 로직
```python
# workflow_manager.py에 추가
def calculate_optimal_parallel(self, task_count: int) -> int:
    """Calculate optimal parallelism for H100 GPUs."""
    H100_MAX_PARALLEL = 25

    if task_count <= 10:
        return task_count
    elif task_count <= 25:
        return min(task_count, H100_MAX_PARALLEL)
    else:
        return H100_MAX_PARALLEL

# _execute_parallel_coding 메서드 수정
optimal_parallel = self.calculate_optimal_parallel(len(grouped_checklist))
```

### 3. GPU 분산 Review
```python
# workflow_manager.py __init__ 수정
self.review_llm = ChatOpenAI(
    base_url=settings.vllm_reasoning_endpoint,  # GPU 0으로 변경
    model=settings.reasoning_model,
    temperature=0.3,
    streaming=True
)
```

---

## 모니터링 및 검증

### 성능 테스트 스크립트
```python
# performance_test.py
import asyncio
import time

async def test_parallel_performance():
    """Test parallel coding performance."""
    tasks = [
        {"task": f"Create file_{i}.py", "complexity": "simple"}
        for i in range(30)
    ]

    start = time.time()
    # Execute workflow with tasks
    elapsed = time.time() - start

    print(f"Processed {len(tasks)} tasks in {elapsed:.2f}s")
    print(f"Throughput: {len(tasks)/elapsed:.2f} tasks/sec")
```

### GPU 활용도 모니터링
```bash
# 실시간 GPU 모니터링
watch -n 1 nvidia-smi

# vLLM 메트릭 확인
curl http://localhost:8001/metrics | grep throughput
curl http://localhost:8002/metrics | grep throughput
```

---

## 결론

**즉시 적용 권장 (Phase 1):**
1. `max_parallel_agents = 25`로 증가
2. vLLM 서버 최적화 파라미터로 재시작

**예상 총 개선:**
- 단일 세션: 37% 속도 향상
- 다중 세션: 64% 속도 향상 (Phase 3까지)
- GPU 활용도: 40% → 75%+ 증가

H100 2개의 강력한 성능을 충분히 활용하지 못하고 있었습니다. 위 최적화로 하드웨어 잠재력을 최대한 끌어낼 수 있습니다.
