# Ollama Web Interface - FastAPI 버전

Flask 기반 Ollama 웹 인터페이스를 FastAPI로 변환한 버전입니다.

## 🚀 주요 변경사항

### Flask → FastAPI 변환
- **Flask** → **FastAPI**: 더 빠른 성능과 자동 API 문서화
- **Flask-CORS** → **FastAPI CORS Middleware**: 내장 CORS 지원
- **Flask Blueprint** → **FastAPI Router**: 모듈화된 라우팅
- **Flask Response** → **FastAPI Response**: 타입 안전성 향상

### 새로운 기능
- **자동 API 문서화**: `/docs` (Swagger UI) 및 `/redoc` (ReDoc)
- **Pydantic 모델**: 요청/응답 데이터 검증
- **비동기 지원**: `async/await` 패턴으로 성능 향상
- **타입 힌트**: 더 나은 개발자 경험

## 📁 파일 구조

```
├── main_fastapi.py          # 메인 FastAPI 애플리케이션
├── fastapi_app.py           # Ollama 앱 전용 FastAPI 서버
├── ask_gemma_router.py      # Ask Gemma 라우터
├── requirements.txt         # 필요한 패키지 목록
├── templates/               # HTML 템플릿
│   ├── main.html
│   ├── ollama-app.html
│   └── ask_Gemma.html
└── static/                  # 정적 파일
    └── uploads/
```

## 🛠️ 설치 및 실행

### 1. 가상 환경 활성화
```bash
conda activate ollama
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 서버 실행

#### 메인 애플리케이션 (모든 기능 포함)
```bash
uvicorn main_fastapi:app --host 0.0.0.0 --port 11010 --reload
```

#### Ollama 앱 전용 서버
```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 11030 --reload
```

## 🌐 접속 주소

- **메인 페이지**: http://localhost:11010/
- **Ollama 앱**: http://localhost:11010/ollama-app
- **Ask Gemma**: http://localhost:11010/ask_Gemma/
- **API 문서**: http://localhost:11010/docs
- **ReDoc 문서**: http://localhost:11010/redoc

## 📚 API 엔드포인트

### 모델 관련
- `GET /api/models` - 사용 가능한 모델 목록
- `GET /api/health` - 서버 및 Ollama 연결 상태

### 생성 관련
- `POST /api/generate` - 스트리밍 응답 생성
- `POST /api/generate-simple` - 단순 응답 생성

### Ask Gemma
- `GET /ask_Gemma/` - Ask Gemma 페이지
- `POST /ask_Gemma/` - Gemma 모델에 질문

## 🔧 설정

### Ollama 서버 설정
`main_fastapi.py` 또는 `fastapi_app.py`에서 다음 설정을 수정할 수 있습니다:

```python
OLLAMA_BASE_URL = "http://1.237.52.240:11434"
```

### 사용 가능한 모델
```python
AVAILABLE_MODELS = [
    {"name": "deepseek-v2:16b-lite-chat-q8_0", "size": "16 GB", "id": "1d62ef756269"},
    {"name": "qwen3:14b-q8_0", "size": "15 GB", "id": "304bf7349c71"},
    # ... 더 많은 모델
]
```

## 🆚 Flask vs FastAPI 비교

| 기능 | Flask | FastAPI |
|------|-------|---------|
| 성능 | 보통 | 빠름 |
| API 문서화 | 수동 | 자동 |
| 타입 검증 | 수동 | 자동 (Pydantic) |
| 비동기 지원 | 제한적 | 완전 지원 |
| CORS | Flask-CORS | 내장 |
| 라우팅 | Blueprint | Router |

## 🐛 문제 해결

### 서버가 시작되지 않는 경우
1. 포트가 사용 중인지 확인: `netstat -tlnp | grep 11010`
2. 다른 포트 사용: `--port 11011`
3. 로그 확인: 터미널 출력 확인

### Ollama 연결 실패
1. Ollama 서버가 실행 중인지 확인
2. `OLLAMA_BASE_URL` 설정 확인
3. 방화벽 설정 확인

## 📝 개발 노트

- FastAPI는 Flask보다 더 현대적이고 성능이 좋습니다
- 자동 API 문서화로 개발 및 테스트가 용이합니다
- Pydantic 모델로 데이터 검증이 강화되었습니다
- 비동기 처리로 동시 요청 처리 성능이 향상되었습니다 