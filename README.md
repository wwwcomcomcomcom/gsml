# GSML

llama.cpp/vLLM을 OpenAI 호환 API로 감싸 사용자에게 API Key 형태로 배포하는 사내 서비스.

## 구성

- `apps/api` — FastAPI 백엔드 (OAuth, JWT, API Key, OpenAI 프록시)
- `apps/web` — React + Vite SPA 대시보드
- `docker-compose.yml` — api + web 통합 실행 (llama-server는 외부 운영)

## 실행

```bash
cp .env.example .env
# .env 값 채우기 (OAUTH_*, JWT_SECRET, UPSTREAM_BASE_URL)
docker compose up --build
```

- 대시보드: http://localhost:5173
- API: http://localhost:8000

llama-server는 별도로 기동하고 `.env`의 `UPSTREAM_BASE_URL`로 연결한다.

## 관리자

관리자 UI 없음. DB에 직접 접근해 사용자별 `usage_limit`, `max_concurrent` 조절:

```bash
sqlite3 data/gsml.db
> UPDATE users SET usage_limit = 1000000 WHERE email = 'foo@gsm.hs.kr';
```

## 스펙

전체 설계는 `C:\Users\user\.claude\plans\drifting-squishing-storm.md` 참고.
