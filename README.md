# Ollama 대화형 인터페이스

FastAPI 기반의 Ollama 대화형 인터페이스 애플리케이션입니다. 날씨 정보, 웹 검색, 파일 시스템, 데이터베이스 통합 서비스를 제공하며, RAG(Retrieval-Augmented Generation) 기능을 포함합니다.

## ✨ 최근 개선사항 (2024년 8월)

- 🔒 **보안 강화**: CORS 설정 개선 및 에러 메시지 보안 강화
- 📝 **로깅 최적화**: 로그 파일 로테이션 및 크기 제한 적용
- 🧹 **코드 정리**: 불필요한 코드 제거 및 예외 처리 개선
- ⚡ **성능 향상**: 로깅 미들웨어 최적화 및 메모리 사용량 개선
- 📦 **의존성 관리**: 패키지 버전 최적화 및 불필요한 의존성 제거

## 🏗️ 프로젝트 구조

```
ollama/
├── 📁 src/                          # 소스 코드 메인 디렉토리
│   ├── 📁 api/                      # API 엔드포인트
│   │   └── 📁 endpoints/            # API 라우터들
│   │       ├── chat.py              # 채팅 기능 API (940줄)
│   │       ├── weather.py           # 날씨 서비스 API (134줄)
│   │       ├── stock.py             # 주식 서비스 API (224줄)
│   │       ├── web_search.py        # 웹 검색 서비스 API (219줄)
│   │       ├── # 의사결정 API는 현재 사용하지 않음
│   │       ├── documents.py         # 문서 관리 API (339줄)
│   │       ├── health.py            # 헬스 체크 API (201줄)
│   │       ├── models.py            # 모델 관리 API (117줄)
│   │       ├── sessions.py          # 세션 관리 API (152줄)
│   │       └── settings.py          # 설정 관리 API (167줄)
│   ├── 📁 config/                   # 설정 관리
│   │   └── settings.py              # 애플리케이션 설정 (422줄)
│   ├── 📁 models/                   # 데이터 모델
│   │   └── schemas.py               # Pydantic 스키마 (85줄)
│   ├── 📁 services/                 # 비즈니스 로직 서비스
│   │   ├── weather_service.py       # 날씨 서비스 (119줄)
│   │   ├── stock_service.py         # 주식 서비스 (217줄)
│   │   ├── web_search_service.py    # 웹 검색 서비스 (251줄)
│   │   ├── document_service.py      # 문서 처리 서비스 (321줄)
│   │   ├── # LangChain 의사결정 서비스는 현재 사용하지 않음
│   │   ├── mcp_client_service.py    # MCP 클라이언트 서비스 (1513줄)
│   │   ├── rag_service.py           # RAG 서비스 (420줄)
│   │   └── session_service.py       # 세션 관리 서비스 (160줄)
│   ├── 📁 utils/                    # 유틸리티
│   │   └── session_manager.py       # 세션 관리 유틸리티 (220줄)
│   └── main.py                      # FastAPI 메인 애플리케이션 (161줄)
├── 📁 templates/                    # HTML 템플릿
│   └── app.html                     # 메인 웹 인터페이스 (2443줄)
├── 📁 static/                       # 정적 파일
│   └── 📁 RAG/                      # RAG 문서 저장소
│       ├── 2024년도_2학기_빅데이터 저장시스템 및 응용_강의계획서.pdf
│       └── 한국주식종목데이터.xlsx
├── 📁 data/                         # 데이터 저장소
│   ├── 📁 vectorstore/              # 벡터 데이터베이스 (ChromaDB)
│   └── 📁 documents/                # 업로드된 문서 저장소
├── 📁 scripts/                      # 유틸리티 스크립트
│   ├── setup_env.py                 # 환경 설정 스크립트 (338줄)
│   └── update_embedding_model.py    # 임베딩 모델 업데이트 스크립트 (111줄)
├── 📁 docs/                         # 문서화
│   ├── README_CONTEXT_MANAGEMENT.md # 컨텍스트 관리 문서
│   ├── README_DECISION_SERVICE.md   # 의사결정 서비스 문서
│   ├── README_RAG.md                # RAG 시스템 문서
│   ├── README_WEATHER_SYSTEM.md     # 날씨 시스템 문서
│   └── 주요 Logic 및 Flow.md        # 주요 로직 및 플로우 문서
├── 📁 logs/                         # 로그 파일
│   ├── mcp_client.log               # MCP 클라이언트 로그
│   ├── weather_test.log             # 날씨 테스트 로그
│   └── mcp_server.log               # MCP 서버 로그
├── app.py                           # 메인 실행 파일 (257줄)
├── requirements.txt                 # Python 의존성 (35개 패키지)
├── env.settings                     # 환경 설정 파일 (153줄)
├── .gitignore                       # Git 제외 파일 설정 (245줄)
└── app_debug.log                    # 디버그 로그 파일
```

