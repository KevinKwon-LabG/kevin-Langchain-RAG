# Langchain Decision Service with RAG Integration

사용자의 prompt를 분석하여 4가지 카테고리 중 하나로 분류하는 **RAG 통합 Langchain 기반 시스템**입니다.

## 🚀 주요 기능

### 1. **RAG 통합 의사결정** ⭐ NEW
- RAG 문서를 참고하여 더 정확한 질문 분류
- 관련 문서 정보를 바탕으로 한 컨텍스트 기반 분류
- 기존 분류 방식과 RAG 통합 방식 선택 가능

### 2. **하이브리드 분류 시스템**
- RAG 사용/미사용 모드 선택
- 컨텍스트 품질에 따른 분류 정확도 향상
- 메타데이터 포함 분류 결과 제공

### 3. **향상된 분류 정확도**
- RAG 컨텍스트가 있는 경우 신뢰도 자동 향상
- 관련 문서 정보를 활용한 더 정확한 카테고리 판단
- 분류 결과에 대한 상세한 메타데이터 제공

## 🎯 분류 카테고리

1. **날씨 정보 요청** → "날씨 정보를 요청하셨습니다."
2. **한국 주식 시장 종목 주가 정보 요청** → "한국 주식 시장에 상장되어 있는 종목의 주가 관련 정보를 요청하셨습니다."
3. **웹 검색 필요** → "정확한 답변을 위해서는 웹 검색이 필요합니다."
4. **바로 답변 가능** → "바로 답변드리겠습니다"

## 🚀 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. OpenAI API 키 설정
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### 3. 애플리케이션 실행
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 사용법

### 1. 웹 인터페이스 사용
브라우저에서 `http://localhost:8000/decision-test`에 접속하여 웹 인터페이스를 통해 테스트할 수 있습니다.

### 2. API 직접 호출 (RAG 통합)
```bash
# RAG 통합 분류
curl -X POST "http://localhost:8000/api/decision/classify" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "삼성전자 주가 정보를 알려주세요", "use_async": true, "use_rag": true}'

# 기존 분류 (RAG 미사용)
curl -X POST "http://localhost:8000/api/decision/classify" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "삼성전자 주가 정보를 알려주세요", "use_async": true, "use_rag": false}'
```

### 3. Python 스크립트 테스트
```bash
# RAG 통합 테스트
python test_rag_decision_service.py

# 기존 테스트
python test_decision_service.py
```

## 🔧 API 엔드포인트

### POST /api/decision/classify
사용자의 prompt를 분류합니다 (RAG 통합).

**요청 본문:**
```json
{
    "prompt": "분류할 질문",
    "use_async": true,
    "use_rag": true
}
```

**응답 (RAG 통합):**
```json
{
    "user_prompt": "분류할 질문",
    "decision_result": "분류 결과 메시지",
    "success": true,
    "error_message": null,
    "rag_metadata": {
        "use_rag": true,
        "rag_context_length": 1250,
        "rag_context_preview": "관련 문서 정보: 삼성전자 주가 데이터...",
        "model_used": "gemma3:12b-it-qat"
    }
}
```

### POST /api/chat/analyze-request
채팅 요청 분석 (RAG 통합).

**요청 본문:**
```json
{
    "model": "gemma3:12b-it-qat",
    "message": "삼성전자 주가 정보를 알려주세요",
    "session_id": "session_123",
    "use_rag_for_decision": true
}
```

**응답:**
```json
{
    "chat_request": {...},
    "analysis": {
        "decision": "STOCK_SERVICE",
        "reason": "한국 주식 시장 정보 요청으로 판단됨 (RAG 컨텍스트 참조: 1250자)",
        "confidence": 1.0,
        "service_type": "stock_service",
        "decision_result": "한국 주식 시장에 상장되어 있는 종목의 주가 관련 정보를 요청하셨습니다.",
        "recommended_action": "주식 API 서비스를 호출하여 실시간 주가 정보를 제공합니다.",
        "rag_metadata": {
            "use_rag_for_decision": true,
            "rag_context_length": 1250,
            "rag_context_preview": "관련 문서 정보: 삼성전자 주가 데이터..."
        }
    },
    "timestamp": "2024-01-01T12:00:00"
}
```

