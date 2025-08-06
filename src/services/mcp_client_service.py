"""
MCP (Model Context Protocol) 클라이언트 서비스
실제 MCP 서버와 통신하여 Google Search, 날씨 정보, 한국 주식 정보를 제공
"""

import logging
import json
import asyncio
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import httpx
import aiohttp
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """대화 컨텍스트 정보"""
    session_id: str
    previous_messages: List[Dict[str, str]]  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    current_request: str
    missing_params: List[str] = None
    is_waiting_for_params: bool = False

class MCPClientService:
    """
    MCP 서버와 통신하는 실제 서비스
    Google Search, 날씨 정보, 한국 주식 정보를 제공
    """
    
    def __init__(self, mcp_server_url: str = None):
        """
        MCP 클라이언트 서비스 초기화
        
        Args:
            mcp_server_url: MCP 서버 URL (기본값은 환경 설정에서 가져옴)
        """
        if mcp_server_url is None:
            from src.config.settings import get_settings
            settings = get_settings()
            self.mcp_server_url = settings.mcp_server_url
        else:
            self.mcp_server_url = mcp_server_url
        
        self.session_contexts: Dict[str, ConversationContext] = {}
        
        # HTTP 클라이언트 설정
        self.timeout = 30
        self.max_retries = 3
        
        # 주식 종목 매핑 초기화 (애플리케이션 시작 시 한 번만 로드)
        self._stock_mapping_cache = None
        self._stock_reverse_mapping_cache = None
        self._initialize_stock_mapping()
        
        logger.info(f"MCP 클라이언트 서비스 초기화 - 서버: {self.mcp_server_url}")
    
    def _initialize_stock_mapping(self):
        """애플리케이션 시작 시 주식 종목 매핑을 초기화합니다."""
        try:
            json_file = Path("data/stocks_data.json")
            if not json_file.exists():
                logger.warning("stocks_data.json 파일이 존재하지 않습니다. 기본 매핑을 사용합니다.")
                self._stock_mapping_cache = self._get_default_stock_mapping()
                return
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # stocks 배열에서 종목 정보 추출
            stocks = data.get("result", {}).get("stocks", [])
            if not stocks:
                logger.warning("stocks_data.json 파일에 종목 정보가 없습니다. 기본 매핑을 사용합니다.")
                self._stock_mapping_cache = self._get_default_stock_mapping()
                return
            
            stock_mapping = {}
            for stock in stocks:
                stock_code = stock.get("stock_code", "")
                korean_name = stock.get("korean_name", "")
                korean_short_name = stock.get("korean_short_name", "")
                
                if stock_code and korean_name:
                    # 긴 이름과 짧은 이름 모두 매핑에 추가
                    stock_mapping[korean_name] = stock_code
                    if korean_short_name and korean_short_name != korean_name:
                        stock_mapping[korean_short_name] = stock_code
            
            self._stock_mapping_cache = stock_mapping
            # 역방향 매핑도 미리 생성 (종목코드 → 종목명)
            self._stock_reverse_mapping_cache = {v: k for k, v in stock_mapping.items()}
            logger.info(f"주식 종목 매핑 초기화 완료: {len(stock_mapping)}개 종목")
            
        except Exception as e:
            logger.error(f"주식 종목 매핑 초기화 실패: {e}")
            self._stock_mapping_cache = self._get_default_stock_mapping()
            self._stock_reverse_mapping_cache = {v: k for k, v in self._stock_mapping_cache.items()}
    
    def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """
        세션의 대화 컨텍스트를 가져옵니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Optional[ConversationContext]: 세션 컨텍스트 또는 None
        """
        return self.session_contexts.get(session_id)
    
    def update_conversation_context(self, session_id: str, context: ConversationContext):
        """
        세션 컨텍스트를 업데이트합니다.
        
        Args:
            session_id: 세션 ID
            context: 업데이트할 컨텍스트
        """
        self.session_contexts[session_id] = context
        logger.debug(f"세션 {session_id} 컨텍스트 업데이트됨")
    
    def add_message_to_context(self, session_id: str, role: str, content: str):
        """
        세션에 메시지를 추가합니다.
        
        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user/assistant)
            content: 메시지 내용
        """
        context = self.get_conversation_context(session_id)
        if not context:
            context = ConversationContext(
                session_id=session_id,
                previous_messages=[],
                current_request=""
            )
        
        context.previous_messages.append({
            "role": role,
            "content": content
        })
        
        # 최근 10개 메시지만 유지
        if len(context.previous_messages) > 10:
            context.previous_messages = context.previous_messages[-10:]
        
        self.update_conversation_context(session_id, context)
        logger.debug(f"세션 {session_id}에 {role} 메시지 추가됨")
    
    async def _make_mcp_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP 서버에 요청을 보냅니다.
        
        Args:
            endpoint: API 엔드포인트 (weather, stock, search 등)
            data: 요청 데이터
            
        Returns:
            Dict[str, Any]: 응답 데이터
        """
        # MCP 서버의 도구 매핑
        tool_mapping = {
            "weather": "get_current_weather",
            "stock": "get_stock_info", 
            "search": "google_web_search"
        }
        
        tool_name = tool_mapping.get(endpoint)
        if not tool_name:
            raise Exception(f"지원하지 않는 엔드포인트: {endpoint}")
        
        url = f"{self.mcp_server_url}/tools/{tool_name}"
        
        # 데이터 변환
        if endpoint == "weather":
            # 날씨 요청 데이터 변환
            request_data = {
                "city": data.get("location", "서울")
            }
        elif endpoint == "stock":
            # 주식 요청 데이터 변환
            request_data = {
                "stock_code": data.get("code", "")
            }
        elif endpoint == "search":
            # 검색 요청 데이터 변환
            request_data = {
                "query": data.get("query", ""),
                "num_results": data.get("max_results", 5),
                "language": "ko"
            }
        else:
            request_data = data
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(url, json=request_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.debug(f"MCP 요청 성공: {endpoint}")
                            return {
                                "success": True,
                                "data": result
                            }
                        else:
                            logger.warning(f"MCP 요청 실패 (시도 {attempt + 1}): {response.status}")
                            
            except Exception as e:
                logger.warning(f"MCP 요청 오류 (시도 {attempt + 1}): {e}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)  # 재시도 전 대기
        
        raise Exception(f"MCP 서버 요청 실패: {endpoint}")
    
    def _extract_location_from_prompt(self, prompt: str) -> Optional[str]:
        """프롬프트에서 위치 정보를 추출합니다."""
        # 파일에서 도시 목록 로드
        korean_cities = self._load_korean_cities() # 한국 도시 목록 (weather_cities.csv) 파일에 있으며, get_weather_cities.py 파일에서 생성됨
        
        for city in korean_cities:
            if city in prompt:
                return city
        
        return None
    
    def _load_korean_cities(self) -> List[str]:
        """저장된 파일에서 한국 도시 목록을 로드합니다."""
        try:
            # 먼저 weather_cities.csv 파일 시도
            csv_file = Path("data/weather_cities.csv")
            if csv_file.exists():
                import csv
                cities = []
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        city_name = row.get('city_name', '').strip()
                        if city_name:
                            cities.append(city_name)
                
                if cities:
                    logger.debug(f"CSV 파일에서 도시 목록 로드 완료: {len(cities)}개 도시")
                    return cities
            
            # CSV 파일이 없거나 비어있으면 JSON 파일 시도
            json_file = Path("data/korean_cities.json")
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cities = data.get("cities", [])
                if cities:
                    logger.debug(f"JSON 파일에서 도시 목록 로드 완료: {len(cities)}개 도시")
                    return cities
            
            # 파일이 없거나 비어있으면 기본 도시 목록 사용
            logger.warning("도시 목록 파일이 존재하지 않거나 비어있습니다. 기본 도시 목록을 사용합니다.")
            return self._get_default_cities()
                
        except Exception as e:
            logger.error(f"도시 목록 파일 로드 실패: {e}")
            return self._get_default_cities()
    
    def _get_default_cities(self) -> List[str]:
        """기본 도시 목록을 반환합니다. (파일이 없거나 로드 실패 시 사용)"""
        return [
            "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
            "수원", "성남", "의정부", "안양", "부천", "광명", "평택", "동두천",
            "안산", "고양", "과천", "구리", "남양주", "오산", "시흥", "군포",
            "의왕", "하남", "용인", "파주", "이천", "안성", "김포", "화성",
            "광주", "여주", "양평", "양주", "포천", "연천", "가평",
            "춘천", "원주", "강릉", "태백", "속초", "삼척", "동해", "횡성",
            "영월", "평창", "정선", "철원", "화천", "양구", "인제", "고성",
            "양양", "홍천", "태안", "당진", "서산", "논산", "계룡", "공주",
            "보령", "아산", "서천", "천안", "예산", "금산", "부여",
            "청양", "홍성", "제주", "서귀포", "포항", "경주", "김천", "안동",
            "구미", "영주", "영천", "상주", "문경", "경산", "군산", "익산",
            "정읍", "남원", "김제", "완주", "진안", "무주", "장수", "임실",
            "순창", "고창", "부안", "여수", "순천", "나주", "광양", "담양",
            "곡성", "구례", "고흥", "보성", "화순", "장흥", "강진", "해남",
            "영암", "무안", "함평", "영광", "장성", "완도", "진도", "신안"
        ]
    
    def _extract_stock_code_from_prompt(self, prompt: str) -> Optional[str]:
        """프롬프트에서 주식 종목 코드를 추출합니다."""
        # 6자리 숫자 패턴 (주식 종목 코드)
        pattern = r'\b\d{6}\b'
        match = re.search(pattern, prompt)
        if match:
            return match.group()
        
        # stocks_data.json 파일에서 주식 종목 정보 로드
        stock_mapping = self._load_stock_mapping()
        
        # 종목명으로 검색 (한글 이름, 짧은 이름 모두 검색)
        for stock_name, code in stock_mapping.items():
            if stock_name in prompt:
                return code
        
        return None
    
    def _load_stock_mapping(self) -> Dict[str, str]:
        """초기화된 주식 종목 매핑을 반환합니다."""
        if self._stock_mapping_cache is None:
            logger.warning("주식 종목 매핑이 초기화되지 않았습니다. 기본 매핑을 사용합니다.")
            return self._get_default_stock_mapping()
        return self._stock_mapping_cache
    
    def _get_stock_name_by_code(self, stock_code: str) -> str:
        """종목 코드로 종목명을 조회합니다."""
        if self._stock_reverse_mapping_cache:
            return self._stock_reverse_mapping_cache.get(stock_code, f"종목코드 {stock_code}")
        return f"종목코드 {stock_code}"
    
    def _get_default_stock_mapping(self) -> Dict[str, str]:
        """기본 주식 종목 매핑을 반환합니다. (파일이 없거나 로드 실패 시 사용)"""
        return {
            "삼성전자": "005930",
            "SK하이닉스": "000660",
            "NAVER": "035420",
            "카카오": "035720",
            "LG에너지솔루션": "373220",
            "삼성바이오로직스": "207940",
            "현대차": "005380",
            "기아": "000270",
            "POSCO홀딩스": "005490",
            "삼성SDI": "006400",
            "LG화학": "051910",
            "현대모비스": "012330",
            "KB금융": "105560",
            "신한지주": "055550",
            "하나금융지주": "086790",
            "우리금융지주": "316140",
            "LG전자": "066570",
            "삼성물산": "028260",
            "SK이노베이션": "096770",
            "아모레퍼시픽": "090430"
        }
    
    async def process_weather_request(self, user_prompt: str, session_id: Optional[str] = None) -> Tuple[str, bool]:
        """
        날씨 요청을 처리합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"날씨 요청 처리: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        try:
            # 위치 정보 추출
            location = self._extract_location_from_prompt(user_prompt)
            if not location:
                location = "서울"  # 기본값
            
            # MCP 서버에 날씨 요청
            weather_data = await self._make_mcp_request("weather", {
                "location": location,
                "query": user_prompt
            })
            
            # 응답 생성
            if weather_data.get("success"):
                weather_info = weather_data.get("data", {})
                # 위치 정보를 weather_info에 추가
                weather_info["location"] = location
                response = self._format_weather_response(weather_info, location)
            else:
                response = f"죄송합니다. {location}의 날씨 정보를 가져올 수 없습니다."
            
        except Exception as e:
            logger.error(f"날씨 요청 처리 실패: {e}")
            response = f"날씨 정보 서비스에 일시적인 오류가 발생했습니다: {str(e)}"
        
        # 세션에 응답 추가
        if session_id:
            self.add_message_to_context(session_id, "assistant", response)
        
        return response, True
    
    def _format_weather_response(self, weather_info: Dict[str, Any], location: str) -> str:
        """날씨 정보를 포맷팅합니다."""
        try:
            # 위치 정보가 "알 수 없는 위치"인 경우 기본값으로 변경
            if location == "알 수 없는 위치":
                location = "서울"
            
            # MCP 서버의 실제 응답 형식에 맞게 수정
            if isinstance(weather_info, dict):
                # MCP 서버 응답 구조: {"success": true, "result": {"success": true, "data": {...}}}
                if "result" in weather_info and isinstance(weather_info["result"], dict):
                    result_data = weather_info["result"]
                    
                    # content 필드가 있는 경우 (이미 포맷된 텍스트) - 우선 처리
                    if "content" in result_data and isinstance(result_data["content"], list):
                        for content_item in result_data["content"]:
                            if isinstance(content_item, dict) and content_item.get("type") == "text":
                                formatted_text = content_item.get("text", f"{location}의 날씨 정보를 표시할 수 없습니다.")
                                # content 텍스트에 위치 정보가 없으면 추가
                                if location not in formatted_text:
                                    formatted_text = f"📍 {location} {formatted_text}"
                                return formatted_text
                    
                    # data 필드가 있는 경우 (구조화된 데이터)
                    if "data" in result_data and isinstance(result_data["data"], dict):
                        data = result_data["data"]
                        
                        # 온도 정보
                        temp_info = data.get("temperature", {})
                        if isinstance(temp_info, dict):
                            temperature = temp_info.get("celsius", "N/A")
                        else:
                            temperature = temp_info
                        
                        # 날씨 설명
                        description = data.get("description_korean", data.get("description", "N/A"))
                        
                        # 습도
                        humidity = data.get("humidity", "N/A")
                        
                        # 바람 정보
                        wind_info = data.get("wind", {})
                        if isinstance(wind_info, dict):
                            wind_speed = wind_info.get("speed", "N/A")
                        else:
                            wind_speed = wind_info
                        
                        # 체감온도
                        feels_like_info = data.get("feels_like", {})
                        if isinstance(feels_like_info, dict):
                            feels_like = feels_like_info.get("celsius", "N/A")
                        else:
                            feels_like = feels_like_info
                        
                        # 일출/일몰
                        sunrise = data.get("sunrise", "N/A")
                        sunset = data.get("sunset", "N/A")
                        
                        response = f"📍 {location} 날씨 정보\n\n"
                        response += f"🌡️ 기온: {temperature}°C\n"
                        if feels_like != "N/A" and feels_like != temperature:
                            response += f"💨 체감온도: {feels_like}°C\n"
                        response += f"☁️ 날씨: {description}\n"
                        response += f"💧 습도: {humidity}%\n"
                        response += f"💨 풍속: {wind_speed}m/s\n"
                        if sunrise != "N/A" and sunset != "N/A":
                            response += f"🌅 일출: {sunrise} | 🌇 일몰: {sunset}\n"
                        
                        return response
                
                # 기존 형식 지원
                temperature = weather_info.get("temperature", weather_info.get("temp", "N/A"))
                condition = weather_info.get("condition", weather_info.get("weather", "N/A"))
                humidity = weather_info.get("humidity", "N/A")
                wind_speed = weather_info.get("wind_speed", weather_info.get("wind", "N/A"))
                
                response = f"📍 {location} 날씨 정보\n\n"
                response += f"🌡️ 기온: {temperature}°C\n"
                response += f"☁️ 날씨: {condition}\n"
                response += f"💧 습도: {humidity}%\n"
                response += f"💨 풍속: {wind_speed}m/s\n"
                
                return response
            else:
                # 응답이 문자열인 경우 (JSON 문자열)
                try:
                    import json
                    weather_data = json.loads(str(weather_info)) if isinstance(weather_info, str) else weather_info
                    return self._format_weather_response(weather_data, location)
                except:
                    # 파싱 실패 시 원본 응답 사용
                    return f"📍 {location} 날씨 정보\n\n{weather_info}"
            
        except Exception as e:
            logger.error(f"날씨 응답 포맷팅 실패: {e}")
            return f"{location}의 날씨 정보를 표시할 수 없습니다."
    
    async def process_stock_request(self, user_prompt: str, session_id: Optional[str] = None) -> Tuple[str, bool]:
        """
        주식 요청을 처리합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"주식 요청 처리: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        try:
            # 주식 종목 코드 추출
            stock_code = self._extract_stock_code_from_prompt(user_prompt)
            if not stock_code:
                response = "주식 종목 코드나 종목명을 찾을 수 없습니다. 예: '삼성전자 주가' 또는 '005930 주가'"
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                return response, True
            
            # MCP 서버에 주식 요청
            stock_data = await self._make_mcp_request("stock", {
                "code": stock_code,
                "query": user_prompt
            })
            
            # 응답 생성
            if stock_data.get("success"):
                stock_info = stock_data.get("data", {})
                # 주식 코드를 응답 데이터에 포함
                stock_info["code"] = stock_code
                response = self._format_stock_response(stock_info, stock_code)
            else:
                response = f"죄송합니다. 종목 코드 {stock_code}의 주식 정보를 가져올 수 없습니다."
            
        except Exception as e:
            logger.error(f"주식 요청 처리 실패: {e}")
            response = f"주식 정보 서비스에 일시적인 오류가 발생했습니다: {str(e)}"
        
        # 세션에 응답 추가
        if session_id:
            self.add_message_to_context(session_id, "assistant", response)
        
        return response, True
    
    def _format_stock_response(self, stock_info: Dict[str, Any], stock_code: str) -> str:
        """주식 정보를 포맷팅합니다."""
        try:
            # MCP 서버의 실제 응답 형식에 맞게 수정
            if isinstance(stock_info, dict):
                # MCP 서버 응답 구조: {"success": true, "result": {"success": true, ...}}
                if "result" in stock_info and isinstance(stock_info["result"], dict):
                    result_data = stock_info["result"]
                    
                    # 기본 정보
                    company_name = "N/A"
                    if "Basic Information" in result_data and isinstance(result_data["Basic Information"], dict):
                        basic_info = result_data["Basic Information"]
                        company_name = basic_info.get("Company Name", "N/A")
                    
                    # 회사명이 N/A인 경우 종목 코드로 대체
                    if company_name == "N/A":
                        company_name = self._get_stock_name_by_code(stock_code)
                    
                    # 재무 데이터
                    price = "N/A"
                    pe_ratio = "N/A"
                    pb_ratio = "N/A"
                    dividend_yield = "N/A"
                    
                    if "Financial Data" in result_data and isinstance(result_data["Financial Data"], dict):
                        financial_data = result_data["Financial Data"]
                        price = financial_data.get("Latest Stock Price", "N/A")
                        pe_ratio = financial_data.get("Price-Earnings Ratio", "N/A")
                        pb_ratio = financial_data.get("Price-Book Ratio", "N/A")
                        dividend_yield = financial_data.get("Dividend Yield", "N/A")
                    
                    # 데이터 신선도
                    data_source = "N/A"
                    data_quality = "N/A"
                    if "Data Freshness" in result_data and isinstance(result_data["Data Freshness"], dict):
                        freshness = result_data["Data Freshness"]
                        data_source = freshness.get("Data Source", "N/A")
                        data_quality = freshness.get("Data Quality", "N/A")
                    
                    response = f"📈 {company_name} ({stock_code}) 주식 정보\n\n"
                    response += f"💰 현재가: {price:,}원\n"
                    response += f"📊 PER: {pe_ratio}\n"
                    response += f"📊 PBR: {pb_ratio}\n"
                    response += f"💰 배당수익률: {dividend_yield}%\n"
                    response += f"📈 데이터 출처: {data_source} ({data_quality})\n"
                    
                    return response
                
                # 기존 형식 지원
                name = stock_info.get("name", stock_info.get("company_name", "N/A"))
                price = stock_info.get("price", stock_info.get("current_price", "N/A"))
                change = stock_info.get("change", stock_info.get("price_change", "N/A"))
                change_rate = stock_info.get("change_rate", stock_info.get("price_change_rate", "N/A"))
                volume = stock_info.get("volume", stock_info.get("trading_volume", "N/A"))
                market_cap = stock_info.get("market_cap", stock_info.get("market_capitalization", "N/A"))
                
                response = f"📈 {name} ({stock_code}) 주식 정보\n\n"
                response += f"💰 현재가: {price:,}원\n"
                
                if change != "N/A" and change != 0:
                    change_symbol = "📈" if change >= 0 else "📉"
                    response += f"{change_symbol} 변동: {change:+,}원 ({change_rate:+.2f}%)\n"
                
                response += f"📊 거래량: {volume:,}주\n"
                response += f"🏢 시가총액: {market_cap:,}원\n"
                
                return response
            else:
                # 응답이 문자열인 경우 (JSON 문자열)
                try:
                    import json
                    stock_data = json.loads(str(stock_info)) if isinstance(stock_info, str) else stock_info
                    return self._format_stock_response(stock_data, stock_code)
                except:
                    # 파싱 실패 시 원본 응답 사용
                    return f"📈 주식 정보 ({stock_code})\n\n{stock_info}"
            
        except Exception as e:
            logger.error(f"주식 응답 포맷팅 실패: {e}")
            return f"종목 코드 {stock_code}의 주식 정보를 표시할 수 없습니다."
    
    async def process_web_search_request(self, user_prompt: str, session_id: Optional[str] = None) -> Tuple[str, bool]:
        """
        웹 검색 요청을 처리합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"웹 검색 요청 처리: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        try:
            # MCP 서버에 웹 검색 요청
            search_data = await self._make_mcp_request("search", {
                "query": user_prompt,
                "max_results": 5
            })
            
            # 응답 생성
            if search_data.get("success"):
                search_results = search_data.get("data", [])
                response = self._format_search_response(search_results, user_prompt)
            else:
                response = f"죄송합니다. '{user_prompt}'에 대한 검색 결과를 가져올 수 없습니다."
            
        except Exception as e:
            logger.error(f"웹 검색 요청 처리 실패: {e}")
            response = f"웹 검색 서비스에 일시적인 오류가 발생했습니다: {str(e)}"
        
        # 세션에 응답 추가
        if session_id:
            self.add_message_to_context(session_id, "assistant", response)
        
        return response, True
    
    def _process_snippet_text(self, snippet: str) -> str:
        """
        검색 결과 스니펫 텍스트를 처리합니다.
        
        Args:
            snippet: 원본 스니펫 텍스트
            
        Returns:
            str: 처리된 스니펫 텍스트
        """
        if not snippet or snippet == "내용 없음":
            return "내용 없음"
        
        try:
            # HTML 태그 제거 (간단한 정규식 사용)
            import re
            # HTML 태그 제거
            clean_text = re.sub(r'<[^>]+>', '', snippet)
            
            # 줄바꿈을 임시 마커로 보존
            clean_text = clean_text.replace('\n', '{{NEWLINE}}')
            
            # 연속된 공백 정리 (줄바꿈 제외)
            clean_text = re.sub(r'[ \t]+', ' ', clean_text)
            
            # 임시 마커를 다시 줄바꿈으로 복원
            clean_text = clean_text.replace('{{NEWLINE}}', '\n')
            
            # 줄바꿈 보존하면서 길이 제한
            max_length = 200  # 길이 제한을 200자로 증가
            
            if len(clean_text) <= max_length:
                # 줄바꿈을 보존하여 반환
                return clean_text.replace('\n', '\n   ')  # 들여쓰기 추가
            else:
                # 길이가 긴 경우 적절한 위치에서 자르기
                truncated = clean_text[:max_length]
                
                # 마지막 완전한 문장이나 단어에서 자르기
                last_period = truncated.rfind('.')
                last_space = truncated.rfind(' ')
                
                if last_period > max_length * 0.7:  # 70% 이상에서 마침표가 있으면
                    truncated = truncated[:last_period + 1]
                elif last_space > max_length * 0.8:  # 80% 이상에서 공백이 있으면
                    truncated = truncated[:last_space]
                
                # 줄바꿈 보존
                return truncated.replace('\n', '\n   ') + "..."
                
        except Exception as e:
            logger.warning(f"스니펫 텍스트 처리 중 오류: {e}")
            # 오류 발생 시 원본 텍스트 반환 (길이 제한만 적용)
            return snippet[:200] + "..." if len(snippet) > 200 else snippet

    def _format_search_response(self, search_results: List[Dict[str, Any]], query: str) -> str:
        """검색 결과를 포맷팅합니다."""
        try:
            if not search_results:
                return f"'{query}'에 대한 검색 결과를 찾을 수 없습니다."
            
            # MCP 서버의 실제 응답 형식에 맞게 수정
            if isinstance(search_results, dict):
                # MCP 서버 응답 구조: {"success": true, "result": {"success": true, ...}}
                if "result" in search_results and isinstance(search_results["result"], dict):
                    result_data = search_results["result"]
                    
                    # content 필드가 있는 경우 (이미 포맷된 텍스트)
                    if "content" in result_data and isinstance(result_data["content"], list):
                        for content_item in result_data["content"]:
                            if isinstance(content_item, dict) and content_item.get("type") == "text":
                                return content_item.get("text", f"'{query}' 검색 결과를 표시할 수 없습니다.")
                    
                    # results 필드가 있는 경우
                    if "results" in result_data and isinstance(result_data["results"], list):
                        results = result_data["results"]
                        total_results = result_data.get("total_results", "N/A")
                        search_time = result_data.get("search_time", "N/A")
                        
                        response = f"🔍 '{query}' 검색 결과\n\n"
                        response += f"📊 총 결과 수: {total_results}개\n"
                        response += f"⏱️ 검색 시간: {search_time}\n\n"
                        
                        for i, result in enumerate(results[:5], 1):
                            if isinstance(result, dict):
                                title = result.get("title", "제목 없음")
                                snippet = result.get("snippet", "내용 없음")
                                url = result.get("link", result.get("url", ""))
                                display_link = result.get("display_link", "")
                            else:
                                title = str(result)
                                snippet = "내용 없음"
                                url = ""
                                display_link = ""
                            
                            response += f"{i}. **{title}**\n"
                            if url:
                                response += f"   🔗 <a href=\"{url}\" target=\"_blank\">{url}</a>\n"
                            
                            # 스니펫 처리 - 줄바꿈 보존 및 HTML 태그 제거
                            processed_snippet = self._process_snippet_text(snippet)
                            response += f"   📝 {processed_snippet}\n"
                            
                            if display_link:
                                response += f"   🌐 {display_link}\n"
                            response += "\n"
                        
                        return response
                
                # 기존 형식 지원
                if isinstance(search_results, list):
                    results = search_results
                else:
                    # 응답이 문자열인 경우 (JSON 문자열)
                    try:
                        import json
                        results = json.loads(str(search_results)) if isinstance(search_results, str) else search_results
                        if not isinstance(results, list):
                            results = [results]
                    except:
                        # 파싱 실패 시 원본 응답 사용
                        return f"🔍 '{query}' 검색 결과\n\n{search_results}"
                
                response = f"🔍 '{query}' 검색 결과\n\n"
                
                for i, result in enumerate(results[:5], 1):
                    if isinstance(result, dict):
                        title = result.get("title", result.get("name", "제목 없음"))
                        snippet = result.get("snippet", result.get("description", result.get("summary", "내용 없음")))
                        url = result.get("url", result.get("link", ""))
                    else:
                        title = str(result)
                        snippet = "내용 없음"
                        url = ""
                    
                    response += f"{i}. **{title}**\n"
                    
                    # 스니펫 처리 - 줄바꿈 보존 및 HTML 태그 제거
                    processed_snippet = self._process_snippet_text(snippet)
                    response += f"   📝 {processed_snippet}\n"
                    
                    if url:
                        response += f"   🔗 <a href=\"{url}\" target=\"_blank\">{url}</a>\n"
                    response += "\n"
                
                return response
            else:
                # 응답이 문자열인 경우 (JSON 문자열)
                try:
                    import json
                    search_data = json.loads(str(search_results)) if isinstance(search_results, str) else search_results
                    return self._format_search_response(search_data, query)
                except:
                    # 파싱 실패 시 원본 응답 사용
                    return f"🔍 '{query}' 검색 결과\n\n{search_results}"
            
        except Exception as e:
            logger.error(f"검색 응답 포맷팅 실패: {e}")
            return f"'{query}' 검색 결과를 표시할 수 없습니다."
    
    async def process_rag_with_mcp(self, user_prompt: str, rag_service, session_id: Optional[str] = None) -> Tuple[str, bool]:
        """
        RAG와 MCP를 함께 사용하여 응답을 생성합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            rag_service: RAG 서비스 인스턴스
            session_id: 세션 ID
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"RAG + MCP 요청 처리: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        try:
            # 1. RAG 컨텍스트 검색
            context, context_sources = rag_service.retrieve_context(user_prompt, top_k=3)
            
            # 2. MCP 서비스 요청 (필요한 경우)
            mcp_data = {}
            
            # 날씨 관련 키워드 확인
            weather_keywords = ["날씨", "기온", "습도", "비", "눈", "맑음", "흐림"]
            if any(keyword in user_prompt for keyword in weather_keywords):
                location = self._extract_location_from_prompt(user_prompt)
                if location:
                    try:
                        weather_data = await self._make_mcp_request("weather", {
                            "location": location,
                            "query": user_prompt
                        })
                        if weather_data.get("success"):
                            weather_info = weather_data.get("data", {})
                            # 위치 정보를 weather_info에 추가
                            weather_info["location"] = location
                            mcp_data["weather"] = weather_info
                    except Exception as e:
                        logger.warning(f"날씨 데이터 가져오기 실패: {e}")
            
            # 주식 관련 키워드 확인
            stock_keywords = ["주가", "주식", "종목", "증시", "코스피", "코스닥"]
            if any(keyword in user_prompt for keyword in stock_keywords):
                stock_code = self._extract_stock_code_from_prompt(user_prompt)
                if stock_code:
                    try:
                        stock_data = await self._make_mcp_request("stock", {
                            "code": stock_code,
                            "query": user_prompt
                        })
                        if stock_data.get("success"):
                            # 주식 코드를 응답 데이터에 포함
                            stock_response = stock_data.get("data", {})
                            stock_response["code"] = stock_code  # 주식 코드 추가
                            mcp_data["stock"] = stock_response
                    except Exception as e:
                        logger.warning(f"주식 데이터 가져오기 실패: {e}")
            
            # 검색 관련 키워드 확인
            search_keywords = ["검색", "찾기", "최신", "뉴스", "정보"]
            if any(keyword in user_prompt for keyword in search_keywords):
                try:
                    search_data = await self._make_mcp_request("search", {
                        "query": user_prompt,
                        "max_results": 3
                    })
                    if search_data.get("success"):
                        mcp_data["search"] = search_data.get("data", [])
                except Exception as e:
                    logger.warning(f"검색 데이터 가져오기 실패: {e}")
            
            # 3. 통합 응답 생성
            response = self._generate_integrated_response(user_prompt, context, mcp_data)
            
        except Exception as e:
            logger.error(f"RAG + MCP 요청 처리 실패: {e}")
            response = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
        
        # 세션에 응답 추가
        if session_id:
            self.add_message_to_context(session_id, "assistant", response)
        
        return response, True
    
    def _generate_integrated_response(self, user_prompt: str, context: str, mcp_data: Dict[str, Any]) -> str:
        """RAG 컨텍스트와 MCP 데이터를 통합하여 응답을 생성합니다."""
        try:
            response_parts = []
            
            # MCP 데이터 처리
            if "weather" in mcp_data:
                weather_info = mcp_data["weather"]
                # 위치 정보 추출 - weather_info에서 직접 가져오거나 사용자 프롬프트에서 추출
                location = weather_info.get("location", "알 수 없는 위치")
                if location == "알 수 없는 위치":
                    # 사용자 프롬프트에서 위치 정보 재추출
                    extracted_location = self._extract_location_from_prompt(user_prompt)
                    if extracted_location:
                        location = extracted_location
                    else:
                        location = "서울"  # 기본값
                response_parts.append(self._format_weather_response(weather_info, location))
            
            if "stock" in mcp_data:
                stock_info = mcp_data["stock"]
                # stock_info에 code가 없으면 원본 stock_code 사용
                stock_code = stock_info.get("code", stock_info.get("stock_code", "알 수 없는 종목"))
                response_parts.append(self._format_stock_response(stock_info, stock_code))
            
            if "search" in mcp_data:
                search_results = mcp_data["search"]
                response_parts.append(self._format_search_response(search_results, user_prompt))
            

            
            # 응답 조합
            if response_parts:
                response = "\n\n".join(response_parts)
            else:
                response = "죄송합니다. 요청하신 정보를 찾을 수 없습니다."
            
            return response
            
        except Exception as e:
            logger.error(f"통합 응답 생성 실패: {e}")
            return "응답을 생성하는 중 오류가 발생했습니다."
    
    def _should_use_mcp(self, query: str) -> bool:
        """
        주어진 쿼리가 MCP 서비스를 사용해야 하는지 확인합니다.
        
        Args:
            query: 사용자 쿼리
            
        Returns:
            bool: MCP 서비스 사용 여부
        """
        # 날씨 관련 키워드
        weather_keywords = ["날씨", "기온", "습도", "비", "눈", "맑음", "흐림", "온도"]
        if any(keyword in query for keyword in weather_keywords):
            return True
        
        # 주식 관련 키워드
        stock_keywords = ["주가", "주식", "종목", "증시", "코스피", "코스닥", "삼성전자", "SK하이닉스"]
        if any(keyword in query for keyword in stock_keywords):
            return True
        
        # 검색 관련 키워드
        search_keywords = ["검색", "찾기", "최신", "뉴스", "정보", "어떻게", "무엇"]
        if any(keyword in query for keyword in search_keywords):
            return True
        
        return False

    def get_service_status(self) -> Dict[str, Any]:
        """MCP 서비스의 상태를 반환합니다."""
        try:
            return {
                "status": "active",
                "server_url": self.mcp_server_url,
                "model_name": "N/A", # model_name 파라미터가 제거되어 기본값 사용
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "active_sessions": len(self.session_contexts)
            }
        except Exception as e:
            logger.error(f"MCP 서비스 상태 확인 중 오류: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# 전역 인스턴스 생성
mcp_client_service = MCPClientService()