## 🚀 주요 기능

### 1. **채팅 인터페이스** (`src/api/endpoints/chat.py`)
- Ollama 모델과의 실시간 대화
- 스트리밍 응답 지원
- 세션 기반 대화 관리
- 컨텍스트 유지 및 메모리 관리

### 2. **RAG 시스템** (`src/services/rag_service.py`)
- 문서 업로드 및 벡터화
- 의미 기반 문서 검색
- ChromaDB 벡터 데이터베이스 활용
- 한국어 특화 임베딩 모델 (KURE) 사용

### 3. **문서 관리 서비스** (`src/services/document_service.py`)
- 다양한 문서 형식 지원 (PDF, DOCX, Excel, TXT)
- 문서 업로드 및 벡터화
- 문서 검색 및 관리

### 4. **MCP 클라이언트** (`src/services/mcp_client_service.py`)
- Model Context Protocol 지원
- 외부 서비스 통합
- 확장 가능한 플러그인 아키텍처

### 5. **워드 임베딩 서비스** (`src/services/word_embedding_service.py`)
- 워드 문서 RAG 워크플로우 처리
- 텍스트 추출: python-docx로 워드 문서에서 텍스트 추출
- 전처리: 텍스트 정제 및 한국어 형태소 분석 (KoNLPy - Okt, Mecab, Komoran)
- 문서 분할: 100~500 토큰 단위로 분할
- 임베딩 생성: Sentence Transformers로 문서 청크 임베딩
- 벡터 검색: 유사한 문서 청크 검색

### 6. **날씨 서비스** (`src/services/weather_service.py`)
- 날씨 정보 조회 및 예보
- MCP 서버를 통한 날씨 도구 연동
- 지역별, 시간별 날씨 정보 제공

### 6. **주식 서비스** (`src/services/stock_service.py`)
- 한국 주식 시장 데이터 제공
- 실시간 주식 정보 조회
- 섹터별 주식 목록 및 검색

### 7. **웹 검색 서비스** (`src/services/web_search_service.py`)
- 웹 검색 기능 제공
- DuckDuckGo API 연동
- 검색 결과 포맷팅 및 요약

## 🛠️ 기술 스택

### **백엔드**
- **FastAPI**: 고성능 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 직렬화

### **AI/ML**
- **LangChain**: LLM 애플리케이션 프레임워크
- **ChromaDB**: 벡터 데이터베이스
- **Sentence Transformers**: 임베딩 모델
- **Ollama**: 로컬 LLM 실행

### **문서 처리**
- **PyPDF**: PDF 파일 처리 (고품질 텍스트 전처리)
- **python-docx**: Word 문서 처리
- **docx2txt**: 텍스트 추출
- **Tiktoken**: 토큰화

### **개발 도구**
- **Pytest**: 테스트 프레임워크
- **Jinja2**: 템플릿 엔진
- **Requests/Aiohttp**: HTTP 클라이언트

## 📋 API 엔드포인트

### **채팅 관련**
- `POST /api/chat/` - 새로운 채팅 시작 (스트리밍 응답)
- `POST /api/chat/analyze-request` - 요청 분석 및 분류

### **날씨 서비스**
- `POST /api/weather/` - 날씨 정보 요청
- `POST /api/weather/params` - 날씨 파라미터 추출
- `GET /api/weather/info` - 날씨 서비스 정보

### **주식 서비스**
- `POST /api/stock/` - 주식 정보 요청
- `POST /api/stock/params` - 주식 파라미터 추출
- `GET /api/stock/info` - 주식 서비스 정보
- `GET /api/stock/stocks` - 지원 주식 목록
- `GET /api/stock/sectors` - 지원 섹터 목록
- `GET /api/stock/sectors/{sector}` - 섹터별 주식 목록

