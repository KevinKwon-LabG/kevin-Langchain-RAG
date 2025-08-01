# RAG (Retrieval-Augmented Generation) 기능

이 프로젝트는 `static/RAG` 디렉토리에 있는 문서들을 참고하여 AI 모델이 더 정확하고 관련성 높은 응답을 생성할 수 있도록 **하이브리드 RAG 기능**을 제공합니다.

## 🚀 주요 기능

### 1. **하이브리드 응답 시스템** ⭐ NEW
- RAG 데이터와 일반 지식을 적절히 조합한 응답 생성
- 컨텍스트 품질에 따른 자동 응답 전략 선택
- RAG 데이터에 과도하게 의존하지 않는 균형잡힌 응답

### 2. **지능형 컨텍스트 품질 평가**
- 컨텍스트 길이와 유사도 점수 기반 품질 평가
- 고품질/중간품질/낮은품질에 따른 차별화된 응답 전략
- 최소 컨텍스트 길이 임계값 설정

### 3. **개선된 유사도 필터링**
- 유사도 임계값 상향 조정 (0.3 → 0.5)
- 평균 유사도 점수 계산 및 로깅
- 관련성 낮은 문서 자동 제외

### 4. **동적 설정 관리**
- 실시간 RAG 설정 업데이트
- 유사도 임계값, 컨텍스트 가중치, 최소 길이 조정
- 설정 변경 시 즉시 적용

### 5. **자동 문서 로드**
- `static/RAG` 디렉토리의 모든 문서를 자동으로 벡터 저장소에 로드
- 지원 파일 형식: PDF, TXT, DOCX, MD, XLSX, XLS
- 중복 로드 방지 기능

## 📁 디렉토리 구조

```
static/
└── RAG/
    ├── 한국주식종목데이터.xlsx
    ├── 기타문서.pdf
    └── ...
```

## 🔧 설정

### 임베딩 모델
- **KURE (Korea University Retrieval Embedding)**: 한국어에 특화된 고성능 임베딩 모델
- 모델명: `BM-K/KURE`
- 한국어 문서 검색 및 유사도 계산에 최적화
- 다국어 지원 (한국어 우선)

### 기본 설정
- RAG 기능은 기본적으로 활성화되어 있습니다
- 기본 검색 문서 수: 5개
- **개선된 유사도 임계값: 0.5** (기존 0.3에서 상향)
- **컨텍스트 가중치: 0.7**
- **최소 컨텍스트 길이: 50 문자**

### 환경 변수 설정
```bash
# RAG 관련 설정
DEFAULT_USE_RAG=true
DEFAULT_TOP_K_DOCUMENTS=5
DEFAULT_SIMILARITY_THRESHOLD=0.5
```

## 📡 API 엔드포인트

### 1. 채팅 (하이브리드 RAG 통합)
```http
POST /api/chat
```

**요청 예시:**
```json
{
  "model": "gemma3:12b-it-qat",
  "message": "삼성전자에 대해 알려주세요",
  "session_id": "session_123",
  "use_rag": true,
  "rag_top_k": 5,
  "system": "당신은 도움이 되는 한국어 어시스턴트입니다."
}
```

**응답 전략:**
- **고품질 컨텍스트**: RAG 중심 응답 (500자 이상)
- **중간 품질 컨텍스트**: 하이브리드 응답 (50-500자)
- **낮은 품질/없음**: 일반 AI 응답 (50자 미만)

### 2. RAG 설정 조회 ⭐ NEW
```http
GET /api/chat/rag/settings
```

**응답 예시:**
```json
{
  "status": "success",
  "settings": {
    "similarity_threshold": 0.5,
    "context_weight": 0.7,
    "min_context_length": 50
  },
  "description": {
    "similarity_threshold": "유사도 임계값 (0.0 ~ 1.0) - 높을수록 더 관련성 높은 문서만 포함",
    "context_weight": "컨텍스트 가중치 (0.0 ~ 1.0) - RAG 데이터의 중요도",
    "min_context_length": "최소 컨텍스트 길이 (문자 수) - 이보다 짧으면 일반 응답으로 폴백"
  }
}
```

