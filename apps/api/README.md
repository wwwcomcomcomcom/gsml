# gsml-api

FastAPI 기반 OpenAI 호환 프록시 + 대시보드 백엔드.

## 로컬 실행

```bash
cd apps/api
pip install -e .
uvicorn app.main:app --reload
```

환경 변수는 레포 루트의 `.env` 참조.

## 주요 모듈

| 파일 | 역할 |
|---|---|
| `app/main.py` | FastAPI 앱, lifespan에서 `init_db` + `catch_up_resets` + 스케줄러 |
| `app/config.py` | pydantic-settings, 모든 기본값은 ENV에서 |
| `app/models.py` | User / ApiKey / RequestLog |
| `app/deps.py` | JWT 인증, API Key 인증 |
| `app/security.py` | JWT, API Key 생성/해시 (SHA-256) |
| `app/concurrency.py` | 유저별 `asyncio.Semaphore` 딕셔너리 |
| `app/scheduler.py` | 매일 자정 리셋 + 로그 purge |
| `app/errors.py` | OpenAI 표준 에러 포맷 |
| `app/routers/openai_proxy.py` | `/v1/models`, `/v1/chat/completions` 프록시 |
| `app/upstream/__init__.py` | 업스트림 라우팅 레지스트리 (dict 기반) |
| `app/upstream/token_count.py` | usage 폴백 tiktoken 카운터 |

---

## 확장 지점

설계 상 명확히 비워둔 부분. 필요 시점에 다음을 수정하라.

### 1. llama.cpp → vLLM 교체

둘 다 OpenAI 호환 스키마를 제공하므로 `.env`의 `UPSTREAM_BASE_URL`만 교체하면
된다. 코드 수정 불필요.

### 2. 멀티 모델 서빙

현재 `app/upstream/__init__.py`는 단일 `DEFAULT_UPSTREAM`만 사용한다. 하지만
`UPSTREAMS: dict[str, UpstreamConfig]` 구조가 이미 존재하므로, 새 모델을 추가할
때는 다음 한 줄만 추가하면 라우팅이 자동으로 동작한다.

```python
from .config import settings
UPSTREAMS["llama3-70b"] = UpstreamConfig(base_url="http://llama-70b:8080")
UPSTREAMS["qwen2-7b"] = UpstreamConfig(base_url="http://qwen2:8080")
```

`openai_proxy.chat_completions`는 이미 `resolve(body["model"])`을 호출한다.
`/v1/models` 응답을 업스트림들로부터 머지하려면 `list_models` 핸들러에서 각
업스트림에 병렬로 호출 후 `data` 배열을 concat하면 된다 (현재는 단일 업스트림
응답을 그대로 프록시).

### 3. 멀티 프로세스 / 수평 확장

`app/concurrency.py`는 프로세스 내 in-memory 세마포를 쓰므로 uvicorn worker가
2개 이상이면 동시 요청 제한이 **프로세스별**로 집계된다. 수평 확장이 필요하면:

1. Redis를 추가하고
2. `acquire_slot`을 Redis Lua (INCR + expire) 기반 카운터로 교체
3. 리셋/로그 purge 스케줄러는 한 워커에서만 실행되도록 leader election 도입

### 4. 관리자 UI/API

현재는 DB 직접 접근만 지원. `users` 테이블에 `is_admin` bool 추가 + `/api/admin/*`
라우터 + `is_admin` 요구 dependency가 1단계 구현 방안. 현재는 필드를 추가하지
**않는다** (YAGNI).

### 5. API Key 다수 발급

현재 `api_keys.user_id`에 unique 제약이 있어 1계정 1키. unique 제거 + label
필드 추가 + 사용자 UI 리스트화가 필요.

---

## 운영 수기 (관리자)

```bash
sqlite3 data/gsml.db

# 사용량 한도 상향
UPDATE users SET usage_limit = 1000000 WHERE email = 'vip@gsm.hs.kr';

# 동시 요청 수 조절
UPDATE users SET max_concurrent = 5 WHERE email = 'vip@gsm.hs.kr';

# 강제 리셋
UPDATE users SET current_usage = 0 WHERE id = '...';

# 특정 유저 키 즉시 무효화
DELETE FROM api_keys WHERE user_id = (SELECT id FROM users WHERE email = '...');
```
