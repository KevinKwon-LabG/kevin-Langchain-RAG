# Langchain Decision Service

사용자의 prompt를 분석하여 4가지 카테고리 중 하나로 분류하는 Langchain 기반 시스템입니다.

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

### 2. API 직접 호출
```bash
curl -X POST "http://localhost:8000/api/decision/classify" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "오늘 서울 날씨는 어때?", "use_async": true}'
```

### 3. Python 스크립트 테스트
```bash
python test_decision_service.py
```

## 🔧 API 엔드포인트

### POST /api/decision/classify
사용자의 prompt를 분류합니다.

**요청 본문:**
```json
{
    "prompt": "분류할 질문",
    "use_async": true
}
```

**응답:**
```json
{
    "user_prompt": "분류할 질문",
    "decision_result": "분류 결과 메시지",
    "success": true,
    "error_message": null
}
```

### GET /api/decision/health
서비스 상태를 확인합니다.

## 📁 프로젝트 구조

```
src/
├── services/
│   └── langchain_decision_service.py  # 핵심 의사결정 서비스
├── api/
│   └── decision_api.py                # API 엔드포인트
├── main.py                            # FastAPI 메인 애플리케이션
templates/
└── decision_test.html                 # 웹 테스트 인터페이스
test_decision_service.py               # Python 테스트 스크립트
```

## 🧪 테스트 예시

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

## 🔍 분류 기준

### 1. 날씨 관련 정보 요청
- 날씨, 기온, 강수, 날씨 예보, 기후 등과 관련된 질문
- 키워드: 날씨, 기온, 비, 눈, 맑음, 흐림, 습도, 기압 등

### 2. 한국 주식 시장 종목 주가 정보 요청
- 한국 주식, KOSPI, KOSDAQ, 특정 종목 주가, 주식 시장 등과 관련된 질문
- 키워드: 주가, 주식, KOSPI, KOSDAQ, 삼성전자, SK하이닉스 등

### 3. 웹 검색 필요
- 최신 정보, 실시간 데이터, 특정 사이트 정보, 현재 시점의 구체적인 정보가 필요한 질문
- 키워드: 현재, 지금, 실시간, 최신, 가격, 시간, 날짜 등

### 4. 바로 답변 가능
- 일반적인 지식, 개념 설명, 역사적 사실, 공식 등 AI가 가진 정보로 답변 가능한 질문
- 키워드: 정의, 개념, 역사, 공식, 원리 등

## 🛠️ 개발자 정보

### 주요 컴포넌트

1. **LangchainDecisionService**: 핵심 분류 로직
   - `classify_prompt()`: 비동기 분류
   - `classify_prompt_sync()`: 동기 분류

2. **DecisionCategory**: 분류 카테고리 열거형
   - WEATHER, KOREAN_STOCK, WEB_SEARCH_NEEDED, DIRECT_ANSWER

3. **API 엔드포인트**: RESTful API 제공
   - POST /api/decision/classify
   - GET /api/decision/health

### 확장 가능성

- 새로운 분류 카테고리 추가
- 분류 정확도 향상을 위한 프롬프트 최적화
- 다양한 AI 모델 지원 (Ollama, Anthropic 등)
- 분류 결과 로깅 및 분석 기능

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 