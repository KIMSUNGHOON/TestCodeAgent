# 다중 사용자 동시 접속 관리 전략 분석

## 📊 현재 구현 현황 (Current Implementation)

### ✅ 이미 구현된 기능

#### 1. **세션 관리 (Session Management)**
**구현 파일**: `backend/app/core/session_store.py`

**현재 기능**:
- ✅ **Thread-safe 세션 저장소**: `asyncio.Lock` per session
- ✅ **세션별 격리**: 각 세션은 독립적인 락을 가짐
- ✅ **세션별 프레임워크 선택**: standard/deepagents 독립 관리
- ✅ **세션별 워크스페이스**: 각 사용자는 별도의 작업 공간
- ✅ **세션 정보 조회/삭제**: list_sessions(), delete_session()

**구현 방식**:
```python
class SessionStore:
    def __init__(self):
        self._frameworks: Dict[str, FrameworkType] = {}
        self._workspaces: Dict[str, str] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()  # For lock management
```

**장점**:
- 세션별 락으로 **fine-grained locking** → 다른 세션은 동시 처리 가능
- Race condition 방지
- 메모리 효율적 (session당 하나의 Lock만 생성)

#### 2. **워크스페이스 관리 (Workspace Management)**
**구현 파일**: `backend/app/services/workflow_service.py`

**현재 기능**:
- ✅ **세션별 독립 워크스페이스**: `/home/user/workspace/project_name_<session>`
- ✅ **프로젝트명 자동 생성**: LLM이 사용자 요청 기반으로 제안
- ✅ **중복 방지**: 같은 이름 프로젝트 존재 시 `_1`, `_2` 접미사 추가
- ✅ **워크스페이스 재사용**: 같은 세션은 기존 워크스페이스 재사용
- ✅ **Path Traversal 방지**: `sanitize_path()` 보안 검증

**구현 방식**:
```python
async def get_or_create_workspace(
    session_id: str,
    user_message: str,
    base_workspace: Optional[str] = None
) -> str:
    # 기존 워크스페이스 재사용
    existing_workspace = await self.session_store.get_workspace(session_id, default=None)
    if existing_workspace:
        return existing_workspace

    # 새 프로젝트 생성
    project_name = await self.suggest_project_name(user_message)
    workspace = os.path.join(workspace_root, project_name)

    # 중복 방지
    while os.path.exists(workspace):
        workspace = os.path.join(workspace_root, f"{project_name}_{counter}")
        counter += 1
```

**장점**:
- 사용자간 워크스페이스 완전 격리
- 파일 충돌 방지
- 보안: Path traversal 공격 차단

#### 3. **데이터베이스 동시성 (Database Concurrency)**
**구현 파일**: `backend/app/db/database.py`

**현재 기능**:
- ✅ **SQLite WAL 모드**: 동시 읽기/쓰기 가능
- ✅ **Connection Pooling**: `StaticPool` (단일 연결 유지)
- ✅ **타임아웃 설정**: 30초 lock timeout
- ✅ **성능 최적화**: 10MB 캐시, foreign key 제약

**구현 방식**:
```python
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # 다중 스레드 허용
        "timeout": 30  # 30초 대기
    },
    poolclass=StaticPool,  # SQLite에 최적화
    pool_pre_ping=True,  # 연결 검증
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor.execute("PRAGMA journal_mode=WAL")  # 동시 읽기/쓰기
    cursor.execute("PRAGMA cache_size=-10000")  # 10MB 캐시
```

**장점**:
- WAL 모드: 여러 reader + 1 writer 동시 작동 가능
- Lock contention 감소
- 성능: 캐시로 디스크 I/O 감소

#### 4. **비동기 파일 I/O (Async File Operations)**
**구현 파일**: `backend/app/api/routes.py`

**현재 기능**:
- ✅ **aiofiles 사용**: 모든 파일 읽기/쓰기 비동기
- ✅ **Non-blocking**: Event loop 차단 방지
- ✅ **동시 파일 작업**: 여러 사용자가 각자 파일 작업 가능

**구현 방식**:
```python
async def write_artifact_to_workspace(artifact: dict) -> dict:
    import aiofiles
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(content)
```

**장점**:
- CPU 효율: I/O 대기 중 다른 요청 처리
- 확장성: 수백 개의 동시 요청 처리 가능

---

## ⚠️ 현재 한계점 및 개선 필요 사항

### 🔴 Critical Issues

#### 1. **메모리 내 세션 저장소 (In-Memory SessionStore)**
**문제점**:
- 서버 재시작 시 모든 세션 데이터 손실
- 수평 확장 불가능 (여러 서버 인스턴스 시 세션 공유 안 됨)
- 무한정 메모리 증가 (세션 만료 로직 없음)

**현재 코드**:
```python
class SessionStore:
    def __init__(self):
        self._frameworks: Dict[str, FrameworkType] = {}  # 메모리에만 저장
        self._workspaces: Dict[str, str] = {}
```