### **웹 검색 서비스**
- `POST /api/web-search/` - 웹 검색 요청
- `POST /api/web-search/extract-query` - 검색어 추출
- `POST /api/web-search/search` - 직접 웹 검색 수행
- `GET /api/web-search/info` - 웹 검색 서비스 정보
- `GET /api/web-search/engines` - 지원 검색 엔진 목록

> **⚠️ 주의**: 기존 `/api/chat/weather`, `/api/chat/stock` 등은 더 이상 사용하지 않습니다. 새로운 서비스별 엔드포인트를 사용하세요.

### **세션 관리**
- `POST /api/sessions` - 새 세션 생성
- `GET /api/sessions` - 세션 목록 조회
- `DELETE /api/sessions/{session_id}` - 세션 삭제
- `PUT /api/sessions/{session_id}/title` - 세션 제목 업데이트

### **워드 임베딩**
- `POST /api/word-embedding/upload` - 워드 문서 업로드 및 임베딩 처리
- `POST /api/word-embedding/search` - 유사한 문서 청크 검색
- `GET /api/word-embedding/search` - 검색 (GET 방식)
- `GET /api/word-embedding/stats` - 벡터 DB 통계 조회
- `DELETE /api/word-embedding/collection` - 벡터 DB 컬렉션 초기화
- `GET /api/word-embedding/health` - 서비스 상태 확인

### **문서 관리**
- `POST /api/documents/upload` - 문서 업로드
- `GET /api/documents` - 문서 목록 조회
- `DELETE /api/documents/{filename}` - 문서 삭제

### **모델 관리**
- `GET /api/models` - 사용 가능한 모델 목록
- `GET /api/models/{model_name}` - 모델 상세 정보

### **시스템 관리**
- `GET /api/health` - 시스템 상태 확인
- `GET /api/settings` - 설정 조회
- `POST /api/settings/reload` - 설정 리로드

## 🔧 설정

### **환경 변수** (`env.settings`)

#### **Chroma DB 설정**
- `CHROMA_MODE`: Chroma DB 모드 (`local` 또는 `http`)
- `CHROMA_PERSIST_DIRECTORY`: 로컬 저장 경로 (기본값: `data/vectorstore`)
- `CHROMA_HOST`: 외부 서버 호스트 (기본값: `localhost`)
- `CHROMA_PORT`: 외부 서버 포트 (기본값: `8000`)
- `CHROMA_USERNAME`: 인증 사용자명 (선택사항)
- `CHROMA_PASSWORD`: 인증 비밀번호 (선택사항)
- `CHROMA_SSL`: SSL 사용 여부 (기본값: `false`)
- `CHROMA_COLLECTION_NAME`: 컬렉션 이름 (기본값: `documents`)

#### **임베딩 설정**
- `EMBEDDING_MODEL_NAME`: 임베딩 모델명 (기본값: `nlpai-lab/KURE-v1`)
- `EMBEDDING_DEVICE`: 임베딩 디바이스 (기본값: `cpu`)
- `HUGGINGFACE_API_KEY`: HuggingFace API 키 (선택사항)

#### **Ollama 설정**
- `OLLAMA_BASE_URL`: Ollama 서버 URL

### **주요 설정**
- **임베딩 모델**: nlpai-lab/KURE-v1 (한국어 특화)
- **벡터 DB**: ChromaDB (로컬 또는 외부 서버)
- **문서 청크 크기**: 1000 토큰
- **청크 오버랩**: 200 토큰
- **워드 임베딩**: 
  - 청크 크기: 300 토큰 (기본값)
  - 청크 오버랩: 50 토큰 (기본값)
  - 형태소 분석기: Okt, Mecab, Komoran
  - 임베딩 모델: sentence-transformers/xlm-r-100langs-bert-base-nli-stsb-mean-tokens

## 🚀 실행 방법

### **1. 의존성 설치**
```bash
pip install -r requirements.txt
```

**한국어 NLP 라이브러리 설치 (선택사항)**
```bash
# KoNLPy 설치 (한국어 형태소 분석)
pip install konlpy

# Mecab 설치 (Ubuntu/Debian)
sudo apt-get install mecab mecab-ipadic-utf8 mecab-ko mecab-ko-dic

# Mecab 설치 (macOS)
brew install mecab mecab-ko mecab-ko-dic

# Windows의 경우 Mecab 대신 Okt 사용 권장
```

### **2. 환경 설정**
```bash
python scripts/setup_env.py
```

### **3. 애플리케이션 실행**
```bash
# 개발 모드
python app.py --debug

# 프로덕션 모드
python app.py
```

