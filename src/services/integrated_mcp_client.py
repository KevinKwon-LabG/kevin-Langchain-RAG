import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import re

class MCPServiceError(Exception):
    """MCP 서비스 에러 기본 클래스"""
    pass

class StockNotFoundError(MCPServiceError):
    """주식 종목을 찾을 수 없음"""
    pass

class InvalidStockCodeError(MCPServiceError):
    """잘못된 주식 코드"""
    pass

class ServiceUnavailableError(MCPServiceError):
    """서비스 사용 불가"""
    pass

async def safe_mcp_call(client, method, *args, **kwargs):
    """
    안전한 MCP 서비스 호출을 위한 래퍼 함수
    
    Args:
        client: MCP 클라이언트 인스턴스
        method: 호출할 메서드
        *args: 메서드 인자
        **kwargs: 메서드 키워드 인자
    
    Returns:
        메서드 실행 결과
    
    Raises:
        MCPServiceError: 서비스 호출 중 오류 발생 시
    """
    try:
        result = await method(*args, **kwargs)
        
        # 응답 형식 검증 및 정규화
        if isinstance(result, dict):
            # success 필드가 없으면 추가
            if 'success' not in result:
                result['success'] = True
            
            # 오류 응답 처리
            if not result.get('success', True):
                error_msg = result.get('error', '알 수 없는 오류가 발생했습니다')
                if '찾을 수 없습니다' in error_msg:
                    raise StockNotFoundError(error_msg)
                elif '잘못된' in error_msg:
                    raise InvalidStockCodeError(error_msg)
                else:
                    raise MCPServiceError(error_msg)
        
        return result
        
    except aiohttp.ClientResponseError as e:
        if e.status == 404:
            raise StockNotFoundError(f"요청한 리소스를 찾을 수 없습니다: {args[0] if args else ''}")
        elif e.status == 400:
            raise InvalidStockCodeError(f"잘못된 요청입니다: {args[0] if args else ''}")
        elif e.status >= 500:
            raise ServiceUnavailableError("서비스가 일시적으로 사용할 수 없습니다")
        else:
            raise MCPServiceError(f"서비스 호출 실패: {e}")
    except aiohttp.ClientError as e:
        raise ServiceUnavailableError(f"네트워크 오류: {e}")
    except Exception as e:
        if isinstance(e, (StockNotFoundError, InvalidStockCodeError, ServiceUnavailableError, MCPServiceError)):
            raise
        raise MCPServiceError(f"예상치 못한 오류: {e}")

