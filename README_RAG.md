# Ollama RAG Interface

LangChain과 RAG(Retrieval-Augmented Generation)를 사용한 고급 Ollama 웹 인터페이스입니다.

## 🚀 주요 기능

### RAG (Retrieval-Augmented Generation)
- **문서 업로드**: PDF, TXT, DOCX, MD 파일 지원
- **벡터 검색**: ChromaDB를 사용한 의미론적 검색
- **컨텍스트 강화**: 관련 문서를 기반으로 한 정확한 답변
- **소스 추적**: 답변의 출처 문서 표시

### LangChain 통합
- **문서 처리**: 자동 청킹 및 임베딩
- **프롬프트 관리**: 템플릿 기반 프롬프트 구성
- **체인 구성**: 모듈화된 처리 파이프라인

### 대화 관리
- **세션 관리**: 대화 히스토리 유지
- **멀티 모델**: 다양한 Ollama 모델 지원
- **스트리밍**: 실시간 응답 생성

## 📁 프로젝트 구조

```
ollama-rag/
├── src/                          # 소스 코드
│   ├── api/                      # API 라우터
│   │   ├── chat_router.py        # 채팅 API
│   │   └── document_router.py    # 문서 관리 API
│   ├── config/                   # 설정
│   │   └── settings.py           # 애플리케이션 설정
│   ├── models/                   # 데이터 모델
│   │   └── schemas.py            # Pydantic 스키마
│   ├── services/                 # 비즈니스 로직
│   │   ├── document_service.py   # 문서 처리 서비스
│   │   ├── rag_service.py        # RAG 서비스
│   │   └── session_service.py    # 세션 관리 서비스
│   └── main.py                   # 메인 애플리케이션
├── data/                         # 데이터 저장소
│   ├── documents/                # 업로드된 문서
│   ├── embeddings/               # 임베딩 캐시
│   └── vectorstore/              # ChromaDB 저장소
├── templates/                    # HTML 템플릿
├── static/                       # 정적 파일
├── tests/                        # 테스트
├── docs/                         # 문서
└── scripts/                      # 유틸리티 스크립트
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

### 3. 환경 변수 설정
```bash
# 자동 설정 스크립트 실행
python scripts/setup_env.py

# 또는 수동으로 env.settings 파일 생성
# env.settings 파일을 편집하여 설정 커스터마이즈
```

### 4. 서버 실행
```bash
# 메인 애플리케이션 실행
python src/main.py

# 또는 uvicorn 사용
uvicorn src.main:app --host 0.0.0.0 --port 11040 --reload
```

## 🌐 접속 주소

- **메인 페이지**: http://localhost:11040/
- **API 문서**: http://localhost:11040/docs
- **ReDoc 문서**: http://localhost:11040/redoc

## 📚 API 엔드포인트

### 채팅 관련
- `POST /api/chat` - RAG를 사용한 대화 (스트리밍)
- `GET /api/sessions` - 세션 목록
- `GET /api/sessions/{session_id}` - 세션 상세
- `POST /api/sessions` - 새 세션 생성
- `DELETE /api/sessions/{session_id}` - 세션 삭제

### 문서 관리
- `POST /api/documents/upload` - 문서 업로드 (JSON)
- `POST /api/documents/upload-file` - 파일 업로드
- `POST /api/documents/search` - 문서 검색
- `GET /api/documents/count` - 문서 수 조회
- `DELETE /api/documents/{doc_id}` - 문서 삭제
- `GET /api/documents/status` - 문서 처리 상태

### 시스템
- `GET /api/models` - 사용 가능한 모델 목록
- `GET /api/health` - 시스템 상태 확인

## 🔧 설정

### 환경 변수 설정
프로젝트의 모든 주요 설정은 `env.settings` 파일을 통해 관리됩니다.

#### 자동 설정
```bash
python scripts/setup_env.py
```

#### 수동 설정
1. `env.settings` 파일을 직접 편집하여 설정 커스터마이즈

### 주요 설정 카테고리

#### 서버 설정
```env
HOST=0.0.0.0
PORT=11040
DEBUG=true
LOG_LEVEL=INFO
```

#### Ollama 설정
```env
OLLAMA_BASE_URL=http://1.237.52.240:11434
OLLAMA_TIMEOUT=120
OLLAMA_MAX_RETRIES=3
```

#### LLM 모델 설정
```env
DEFAULT_MODEL=gemma3:12b-it-qat
DEFAULT_TEMPERATURE=0.7
DEFAULT_TOP_P=0.9
DEFAULT_TOP_K=40
DEFAULT_REPEAT_PENALTY=1.1
```

#### RAG 설정
```env
DEFAULT_USE_RAG=true
DEFAULT_TOP_K_DOCUMENTS=5
DEFAULT_SIMILARITY_THRESHOLD=0.7
```

#### 고급 설정 범위
```env
# Temperature 범위
TEMPERATURE_MIN=0.0
TEMPERATURE_MAX=2.0
TEMPERATURE_PRESETS=0.1,0.3,0.5,0.7,0.9,1.0,1.2