**권장 해결책**:
```python
# Option 1: Redis 기반 세션 저장소
import aioredis

class RedisSessionStore:
    def __init__(self):
        self.redis = aioredis.from_url("redis://localhost")

    async def get_framework(self, session_id: str) -> FrameworkType:
        value = await self.redis.get(f"session:{session_id}:framework")
        return value.decode() if value else "standard"

    async def set_framework(self, session_id: str, framework: FrameworkType):
        await self.redis.setex(
            f"session:{session_id}:framework",
            3600 * 24,  # 24시간 TTL
            framework
        )

# Option 2: DB 기반 세션 저장소
# SQLite → PostgreSQL/MySQL로 마이그레이션
```

**영향**:
- ✅ 서버 재시작해도 세션 유지
- ✅ 수평 확장 가능 (로드 밸런서 + 여러 서버)
- ✅ 자동 만료 (TTL)

---

#### 2. **워크플로우 캐시 메모리 누수 (Workflow Cache Memory Leak)**
**문제점**:
- `_deepagent_workflows` 딕셔너리가 무한정 증가
- 세션 종료해도 워크플로우 객체 삭제 안 됨
- LLM 모델이 메모리에 계속 유지

**현재 코드** (`workflow_service.py`):
```python
class WorkflowService:
    def __init__(self):
        self._deepagent_workflows: Dict[str, Any] = {}  # 무한 증가
```

**권장 해결책**:
```python
from datetime import datetime, timedelta
from collections import OrderedDict

class WorkflowService:
    def __init__(self):
        self._deepagent_workflows: OrderedDict[str, Dict] = OrderedDict()
        self._max_cache_size = 100  # 최대 100개 세션
        self._cache_ttl = timedelta(hours=1)  # 1시간 후 만료

    async def get_workflow(self, session_id: str, workspace: str):
        # LRU eviction: 오래된 것부터 제거
        if len(self._deepagent_workflows) >= self._max_cache_size:
            oldest_session = next(iter(self._deepagent_workflows))
            del self._deepagent_workflows[oldest_session]
            logger.info(f"Evicted oldest workflow: {oldest_session}")

        # TTL 체크
        if session_id in self._deepagent_workflows:
            cache_entry = self._deepagent_workflows[session_id]
            if datetime.now() - cache_entry['created_at'] > self._cache_ttl:
                del self._deepagent_workflows[session_id]
                logger.info(f"Expired workflow: {session_id}")

        # 워크플로우 생성 또는 재사용
        if session_id not in self._deepagent_workflows:
            workflow = await self._create_deepagent_workflow(...)
            self._deepagent_workflows[session_id] = {
                'workflow': workflow,
                'created_at': datetime.now()
            }

        return self._deepagent_workflows[session_id]['workflow']
```

**영향**:
- ✅ 메모리 사용량 제한
- ✅ 오래된 세션 자동 정리
- ✅ 서버 안정성 향상

---

#### 3. **요청 스케줄링 및 큐잉 없음 (No Request Queuing)**
**문제점**:
- 동시에 100명 사용자가 workflow 실행 시 100개 LLM 인스턴스 생성
- GPU/메모리 고갈
- 서버 크래시 가능성

**현재 코드**:
```python
# routes.py - 제한 없이 즉시 실행
@router.post("/workflow/execute")
async def execute_workflow(request: ChatRequest):
    workflow = await workflow_service.get_workflow(...)  # 즉시 생성
    async for update in workflow.execute_stream(...):  # 즉시 실행
        yield update
```

**권장 해결책**:
```python
import asyncio
from collections import deque

class WorkflowQueue:
    def __init__(self, max_concurrent=10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = deque()
        self.active_count = 0

    async def enqueue(self, session_id: str, workflow_fn):
        """큐에 워크플로우 추가"""
        queue_position = len(self.queue) + self.active_count + 1

        # 큐 대기 상태 전송
        yield {
            "type": "queued",
            "position": queue_position,
            "estimated_wait_seconds": queue_position * 60  # 1분/작업 예상
        }

        # Semaphore로 동시 실행 제한
        async with self.semaphore:
            self.active_count += 1
            try:
                yield {"type": "started", "message": "워크플로우 시작"}
                async for update in workflow_fn():
                    yield update
            finally:
                self.active_count -= 1

# 사용
workflow_queue = WorkflowQueue(max_concurrent=10)

@router.post("/workflow/execute")
async def execute_workflow(request: ChatRequest):
    async def workflow_fn():
        workflow = await workflow_service.get_workflow(...)
        async for update in workflow.execute_stream(...):
            yield update

    # 큐 통과 후 실행
    async for update in workflow_queue.enqueue(request.session_id, workflow_fn):
        yield json.dumps(update) + "\n"
```

**효과**:
- ✅ 동시 실행 제한 (예: 최대 10개)
- ✅ 나머지는 큐에서 대기
- ✅ GPU/메모리 안정적 사용
- ✅ 사용자에게 대기 시간 알림

---

#### 4. **Rate Limiting 없음 (No Rate Limiting)**
**문제점**:
- 한 사용자가 1초에 100번 요청 가능
- DDoS 공격에 취약
- 정상 사용자 서비스 방해

**권장 해결책**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/workflow/execute")
@limiter.limit("10/minute")  # 분당 10회 제한
async def execute_workflow(request: Request, chat_request: ChatRequest):
    ...
