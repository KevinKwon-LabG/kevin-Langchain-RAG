# MCP (Model Context Protocol) 통합

이 프로젝트는 외부 MCP 서버와의 통신을 지원합니다. MCP는 다양한 AI 모델과의 표준화된 인터페이스를 제공하는 프로토콜입니다.

## 날씨 서비스 기능

이 프로젝트는 AI가 날씨 관련 질문을 받았을 때 자동으로 MCP 서버에 정보를 요청하여 답변하는 기능을 제공합니다.

### 주요 기능

- **자동 날씨 질문 감지**: 한국어/영어 날씨 관련 키워드와 패턴을 자동으로 감지
- **위치 정보 추출**: 메시지에서 도시명을 자동으로 추출
- **MCP 서버 연동**: 감지된 날씨 질문을 MCP 서버에 전송하여 정확한 정보 제공
- **실시간 응답**: 스트리밍 방식으로 실시간 날씨 정보 제공

### 지원하는 날씨 질문 유형

- **기본 날씨 정보**: "서울 날씨 어때?", "부산 기온은?"
- **예보 정보**: "내일 대구 날씨 예보", "주말 제주도 날씨"
- **상세 정보**: "부산 비 올 확률", "대구 바람 세기", "제주 습도 정보"
- **영어 질문**: "What's the weather like in Seoul?", "How's the temperature in Busan?"

### 지원하는 도시

- **대도시**: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종
- **중소도시**: 제주, 강릉, 춘천, 청주, 전주, 포항, 창원, 수원 등
- **영어 도시명**: seoul, busan, daegu, incheon, gwangju, daejeon, ulsan, jeju 등

## 설정

### 환경 설정

MCP 서버 설정은 `src/config/settings.py` 파일에서 관리됩니다:

```python
# MCP (Model Context Protocol) 설정
mcp_server_host: str = "1.237.52.240"
mcp_server_port: int = 11045
mcp_server_url: str = "http://1.237.52.240:11045"
mcp_timeout: int = 30
mcp_max_retries: int = 3
mcp_enabled: bool = True
```

### 환경 변수 설정

`env.settings` 파일에서 MCP 설정을 변경할 수 있습니다:

```bash
# MCP 서버 설정
MCP_SERVER_HOST=1.237.52.240
MCP_SERVER_PORT=11045
MCP_SERVER_URL=http://1.237.52.240:11045
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3
MCP_ENABLED=true
```

## API 엔드포인트

### 1. 서버 상태 확인

```http
GET /mcp/health
```

MCP 서버의 상태를 확인합니다.

**응답 예시:**
```json
{
  "status": "success",
  "mcp_server": "http://1.237.52.240:11045",
  "health_check": {
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### 2. 모델 목록 조회

```http
GET /mcp/models
```

MCP 서버에서 사용 가능한 모델 목록을 조회합니다.

**응답 예시:**
```json
{
  "status": "success",
  "models": [
    {
      "name": "gpt-3.5-turbo",
      "description": "GPT-3.5 Turbo 모델"
    }
  ],
  "total_count": 1
}
```

### 3. 특정 모델 정보 조회

```http
GET /mcp/models/{model_name}
```

특정 모델의 상세 정보를 조회합니다.

### 4. 채팅 완성

```http
POST /mcp/chat/completions
```

**요청 본문:**
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "안녕하세요!"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 0.9,
  "top_k": 40,
  "repeat_penalty": 1.1
}
```

### 5. 텍스트 완성

```http
POST /mcp/completions
```