### **4. Chroma DB 설정 (선택사항)**

#### **로컬 Chroma DB 사용 (기본값)**
```bash
# env.settings 파일에서 설정
CHROMA_MODE=local
CHROMA_PERSIST_DIRECTORY=data/vectorstore
```

#### **외부 Chroma DB 서버 사용**
```bash
# env.settings 파일에서 설정
CHROMA_MODE=http
CHROMA_HOST=your-chroma-server.com
CHROMA_PORT=8000
CHROMA_USERNAME=your_username
CHROMA_PASSWORD=your_password
CHROMA_SSL=true
```

#### **Docker로 Chroma DB 실행**
```bash
# Chroma DB 서버 실행
docker run -p 8000:8000 chromadb/chroma

# 환경 변수 설정
export CHROMA_MODE=http
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
```

### **5. 웹 인터페이스 접속**
- URL: `http://1.237.52.240:11040`
- API 문서: `http://1.237.52.240:11040/docs`

## 📊 데이터 구조

### **벡터 저장소** (`data/vectorstore/`)
- ChromaDB 기반 벡터 데이터베이스
- 문서 임베딩 및 메타데이터 저장
- 의미 기반 검색 지원

### **문서 저장소** (`static/RAG/`)
- PDF, Word, Excel, Markdown 파일 지원
- 자동 텍스트 추출 및 청킹
- 벡터화를 통한 지식 베이스 구축

## 🧪 테스트

### **Chroma DB 설정 테스트**
```bash
# Chroma DB 연결 및 설정 테스트
python scripts/test_chroma_config.py
```

### **MCP 로깅 테스트**
```bash
# MCP 도구 호출 및 응답 로깅 테스트
python scripts/test_mcp_logging.py
```

### **워드 임베딩 테스트**
```bash
# 워드 임베딩 기능 테스트
python test_word_embedding.py
```

### **API 테스트**
```bash
# 서버 실행 후 API 테스트
curl -X GET "http://1.237.52.240:11040/api/word-embedding/health"
curl -X GET "http://1.237.52.240:11040/api/word-embedding/stats"
```

## 🔍 모니터링 및 로깅

### **로그 파일**
- `app_debug.log`: 애플리케이션 디버그 로그
- `logs/mcp_client.log`: MCP 클라이언트 로그
- `logs/weather_test.log`: 날씨 서비스 테스트 로그

### **MCP 로깅 기능**
MCP 도구 사용 시 다음 정보가 로그에 기록됩니다:

#### **로그 형식**
- `[MCP 사용 결정]`: MCP 서비스 사용 여부 결정 과정
- `[MCP 도구 호출]`: MCP 도구 호출 시 파라미터 (앞 100자)
- `[MCP 도구 응답]`: MCP 도구 응답 (앞 20자)
- `[MCP 키워드 매칭]`: 키워드 기반 매칭 결과
- `[MCP AI 결정]`: AI 기반 결정 과정

#### **예시 로그**
```
[MCP 사용 결정] 결정 방식: keyword, 질문: 서울 날씨 어때?...
[MCP 키워드 매칭] 날씨 키워드 발견: ['날씨']
[MCP 날씨 요청] 사용자 프롬프트: 서울 날씨 어때?...
[MCP 도구 호출] 도구: get_current_weather, 파라미터: {"city": "서울"}...
[MCP 도구 응답] 도구: get_current_weather, 응답: {"success": true, "result":...
```

### **헬스 체크**
- 시스템 상태 모니터링
- 서비스 가용성 확인
- 성능 메트릭 수집

## 🧪 테스트

### **테스트 실행**
```bash
pytest tests/
```

### **테스트 커버리지**
```bash
pytest --cov=src tests/
```

## 📚 추가 문서

- [서비스 분리 아키텍처](docs/README_SERVICE_ARCHITECTURE.md) - 새로운 서비스 분리 구조 설명
- [RAG 시스템 가이드](docs/README_RAG.md)
- [의사결정 서비스 문서](docs/README_DECISION_SERVICE.md)
- [날씨 시스템 문서](docs/README_WEATHER_SYSTEM.md)
- [컨텍스트 관리 가이드](docs/README_CONTEXT_MANAGEMENT.md)

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

**개발자**: Ollama 대화형 인터페이스 팀  
**버전**: 1.0.0  
**최종 업데이트**: 2024년 12월 