### 3. RAG 설정 업데이트 ⭐ NEW
```http
PUT /api/chat/rag/settings
```

**요청 예시:**
```bash
curl -X PUT "http://localhost:11040/api/chat/rag/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "similarity_threshold": 0.6,
    "context_weight": 0.8,
    "min_context_length": 100
  }'
```

**응답 예시:**
```json
{
  "status": "success",
  "message": "설정이 성공적으로 업데이트되었습니다.",
  "current_settings": {
    "similarity_threshold": 0.6,
    "context_weight": 0.8,
    "min_context_length": 100
  }
}
```

### 4. RAG 상태 조회
```http
GET /api/chat/rag/status
```

**응답 예시:**
```json
{
  "status": "active",
  "total_documents": 150,
  "rag_documents": 25,
  "rag_directory": "static/RAG",
  "vectorstore_status": "active (150 documents)",
  "settings": {
    "similarity_threshold": 0.5,
    "context_weight": 0.7,
    "min_context_length": 50
  }
}
```

### 5. RAG 문서 재로드
```http
POST /api/chat/rag/reload
```

**응답 예시:**
```json
{
  "status": "success",
  "message": "RAG 문서가 성공적으로 재로드되었습니다.",
  "total_documents": 150,
  "rag_documents": 25
}
```

### 6. 헬스 체크 (RAG 상태 포함)
```http
GET /api/chat/health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "ollama_server": "connected",
  "session_stats": {...},
  "rag_status": {
    "status": "active",
    "total_documents": 150,
    "rag_documents": 25,
    "settings": {
      "similarity_threshold": 0.5,
      "context_weight": 0.7,
      "min_context_length": 50
    }
  }
}
```

## 🧪 테스트

### RAG 서비스 테스트
```bash
python test_rag_service.py
```

이 스크립트는 다음을 테스트합니다:
1. RAG 서비스 초기화
2. 문서 검색 기능
3. 하이브리드 응답 생성 기능
4. 컨텍스트 품질 평가
5. 설정 업데이트 기능

## 📊 사용 예시

### 1. 주식 정보 질문 (고품질 컨텍스트)
```
사용자: "삼성전자 주가 정보를 알려주세요"
AI: [한국주식종목데이터.xlsx에서 삼성전자 관련 정보를 우선 참고하고, 
     일반적인 주식 지식으로 보완하여 응답]
```

### 2. 시장 분석 질문 (중간 품질 컨텍스트)
```
사용자: "KOSPI 상위 종목은 무엇인가요?"
AI: [주식 데이터에서 시가총액 기준 상위 종목 정보를 참고하되, 
     일반적인 시장 지식과 조합하여 응답]
```

### 3. 일반 질문 (낮은 품질 컨텍스트)
```
사용자: "파이썬 프로그래밍에 대해 알려주세요"
AI: [RAG 컨텍스트가 부족하므로 일반 AI 지식으로 응답]
```

### 4. RAG 비활성화
```json
{
  "message": "파이썬 프로그래밍에 대해 알려주세요",
  "use_rag": false
}
```

## 🔍 고급 설정

### 1. 검색 파라미터 조정
```python
# 더 많은 문서 검색
hybrid_response = rag_service.generate_hybrid_response(
    query="질문",
    model="gemma3:12b-it-qat",
    top_k=10  # 기본값: 5
)
```

### 2. 유사도 임계값 조정
```bash
# API를 통한 실시간 조정
curl -X PUT "http://localhost:11040/api/chat/rag/settings" \
  -H "Content-Type: application/json" \
  -d '{"similarity_threshold": 0.7}'
```

### 3. 컨텍스트 가중치 조정
```bash
# RAG 데이터의 중요도 조정
curl -X PUT "http://localhost:11040/api/chat/rag/settings" \
  -H "Content-Type: application/json" \
  -d '{"context_weight": 0.9}'
```