```

**효과**:
- ✅ 사용자당 요청 제한
- ✅ 서버 리소스 공정 분배
- ✅ 악의적 사용 방지

---

### 🟡 Medium Priority Issues

#### 5. **세션 타임아웃 없음 (No Session Timeout)**
**문제점**:
- 사용자가 브라우저 닫아도 세션 유지
- 메모리 누적

**해결책**:
```python
class SessionStore:
    def __init__(self):
        self._last_access: Dict[str, datetime] = {}
        self.session_timeout = timedelta(hours=2)

    async def cleanup_expired_sessions(self):
        """주기적으로 만료된 세션 삭제"""
        while True:
            await asyncio.sleep(300)  # 5분마다 체크
            now = datetime.now()
            expired = [
                sid for sid, last_time in self._last_access.items()
                if now - last_time > self.session_timeout
            ]
            for sid in expired:
                await self.delete_session(sid)
                logger.info(f"Auto-deleted expired session: {sid}")
```

---

#### 6. **SQLite 확장성 한계 (SQLite Scalability)**
**문제점**:
- SQLite는 단일 서버용
- 수평 확장 불가능
- 1000+ 동시 사용자 시 병목

**해결책**:
```python
# PostgreSQL로 마이그레이션
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/dbname"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,  # 연결 풀
    max_overflow=10,
    pool_pre_ping=True
)
```

**효과**:
- ✅ 진정한 동시 쓰기
- ✅ 클러스터링 가능
- ✅ 10,000+ 동시 사용자 지원

---

## 🎯 권장 아키텍처 (Recommended Architecture)

### Phase 1: 즉시 적용 가능 (Quick Wins)
```
1. Workflow Cache LRU + TTL 추가
2. Request Queue + Semaphore (max_concurrent=10)
3. Rate Limiting (slowapi)
4. Session Timeout 자동 정리
```

**예상 효과**:
- 현재 시스템에서 10-50명 동시 사용자 안정적 처리

---

### Phase 2: 중기 개선 (Medium Term)
```
1. Redis Session Store
2. PostgreSQL 마이그레이션
3. Celery 워크 큐 (백그라운드 작업)
4. Nginx + Gunicorn (프로덕션 배포)
```

**예상 효과**:
- 50-500명 동시 사용자
- 서버 재시작해도 세션 유지
- 수평 확장 가능

---

### Phase 3: 대규모 확장 (Large Scale)
```
┌─────────────────────────────────────────────┐
│         Load Balancer (Nginx)               │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  FastAPI #1  │    │  FastAPI #2  │  (Auto-scaling)
└───────┬──────┘    └───────┬──────┘
        │                   │
        └─────────┬─────────┘
                  ▼
        ┌───────────────────┐
        │  Redis Cluster    │  (Session Store)
        └───────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ PostgreSQL   │    │    Celery    │  (Background Tasks)
│  (Primary)   │    │   Workers    │
└──────────────┘    └──────────────┘
        │
        ▼
┌──────────────┐
│ PostgreSQL   │
│  (Replica)   │
└──────────────┘
```

**예상 효과**:
- 1000+ 동시 사용자
- 99.9% uptime
- Auto-scaling

---

## 📈 성능 벤치마크 예상치

| 구현 단계 | 동시 사용자 | 평균 응답시간 | 메모리 사용 | 비용/월 |
|---------|----------|------------|----------|---------|
| **현재** | ~10명 | 2-5초 | 2-4GB | $50 |
| **Phase 1** | ~50명 | 3-8초 | 4-8GB | $50 |
| **Phase 2** | ~500명 | 5-15초 | 8-16GB | $200 |
| **Phase 3** | 1000+명 | 10-30초 | 16-64GB | $500+ |

---

## 🛠️ 구현 우선순위

### 🔥 High Priority (1주일)
1. ✅ **Workflow Cache LRU**: 메모리 누수 방지
2. ✅ **Request Semaphore**: GPU 과부하 방지
3. ✅ **Rate Limiting**: DDoS 방지

### 🟡 Medium Priority (1개월)
4. ⏳ **Redis Session Store**: 세션 영속성
5. ⏳ **Session Timeout**: 자동 정리
6. ⏳ **PostgreSQL**: DB 확장성

### 🟢 Low Priority (3개월)
7. ⏳ **Celery Queue**: 백그라운드 작업
8. ⏳ **Load Balancer**: 수평 확장
9. ⏳ **Monitoring**: Prometheus + Grafana

---

## 💡 결론

**현재 시스템은**:
- ✅ 기본적인 다중 사용자 지원 (10명 이하)
- ✅ Thread-safe 세션 관리
- ✅ 워크스페이스 격리
- ⚠️ 메모리 누수 위험
- ⚠️ 확장성 제한
- ❌ Rate limiting 없음

**즉시 개선 필요**:
1. Workflow Cache 관리 (LRU + TTL)
2. Request Queue (Semaphore)
3. Rate Limiting

**이렇게 하면**:
- 현재 10명 → 50-100명 안정적 처리 가능
- 서버 크래시 방지
- 메모리 안정화
