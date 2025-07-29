# API 엔드포인트 문서

이 문서는 `/src/api/endpoints/` 경로에 있는 모든 API 엔드포인트에 대한 설명을 제공합니다.

## 목차

1. [Chat API](#chat-api)
2. [Stock API](#stock-api)
3. [Weather API](#weather-api)
4. [File API](#file-api)
5. [Web API](#web-api)
6. [Database API](#database-api)
7. [Health API](#health-api)
8. [Models API](#models-api)
9. [Sessions API](#sessions-api)
10. [Web Search API](#web-search-api)
11. [Settings API](#settings-api)


---

## Chat API

**파일**: `src/api/endpoints/chat.py`

### 개요
Ollama 모델과의 대화, 세션 관리, 웹 검색 통합 등을 제공하는 핵심 채팅 API입니다.

### 주요 기능

#### 1. 채팅 대화 (`POST /api/chat/`)
- **기능**: Ollama 모델과의 실시간 대화
- **특징**: 
  - 스트리밍 응답 지원
  - 웹 검색 모드 통합 (MCP 서버)
  - 지능형 요청 분류 (주식, 날씨, 웹 검색 등)
  - 세션 기반 대화 관리

#### 2. 요청 분석 (`POST /api/chat/analyze-request`)
- **기능**: 사용자 요청을 분석하여 적절한 서비스 결정
- **분류 항목**: 주식 정보, 날씨 정보, 웹 검색, 일반 대화

#### 3. 모델 관리 (`GET /api/chat/models`)
- **기능**: 사용 가능한 Ollama 모델 목록 조회
- **제공 모델**:
  - gemma3:12b-it-qat (8.9 GB)
  - llama3.1:8b (4.9 GB)
  - llama3.2-vision:11b-instruct-q4_K_M (7.8 GB)
  - qwen3:14b-q8_0 (15 GB)
  - deepseek-r1:14b (9.0 GB)
  - deepseek-v2:16b-lite-chat-q8_0 (16 GB)

#### 4. 세션 관리
- **세션 목록 조회** (`GET /api/chat/sessions`)
- **세션 정보 조회** (`GET /api/chat/sessions/{session_id}`)
- **세션 삭제** (`DELETE /api/chat/sessions/{session_id}`)
- **새 세션 생성** (`POST /api/chat/sessions`)

#### 5. 웹 검색 통합

- **MCP 서버 통합 검색**: 지능형 서비스 (주식, 날씨, 웹 검색) 자동 선택
- **검색 모드 전환**: model_only, mcp_server

---

## Stock API

**파일**: `src/api/endpoints/stock.py`

### 개요
주식 정보 조회, 검색, 가격 데이터, 재무 정보 등을 제공하는 주식 관련 API입니다.

### 주요 기능

#### 1. 주식 정보 조회 (`GET /api/stocks/{stock_code}`)
- **기능**: 6자리 주식 코드로 상세 정보 조회
- **제공 정보**: 회사명, 현재가, 시장구분, 거래량 등

#### 2. 주식 검색 (`GET /api/stocks/search/{keyword}`)
- **기능**: 종목명 또는 키워드로 주식 종목 검색
- **검색 방식**: 부분 일치, 유사도 기반 검색

#### 3. 가격 데이터 조회 (`GET /api/stocks/{stock_code}/price`)
- **기능**: OHLCV 가격 데이터 조회
- **파라미터**: 시작 날짜, 종료 날짜 (선택사항)

#### 4. 시가총액 정보 (`GET /api/stocks/{stock_code}/market-cap`)
- **기능**: 주식 시가총액 정보 조회
- **제공 정보**: 시가총액, 상장주식수, 주가 등

#### 5. 재무 정보 (`GET /api/stocks/{stock_code}/fundamental`)
- **기능**: 재무제표 정보 조회
- **제공 정보**: 매출, 영업이익, 순이익, 부채비율 등

#### 6. 일괄 조회 (`POST /api/stocks/batch`)
- **기능**: 여러 주식 정보를 한 번에 조회
- **입력**: 주식 코드 목록

#### 7. 전체 종목 로드 (`GET /api/stocks/tickers/all`)
- **기능**: 전체 상장 종목 목록 조회

---

## Weather API

**파일**: `src/api/endpoints/weather.py`

### 개요
도시별 실시간 날씨 정보, 예보, 대기질 정보를 제공하는 날씨 API입니다.

### 주요 기능

#### 1. 실시간 날씨 조회 (`GET /api/weather/{city}`)
- **기능**: 도시별 현재 날씨 정보 조회
- **제공 정보**: 온도, 습도, 날씨 상태, 풍속, 기압 등

#### 2. 쿼리 기반 날씨 조회 (`GET /api/weather/`)
- **기능**: 쿼리 파라미터로 날씨 정보 조회
- **파라미터**: city (도시명)

#### 3. POST 요청 날씨 조회 (`POST /api/weather/`)
- **기능**: POST 요청으로 날씨 정보 조회
- **요청 모델**: WeatherRequest (도시명 포함)

#### 4. 인기 도시 목록 (`GET /api/weather/cities/popular`)
- **기능**: 인기 도시 목록 제공
- **제공 도시**: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 제주, 수원, 고양

#### 5. 날씨 예보 (`GET /api/weather/forecast/{city}`)
- **기능**: 도시의 날씨 예보 조회
- **파라미터**: city (도시명), days (예보 일수, 기본값: 5일)

#### 6. 대기질 정보 (`GET /api/weather/air-quality/{city}`)
- **기능**: 도시의 대기질 정보 조회
- **제공 정보**: PM10, PM2.5, 오존, 이산화질소 등

---

## File API

**파일**: `src/api/endpoints/file.py`

### 개요
파일 시스템 접근, 파일 읽기/쓰기, 검색, 삭제 등을 제공하는 파일 관리 API입니다.

### 주요 기능

#### 1. 파일 목록 조회 (`GET /api/files/`)
- **기능**: 디렉토리 내 파일 및 폴더 목록 조회
- **파라미터**: directory (조회할 디렉토리 경로, 기본값: 현재 디렉토리)

#### 2. 파일 읽기 (`GET /api/files/{file_path:path}`)
- **기능**: 파일 내용을 읽어옴
- **지원 형식**: 텍스트 파일, 바이너리 파일
- **오류 처리**: 파일 없음, 권한 없음 등

#### 3. 파일 쓰기 (`POST /api/files/{file_path:path}`)
- **기능**: 파일에 내용을 씀
- **요청 모델**: FileWriteRequest (내용 포함)
- **오류 처리**: 권한 없음, 디렉토리 없음 등

#### 4. 파일 검색 (`GET /api/files/search/{pattern}`)
- **기능**: 파일명 패턴으로 파일 검색
- **파라미터**: pattern (검색 패턴, 예: *.txt, *.py), directory (검색 디렉토리)

#### 5. 파일 삭제 (`DELETE /api/files/{file_path:path}`)
- **기능**: 파일 삭제
- **오류 처리**: 파일 없음, 권한 없음 등

#### 6. 파일 정보 조회 (`GET /api/files/info/{file_path:path}`)
- **기능**: 파일 상세 정보 조회
- **제공 정보**: 크기, 수정일, 권한, 타입 등

---

## Web API

**파일**: `src/api/endpoints/web.py`

### 개요
웹 검색, 웹페이지 내용 가져오기, 트렌딩 검색어 등을 제공하는 웹 관련 API입니다.

### 주요 기능

#### 1. 웹 검색 (`GET /api/web/search`)
- **기능**: 키워드 기반 웹 검색 수행
- **파라미터**: q (검색어), max_results (최대 결과 수, 1-20)
- **제공 정보**: 제목, URL, 요약, 스니펫 등

#### 2. POST 웹 검색 (`POST /api/web/search`)
- **기능**: POST 요청으로 웹 검색 수행
- **요청 모델**: WebSearchRequest

#### 3. 웹페이지 가져오기 (`GET /api/web/fetch`)
- **기능**: 웹페이지 내용을 가져옴
- **파라미터**: url (가져올 웹페이지 URL)
- **제공 정보**: HTML 내용, 메타데이터 등

#### 4. POST 웹페이지 가져오기 (`POST /api/web/fetch`)
- **기능**: POST 요청으로 웹페이지 내용 가져오기

#### 5. 고급 웹 검색 (`GET /api/web/search/advanced`)
- **기능**: 고급 옵션을 포함한 웹 검색
- **파라미터**: 
  - q (검색어)
  - max_results (최대 결과 수)
  - language (검색 언어, ko, en, ja 등)
  - region (검색 지역, KR, US, JP 등)

#### 6. 트렌딩 검색어 (`GET /api/web/trending`)
- **기능**: 현재 트렌딩 검색어 목록 제공
- **제공 정보**: 인기 검색어, 검색량, 카테고리 등

#### 7. 검색 기록 (`GET /api/web/search/history`)
- **기능**: 최근 검색 기록 조회
- **파라미터**: limit (조회할 기록 수, 1-100)

---

## Database API

**파일**: `src/api/endpoints/db.py`

### 개요
사용자 관리, 노트 관리, SQL 쿼리 실행, 데이터베이스 통계 등을 제공하는 데이터베이스 API입니다.

### 주요 기능

#### 1. 사용자 관리
- **사용자 목록 조회** (`GET /api/db/users`)
  - 파라미터: limit (조회할 사용자 수, 1-100)
- **사용자 추가** (`POST /api/db/users`)
  - 요청 모델: UserRequest (이름, 이메일)
- **사용자 정보 조회** (`GET /api/db/users/{user_id}`)

#### 2. 노트 관리
- **노트 목록 조회** (`GET /api/db/notes`)
  - 파라미터: user_id (특정 사용자), limit (조회할 노트 수)
- **노트 추가** (`POST /api/db/notes`)
  - 요청 모델: NoteRequest (사용자 ID, 제목, 내용)
- **노트 정보 조회** (`GET /api/db/notes/{note_id}`)

#### 3. SQL 쿼리 실행 (`POST /api/db/query`)
- **기능**: SQL 쿼리 실행
- **요청 모델**: DatabaseQueryRequest (SQL 쿼리)
- **보안**: SQL 인젝션 방지, 권한 검증

#### 4. 데이터베이스 통계 (`GET /api/db/stats`)
- **기능**: 데이터베이스 통계 정보 조회
- **제공 정보**: 테이블 수, 레코드 수, 크기, 성능 지표 등

#### 5. 백업 생성 (`GET /api/db/backup`)
- **기능**: 데이터베이스 백업 생성
- **제공 정보**: 백업 파일 경로, 크기, 생성 시간 등

#### 6. 데이터베이스 상태 확인 (`GET /api/db/health`)
- **기능**: 데이터베이스 연결 상태 및 성능 확인
- **제공 정보**: 연결 상태, 응답 시간, 오류 수 등

---

## Health API

**파일**: `src/api/endpoints/health.py`

### 개요
애플리케이션 상태 확인, 시스템 리소스 모니터링을 위한 헬스체크 API입니다.

### 주요 기능

#### 1. 전체 상태 확인 (`GET /api/health`)
- **기능**: 애플리케이션의 전체 상태 정보 반환
- **제공 정보**:
  - 상태 (healthy/unhealthy)
  - 타임스탬프
  - 버전 정보
  - 서비스별 상태 (chat, stock, file, weather, web, database)
  - 업타임
  - 메모리/CPU 사용량
  - Ollama 서버 연결 상태

#### 2. 간단한 상태 확인 (`GET /api/health/simple`)
- **기능**: 최소한의 부하로 서버 실행 상태 확인
- **제공 정보**: 상태, 타임스탬프

#### 3. 시스템 리소스 정보 (`GET /api/system/resources`)
- **기능**: 시스템 리소스 사용량 정보 반환
- **제공 정보**:
  - CPU 사용률
  - 메모리 사용량 (사용/전체/비율)
  - 디스크 사용량
  - 네트워크 정보
- **의존성**: psutil 모듈 (선택적)

#### 4. 애플리케이션 정보 (`GET /api/info`)
- **기능**: 애플리케이션 상세 정보 반환
- **제공 정보**:
  - 버전
  - 빌드 정보
  - 환경 설정
  - 라이선스 정보

---

## Models API

**파일**: `src/api/endpoints/models.py`

### 개요
Ollama 모델 관리, 조회, 삭제, 다운로드 등을 제공하는 모델 관리 API입니다.

### 주요 기능

#### 1. 모델 목록 조회 (`GET /api/models`)
- **기능**: 사용 가능한 Ollama 모델 목록 반환
- **제공 정보**: 모델명, 크기, ID, 수정일 등

#### 2. 모델 상세 정보 (`GET /api/models/{model_id}`)
- **기능**: 특정 모델의 상세 정보 반환
- **제공 정보**:
  - 모델 ID, 이름, 크기
  - 수정일, 다이제스트
  - 상세 정보 (포맷, 패밀리, 파라미터 크기, 양자화 레벨)

#### 3. 모델 삭제 (`DELETE /api/models/{model_id}`)
- **기능**: 특정 모델 삭제
- **반환 정보**: 삭제 성공 여부, 메시지, 모델 ID

#### 4. 모델 다운로드 (`POST /api/models/pull`)
- **기능**: 새로운 모델 다운로드
- **파라미터**: model_name (다운로드할 모델 이름)
- **반환 정보**: 다운로드 상태, 진행률, 완료 시간 등

---

## Sessions API

**파일**: `src/api/endpoints/sessions.py`

### 개요
채팅 세션 관리, 조회, 삭제, 제목 수정 등을 제공하는 세션 관리 API입니다.

### 주요 기능

#### 1. 세션 목록 조회 (`GET /api/sessions`)
- **기능**: 사용자의 채팅 세션 목록 반환
- **제공 정보**: 세션 ID, 제목, 생성일, 마지막 활동 시간 등

#### 2. 새 세션 생성 (`POST /api/sessions`)
- **기능**: 새로운 채팅 세션 생성
- **반환 정보**: 세션 ID, 제목, 생성 시간

#### 3. 세션 상세 정보 (`GET /api/sessions/{session_id}`)
- **기능**: 특정 세션의 상세 정보 반환
- **제공 정보**:
  - 세션 ID
  - 메시지 목록 (역할, 내용, 타임스탬프, 모델)
  - 생성일, 마지막 활동 시간

#### 4. 세션 삭제 (`DELETE /api/sessions/{session_id}`)
- **기능**: 특정 세션 삭제
- **반환 정보**: 삭제 성공 여부, 메시지

#### 5. 세션 제목 수정 (`PUT /api/sessions/{session_id}/title`)
- **기능**: 세션 제목 수정
- **요청**: JSON body에 title 포함
- **반환 정보**: 수정된 세션 정보

---

## Web Search API

**파일**: `src/api/endpoints/web_search.py`

### 개요
웹 검색 모드 설정, 관리, 히스토리 등을 제공하는 웹 검색 설정 API입니다.

### 주요 기능

#### 1. 웹 검색 모드 목록 (`GET /api/web-search-modes`)
- **기능**: 사용 가능한 웹 검색 모드 목록 반환
- **제공 모드**:
  - model_only: 모델에서만 답변
  - mcp_server: MCP 서버 통합 검색 (주식, 날씨, 웹 검색 자동 선택)
- **반환 정보**: 모드 목록, 현재 선택된 모드

#### 2. 웹 검색 모드 설정 (`POST /api/web-search-mode`)
- **기능**: 웹 검색 모드 변경
- **요청**: JSON body에 mode 포함
- **반환 정보**: 설정 성공 여부, 메시지, 설정된 모드

#### 3. 현재 모드 조회 (`GET /api/web-search-mode/current`)
- **기능**: 현재 설정된 웹 검색 모드 반환
- **제공 정보**: 현재 모드, 타임스탬프

#### 4. 모드 변경 히스토리 (`GET /api/web-search-mode/history`)
- **기능**: 웹 검색 모드 변경 히스토리 조회
- **제공 정보**: 변경 기록 (모드, 시간, 사용자 등)

---

## Settings API

**파일**: `src/api/endpoints/settings.py`

### 개요
애플리케이션 설정 관리, 조회, 검증, 리로드 등을 제공하는 설정 관리 API입니다.

### 주요 기능

#### 1. 설정 조회 (`GET /api/settings`)
- **기능**: 현재 애플리케이션 설정 반환
- **제공 정보**: 설정 정보, 검증 결과, 타임스탬프

#### 2. 설정 리로드 (`POST /api/settings/reload`)
- **기능**: 설정을 다시 로드
- **반환 정보**: 리로드 성공 여부, 메시지, 업데이트된 설정

#### 3. 설정 검증 (`GET /api/settings/validation`)
- **기능**: 현재 설정의 유효성 검증
- **제공 정보**: 검증 결과, 오류 목록, 경고 목록

#### 4. 설정 요약 (`GET /api/settings/summary`)
- **기능**: 설정 요약 정보 반환
- **제공 정보**: 핵심 설정 항목, 타임스탬프

#### 5. 사용 가능한 모델 (`GET /api/settings/models`)
- **기능**: 시스템에서 사용 가능한 모델 목록 반환
- **제공 정보**: 모델명, 크기, 상태, 권장사항 등

#### 6. 시스템 프롬프트 (`GET /api/settings/prompts`)
- **기능**: 시스템 프롬프트 목록 반환
- **제공 정보**: 프롬프트 ID, 내용, 설명, 카테고리 등

#### 7. 프리셋 목록 (`GET /api/settings/presets`)
- **기능**: 사용 가능한 프리셋 목록 반환
- **제공 정보**: 프리셋명, 설정값, 설명, 카테고리 등

---

## API 사용 예시

### 채팅 API 사용 예시

```bash
# 채팅 대화 시작
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "session_id": "session_123",
    "model": "gemma3:12b-it-qat"
  }'

# 모델 목록 조회
curl -X GET "http://localhost:8000/api/chat/models"
```

### 주식 API 사용 예시

```bash
# 주식 정보 조회
curl -X GET "http://localhost:8000/api/stocks/005930"

# 주식 검색
curl -X GET "http://localhost:8000/api/stocks/search/삼성전자"

# 가격 데이터 조회
curl -X GET "http://localhost:8000/api/stocks/005930/price?start_date=2024-01-01&end_date=2024-01-31"
```

### 날씨 API 사용 예시

```bash
# 날씨 정보 조회
curl -X GET "http://localhost:8000/api/weather/서울"

# 인기 도시 목록
curl -X GET "http://localhost:8000/api/weather/cities/popular"
```

### 파일 API 사용 예시

```bash
# 파일 목록 조회
curl -X GET "http://localhost:8000/api/files/?directory=/home/user"

# 파일 읽기
curl -X GET "http://localhost:8000/api/files/example.txt"

# 파일 쓰기
curl -X POST "http://localhost:8000/api/files/newfile.txt" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, World!"}'
```

---

## 오류 처리

모든 API 엔드포인트는 일관된 오류 처리 방식을 사용합니다:

### HTTP 상태 코드
- `200`: 성공
- `400`: 잘못된 요청
- `404`: 리소스를 찾을 수 없음
- `500`: 내부 서버 오류

### 오류 응답 형식
```json
{
  "detail": "오류 메시지"
}
```

### 로깅
모든 API는 구조화된 로깅을 사용하여 요청, 응답, 오류를 기록합니다.

---

## 보안 고려사항

1. **입력 검증**: 모든 사용자 입력은 검증됩니다
2. **SQL 인젝션 방지**: 데이터베이스 쿼리는 파라미터화됩니다
3. **파일 시스템 보안**: 파일 경로는 검증되고 제한됩니다
4. **권한 검증**: 적절한 권한 검증이 수행됩니다

---

## 성능 최적화

1. **비동기 처리**: 모든 API는 비동기로 구현되어 있습니다
2. **연결 풀링**: 데이터베이스 및 외부 서비스 연결은 풀링됩니다
3. **캐싱**: 적절한 캐싱 전략이 적용됩니다
4. **스트리밍**: 대용량 응답은 스트리밍으로 처리됩니다 