# Top P 범위
TOP_P_MIN=0.1
TOP_P_MAX=1.0
TOP_P_PRESETS=0.1,0.3,0.5,0.7,0.9,1.0

# 최대 토큰 수 범위
MAX_TOKENS_MIN=100
MAX_TOKENS_MAX=8192
MAX_TOKENS_PRESETS=512,1024,2048,4096,6144,8192
```

### 설정 API
애플리케이션 실행 중에도 설정을 확인할 수 있습니다:

- `GET /api/config/` - 모든 설정
- `GET /api/config/models` - 모델 설정
- `GET /api/config/rag` - RAG 설정
- `GET /api/config/advanced-settings` - 고급 설정
- `GET /api/config/temperature-presets` - Temperature 프리셋
- `GET /api/config/top-p-presets` - Top P 프리셋
- `GET /api/config/system-prompt-templates` - 시스템 프롬프트 템플릿

## 📖 사용법

### 1. 문서 업로드
1. 웹 인터페이스에서 파일 업로드
2. 또는 API를 통해 문서 전송
3. 자동으로 청킹 및 벡터화

### 2. RAG 대화
1. 모델 선택 (gemma3:12b-it-qat 권장)
2. RAG 옵션 활성화
3. 질문 입력
4. 관련 문서 기반 답변 수신

### 3. 문서 검색
1. 검색 API를 통해 직접 문서 검색
2. 메타데이터 필터링 지원
3. 유사도 점수 제공

## 🆚 기존 버전과의 차이점

| 기능 | 기존 버전 | RAG 버전 |
|------|-----------|----------|
| 문서 처리 | ❌ | ✅ |
| 벡터 검색 | ❌ | ✅ |
| 컨텍스트 강화 | ❌ | ✅ |
| 소스 추적 | ❌ | ✅ |
| LangChain | ❌ | ✅ |
| ChromaDB | ❌ | ✅ |
| 모듈화 | 기본 | 고급 |

## 🐛 문제 해결

### 벡터 저장소 초기화 실패
```bash
# ChromaDB 데이터 삭제 후 재시작
rm -rf data/vectorstore
python src/main.py
```

### 임베딩 모델 다운로드 실패
```bash
# 수동으로 모델 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

### 메모리 부족
- `CHUNK_SIZE`를 줄이기
- `MAX_TOKENS` 조정
- 더 작은 임베딩 모델 사용

## 📝 개발 노트

- **LangChain**: 문서 처리 및 RAG 파이프라인
- **ChromaDB**: 벡터 저장소 및 검색
- **Sentence Transformers**: 임베딩 생성
- **FastAPI**: 고성능 웹 API
- **Pydantic**: 데이터 검증 및 직렬화

## 🔮 향후 계획

- [ ] 다중 벡터 저장소 지원 (Pinecone, Weaviate)
- [ ] 고급 프롬프트 템플릿
- [ ] 문서 버전 관리
- [ ] 사용자 인증 및 권한 관리
- [ ] 대시보드 및 분석 도구 