### GET /api/decision/health
서비스 상태를 확인합니다.

## 📁 프로젝트 구조

```
src/
├── services/
│   └── langchain_decision_service.py  # RAG 통합 핵심 의사결정 서비스
├── api/
│   └── decision_api.py                # RAG 통합 API 엔드포인트
├── main.py                            # FastAPI 메인 애플리케이션
templates/
└── decision_test.html                 # 웹 테스트 인터페이스
test_rag_decision_service.py           # RAG 통합 Python 테스트 스크립트
test_decision_service.py               # 기존 Python 테스트 스크립트
```

## 🧪 테스트 예시

### RAG 통합 분류 테스트
```python
# RAG 통합 분류
result_with_rag = await langchain_decision_service.classify_prompt(
    "삼성전자 주가 정보", 
    use_rag=True
)

# 메타데이터 포함 분류
metadata = await langchain_decision_service.classify_prompt_with_metadata(
    "삼성전자 주가 정보", 
    use_rag=True
)
print(f"RAG 컨텍스트 길이: {metadata['rag_context_length']}")
```

### 날씨 관련
- "오늘 서울 날씨는 어때?"
- "내일 비 올 확률은?"
- "주말 날씨 예보"

### 한국 주식 관련
- "삼성전자 주가가 어떻게 되나요?"
- "KOSPI 지수는 현재 몇 점인가요?"
- "SK하이닉스 주가 정보"

### 웹 검색 필요
- "2024년 최신 아이폰 가격은?"
- "현재 시간이 몇 시인가요?"
- "오늘 날짜는?"

### 바로 답변 가능
- "파이썬이란 무엇인가요?"
- "세계에서 가장 큰 나라는?"
- "인공지능의 정의는?"

## 🔍 분류 기준 (RAG 통합)

### 1. 날씨 관련 정보 요청
- 날씨, 기온, 강수, 날씨 예보, 기후 등과 관련된 질문
- 키워드: 날씨, 기온, 비, 눈, 맑음, 흐림, 습도, 기압 등
- **RAG 컨텍스트**: 날씨 관련 문서가 있는 경우 더 정확한 분류

### 2. 한국 주식 시장 종목 주가 정보 요청
- 한국 주식, KOSPI, KOSDAQ, 특정 종목 주가, 주식 시장 등과 관련된 질문
- 키워드: 주가, 주식, KOSPI, KOSDAQ, 삼성전자, SK하이닉스 등
- **RAG 컨텍스트**: 주식 데이터 문서가 있는 경우 높은 신뢰도로 분류

### 3. 웹 검색 필요
- 최신 정보, 실시간 데이터, 특정 사이트 정보, 현재 시점의 구체적인 정보가 필요한 질문
- 키워드: 현재, 지금, 실시간, 최신, 가격, 시간, 날짜 등
- **RAG 컨텍스트**: 관련 문서가 없는 경우 웹 검색으로 분류

### 4. 바로 답변 가능
- 일반적인 지식, 개념 설명, 역사적 사실, 공식 등 AI가 가진 정보로 답변 가능한 질문
- 키워드: 정의, 개념, 역사, 공식, 원리 등
- **RAG 컨텍스트**: 관련 문서가 있는 경우 더 상세한 답변 가능

## 🛠️ 개발자 정보

### 주요 컴포넌트

1. **LangchainDecisionService**: RAG 통합 핵심 분류 로직
   - `classify_prompt()`: RAG 통합 비동기 분류
   - `classify_prompt_sync()`: RAG 통합 동기 분류
   - `classify_prompt_with_metadata()`: 메타데이터 포함 분류
   - `_get_rag_context_for_decision()`: 의사결정용 RAG 컨텍스트 검색

2. **DecisionCategory**: 분류 카테고리 열거형
   - WEATHER, KOREAN_STOCK, WEB_SEARCH_NEEDED, DIRECT_ANSWER

3. **RAG 통합 프롬프트 템플릿**
   - `decision_prompt_with_rag`: RAG 컨텍스트를 포함한 분류 프롬프트
   - `decision_prompt`: 기존 분류 프롬프트