class MCPServiceClient:
    """MCP Service 통합 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:11045"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """HTTP 요청 수행"""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, json=data) as response:
                response.raise_for_status()
                result = await response.json()
                
                # 응답 형식 검증
                if isinstance(result, dict):
                    # success 필드가 없으면 추가
                    if 'success' not in result:
                        result['success'] = True
                    
                    # 오류 응답 처리
                    if not result.get('success', True):
                        error_msg = result.get('error', '알 수 없는 오류가 발생했습니다')
                        if '찾을 수 없습니다' in error_msg or 'not found' in error_msg.lower():
                            raise StockNotFoundError(error_msg)
                        elif '잘못된' in error_msg or 'invalid' in error_msg.lower():
                            raise InvalidStockCodeError(error_msg)
                        else:
                            raise MCPServiceError(error_msg)
                
                return result
                
        except aiohttp.ClientResponseError as e:
            self.logger.error(f"HTTP request failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """사용 가능한 도구 목록 조회"""
        response = await self._make_request("GET", "/tools")
        return response.get("tools", [])
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """도구 호출"""
        response = await self._make_request("POST", f"/tools/{tool_name}", kwargs)
        return response.get("result", response)  # result 필드가 없으면 전체 응답 반환

class IntegratedMCPClient(MCPServiceClient):
    """모든 MCP 서비스를 통합한 클라이언트"""
    
    def _validate_stock_code(self, stock_code: str) -> bool:
        """주식 코드 유효성 검사"""
        if not stock_code or not isinstance(stock_code, str):
            return False
        
        # 6자리 숫자 패턴 검사
        pattern = r'^\d{6}$'
        return bool(re.match(pattern, stock_code))
    
    def _validate_date_format(self, date_str: str) -> bool:
        """날짜 형식 유효성 검사"""
        if not date_str:
            return True  # 선택적 파라미터
        
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _sanitize_keyword(self, keyword: str) -> str:
        """검색 키워드 정제"""
        if not keyword:
            return ""
        
        # 특수 문자 제거 (한글, 영문, 숫자만 허용)
        sanitized = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', keyword)
        return sanitized.strip()
    
    def _format_stock_response(self, response: Dict[str, Any], stock_code: str = None) -> Dict[str, Any]:
        """주식 응답 형식 정규화"""
        if not isinstance(response, dict):
            return {
                "success": False,
                "error": "응답 형식이 올바르지 않습니다"
            }
        
        # success 필드가 없으면 추가
        if 'success' not in response:
            response['success'] = True
        
        # stock_code 필드가 없고 파라미터로 전달된 경우 추가
        if stock_code and 'stock_code' not in response:
            response['stock_code'] = stock_code
        
        return response
    
    # Stock Service 메서드들
    async def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """주식 종목 상세 정보 조회"""
        if not self._validate_stock_code(stock_code):
            raise InvalidStockCodeError(f"잘못된 주식 코드 형식: {stock_code}")
        
        result = await self.call_tool("get_stock_info", stock_code=stock_code)
        return self._format_stock_response(result, stock_code)
    
    async def search_stock(self, keyword: str) -> Dict[str, Any]:
        """주식 종목 검색"""
        sanitized_keyword = self._sanitize_keyword(keyword)
        if not sanitized_keyword:
            raise ValueError("검색 키워드가 비어있습니다")
        
        result = await self.call_tool("search_stock", keyword=sanitized_keyword)
        
        # 검색 결과 형식 정규화
        if isinstance(result, dict):
            if 'success' not in result:
                result['success'] = True
            if 'keyword' not in result:
                result['keyword'] = sanitized_keyword
            if 'result_count' not in result and 'results' in result:
                result['result_count'] = len(result['results'])
        
        return result
    
    async def get_stock_price_data(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """주식 가격 데이터 조회"""
        if not self._validate_stock_code(stock_code):
            raise InvalidStockCodeError(f"잘못된 주식 코드 형식: {stock_code}")
        
        if start_date and not self._validate_date_format(start_date):
            raise ValueError(f"잘못된 시작 날짜 형식: {start_date}")
        
        if end_date and not self._validate_date_format(end_date):
            raise ValueError(f"잘못된 종료 날짜 형식: {end_date}")
        
        params = {"stock_code": stock_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        result = await self.call_tool("get_stock_price_data", **params)
        
        # 가격 데이터 응답 형식 정규화
        if isinstance(result, dict):
            if 'success' not in result:
                result['success'] = True
            if 'stock_code' not in result:
                result['stock_code'] = stock_code
            if 'start_date' not in result and start_date:
                result['start_date'] = start_date
            if 'end_date' not in result and end_date:
                result['end_date'] = end_date
            if 'data_count' not in result and 'price_data' in result:
                result['data_count'] = len(result['price_data'])
        
        return result
    
    async def get_stock_market_cap(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """주식 시가총액 데이터 조회"""
        if not self._validate_stock_code(stock_code):
            raise InvalidStockCodeError(f"잘못된 주식 코드 형식: {stock_code}")
        
        params = {"stock_code": stock_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        result = await self.call_tool("get_stock_market_cap", **params)
        
        # 시가총액 데이터 응답 형식 정규화
        if isinstance(result, dict):
            if 'success' not in result:
                result['success'] = True
            if 'stock_code' not in result:
                result['stock_code'] = stock_code
            if 'start_date' not in result and start_date:
                result['start_date'] = start_date
            if 'end_date' not in result and end_date:
                result['end_date'] = end_date
            if 'data_count' not in result and 'market_cap_data' in result:
                result['data_count'] = len(result['market_cap_data'])
        
        return result
    
    async def get_stock_fundamental(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """주식 기본 지표 데이터 조회"""
        if not self._validate_stock_code(stock_code):
            raise InvalidStockCodeError(f"잘못된 주식 코드 형식: {stock_code}")
        
        params = {"stock_code": stock_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        result = await self.call_tool("get_stock_fundamental", **params)
        
        # 기본 지표 데이터 응답 형식 정규화
        if isinstance(result, dict):
            if 'success' not in result:
                result['success'] = True
            if 'stock_code' not in result:
                result['stock_code'] = stock_code
        
        return result
    
    async def load_all_tickers(self) -> Dict[str, Any]:
        """모든 주식 종목 정보를 로드합니다"""
        result = await self.call_tool("load_all_tickers")
        
        # 전체 종목 응답 형식 정규화
        if isinstance(result, dict):
            if 'success' not in result:
                result['success'] = True
            if 'total_count' not in result and 'stocks' in result:
                result['total_count'] = len(result['stocks'])
            if 'note' not in result:
                result['note'] = "참고: 모든 한국 주식 종목 코드(6자리 숫자)를 직접 입력하여 정보를 조회할 수 있습니다."
        
        return result
    
    # Web Service 메서드들
    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """웹 검색 수행"""
        return await self.call_tool("web_search", query=query, max_results=max_results)
    
    async def fetch_webpage(self, url: str) -> Dict[str, Any]:
        """웹 페이지 내용 가져오기"""
        return await self.call_tool("fetch_webpage", url=url)
    
    async def get_weather(self, city: str) -> Dict[str, Any]:
        """날씨 정보 조회"""
        return await self.call_tool("get_weather", city=city)
    
    # File Service 메서드들
    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """파일 읽기"""
        return await self.call_tool("read_file", file_path=file_path)
    
    async def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """파일 쓰기"""
        return await self.call_tool("write_file", file_path=file_path, content=content)
    
    async def list_files(self, directory: str = ".") -> Dict[str, Any]:
        """파일 목록 조회"""
        return await self.call_tool("list_files", directory=directory)
    
    async def search_files(self, pattern: str, directory: str = ".") -> Dict[str, Any]:
        """파일 검색"""
        return await self.call_tool("search_files", pattern=pattern, directory=directory)
    
    # Database Service 메서드들
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """SQL 쿼리 실행"""
        return await self.call_tool("execute_query", query=query)
    
    async def add_user(self, name: str, email: str) -> Dict[str, Any]:
        """사용자 추가"""
        return await self.call_tool("add_user", name=name, email=email)
    
    async def add_note(self, title: str, content: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """노트 추가"""
        params = {"title": title, "content": content}
        if user_id:
            params["user_id"] = user_id
        return await self.call_tool("add_note", **params)
    
    async def get_users(self, limit: int = 10) -> Dict[str, Any]:
        """사용자 목록 조회"""
        return await self.call_tool("get_users", limit=limit)
    
    async def get_notes(self, user_id: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
        """노트 목록 조회"""
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        return await self.call_tool("get_notes", **params)

# 에러 처리 헬퍼 함수
async def safe_mcp_call(client, method, *args, **kwargs):
    """안전한 MCP 서비스 호출"""
    try:
        return await method(*args, **kwargs)
    except aiohttp.ClientResponseError as e:
        if e.status == 404:
            raise StockNotFoundError(f"요청한 데이터를 찾을 수 없습니다: {args[0] if args else ''}")
        elif e.status == 400:
            raise InvalidStockCodeError(f"잘못된 요청입니다: {args[0] if args else ''}")
        elif e.status >= 500:
            raise ServiceUnavailableError("서비스가 일시적으로 사용할 수 없습니다")
        else:
            raise MCPServiceError(f"서비스 호출 실패: {e}")
    except aiohttp.ClientError as e:
        raise ServiceUnavailableError(f"네트워크 오류: {e}")
    except Exception as e:
        raise MCPServiceError(f"예상치 못한 오류: {e}")

# 성능 최적화된 클라이언트
class OptimizedIntegratedMCPClient(IntegratedMCPClient):
    """성능 최적화된 통합 MCP 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:11045", max_connections: int = 100, cache_ttl: int = 300):
        super().__init__(base_url)
        self.max_connections = max_connections
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl  # 캐시 유효 시간 (초)
        
    async def __aenter__(self):
        """연결 풀링이 적용된 세션 생성"""
        from aiohttp import TCPConnector
        connector = TCPConnector(
            limit=self.max_connections,
            limit_per_host=10,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_parts = [method]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """캐시 유효성 검사"""
        if not cache_entry:
            return False
        
        created_at = cache_entry.get('created_at')
        if not created_at:
            return False
        
        return datetime.now() - created_at < timedelta(seconds=self.cache_ttl)
    
    async def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """캐싱이 적용된 주식 정보 조회"""
        cache_key = self._get_cache_key("get_stock_info", stock_code)
        
        # 캐시 확인
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']
        
        # 실제 API 호출
        result = await super().get_stock_info(stock_code)
        
        # 캐시 저장
        self.cache[cache_key] = {
            'data': result,
            'created_at': datetime.now()
        }
        
        return result
    
    async def search_stock(self, keyword: str) -> Dict[str, Any]:
        """캐싱이 적용된 주식 검색"""
        cache_key = self._get_cache_key("search_stock", keyword)
        
        # 캐시 확인
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']
        
        # 실제 API 호출
        result = await super().search_stock(keyword)
        
        # 캐시 저장
        self.cache[cache_key] = {
            'data': result,
            'created_at': datetime.now()
        }
        
        return result
    
    async def get_stock_price_data(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """캐싱이 적용된 주식 가격 데이터 조회"""
        cache_key = self._get_cache_key("get_stock_price_data", stock_code, start_date, end_date)
        
        # 캐시 확인
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']
        
        # 실제 API 호출
        result = await super().get_stock_price_data(stock_code, start_date, end_date)
        
        # 캐시 저장
        self.cache[cache_key] = {
            'data': result,
            'created_at': datetime.now()
        }
        
        return result
    
    async def get_stock_market_cap(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """캐싱이 적용된 주식 시가총액 데이터 조회"""
        cache_key = self._get_cache_key("get_stock_market_cap", stock_code, start_date, end_date)
        
        # 캐시 확인
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']
        
        # 실제 API 호출
        result = await super().get_stock_market_cap(stock_code, start_date, end_date)
        
        # 캐시 저장
        self.cache[cache_key] = {
            'data': result,
            'created_at': datetime.now()
        }
        
        return result
    
    async def get_stock_fundamental(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """캐싱이 적용된 주식 기본 지표 데이터 조회"""
        cache_key = self._get_cache_key("get_stock_fundamental", stock_code, start_date, end_date)
        
        # 캐시 확인
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']
        
        # 실제 API 호출
        result = await super().get_stock_fundamental(stock_code, start_date, end_date)
        
        # 캐시 저장
        self.cache[cache_key] = {
            'data': result,
            'created_at': datetime.now()
        }
        
        return result
    
    async def load_all_tickers(self) -> Dict[str, Any]:
        """캐싱이 적용된 전체 종목 정보 로드"""
        cache_key = self._get_cache_key("load_all_tickers")
        
        # 캐시 확인 (전체 종목은 더 긴 캐시 시간 적용)
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']
        
        # 실제 API 호출
        result = await super().load_all_tickers()
        
        # 캐시 저장 (전체 종목은 더 긴 캐시 시간 적용)
        self.cache[cache_key] = {
            'data': result,
            'created_at': datetime.now()
        }
        
        return result
    
    async def get_multiple_stock_info(self, stock_codes: List[str]) -> Dict[str, Any]:
        """여러 주식 정보를 동시에 조회"""
        tasks = [self.get_stock_info(code) for code in stock_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            code: result if not isinstance(result, Exception) else {"error": str(result)}
            for code, result in zip(stock_codes, results)
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        return {
            "cache_size": len(self.cache),
            "cache_ttl": self.cache_ttl,
            "max_connections": self.max_connections
        } 