### 4. 최소 컨텍스트 길이 조정
```bash
# 더 짧은 컨텍스트도 허용
curl -X PUT "http://localhost:11040/api/chat/rag/settings" \
  -H "Content-Type: application/json" \
  -d '{"min_context_length": 30}'
```

## 🛠️ 문제 해결

### 1. 문서가 로드되지 않는 경우
```bash
# RAG 문서 재로드
curl -X POST http://localhost:11040/api/chat/rag/reload
```

### 2. 검색 결과가 없는 경우
- 문서 내용 확인
- 검색어 변경
- 유사도 임계값 하향 조정
```bash
curl -X PUT "http://localhost:11040/api/chat/rag/settings" \
  -d '{"similarity_threshold": 0.3}'
```

### 3. RAG 데이터에 과도하게 의존하는 경우
- 유사도 임계값 상향 조정
- 컨텍스트 가중치 하향 조정
- 최소 컨텍스트 길이 상향 조정
```bash
curl -X PUT "http://localhost:11040/api/chat/rag/settings" \
  -d '{
    "similarity_threshold": 0.7,
    "context_weight": 0.5,
    "min_context_length": 100
  }'
```

### 4. 응답 품질 개선
- 더 많은 문서 추가
- top_k 값 증가
- 시스템 프롬프트 최적화

## 📈 성능 최적화

### 1. 벡터 저장소 최적화
- 청크 크기 조정 (기본값: 1000)
- 청크 오버랩 조정 (기본값: 200)
- 임베딩 모델 변경

### 2. 검색 최적화
- 적절한 top_k 값 설정
- 유사도 임계값 조정
- 메타데이터 필터링 활용

### 3. 응답 품질 최적화
- 컨텍스트 품질 평가 임계값 조정
- 하이브리드 응답 전략 세분화
- 폴백 메커니즘 개선

## 🔒 보안 고려사항

1. **문서 접근 제어**: RAG 디렉토리의 문서는 공개적으로 접근 가능
2. **API 보안**: 프로덕션 환경에서는 적절한 인증/인가 구현 필요
3. **데이터 보호**: 민감한 정보가 포함된 문서는 RAG 디렉토리에 배치하지 않음
4. **설정 보안**: 설정 업데이트 API에 대한 접근 제어 필요

## 📝 로그 모니터링

RAG 관련 로그는 다음에서 확인할 수 있습니다:
- 콘솔 출력 (디버그 모드)
- `app_debug.log` 파일
- 로그 레벨: INFO, DEBUG

**주요 로그 메시지:**
- `하이브리드 응답 생성 시작`
- `고품질 컨텍스트 발견 - RAG 중심 응답 생성`
- `중간 품질 컨텍스트 발견 - 하이브리드 응답 생성`
- `컨텍스트 없음 또는 낮은 품질 - 일반 응답 생성`
- `컨텍스트 검색 완료 - X개 문서, 평균 유사도: X.XXX`

## 🤝 기여하기

RAG 기능 개선을 위한 제안사항:
1. 새로운 문서 형식 지원
2. 검색 알고리즘 개선
3. 응답 품질 향상
4. 성능 최적화
5. 하이브리드 응답 전략 개선

## 🔄 변경 사항

### v2.0 (최신)
- ✅ 하이브리드 응답 시스템 도입
- ✅ 컨텍스트 품질 평가 시스템
- ✅ 유사도 임계값 상향 조정 (0.3 → 0.5)
- ✅ 동적 설정 관리 API 추가
- ✅ 개선된 프롬프트 템플릿
- ✅ 자동 폴백 메커니즘

### v1.0 (이전)
- 기본 RAG 기능
- 고정된 설정값
- 단순한 컨텍스트 검색

---

**참고**: 이 RAG 기능은 `static/RAG` 디렉토리의 문서를 기반으로 작동합니다. 새로운 문서를 추가하려면 해당 디렉토리에 파일을 배치하고 재로드 API를 호출하세요. 하이브리드 시스템을 통해 RAG 데이터와 일반 지식의 균형잡힌 응답을 제공합니다. 