4. **API 엔드포인트**: RESTful API 제공
   - POST /api/decision/classify (RAG 통합)
   - POST /api/chat/analyze-request (RAG 통합)
   - GET /api/decision/health

### RAG 통합 작동 방식

1. **컨텍스트 검색**: 사용자 질문과 관련된 RAG 문서 검색
2. **프롬프트 구성**: RAG 컨텍스트를 포함한 분류 프롬프트 생성
3. **AI 분류**: 컨텍스트를 고려한 정확한 카테고리 분류
4. **신뢰도 조정**: RAG 컨텍스트가 있는 경우 신뢰도 향상
5. **메타데이터 제공**: 분류 과정의 상세 정보 제공

### 확장 가능성

- 새로운 분류 카테고리 추가
- RAG 컨텍스트 품질 평가 시스템
- 분류 정확도 향상을 위한 프롬프트 최적화
- 다양한 AI 모델 지원 (Ollama, Anthropic 등)
- 분류 결과 로깅 및 분석 기능
- 실시간 RAG 문서 업데이트 반영

## 📈 성능 최적화

### 1. RAG 컨텍스트 최적화
- 의사결정용 컨텍스트 검색 파라미터 조정
- 컨텍스트 길이 및 품질 임계값 설정
- 검색 결과 캐싱 기능

### 2. 분류 정확도 향상
- RAG 컨텍스트 품질에 따른 가중치 조정
- 분류 신뢰도 계산 알고리즘 개선
- 오류 케이스 분석 및 개선

### 3. 응답 속도 최적화
- 비동기 처리 최적화
- RAG 검색 병렬 처리
- 결과 캐싱 메커니즘

## 🔒 보안 고려사항

1. **RAG 문서 접근 제어**: 의사결정용 문서 접근 권한 관리
2. **API 보안**: 프로덕션 환경에서는 적절한 인증/인가 구현 필요
3. **데이터 보호**: 민감한 정보가 포함된 문서는 RAG 디렉토리에 배치하지 않음
4. **분류 결과 보안**: 분류 메타데이터의 민감한 정보 필터링

## 📝 로그 모니터링

RAG 통합 Decision Service 관련 로그는 다음에서 확인할 수 있습니다:
- 콘솔 출력 (디버그 모드)
- `app_debug.log` 파일
- 로그 레벨: INFO, DEBUG

**주요 로그 메시지:**
- `🔍 의사결정을 위한 RAG 컨텍스트 검색 시작`
- `✅ RAG 컨텍스트 발견 (길이: X 문자)`
- `🤖 RAG 통합 Langchain 체인 실행 중...`
- `📊 RAG 통합 원본 분류 결과`
- `📈 RAG 컨텍스트로 인한 신뢰도 향상`

## 🤝 기여하기

RAG 통합 Decision Service 개선을 위한 제안사항:
1. RAG 컨텍스트 품질 평가 알고리즘 개선
2. 분류 정확도 향상을 위한 프롬프트 최적화
3. 새로운 분류 카테고리 추가
4. 성능 최적화 및 캐싱 메커니즘
5. 실시간 학습 및 개선 시스템

## 🔄 변경 사항

### v2.0 (RAG 통합)
- ✅ RAG 통합 의사결정 시스템 도입
- ✅ 컨텍스트 기반 분류 정확도 향상
- ✅ 메타데이터 포함 분류 결과 제공
- ✅ 신뢰도 자동 조정 시스템
- ✅ 하이브리드 분류 모드 지원
- ✅ 성능 최적화 및 오류 처리 개선

### v1.0 (기존)
- 기본 분류 기능
- 고정된 분류 기준
- 단순한 응답 메시지

---

**참고**: 이 RAG 통합 Decision Service는 `static/RAG` 디렉토리의 문서를 기반으로 작동합니다. 새로운 문서를 추가하려면 해당 디렉토리에 파일을 배치하고 RAG 재로드 API를 호출하세요. RAG 통합을 통해 더 정확하고 컨텍스트 기반의 질문 분류를 제공합니다. 