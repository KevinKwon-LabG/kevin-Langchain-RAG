# MCP Stock Service API 가이드

## 📋 목차

1. [개요](#개요)
2. [설치 및 설정](#설치-및-설정)
3. [API 엔드포인트](#api-엔드포인트)
4. [사용 예제](#사용-예제)
5. [클라이언트 애플리케이션 예제](#클라이언트-애플리케이션-예제)
6. [오류 처리](#오류-처리)
7. [제한사항](#제한사항)

## 🎯 개요

MCP Stock Service는 한국 주식 시장(KOSPI, KOSDAQ)의 주식 데이터를 제공하는 서비스입니다. yfinance API를 기반으로 하여 실시간 주식 정보, 가격 데이터, 기본 지표 등을 조회할 수 있습니다.

### 주요 기능

- 📊 주식 종목 정보 조회
- 📈 실시간 가격 데이터 (OHLCV)
- 💰 시가총액 데이터
- 📋 기본 지표 (PER, PBR, 배당수익률)
- 🔍 주식 종목 검색
- 📝 모든 종목 목록 로드
- 🎯 **키워드 추출 (AI 기반)**: 사용자 프롬프트에서 주식 키워드 자동 추출

### 지원하는 종목

- **KOSPI**: 삼성전자(005930), SK하이닉스(000660), NAVER(035420) 등
- **KOSDAQ**: 다양한 기술주 및 중소형주
- **참고 종목**: 21개 주요 종목이 미리 등록되어 있음

## 🔧 키워드 추출 서비스

### 개요
키워드 추출 서비스는 사용자의 자연어 프롬프트에서 주식 관련 키워드를 정확히 추출하는 AI 기반 서비스입니다.

### 추출 방식

#### 1. 주식 코드 추출 (우선순위 1)
- 6자리 숫자 패턴 매칭 (예: 005930, 000660)
- 신뢰도: 95%

#### 2. AI 모델 추출 (우선순위 2)
- Gemma3b-it 모델을 사용한 지능형 키워드 추출
- 자연어 이해를 통한 정확한 키워드 식별
- 신뢰도: 70-95%

#### 3. 기본 패턴 매칭 (우선순위 3)
- 미리 정의된 주식 종목명 패턴 매칭
- AI 모델 실패 시 fallback 방식
- 신뢰도: 60%

### 추출 예시

| 사용자 입력 | 추출된 키워드 | 추출 방식 | 신뢰도 |
|------------|-------------|----------|--------|
| "Naver 주가 정보를 알려줘" | "Naver" | AI 모델 | 90% |
| "삼성전자 시세 보여줘" | "삼성전자" | AI 모델 | 95% |
| "SK하이닉스 000660 주가" | "000660" | 주식 코드 | 95% |
| "카카오 주식 정보" | "카카오" | 기본 패턴 | 60% |
| "오늘 날씨 어때?" | "" | 없음 | 0% |

### 설정 옵션

```python
# config/settings.py
keyword_extractor_model: str = "gemma3b-it"
keyword_extractor_timeout: int = 30
keyword_extractor_temperature: float = 0.1
keyword_extractor_top_p: float = 0.9
keyword_extractor_max_tokens: int = 200
```

## 🚀 설치 및 설정

### 1. 의존성 설치

```bash
pip install pandas yfinance mcp asyncio aiofiles
```

### 2. 환경 설정

```python
from config.settings import Settings
from services.stock_service import StockService

# Settings 초기화
settings = Settings()

# StockService 인스턴스 생성
stock_service = StockService(settings)
```

## 📡 API 엔드포인트

### 1. load_all_tickers

모든 주식 종목의 코드와 이름을 로드합니다.

**요청:**
```json
{
  "name": "load_all_tickers",
  "arguments": {}
}
```

**응답:**
```json
{
  "success": true,
  "total_count": 21,
  "stocks": [
    {
      "stock_code": "005930",
      "company_name": "Samsung Electronics",
      "market": "KOSPI",
      "ticker_symbol": "005930.KS"
    }
  ],
  "note": "참고: 모든 한국 주식 종목 코드(6자리 숫자)를 직접 입력하여 정보를 조회할 수 있습니다."
}
```

### 2. extract_stock_keyword

사용자 프롬프트에서 주식 키워드를 추출합니다.

**요청:**
```json
POST /api/stocks/extract-keyword
{
  "prompt": "Naver 주가 정보를 알려줘"
}
```

**응답:**
```json
{
  "success": true,
  "keyword": "Naver",
  "extraction_type": "ai_model",
  "confidence": 0.9,
  "reason": "Naver는 명확한 회사명",
  "original_prompt": "Naver 주가 정보를 알려줘",
  "extracted_at": "2024-12-01T12:00:00Z"
}
```

### 3. extract_multiple_stock_keywords

사용자 프롬프트에서 여러 주식 키워드를 추출합니다.

**요청:**
```json
POST /api/stocks/extract-keywords
{
  "prompt": "삼성전자와 SK하이닉스 주가 정보를 알려줘"
}
```

**응답:**
```json
{
  "success": true,
  "keywords": [
    {
      "keyword": "삼성전자",
      "type": "ai_model",
      "confidence": 0.95
    },
    {
      "keyword": "SK하이닉스",
      "type": "ai_model",
      "confidence": 0.95
    }
  ],
  "total_count": 2,
  "original_prompt": "삼성전자와 SK하이닉스 주가 정보를 알려줘",
  "extracted_at": "2024-12-01T12:00:00Z"
}
```

### 4. extract_and_search_stock

사용자 프롬프트에서 키워드를 추출하고 주식 검색 및 상세 정보를 조회합니다.

**요청:**
```json
POST /api/stocks/extract-and-search
{
  "prompt": "Naver 주가 정보를 알려줘"
}
```

**응답:**
```json
{
  "success": true,
  "extraction_result": {
    "success": true,
    "keyword": "Naver",
    "extraction_type": "ai_model",
    "confidence": 0.9,
    "reason": "Naver는 명확한 회사명"
  },
  "search_results": {
    "success": true,
    "keyword": "Naver",
    "result_count": 1,
    "results": [
      {
        "stock_code": "035420",
        "company_name": "NAVER Corp",
        "market": "KOSPI"
      }
    ]
  },
  "stock_info": {
    "success": true,
    "stock_code": "035420",
    "Basic Information": {
      "Company Name": "NAVER Corp",
      "Listed Market": "KOSPI",
      "Industry Classification": "Internet Content & Information"
    },
    "Financial Data": {
      "Latest Stock Price": 172200.0,
      "Price-Earnings Ratio": 0,
      "Price-Book Ratio": 0,
      "Dividend Yield": 0
    }
  },
  "selected_stock_code": "035420",
  "selected_stock_name": "NAVER Corp",
  "processing_type": "keyword_search_then_detail",
  "processed_at": "2024-12-01T12:00:00Z"
}
```

### 5. get_stock_info

특정 주식 종목의 상세 정보를 조회합니다.

**요청:**
```json
{
  "name": "get_stock_info",
  "arguments": {
    "stock_code": "005930"
  }
}
```

**응답:**
```json
{
  "success": true,
  "stock_code": "005930",
  "ticker_symbol": "005930.KS",
  "Basic Information": {
    "Company Name": "Samsung Electronics Co., Ltd.",
    "Listed Market": "KOSPI",
    "Industry Classification": "Consumer Electronics",
    "Founded Date": "Unknown",
    "Number of Employees": "Unknown",
    "Official Website": "https://www.samsung.com"
  },
  "Financial Data": {
    "Latest Stock Price": 70600.0,
    "Price-Earnings Ratio": 0,
    "Price-Book Ratio": 0,
    "Dividend Yield": 0
  }
}
```

### 6. get_stock_price_data

특정 주식의 OHLCV(시가/고가/저가/종가/거래량) 데이터를 조회합니다.

**요청:**
```json
{
  "name": "get_stock_price_data",
  "arguments": {
    "stock_code": "005930",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**응답:**
```json
{
  "success": true,
  "stock_code": "005930",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data_count": 21,
  "price_data": [
    {
      "Date": "2024-01-30",
      "Open": 72980.3,
      "High": 73272.2,
      "Low": 71715.3,
      "Close": 72299.1,
      "Volume": 12244418
    }
  ]
}
```

### 7. get_stock_market_cap

특정 주식의 시가총액 데이터를 조회합니다.

**요청:**
```json
{
  "name": "get_stock_market_cap",
  "arguments": {
    "stock_code": "005930",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**응답:**
```json
{
  "success": true,
  "stock_code": "005930",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data_count": 21,
  "market_cap_data": [
    {
      "Date": "2024-01-30",
      "Market_Cap": 885260994513,
      "Close_Price": 72299.1,
      "Volume": 12244418
    }
  ]
}
```

### 8. get_stock_fundamental

특정 주식의 기본 지표 데이터를 조회합니다.

**요청:**
```json
{
  "name": "get_stock_fundamental",
  "arguments": {
    "stock_code": "005930"
  }
}
```

**응답:**
```json
{
  "success": true,
  "fundamental_data": {
    "stock_code": "005930",
    "Price-Earnings Ratio (PER)": "N/A",
    "Price-Book Ratio (PBR)": "N/A",
    "Dividend Yield": "206.00%",
    "Market Cap": "N/A",
    "Enterprise Value": "N/A",
    "Return on Equity (ROE)": "N/A",
    "Return on Assets (ROA)": "N/A",
    "Debt to Equity": "N/A",
    "Current Ratio": "N/A",
    "Quick Ratio": "N/A"
  }
}
```

### 9. search_stock

키워드로 주식 종목을 검색합니다.

**요청:**
```json
{
  "name": "search_stock",
  "arguments": {
    "keyword": "삼성"
  }
}
```

**응답:**
```json
{
  "success": true,
  "keyword": "삼성",
  "result_count": 1,
  "results": [
    {
      "stock_code": "018260",
      "company_name": "삼성에스디에스",
      "market": "KOSPI"
    }
  ]
}
```

## 💻 사용 예제

### Python 클라이언트 예제

```python
import asyncio
import json
from services.stock_service import StockService
from services.stock_keyword_extractor import stock_keyword_extractor
from config.settings import Settings

async def stock_service_example():
    """Stock Service 사용 예제"""
    
    # 서비스 초기화
    settings = Settings()
    stock_service = StockService(settings)
    
    # 1. 키워드 추출 예제
    print("=== 키워드 추출 예제 ===")
    test_prompts = [
        "Naver 주가 정보를 알려줘",
        "삼성전자 시세 보여줘",
        "SK하이닉스 000660 주가",
        "카카오 주식 정보"
    ]
    
    for prompt in test_prompts:
        result = await stock_keyword_extractor.extract_stock_keyword(prompt)
        if result['success']:
            print(f"'{prompt}' → '{result['keyword']}' (신뢰도: {result['confidence']:.1%})")
        else:
            print(f"'{prompt}' → 추출 실패")
    
    # 2. 모든 종목 로드
    print("\n=== 모든 종목 로드 ===")
    result = await stock_service.load_all_tickers()
    print(f"총 {result['total_count']}개 종목 로드됨")
    
    # 3. 특정 종목 정보 조회
    print("\n=== 삼성전자 정보 조회 ===")
    result = await stock_service.get_stock_info("005930")
    if result['success']:
        info = result['Basic Information']
        financial = result['Financial Data']
        print(f"회사명: {info['Company Name']}")
        print(f"현재가: {financial['Latest Stock Price']:,}원")
    
    # 4. 가격 데이터 조회
    print("\n=== 가격 데이터 조회 ===")
    result = await stock_service.get_stock_price_data(
        "005930", 
        start_date="2024-01-01", 
        end_date="2024-01-31"
    )
    if result['success']:
        print(f"데이터 수: {result['data_count']}개")
        latest = result['price_data'][-1]
        print(f"최신 종가: {latest['Close']:,}원")
    
    # 5. 종목 검색
    print("\n=== 종목 검색 ===")
    result = await stock_service.search_stock("SK")
    if result['success']:
        print(f"검색 결과: {result['result_count']}개")
        for item in result['results']:
            print(f"  {item['stock_code']}: {item['company_name']}")

if __name__ == "__main__":
    asyncio.run(stock_service_example())
```

### 키워드 추출 서비스 예제

```python
import asyncio
from services.stock_keyword_extractor import stock_keyword_extractor

async def keyword_extraction_example():
    """키워드 추출 서비스 사용 예제"""
    
    # 1. 단일 키워드 추출
    print("=== 단일 키워드 추출 ===")
    prompts = [
        "Naver 주가 정보를 알려줘",
        "삼성전자 시세 보여줘",
        "SK하이닉스 000660 주가",
        "오늘 날씨 어때?",
        "카카오 주식 정보"
    ]
    
    for prompt in prompts:
        result = await stock_keyword_extractor.extract_stock_keyword(prompt)
        print(f"\n입력: {prompt}")
        print(f"추출: {result}")
    
    # 2. 다중 키워드 추출
    print("\n=== 다중 키워드 추출 ===")
    multi_prompt = "삼성전자와 SK하이닉스 주가 정보를 알려줘"
    result = await stock_keyword_extractor.extract_multiple_keywords(multi_prompt)
    print(f"입력: {multi_prompt}")
    print(f"추출: {result}")

if __name__ == "__main__":
    asyncio.run(keyword_extraction_example())
```

### 통합 주식 검색 예제

```python
import asyncio
from services.stock_keyword_extractor import stock_keyword_extractor

async def integrated_stock_search_example():
    """통합 주식 검색 서비스 사용 예제"""
    
    test_prompts = [
        "Naver 주가 정보를 알려줘",
        "삼성전자 시세 보여줘",
        "SK하이닉스 000660 주가",
        "카카오 주식 정보"
    ]
    
    for prompt in test_prompts:
        print(f"\n=== 테스트: {prompt} ===")
        
        # 통합 검색 (키워드 추출 → 검색 → 상세 정보 조회)
        result = await stock_keyword_extractor.extract_and_get_stock_info(prompt)
        
        if result.get('success'):
            extraction = result.get('extraction_result', {})
            stock_info = result.get('stock_info', {})
            
            print(f"✅ 성공")
            print(f"추출된 키워드: {extraction.get('keyword', 'N/A')}")
            print(f"처리 방식: {result.get('processing_type', 'N/A')}")
            
            if stock_info and stock_info.get('success'):
                basic = stock_info.get('Basic Information', {})
                financial = stock_info.get('Financial Data', {})
                
                print(f"회사명: {basic.get('Company Name', 'N/A')}")
                print(f"시장: {basic.get('Listed Market', 'N/A')}")
                print(f"현재가: {financial.get('Latest Stock Price', 'N/A'):,}원" if isinstance(financial.get('Latest Stock Price'), (int, float)) else f"현재가: {financial.get('Latest Stock Price', 'N/A')}")
            else:
                print(f"주식 정보 조회 실패: {stock_info.get('error', 'N/A')}")
        else:
            print(f"❌ 실패: {result.get('error', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(integrated_stock_search_example())
```

### FastAPI 클라이언트 예제

```python
from fastapi import FastAPI, HTTPException
from services.stock_service import StockService
from config.settings import Settings
import uvicorn

app = FastAPI(title="Stock Service Client")

# 서비스 초기화
settings = Settings()
stock_service = StockService(settings)

@app.get("/stocks")
async def get_all_stocks():
    """모든 주식 종목 조회"""
    result = await stock_service.load_all_tickers()
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    return result

@app.get("/stocks/{stock_code}")
async def get_stock_info(stock_code: str):
    """특정 주식 정보 조회"""
    result = await stock_service.get_stock_info(stock_code)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.get("/stocks/{stock_code}/price")
async def get_stock_price(stock_code: str, start_date: str = None, end_date: str = None):
    """주식 가격 데이터 조회"""
    result = await stock_service.get_stock_price_data(stock_code, start_date, end_date)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.get("/search")
async def search_stocks(keyword: str):
    """주식 종목 검색"""
    result = await stock_service.search_stock(keyword)
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### JavaScript/Node.js 클라이언트 예제

```javascript
const axios = require('axios');

class StockServiceClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    async getAllStocks() {
        try {
            const response = await axios.get(`${this.baseURL}/stocks`);
            return response.data;
        } catch (error) {
            console.error('모든 주식 조회 실패:', error.message);
            throw error;
        }
    }

    async getStockInfo(stockCode) {
        try {
            const response = await axios.get(`${this.baseURL}/stocks/${stockCode}`);
            return response.data;
        } catch (error) {
            console.error('주식 정보 조회 실패:', error.message);
            throw error;
        }
    }

    async getStockPrice(stockCode, startDate = null, endDate = null) {
        try {
            const params = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            
            const response = await axios.get(`${this.baseURL}/stocks/${stockCode}/price`, { params });
            return response.data;
        } catch (error) {
            console.error('가격 데이터 조회 실패:', error.message);
            throw error;
        }
    }

    async searchStocks(keyword) {
        try {
            const response = await axios.get(`${this.baseURL}/search`, {
                params: { keyword }
            });
            return response.data;
        } catch (error) {
            console.error('주식 검색 실패:', error.message);
            throw error;
        }
    }
}

// 사용 예제
async function example() {
    const client = new StockServiceClient();
    
    try {
        // 모든 주식 조회
        const allStocks = await client.getAllStocks();
        console.log('총 종목 수:', allStocks.total_count);
        
        // 삼성전자 정보 조회
        const samsungInfo = await client.getStockInfo('005930');
        console.log('삼성전자 현재가:', samsungInfo['Financial Data']['Latest Stock Price']);
        
        // 가격 데이터 조회
        const priceData = await client.getStockPrice('005930', '2024-01-01', '2024-01-31');
        console.log('가격 데이터 수:', priceData.data_count);
        
        // 종목 검색
        const searchResults = await client.searchStocks('SK');
        console.log('검색 결과:', searchResults.results);
        
    } catch (error) {
        console.error('오류 발생:', error.message);
    }
}

example();
```

## 🔧 클라이언트 애플리케이션 예제

### 1. 간단한 주식 모니터링 앱

```python
import asyncio
import tkinter as tk
from tkinter import ttk
from services.stock_service import StockService
from config.settings import Settings

class StockMonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("주식 모니터링 앱")
        self.root.geometry("800x600")
        
        # 서비스 초기화
        settings = Settings()
        self.stock_service = StockService(settings)
        
        self.setup_ui()
        
    def setup_ui(self):
        # 검색 프레임
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(search_frame, text="종목 코드:").pack(side='left')
        self.stock_code_var = tk.StringVar(value="005930")
        ttk.Entry(search_frame, textvariable=self.stock_code_var, width=10).pack(side='left', padx=5)
        ttk.Button(search_frame, text="조회", command=self.search_stock).pack(side='left', padx=5)
        
        # 결과 표시 영역
        self.result_text = tk.Text(self.root, height=20)
        self.result_text.pack(fill='both', expand=True, padx=10, pady=10)
        
    def search_stock(self):
        stock_code = self.stock_code_var.get()
        asyncio.create_task(self.update_stock_info(stock_code))
        
    async def update_stock_info(self, stock_code):
        try:
            # 주식 정보 조회
            result = await self.stock_service.get_stock_info(stock_code)
            
            if result['success']:
                info = result['Basic Information']
                financial = result['Financial Data']
                
                display_text = f"""
=== {stock_code} 주식 정보 ===
회사명: {info['Company Name']}
시장: {info['Listed Market']}
업종: {info['Industry Classification']}
현재가: {financial['Latest Stock Price']:,}원
PER: {financial['Price-Earnings Ratio']}
PBR: {financial['Price-Book Ratio']}
배당수익률: {financial['Dividend Yield']}%
                """
            else:
                display_text = f"오류: {result['error']}"
                
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, display_text)
            
        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, f"오류 발생: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = StockMonitorApp()
    app.run()
```

### 2. 주식 데이터 분석 도구

```python
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
from services.stock_service import StockService
from config.settings import Settings

class StockAnalyzer:
    def __init__(self):
        settings = Settings()
        self.stock_service = StockService(settings)
        
    async def analyze_stock(self, stock_code, start_date, end_date):
        """주식 데이터 분석"""
        
        # 가격 데이터 조회
        result = await self.stock_service.get_stock_price_data(stock_code, start_date, end_date)
        
        if not result['success']:
            print(f"데이터 조회 실패: {result['error']}")
            return
        
        # DataFrame으로 변환
        df = pd.DataFrame(result['price_data'])
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # 기본 통계
        print(f"\n=== {stock_code} 분석 결과 ===")
        print(f"분석 기간: {start_date} ~ {end_date}")
        print(f"데이터 수: {len(df)}개")
        print(f"시작가: {df['Open'].iloc[0]:,.0f}원")
        print(f"종가: {df['Close'].iloc[-1]:,.0f}원")
        print(f"최고가: {df['High'].max():,.0f}원")
        print(f"최저가: {df['Low'].min():,.0f}원")
        print(f"평균 거래량: {df['Volume'].mean():,.0f}주")
        
        # 수익률 계산
        total_return = ((df['Close'].iloc[-1] - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
        print(f"총 수익률: {total_return:.2f}%")
        
        # 차트 그리기
        self.plot_stock_data(df, stock_code)
        
    def plot_stock_data(self, df, stock_code):
        """주식 데이터 차트 그리기"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # 가격 차트
        ax1.plot(df.index, df['Close'], label='종가', color='blue')
        ax1.plot(df.index, df['High'], label='고가', color='red', alpha=0.7)
        ax1.plot(df.index, df['Low'], label='저가', color='green', alpha=0.7)
        ax1.set_title(f'{stock_code} 주가 차트')
        ax1.set_ylabel('가격 (원)')
        ax1.legend()
        ax1.grid(True)
        
        # 거래량 차트
        ax2.bar(df.index, df['Volume'], color='gray', alpha=0.7)
        ax2.set_title('거래량')
        ax2.set_ylabel('거래량 (주)')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

async def main():
    analyzer = StockAnalyzer()
    
    # 삼성전자 분석
    await analyzer.analyze_stock('005930', '2024-01-01', '2024-01-31')
    
    # SK하이닉스 분석
    await analyzer.analyze_stock('000660', '2024-01-01', '2024-01-31')

if __name__ == "__main__":
    asyncio.run(main())
```

## ⚠️ 오류 처리

### 일반적인 오류 코드

```python
# 1. 종목 코드를 찾을 수 없는 경우
{
    "success": false,
    "error": "종목 코드 999999에 대한 정보를 찾을 수 없습니다."
}

# 2. 데이터가 없는 경우
{
    "success": false,
    "error": "해당 기간에 데이터가 없습니다."
}

# 3. 네트워크 오류
{
    "success": false,
    "error": "HTTP Error 404"
}
```

### 오류 처리 예제

```python
async def safe_stock_query(stock_service, stock_code):
    """안전한 주식 조회 함수"""
    try:
        result = await stock_service.get_stock_info(stock_code)
        
        if result['success']:
            return result
        else:
            print(f"조회 실패: {result['error']}")
            return None
            
    except Exception as e:
        print(f"예외 발생: {str(e)}")
        return None

# 사용 예제
result = await safe_stock_query(stock_service, "005930")
if result:
    print(f"현재가: {result['Financial Data']['Latest Stock Price']}")
```

## 🔒 제한사항

### 1. API 제한

- **yfinance API 의존성**: 외부 API에 의존하므로 네트워크 상태에 따라 성능이 달라질 수 있습니다.
- **데이터 품질**: 일부 기본 지표(PER, PBR)가 N/A로 표시될 수 있습니다.
- **실시간성**: 데이터는 yfinance API의 업데이트 주기에 따라 달라집니다.

### 2. 성능 고려사항

- **동시 요청**: 너무 많은 동시 요청은 API 제한에 걸릴 수 있습니다.
- **캐싱**: 자주 조회하는 데이터는 캐싱을 고려하세요.
- **배치 처리**: 여러 종목을 조회할 때는 배치 처리를 사용하세요.

### 3. 데이터 정확성

- **배당수익률**: 일부 종목에서 비정상적으로 높은 값이 표시될 수 있습니다.
- **시장 구분**: KOSPI/KOSDAQ 구분이 정확하지 않을 수 있습니다.
- **종목 코드**: 6자리 숫자 코드만 지원합니다.

## 📞 지원 및 문의

이 가이드에 대한 질문이나 개선 사항이 있으시면 언제든지 문의해 주세요.

---

**버전**: 1.0.0  
**최종 업데이트**: 2024년 12월  
**작성자**: MCP Stock Service Team 