**요청 본문:**
```json
{
  "model": "gpt-3.5-turbo",
  "prompt": "다음 문장을 완성하세요:",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### 6. 임베딩 생성

```http
POST /mcp/embeddings
```

**요청 본문:**
```json
{
  "model": "text-embedding-ada-002",
  "input": ["안녕하세요", "반갑습니다"]
}
```

### 7. 설정 정보 조회

```http
GET /mcp/config
```

현재 MCP 설정 정보를 조회합니다.

## 날씨 서비스 API 엔드포인트

### 1. 날씨 질문 분석

```http
POST /api/chat/weather/analyze
```

메시지가 날씨 관련 질문인지 분석합니다.

**요청 본문:**
```json
{
  "message": "서울 날씨 어때?",
  "model": "gemma3:12b-it-qat",
  "session_id": "session_123"
}
```

**응답 예시:**
```json
{
  "message": "서울 날씨 어때?",
  "weather_analysis": {
    "is_weather_question": true,
    "location": "서울",
    "keywords_found": ["날씨"],
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 2. 날씨 정보 직접 요청

```http
POST /api/chat/weather/query
```

날씨 정보를 MCP 서버에 직접 요청합니다.

**요청 본문:**
```json
{
  "message": "서울 오늘 날씨",
  "model": "gemma3:12b-it-qat",
  "session_id": "session_123"
}
```

**응답 예시:**
```json
{
  "message": "서울 오늘 날씨",
  "weather_response": {
    "success": true,
    "response": "서울의 오늘 날씨는 맑고 기온은 15°C입니다...",
    "location": "서울",
    "timestamp": "2024-01-01T00:00:00Z",
    "source": "mcp_weather_service"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 사용 예시

### Python 클라이언트 예시

```python
import asyncio
from src.services.mcp_service import mcp_service
from src.services.weather_service import weather_service

async def example():
    # 서버 상태 확인
    health = await mcp_service.health_check()
    print(f"서버 상태: {health}")
    
    # 모델 목록 조회
    models = await mcp_service.get_models()
    print(f"사용 가능한 모델: {models}")
    
    # 채팅 완성
    messages = [
        {"role": "user", "content": "안녕하세요!"}
    ]
    response = await mcp_service.chat_completion(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7
    )
    print(f"응답: {response}")

# 날씨 서비스 예시
async def weather_example():
    # 날씨 질문 분석
    weather_info = weather_service.get_weather_info("서울 날씨 어때?")
    print(f"날씨 질문 여부: {weather_info['is_weather_question']}")
    print(f"추출된 위치: {weather_info['location']}")
    
    # 날씨 정보 요청
    if weather_info['is_weather_question']:
        weather_response = await weather_service.get_weather_response("서울 날씨 어때?")
        if weather_response['success']:
            print(f"날씨 응답: {weather_response['response']}")
        else:
            print(f"오류: {weather_response['error']}")

# 실행
asyncio.run(example())
asyncio.run(weather_example())
```

### cURL 예시

```bash
# 서버 상태 확인
curl -X GET "http://localhost:11040/mcp/health"

# 모델 목록 조회
curl -X GET "http://localhost:11040/mcp/models"

# 채팅 완성
curl -X POST "http://localhost:11040/mcp/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "안녕하세요!"}
    ],
    "temperature": 0.7
  }'

# 날씨 질문 분석
curl -X POST "http://localhost:11040/api/chat/weather/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "서울 날씨 어때?",
    "model": "gemma3:12b-it-qat",
    "session_id": "session_123"
  }'

# 날씨 정보 요청
curl -X POST "http://localhost:11040/api/chat/weather/query" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "서울 오늘 날씨",
    "model": "gemma3:12b-it-qat",
    "session_id": "session_123"
  }'
```

## 테스트

### MCP 서비스 테스트

MCP 서비스 연결을 테스트하려면 다음 스크립트를 실행하세요:

```bash
python scripts/test_mcp.py
```

이 스크립트는 다음을 테스트합니다:
1. MCP 서버 연결 상태
2. 사용 가능한 모델 목록 조회
3. 간단한 채팅 완성 테스트

### 날씨 서비스 테스트

날씨 서비스 기능을 테스트하려면 다음 스크립트를 실행하세요:

```bash
python test_weather_service.py
```

이 스크립트는 다음을 테스트합니다:
1. 날씨 질문 감지 기능
2. 위치 정보 추출 기능
3. MCP 서버를 통한 날씨 정보 요청
4. 다양한 날씨 질문 패턴 테스트

## 오류 처리

MCP 서비스는 다음과 같은 오류 상황을 처리합니다:

- **연결 실패**: 재시도 로직으로 자동 재시도
- **서버 오류**: 적절한 HTTP 상태 코드와 오류 메시지 반환
- **타임아웃**: 설정된 시간 내에 응답이 없으면 오류 반환

## 의존성

MCP 서비스를 사용하려면 다음 패키지가 필요합니다:

```
aiohttp==3.10.11
```

## 주의사항

1. MCP 서버가 활성화되어 있어야 합니다 (`mcp_enabled=true`)
2. 네트워크 연결이 안정적이어야 합니다
3. MCP 서버의 API 엔드포인트가 올바르게 구현되어 있어야 합니다
4. 타임아웃 설정을 적절히 조정하세요

## 문제 해결

### 일반적인 문제들

1. **연결 실패**
   - MCP 서버 주소와 포트를 확인하세요
   - 네트워크 연결을 확인하세요
   - 방화벽 설정을 확인하세요

2. **타임아웃 오류**
   - `mcp_timeout` 설정을 늘려보세요
   - MCP 서버의 응답 시간을 확인하세요

3. **인증 오류**
   - MCP 서버의 인증 설정을 확인하세요
   - 필요한 경우 API 키를 설정하세요 