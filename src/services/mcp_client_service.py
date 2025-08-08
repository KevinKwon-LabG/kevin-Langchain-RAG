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
from langchain_ollama import OllamaLLM
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
    # MCP 요청 대기 상태 관리
    weather_request_pending: bool = False
    stock_request_pending: bool = False
    pending_location: Optional[str] = None
    pending_stock_symbol: Optional[str] = None

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
        
        # 세션별 MCP 결정 방식 저장소
        self.session_mcp_decision_methods: Dict[str, str] = {}
        
        # HTTP 클라이언트 설정
        self.timeout = 30
        self.max_retries = 3
        
        # MCP 결정 방식 설정 (기본값: AI 기반)
        self.mcp_decision_method = getattr(settings, 'mcp_decision_method', 'ai')
        
        # 주식 종목 매핑 초기화 (애플리케이션 시작 시 한 번만 로드)
        self._stock_mapping_cache = None
        self._stock_reverse_mapping_cache = None
        self._initialize_stock_mapping()
        
        logger.info(f"MCP 클라이언트 서비스 초기화 - 서버: {self.mcp_server_url}, 결정방식: {self.mcp_decision_method}")
    
    def set_mcp_decision_method(self, method: str, session_id: str = None):
        """
        MCP 서비스 사용 결정 방식을 설정합니다.
        
        Args:
            method: 결정 방식 ('keyword' 또는 'ai')
            session_id: 세션 ID (None인 경우 전역 설정)
        """
        if method in ['keyword', 'ai']:
            if session_id:
                # 세션별 설정
                self.session_mcp_decision_methods[session_id] = method
                logger.info(f"세션 {session_id}의 MCP 결정 방식 변경: {method}")
            else:
                # 전역 설정
                self.mcp_decision_method = method
                logger.info(f"전역 MCP 결정 방식 변경: {method}")
        else:
            logger.warning(f"지원하지 않는 MCP 결정 방식: {method}. 기본값 'ai' 사용")
            if session_id:
                self.session_mcp_decision_methods[session_id] = 'ai'
            else:
                self.mcp_decision_method = 'ai'
    
    def get_mcp_decision_method(self, session_id: str = None) -> str:
        """
        현재 MCP 서비스 사용 결정 방식을 반환합니다.
        
        Args:
            session_id: 세션 ID (None인 경우 전역 설정 반환)
            
        Returns:
            str: 현재 결정 방식 ('keyword' 또는 'ai')
        """
        if session_id and session_id in self.session_mcp_decision_methods:
            return self.session_mcp_decision_methods[session_id]
        return self.mcp_decision_method
    
    def _should_clear_pending_state_by_ai(self, user_input: str, model_name: str = None) -> bool:
        """
        AI 모델을 사용하여 대화 주제가 변경되었는지 확인합니다.
        
        Args:
            user_input: 사용자 입력
            model_name: 사용할 AI 모델명 (None인 경우 기본 모델 사용)
            
        Returns:
            bool: 대화 주제가 변경되었으면 True, 아니면 False
        """
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            # 사용할 모델 결정
            target_model = model_name or settings.default_model
            logger.info(f"[대화 주제 변경 감지] 모델: {target_model}, 입력: {user_input}")
            
            # AI 결정을 위한 프롬프트 생성
            decision_prompt = f"""현재 사용자가 MCP 서비스(날씨, 주식 정보) 요청 대기 상태입니다.

사용자 입력: "{user_input}"

이 입력이 다음 중 하나에 해당하는지 판단해주세요:
1. 도시명, 주식 종목명, 종목 코드 6자리가 포함되어 있는 경우)
2. 대화 주제를 완전히 다른 것으로 바꾸려는 경우(위 1번과 관련 없는 경우)

답변은 반드시 "CONTINUE" 또는 "CHANGE"로만 해주세요. 설명은 필요하지 않습니다.
- 날씨/주식 정보 요청 계속: "CONTINUE"
- 대화 주제 변경: "CHANGE"
"""

            # AI 모델을 사용하여 결정
            try:
                # 방법 1: LangChain OllamaLLM 시도
                logger.info(f"[대화 주제 변경 감지] LangChain OllamaLLM 방식 시도")
                llm = OllamaLLM(
                    model=target_model,
                    base_url=settings.ollama_base_url,
                    timeout=settings.ollama_timeout
                )
                response = llm.invoke(decision_prompt)
                logger.info(f"[대화 주제 변경 감지] LangChain 방식 성공, 응답: {str(response)}")
                
            except Exception as e:
                logger.warning(f"[대화 주제 변경 감지] LangChain 방식 실패: {e}")
                
                # 방법 2: 직접 Ollama API 호출
                try:
                    logger.info(f"[대화 주제 변경 감지] 직접 Ollama API 호출 방식 시도")
                    import requests
                    
                    ollama_response = requests.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": target_model,
                            "prompt": decision_prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,  # 결정을 위해 낮은 temperature 사용
                                "top_p": 0.9,
                                "top_k": 40,
                                "repeat_penalty": 1.1,
                                "seed": -1
                            }
                        },
                        timeout=settings.ollama_timeout
                    )
                    
                    if ollama_response.status_code == 200:
                        response_data = ollama_response.json()
                        response = response_data.get('response', 'CONTINUE')
                        logger.info(f"[대화 주제 변경 감지] 직접 API 호출 성공, 응답: {str(response)}")
                    else:
                        logger.error(f"[대화 주제 변경 감지] Ollama API 오류: HTTP {ollama_response.status_code}")
                        return False
                        
                except Exception as e2:
                    logger.error(f"[대화 주제 변경 감지] 직접 API 호출 실패: {e2}")
                    return False
            
            # 응답 파싱 및 분석
            response_text = str(response).strip()
            
            # AI 모델 응답에서 특수 토큰들 제거
            response_text = re.sub(r'\n<end_of_turn>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<end_of_turn>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<|endoftext|>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<|im_end|>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<|im_start|>.*$', '', response_text, flags=re.DOTALL)
            
            # 줄바꿈과 공백 정리 후 대문자 변환
            response_text = re.sub(r'\n+', ' ', response_text)
            response_text = re.sub(r'\s+', ' ', response_text).strip().upper()
            
            logger.info(f"[대화 주제 변경 감지] 정규화된 응답: {response_text}")
            
            # 응답 내용 분석
            if "CHANGE" in response_text:
                logger.info(f"[대화 주제 변경 감지] 결과: 주제 변경 (CHANGE 포함)")
                return True
            else:
                logger.info(f"[대화 주제 변경 감지] 결과: 주제 계속 (CHANGE 없음)")
                return False
                
        except Exception as e:
            logger.error(f"❌ AI 기반 대화 주제 변경 감지 중 오류: {e}")
            # 오류 발생 시 기본적으로 계속 (안전한 선택)
            logger.info("🔄 AI 결정 실패, 기본값으로 계속")
            return False

    def _initialize_stock_mapping(self):
        """애플리케이션 시작 시 주식 종목 매핑을 초기화합니다."""
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            json_file = Path(settings.stocks_data_file)
            if not json_file.exists():
                logger.warning(f"{settings.stocks_data_file} 파일이 존재하지 않습니다. 기본 매핑을 사용합니다.")
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
    
    def set_weather_request_pending(self, session_id: str, location: str = None):
        """
        날씨 요청 대기 상태를 설정합니다.
        
        Args:
            session_id: 세션 ID
            location: 대기 중인 위치 정보
        """
        context = self.get_conversation_context(session_id)
        if not context:
            context = ConversationContext(
                session_id=session_id,
                previous_messages=[],
                current_request=""
            )
        
        context.weather_request_pending = True
        context.pending_location = location
        context.stock_request_pending = False  # 다른 요청 상태 해제
        context.pending_stock_symbol = None
        
        self.update_conversation_context(session_id, context)
        logger.info(f"세션 {session_id}에 날씨 요청 대기 상태 설정: {location}")
    
    def set_stock_request_pending(self, session_id: str, stock_symbol: str = None):
        """
        주식 요청 대기 상태를 설정합니다.
        
        Args:
            session_id: 세션 ID
            stock_symbol: 대기 중인 주식 심볼
        """
        context = self.get_conversation_context(session_id)
        if not context:
            context = ConversationContext(
                session_id=session_id,
                previous_messages=[],
                current_request=""
            )
        
        context.stock_request_pending = True
        context.pending_stock_symbol = stock_symbol
        context.weather_request_pending = False  # 다른 요청 상태 해제
        context.pending_location = None
        
        self.update_conversation_context(session_id, context)
        logger.info(f"세션 {session_id}에 주식 요청 대기 상태 설정: {stock_symbol}")
    
    def clear_pending_state(self, session_id: str):
        """
        모든 대기 상태를 해제합니다.
        
        Args:
            session_id: 세션 ID
        """
        context = self.get_conversation_context(session_id)
        if context:
            context.weather_request_pending = False
            context.stock_request_pending = False
            context.pending_location = None
            context.pending_stock_symbol = None
            
            self.update_conversation_context(session_id, context)
            logger.info(f"세션 {session_id}의 모든 대기 상태 해제")
    
    def get_pending_state(self, session_id: str) -> Dict[str, Any]:
        """
        현재 대기 상태를 반환합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Dict: 대기 상태 정보
        """
        context = self.get_conversation_context(session_id)
        if not context:
            return {
                "weather_request_pending": False,
                "stock_request_pending": False,
                "pending_location": None,
                "pending_stock_symbol": None
            }
        
        return {
            "weather_request_pending": context.weather_request_pending,
            "stock_request_pending": context.stock_request_pending,
            "pending_location": context.pending_location,
            "pending_stock_symbol": context.pending_stock_symbol
        }
    
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
        
        # MCP 도구 호출 로그 기록 (전체 파라미터 표시)
        logger.info(f"[MCP 도구 호출] 도구: {tool_name}")
        logger.info(f"[MCP 도구 호출] URL: {url}")
        logger.info(f"[MCP 도구 호출] 파라미터:")
        logger.info(json.dumps(request_data, ensure_ascii=False, indent=2))
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(url, json=request_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # MCP 응답 로그 기록 (전체 응답 표시)
                            response_str = json.dumps(result, ensure_ascii=False, indent=2)
                            logger.info(f"[MCP 도구 응답] 도구: {tool_name}")
                            logger.info(f"[MCP 도구 응답] 상태 코드: {response.status}")
                            logger.info(f"[MCP 도구 응답] 응답 내용:")
                            logger.info(response_str)
                            
                            return {
                                "success": True,
                                "data": result
                            }
                        else:
                            error_msg = f"MCP 요청 실패 (시도 {attempt + 1}): {response.status}"
                            logger.warning(f"[MCP 도구 오류] 도구: {tool_name}, {error_msg}")
                            
            except Exception as e:
                error_msg = f"MCP 요청 오류 (시도 {attempt + 1}): {e}"
                logger.warning(f"[MCP 도구 오류] 도구: {tool_name}, {error_msg}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)  # 재시도 전 대기
        
        raise Exception(f"MCP 서버 요청 실패: {endpoint}")
    
    def _extract_location_from_prompt(self, prompt: str) -> Optional[str]:
        """프롬프트에서 위치 정보를 추출합니다."""
        # 파일에서 도시 목록 로드
        korean_cities = self._load_korean_cities() # 한국 도시 목록 (weather_cities.csv) 파일에 있으며, get_weather_cities.py 파일에서 생성됨
        
        logger.info(f"도시 매칭 시작 - 프롬프트: '{prompt}'")
        logger.info(f"로드된 도시 목록 개수: {len(korean_cities)}개")
        
        for city in korean_cities:
            if city in prompt:
                logger.info(f"✅ 도시 매칭 성공: '{city}' - 프롬프트에서 발견됨")
                return city
        
        logger.warning(f"❌ 도시 매칭 실패 - 프롬프트에서 도시를 찾을 수 없음: '{prompt}'")
        return None
    
    def _load_korean_cities(self) -> List[str]:
        """저장된 파일에서 한국 도시 목록을 로드합니다."""
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            # 먼저 weather_cities.csv 파일 시도
            csv_file = Path(settings.weather_cities_csv_file)
            logger.info(f"CSV 파일 경로 확인: {csv_file.absolute()}")
            
            if csv_file.exists():
                logger.info(f"✅ CSV 파일 발견: {csv_file}")
                import csv
                cities = []
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        city_name = row.get('city_name', '').strip()
                        if city_name:
                            cities.append(city_name)
                
                if cities:
                    logger.info(f"✅ CSV 파일에서 도시 목록 로드 완료: {len(cities)}개 도시")
                    logger.debug(f"로드된 도시 목록 (처음 10개): {cities[:10]}")
                    return cities
                else:
                    logger.warning("CSV 파일이 비어있거나 유효한 도시 데이터가 없습니다.")
            else:
                logger.warning(f"❌ CSV 파일이 존재하지 않음: {csv_file}")
            
            # CSV 파일이 없거나 비어있으면 JSON 파일 시도
            json_file = Path(settings.weather_cities_json_file)
            logger.info(f"JSON 파일 경로 확인: {json_file.absolute()}")
            
            if json_file.exists():
                logger.info(f"✅ JSON 파일 발견: {json_file}")
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cities = data.get("cities", [])
                if cities:
                    logger.info(f"✅ JSON 파일에서 도시 목록 로드 완료: {len(cities)}개 도시")
                    logger.debug(f"로드된 도시 목록 (처음 10개): {cities[:10]}")
                    return cities
                else:
                    logger.warning("JSON 파일이 비어있거나 유효한 도시 데이터가 없습니다.")
            else:
                logger.warning(f"❌ JSON 파일이 존재하지 않음: {json_file}")
            
            # 파일이 없거나 비어있으면 기본 도시 목록 사용
            logger.warning("도시 목록 파일이 존재하지 않거나 비어있습니다. 기본 도시 목록을 사용합니다.")
            default_cities = self._get_default_cities()
            logger.info(f"기본 도시 목록 사용: {len(default_cities)}개 도시")
            return default_cities
                
        except Exception as e:
            logger.error(f"도시 목록 파일 로드 실패: {e}")
            default_cities = self._get_default_cities()
            logger.info(f"오류로 인해 기본 도시 목록 사용: {len(default_cities)}개 도시")
            return default_cities
    
    def _get_default_cities(self) -> List[str]:
        """기본 도시 목록을 반환합니다. (파일이 없거나 로드 실패 시 사용)"""
        from src.config.settings import get_settings
        settings = get_settings()
        return settings.default_cities
    
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
        from src.config.settings import get_settings
        settings = get_settings()
        return settings.default_stock_mapping
    
    async def _extract_search_query_from_prompt(self, user_prompt: str, model_name: str = None) -> str:
        """
        AI 모델을 사용하여 사용자 프롬프트에서 적절한 검색어를 추출합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            model_name: 사용할 AI 모델명
            
        Returns:
            str: 추출된 검색어
        """
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            # 사용할 모델 결정
            target_model = model_name or settings.default_model
            logger.info(f"[검색어 추출] 모델: {target_model}, 프롬프트: {user_prompt}")
            
            # 검색어 추출을 위한 프롬프트 생성
            extraction_prompt = f"""다음 사용자 질문에서 웹 검색에 적합한 핵심 검색어를 추출해주세요.

사용자 질문: "{user_prompt}"

검색어 추출 규칙:
1. 질문의 핵심 주제나 키워드를 추출
2. 불필요한 조사, 문장 부호, "알려줘", "검색해줘" 등의 요청어는 제거
3. 검색에 적합한 명사나 명사구 위주로 추출
4. 2-5개의 핵심 단어로 구성
5. 한국어로 추출
6. 원본 질문과 다른 간결한 검색어로 추출

예시:
- "AI의 정의에 대해 웹에서 검색해서 요약해줘" → "AI 정의"
- "최신 인공지능 기술 동향을 알려줘" → "인공지능 기술 동향"
- "2024년 한국 경제 전망은?" → "2024년 한국 경제 전망"
- "파이썬 프로그래밍 기초를 배우고 싶어" → "파이썬 프로그래밍 기초"
- "최신 경제 뉴스를 알려줘" → "최신 경제 뉴스"
- "OpenAI 최신 기사를 찾아줘" → "OpenAI 최신 기사"

추출된 검색어만 답변해주세요. 설명이나 따옴표는 필요하지 않습니다."""

            # AI 모델을 사용하여 검색어 추출
            try:
                # 방법 1: LangChain OllamaLLM 시도
                logger.info(f"[검색어 추출] LangChain OllamaLLM 방식 시도")
                llm = OllamaLLM(
                    model=target_model,
                    base_url=settings.ollama_base_url,
                    timeout=settings.ollama_timeout
                )
                response = llm.invoke(extraction_prompt)
                logger.info(f"[검색어 추출] LangChain 방식 성공, 응답: {str(response)}")
                
            except Exception as e:
                logger.warning(f"[검색어 추출] LangChain 방식 실패: {e}")
                
                # 방법 2: 직접 Ollama API 호출
                try:
                    logger.info(f"[검색어 추출] 직접 Ollama API 호출 방식 시도")
                    import requests
                    
                    ollama_response = requests.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": target_model,
                            "prompt": extraction_prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,  # 일관성을 위해 낮은 temperature 사용
                                "top_p": 0.9,
                                "top_k": 40,
                                "repeat_penalty": 1.1,
                                "seed": -1
                            }
                        },
                        timeout=settings.ollama_timeout
                    )
                    
                    if ollama_response.status_code == 200:
                        response_data = ollama_response.json()
                        response = response_data.get('response', user_prompt)
                        logger.info(f"[검색어 추출] 직접 API 호출 성공, 응답: {str(response)}")
                    else:
                        logger.error(f"[검색어 추출] Ollama API 오류: HTTP {ollama_response.status_code}")
                        return user_prompt
                        
                except Exception as e2:
                    logger.error(f"[검색어 추출] 직접 API 호출 실패: {e2}")
                    return user_prompt
            
            # 응답 정리
            extracted_query = str(response).strip()
            
            # 응답에서 불필요한 문자 제거
            extracted_query = re.sub(r'["""]', '', extracted_query).strip()
            
            # AI 모델 응답에서 특수 토큰들 제거
            extracted_query = re.sub(r'\n<end_of_turn>.*$', '', extracted_query, flags=re.DOTALL)
            extracted_query = re.sub(r'<end_of_turn>.*$', '', extracted_query, flags=re.DOTALL)
            extracted_query = re.sub(r'/end_of_turn.*$', '', extracted_query, flags=re.DOTALL)
            extracted_query = re.sub(r'<|endoftext|>.*$', '', extracted_query, flags=re.DOTALL)
            extracted_query = re.sub(r'<|im_end|>.*$', '', extracted_query, flags=re.DOTALL)
            extracted_query = re.sub(r'<|im_start|>.*$', '', extracted_query, flags=re.DOTALL)
            
            # 줄바꿈과 공백 정리
            extracted_query = re.sub(r'\n+', ' ', extracted_query)
            extracted_query = re.sub(r'\s+', ' ', extracted_query).strip()
            
            # 응답이 너무 길거나 부적절한 경우 원본 프롬프트 사용
            if len(extracted_query) > 100 or not extracted_query or extracted_query == user_prompt:
                logger.warning(f"[검색어 추출] 추출된 검색어가 부적절함: '{extracted_query}', 원본 사용")
                return user_prompt
            
            logger.info(f"[검색어 추출] 최종 검색어: '{extracted_query}'")
            return extracted_query
                
        except Exception as e:
            logger.error(f"❌ 검색어 추출 중 오류: {e}")
            # 오류 발생 시 원본 프롬프트 사용
            logger.info("🔄 검색어 추출 실패, 원본 프롬프트 사용")
            return user_prompt
    
    async def process_weather_request(self, user_prompt: str, session_id: Optional[str] = None, model_name: str = None) -> Tuple[str, bool]:
        """
        날씨 요청을 처리합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID
            model_name: AI 모델명 (대화 주제 변경 감지용)
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"[MCP 날씨 요청] 사용자 프롬프트: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        # 대기 상태 확인
        pending_state = self.get_pending_state(session_id)
        
        # 날씨 요청 대기 상태에서 도시명 입력 처리
        if pending_state["weather_request_pending"]:
            logger.info(f"[MCP 날씨 요청] 날씨 요청 대기 상태에서 입력: '{user_prompt}'")
            
            # 입력이 도시명인지 확인
            location = self._extract_location_from_prompt(user_prompt)
            if location:
                logger.info(f"[MCP 날씨 요청] ✅ 대기 상태에서 도시명 인식: '{location}'")
                # 대기 상태 해제
                self.clear_pending_state(session_id)
                
                # MCP 서버에 날씨 요청
                try:
                    weather_data = await self._make_mcp_request("weather", {
                        "location": location,
                        "query": user_prompt
                    })
                    
                    # 응답 생성
                    if weather_data.get("success"):
                        # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                        # 실제 MCP 서버 응답은 weather_data["data"]에 있음
                        mcp_response = weather_data.get("data", {})
                        weather_info = mcp_response.get("result", mcp_response)
                        # 위치 정보를 weather_info에 추가
                        weather_info["location"] = location
                        response = self._format_weather_response(weather_info, location)
                    else:
                        response = f"죄송합니다. {location}의 날씨 정보를 가져올 수 없습니다."
                    
                    # 세션에 응답 추가
                    if session_id:
                        self.add_message_to_context(session_id, "assistant", response)
                    
                    return response, True
                    
                except Exception as e:
                    logger.error(f"대기 상태에서 날씨 요청 처리 실패: {e}")
                    if "Connection reset by peer" in str(e) or "Connection refused" in str(e):
                        response = "🌐 MCP 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
                    else:
                        response = f"날씨 정보 서비스에 일시적인 오류가 발생했습니다: {str(e)}"
                    
                    if session_id:
                        self.add_message_to_context(session_id, "assistant", response)
                    
                    return response, True
            
            # 도시명이 아닌 경우 대화 주제 변경 감지
            if self._should_clear_pending_state_by_ai(user_prompt, model_name):
                logger.info(f"[MCP 날씨 요청] 대화 주제 변경 감지, 대기 상태 해제")
                self.clear_pending_state(session_id)
                response = "네, 다른 주제로 대화를 이어가겠습니다. 무엇을 도와드릴까요?"
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                return response, True
            
            # 도시명도 아니고 주제 변경도 아닌 경우, 다시 도시명 요청
            logger.info(f"[MCP 날씨 요청] 도시명이 아닌 입력, 다시 요청")
            response = "🌤️ 날씨 정보를 제공하기 위해 도시명을 알려주세요. (예: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 제주 등)"
            if session_id:
                self.add_message_to_context(session_id, "assistant", response)
            return response, False
        
        try:
            # 위치 정보 추출
            logger.info(f"날씨 요청에서 위치 정보 추출 시작: '{user_prompt}'")
            location = self._extract_location_from_prompt(user_prompt)
            
            if not location:
                # 위치 정보가 없으면 대기 상태 설정
                logger.info(f"위치 정보 추출 실패, 사용자에게 입력 요청")
                response = "🌤️ 날씨 정보를 제공하기 위해 도시명을 알려주세요. (예: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 제주 등)"
                if session_id:
                    self.set_weather_request_pending(session_id)
                    self.add_message_to_context(session_id, "assistant", response)
                return response, False  # 완료되지 않음
            else:
                logger.info(f"✅ 위치 정보 추출 성공: '{location}'")
                # 대기 상태 해제
                if session_id:
                    self.clear_pending_state(session_id)
            
            # MCP 서버에 날씨 요청
            weather_data = await self._make_mcp_request("weather", {
                "location": location,
                "query": user_prompt
            })
            
            # 응답 생성
            if weather_data.get("success"):
                # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                # 실제 MCP 서버 응답은 weather_data["data"]에 있음
                mcp_response = weather_data.get("data", {})
                weather_info = mcp_response.get("result", mcp_response)
                # 위치 정보를 weather_info에 추가
                weather_info["location"] = location
                response = self._format_weather_response(weather_info, location)
            else:
                response = f"죄송합니다. {location}의 날씨 정보를 가져올 수 없습니다."
            
        except Exception as e:
            logger.error(f"날씨 요청 처리 실패: {e}")
            if "Connection reset by peer" in str(e) or "Connection refused" in str(e):
                response = "🌐 MCP 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
            else:
                response = f"날씨 정보 서비스에 일시적인 오류가 발생했습니다: {str(e)}"
        
        # 세션에 응답 추가
        if session_id:
            self.add_message_to_context(session_id, "assistant", response)
        
        return response, True
    
    def _format_weather_response(self, weather_info: Dict[str, Any], location: str) -> str:
        """날씨 정보를 포맷팅합니다."""
        try:
            logger.info(f"[날씨 포맷팅] 시작 - location: {location}, weather_info 타입: {type(weather_info)}")
            logger.info(f"[날씨 포맷팅] weather_info 키: {list(weather_info.keys()) if isinstance(weather_info, dict) else 'Not a dict'}")
            
            # 위치 정보가 "알 수 없는 위치"인 경우 기본값으로 변경
            if location == "알 수 없는 위치":
                location = "서울"
            
            # MCP 서버의 실제 응답 형식에 맞게 수정
            if isinstance(weather_info, dict):
                # MCP 서버 응답 구조: {"success": true, "result": {"success": true, "data": {...}}}
                # 또는 process_rag_with_mcp에서 이미 result 필드를 추출한 경우: {"success": true, "data": {...}, "content": [...]}
                
                # content 필드가 있는 경우 (이미 포맷된 텍스트) - 우선 처리
                logger.info(f"[날씨 포맷팅] content 필드 확인: {'content' in weather_info}")
                if "content" in weather_info:
                    logger.info(f"[날씨 포맷팅] content 타입: {type(weather_info['content'])}")
                    if isinstance(weather_info["content"], list):
                        logger.info(f"[날씨 포맷팅] content 필드 발견: {len(weather_info['content'])}개 항목")
                    for i, content_item in enumerate(weather_info["content"]):
                        logger.info(f"[날씨 포맷팅] content_item[{i}]: {content_item}")
                        if isinstance(content_item, dict) and content_item.get("type") == "text":
                            formatted_text = content_item.get("text", f"{location}의 날씨 정보를 표시할 수 없습니다.")
                            logger.info(f"[날씨 포맷팅] 원본 content 텍스트: {formatted_text}")
                            # content 텍스트에 위치 정보가 없으면 추가
                            if location not in formatted_text:
                                formatted_text = f"📍 {location} {formatted_text}"
                            logger.info(f"[날씨 포맷팅] 최종 content 텍스트 반환: {formatted_text}")
                            return formatted_text
                
                # data 필드가 있는 경우 (구조화된 데이터)
                if "data" in weather_info and isinstance(weather_info["data"], dict):
                    data = weather_info["data"]
                elif "result" in weather_info and isinstance(weather_info["result"], dict):
                    result_data = weather_info["result"]
                    
                    # content 필드가 있는 경우 (이미 포맷된 텍스트) - 우선 처리
                    if "content" in result_data and isinstance(result_data["content"], list):
                        for content_item in result_data["content"]:
                            if isinstance(content_item, dict) and content_item.get("type") == "text":
                                formatted_text = content_item.get("text", f"{location}의 날씨 정보를 표시할 수 없습니다.")
                                # content 텍스트에 위치 정보가 없으면 추가
                                if location not in formatted_text:
                                    formatted_text = f"📍 {location} {formatted_text}"
                                logger.info(f"[날씨 포맷팅] content 텍스트 반환: {formatted_text}")
                                return formatted_text
                    
                    # data 필드가 있는 경우 (구조화된 데이터)
                    if "data" in result_data and isinstance(result_data["data"], dict):
                        data = result_data["data"]
                    else:
                        # result_data 자체가 data인 경우
                        data = result_data
                else:
                    # weather_info 자체가 data인 경우
                    data = weather_info
                
                # 구조화된 데이터에서 날씨 정보 추출
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
                
                logger.info(f"[날씨 포맷팅] 구조화된 데이터 응답 생성 완료")
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
    
    async def process_stock_request(self, user_prompt: str, session_id: Optional[str] = None, model_name: str = None) -> Tuple[str, bool]:
        """
        주식 요청을 처리합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID
            model_name: AI 모델명 (대화 주제 변경 감지용)
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"[MCP 주식 요청] 사용자 프롬프트: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        # 대기 상태 확인
        pending_state = self.get_pending_state(session_id)
        
        # 주식 요청 대기 상태에서 종목명/종목코드 입력 처리
        if pending_state["stock_request_pending"]:
            logger.info(f"[MCP 주식 요청] 주식 요청 대기 상태에서 입력: '{user_prompt}'")
            
            # 입력이 종목명/종목코드인지 확인
            stock_code = self._extract_stock_code_from_prompt(user_prompt)
            if stock_code:
                logger.info(f"[MCP 주식 요청] ✅ 대기 상태에서 종목코드 인식: '{stock_code}'")
                # 대기 상태 해제
                self.clear_pending_state(session_id)
                
                # MCP 서버에 주식 요청
                try:
                    stock_data = await self._make_mcp_request("stock", {
                        "code": stock_code,
                        "query": user_prompt
                    })
                    
                    # 응답 생성
                    if stock_data.get("success"):
                        # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                        # 실제 MCP 서버 응답은 stock_data["data"]에 있음
                        mcp_response = stock_data.get("data", {})
                        stock_info = mcp_response.get("result", mcp_response)
                        # 주식 코드를 응답 데이터에 포함
                        stock_info["code"] = stock_code
                        response = self._format_stock_response(stock_info, stock_code)
                    else:
                        response = f"죄송합니다. 종목 코드 {stock_code}의 주식 정보를 가져올 수 없습니다."
                    
                    # 세션에 응답 추가
                    if session_id:
                        self.add_message_to_context(session_id, "assistant", response)
                    
                    return response, True
                    
                except Exception as e:
                    logger.error(f"대기 상태에서 주식 요청 처리 실패: {e}")
                    if "Connection reset by peer" in str(e) or "Connection refused" in str(e):
                        response = "🌐 MCP 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
                    else:
                        response = f"주식 정보 서비스에 일시적인 오류가 발생했습니다: {str(e)}"
                    
                    if session_id:
                        self.add_message_to_context(session_id, "assistant", response)
                    
                    return response, True
            
            # 종목명/종목코드가 아닌 경우 대화 주제 변경 감지
            if self._should_clear_pending_state_by_ai(user_prompt, model_name):
                logger.info(f"[MCP 주식 요청] 대화 주제 변경 감지, 대기 상태 해제")
                self.clear_pending_state(session_id)
                response = "네, 다른 주제로 대화를 이어가겠습니다. 무엇을 도와드릴까요?"
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                return response, True
            
            # 종목명/종목코드도 아니고 주제 변경도 아닌 경우, 다시 종목명 요청
            logger.info(f"[MCP 주식 요청] 종목명/종목코드가 아닌 입력, 다시 요청")
            response = "📈 주식 정보를 제공하기 위해 종목명이나 종목코드를 알려주세요. (예: 삼성전자, 005930, SK하이닉스, 000660, LG전자, 066570 등)"
            if session_id:
                self.add_message_to_context(session_id, "assistant", response)
            return response, False
        
        try:
            # 주식 종목 코드 추출
            stock_code = self._extract_stock_code_from_prompt(user_prompt)
            
            if not stock_code:
                # 주식 종목 코드가 없으면 대기 상태 설정
                logger.info(f"주식 종목 코드 추출 실패, 사용자에게 입력 요청")
                response = "📈 주식 정보를 제공하기 위해 종목명이나 종목코드를 알려주세요. (예: 삼성전자, 005930, SK하이닉스, 000660, LG전자, 066570 등)"
                if session_id:
                    self.set_stock_request_pending(session_id)
                    self.add_message_to_context(session_id, "assistant", response)
                return response, False  # 완료되지 않음
            else:
                logger.info(f"✅ 주식 종목 코드 추출 성공: '{stock_code}'")
                # 대기 상태 해제
                if session_id:
                    self.clear_pending_state(session_id)
            
            # MCP 서버에 주식 요청
            stock_data = await self._make_mcp_request("stock", {
                "code": stock_code,
                "query": user_prompt
            })
            
            # 응답 생성
            if stock_data.get("success"):
                # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                # 실제 MCP 서버 응답은 stock_data["data"]에 있음
                mcp_response = stock_data.get("data", {})
                stock_info = mcp_response.get("result", mcp_response)
                # 주식 코드를 응답 데이터에 포함
                stock_info["code"] = stock_code
                response = self._format_stock_response(stock_info, stock_code)
            else:
                response = f"죄송합니다. 종목 코드 {stock_code}의 주식 정보를 가져올 수 없습니다."
            
        except Exception as e:
            logger.error(f"주식 요청 처리 실패: {e}")
            if "Connection reset by peer" in str(e) or "Connection refused" in str(e):
                response = "🌐 MCP 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
            else:
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
                # 새로운 MCP 응답 형식 처리 (Basic Information, Financial Data 포함)
                if "Basic Information" in stock_info and isinstance(stock_info["Basic Information"], dict):
                    # 새로운 MCP 응답 형식
                    basic_info = stock_info["Basic Information"]
                    company_name = basic_info.get("Company Name", "N/A")
                    
                    # 회사명이 N/A인 경우 종목 코드로 대체
                    if company_name == "N/A":
                        company_name = self._get_stock_name_by_code(stock_code)
                    
                    # 재무 데이터
                    price = "N/A"
                    pe_ratio = "N/A"
                    pb_ratio = "N/A"
                    dividend_yield = "N/A"
                    
                    if "Financial Data" in stock_info and isinstance(stock_info["Financial Data"], dict):
                        financial_data = stock_info["Financial Data"]
                        price = financial_data.get("Latest Stock Price", "N/A")
                        pe_ratio = financial_data.get("Price-Earnings Ratio", "N/A")
                        pb_ratio = financial_data.get("Price-Book Ratio", "N/A")
                        dividend_yield = financial_data.get("Dividend Yield", "N/A")
                    
                    # 데이터 신선도
                    data_source = "N/A"
                    data_quality = "N/A"
                    if "Data Freshness" in stock_info and isinstance(stock_info["Data Freshness"], dict):
                        freshness = stock_info["Data Freshness"]
                        data_source = freshness.get("Data Source", "N/A")
                        data_quality = freshness.get("Data Quality", "N/A")
                    
                    response = f"📈 {company_name} ({stock_code}) 주식 정보\n\n"
                    
                    # 현재가 포맷팅 (숫자 타입 처리) - 소숫점 제거하고 천단위 콤마 적용
                    if isinstance(price, (int, float)) and price != "N/A":
                        # 소숫점 제거하고 천단위 콤마 적용
                        formatted_price = f"{int(price):,}"
                        response += f"💰 현재가: {formatted_price}원\n"
                    elif isinstance(price, str) and price != "N/A":
                        # 문자열인 경우 숫자로 변환 시도
                        try:
                            # 소숫점이 포함된 경우 제거
                            if '.' in price:
                                price = price.split('.')[0]
                            numeric_price = int(price)
                            formatted_price = f"{numeric_price:,}"
                            response += f"💰 현재가: {formatted_price}원\n"
                        except (ValueError, TypeError):
                            response += f"💰 현재가: {price}원\n"
                    else:
                        response += f"💰 현재가: {price}원\n"
                    
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
                
                # 현재가 포맷팅 (숫자 타입 처리) - 소숫점 제거하고 천단위 콤마 적용
                if isinstance(price, (int, float)) and price != "N/A":
                    # 소숫점 제거하고 천단위 콤마 적용
                    formatted_price = f"{int(price):,}"
                    response += f"💰 현재가: {formatted_price}원\n"
                elif isinstance(price, str) and price != "N/A":
                    # 문자열인 경우 숫자로 변환 시도
                    try:
                        # 소숫점이 포함된 경우 제거
                        if '.' in price:
                            price = price.split('.')[0]
                        numeric_price = int(price)
                        formatted_price = f"{numeric_price:,}"
                        response += f"💰 현재가: {formatted_price}원\n"
                    except (ValueError, TypeError):
                        response += f"💰 현재가: {price}원\n"
                else:
                    response += f"💰 현재가: {price}원\n"
                
                # 변동 포맷팅 (숫자 타입 처리) - 소숫점 제거하고 천단위 콤마 적용
                if isinstance(change, (int, float)) and change != "N/A" and change != 0:
                    change_symbol = "📈" if change >= 0 else "📉"
                    # 소숫점 제거하고 천단위 콤마 적용
                    formatted_change = f"{int(change):+,}"
                    response += f"{change_symbol} 변동: {formatted_change}원 ({change_rate:+.2f}%)\n"
                elif isinstance(change, str) and change != "N/A" and change != "0":
                    change_symbol = "📈" if not change.startswith('-') else "📉"
                    # 문자열인 경우 숫자로 변환 시도
                    try:
                        # 소숫점이 포함된 경우 제거
                        if '.' in change:
                            change = change.split('.')[0]
                        numeric_change = int(change)
                        formatted_change = f"{numeric_change:+,}"
                        response += f"{change_symbol} 변동: {formatted_change}원 ({change_rate}%)\n"
                    except (ValueError, TypeError):
                        response += f"{change_symbol} 변동: {change}원 ({change_rate}%)\n"
                elif change != "N/A" and change != 0:
                    change_symbol = "📈" if change >= 0 else "📉"
                    response += f"{change_symbol} 변동: {change}원 ({change_rate}%)\n"
                
                # 거래량 포맷팅 (숫자 타입 처리) - 소숫점 제거하고 천단위 콤마 적용
                if isinstance(volume, (int, float)) and volume != "N/A":
                    # 소숫점 제거하고 천단위 콤마 적용
                    formatted_volume = f"{int(volume):,}"
                    response += f"📊 거래량: {formatted_volume}주\n"
                elif isinstance(volume, str) and volume != "N/A":
                    # 문자열인 경우 숫자로 변환 시도
                    try:
                        # 소숫점이 포함된 경우 제거
                        if '.' in volume:
                            volume = volume.split('.')[0]
                        numeric_volume = int(volume)
                        formatted_volume = f"{numeric_volume:,}"
                        response += f"📊 거래량: {formatted_volume}주\n"
                    except (ValueError, TypeError):
                        response += f"📊 거래량: {volume}주\n"
                else:
                    response += f"📊 거래량: {volume}주\n"
                
                # 시가총액 포맷팅 (숫자 타입 처리) - 소숫점 제거하고 천단위 콤마 적용
                if isinstance(market_cap, (int, float)) and market_cap != "N/A":
                    # 소숫점 제거하고 천단위 콤마 적용
                    formatted_market_cap = f"{int(market_cap):,}"
                    response += f"🏢 시가총액: {formatted_market_cap}원\n"
                elif isinstance(market_cap, str) and market_cap != "N/A":
                    # 문자열인 경우 숫자로 변환 시도
                    try:
                        # 소숫점이 포함된 경우 제거
                        if '.' in market_cap:
                            market_cap = market_cap.split('.')[0]
                        numeric_market_cap = int(market_cap)
                        formatted_market_cap = f"{numeric_market_cap:,}"
                        response += f"🏢 시가총액: {formatted_market_cap}원\n"
                    except (ValueError, TypeError):
                        response += f"🏢 시가총액: {market_cap}원\n"
                else:
                    response += f"🏢 시가총액: {market_cap}원\n"
                
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
    
    async def process_web_search_request(self, user_prompt: str, session_id: Optional[str] = None, model_name: str = None) -> Tuple[str, bool]:
        """
        웹 검색 요청을 처리합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID
            model_name: AI 모델명 (검색어 추출에 사용)
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"[MCP 웹 검색 요청] 사용자 프롬프트: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        try:
            # AI 모델을 사용하여 검색어 추출
            search_query = await self._extract_search_query_from_prompt(user_prompt, model_name)
            logger.info(f"[MCP 웹 검색] 추출된 검색어: '{search_query}'")
            
            # MCP 서버에 웹 검색 요청
            search_data = await self._make_mcp_request("search", {
                "query": search_query,
                "max_results": 5
            })
            
            # 응답 생성
            if search_data.get("success"):
                # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                # 실제 MCP 서버 응답은 search_data["data"]에 있음
                mcp_response = search_data.get("data", {})
                result_data = mcp_response.get("result", {})
                search_results = result_data.get("results", [])
                
                # _format_search_response에 전달할 데이터 구조 생성
                formatted_data = {
                    "query": search_query,
                    "results": search_results,
                    "total_results": result_data.get("total_results", "N/A"),
                    "search_time": result_data.get("search_time", "N/A")
                }
                response = self._format_search_response(formatted_data, user_prompt)
            else:
                response = f"죄송합니다. '{user_prompt}'에 대한 검색 결과를 가져올 수 없습니다."
            
        except Exception as e:
            logger.error(f"웹 검색 요청 처리 실패: {e}")
            if "Connection reset by peer" in str(e) or "Connection refused" in str(e):
                response = "🌐 MCP 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
            else:
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

    def _format_search_response(self, search_data: Dict[str, Any], query: str) -> str:
        """검색 결과를 포맷팅합니다."""
        try:
            # 디버깅을 위한 로그 추가
            logger.info(f"[검색 응답 포맷팅] 시작 - search_data 타입: {type(search_data)}")
            logger.info(f"[검색 응답 포맷팅] search_data 키: {list(search_data.keys()) if isinstance(search_data, dict) else 'N/A'}")
            logger.info(f"[검색 응답 포맷팅] search_data 내용: {search_data}")
            
            # MCP 데이터 구조에 맞게 수정
            if not search_data or not isinstance(search_data, dict):
                logger.warning(f"[검색 응답 포맷팅] search_data가 유효하지 않음: {search_data}")
                return f"'{query}'에 대한 검색 결과를 찾을 수 없습니다."
            
            results = search_data.get("results", [])
            total_results = search_data.get("total_results", "N/A")
            search_time = search_data.get("search_time", "N/A")
            
            logger.info(f"[검색 응답 포맷팅] results 개수: {len(results) if results else 0}")
            logger.info(f"[검색 응답 포맷팅] total_results: {total_results}")
            logger.info(f"[검색 응답 포맷팅] search_time: {search_time}")
            
            if not results:
                logger.warning(f"[검색 응답 포맷팅] results가 비어있음")
                return f"'{query}'에 대한 검색 결과를 찾을 수 없습니다."
            
            response = f"🔍 **'{query}' 검색 결과**\n\n"
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
            
        except Exception as e:
            logger.error(f"검색 응답 포맷팅 실패: {e}")
            return f"'{query}' 검색 결과를 표시할 수 없습니다."
            
        except Exception as e:
            logger.error(f"검색 응답 포맷팅 실패: {e}")
            return f"'{query}' 검색 결과를 표시할 수 없습니다."
    
    async def process_rag_with_mcp(self, user_prompt: str, rag_service, session_id: Optional[str] = None, model_name: str = None) -> Tuple[str, bool]:
        """
        RAG와 MCP를 함께 사용하여 응답을 생성합니다.
        
        Args:
            user_prompt: 사용자 프롬프트
            rag_service: RAG 서비스 인스턴스
            session_id: 세션 ID
            model_name: AI 모델명 (대화 주제 변경 감지용)
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        logger.info(f"[MCP RAG 통합 요청] 사용자 프롬프트: {user_prompt}")
        
        # 세션에 메시지 추가
        if session_id:
            self.add_message_to_context(session_id, "user", user_prompt)
        
        # 대기 상태 확인
        pending_state = self.get_pending_state(session_id)
        
        # 날씨 요청 대기 상태에서 도시명 입력 처리
        if pending_state["weather_request_pending"]:
            logger.info(f"[MCP RAG 통합] 날씨 요청 대기 상태에서 입력: '{user_prompt}'")
            
            # 입력이 도시명인지 확인
            location = self._extract_location_from_prompt(user_prompt)
            if location:
                logger.info(f"[MCP RAG 통합] ✅ 대기 상태에서 도시명 인식: '{location}'")
                # 대기 상태 해제
                self.clear_pending_state(session_id)
                
                # MCP 서버에 날씨 요청
                mcp_data = {}
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
                        logger.info(f"[MCP RAG 통합] ✅ 날씨 데이터 성공적으로 추가됨: {location}")
                    else:
                        logger.warning(f"[MCP RAG 통합] 날씨 데이터 요청 실패: {weather_data}")
                except Exception as e:
                    logger.warning(f"대기 상태에서 날씨 데이터 가져오기 실패: {e}")
                
                # RAG 컨텍스트 검색
                context, context_sources = rag_service.retrieve_context(user_prompt, top_k=3)
                
                # 통합 응답 생성
                logger.info(f"[MCP RAG 통합] 통합 응답 생성 시작 - mcp_data: {list(mcp_data.keys())}")
                response = self._generate_integrated_response(user_prompt, context, mcp_data)
                
                # 세션에 응답 추가
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                
                return response, True
            
            # 도시명이 아닌 경우 대화 주제 변경 감지
            if self._should_clear_pending_state_by_ai(user_prompt, model_name):
                logger.info(f"[MCP RAG 통합] 대화 주제 변경 감지, 대기 상태 해제")
                self.clear_pending_state(session_id)
                response = "네, 다른 주제로 대화를 이어가겠습니다. 무엇을 도와드릴까요?"
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                return response, True
            
            # 도시명도 아니고 주제 변경도 아닌 경우, 다시 도시명 요청
            logger.info(f"[MCP RAG 통합] 도시명이 아닌 입력, 다시 요청")
            response = "🌤️ 날씨 정보를 제공하기 위해 도시명을 알려주세요. (예: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 제주 등)"
            if session_id:
                self.add_message_to_context(session_id, "assistant", response)
            return response, False
        
        # 주식 요청 대기 상태에서 종목명/종목코드 입력 처리
        if pending_state["stock_request_pending"]:
            logger.info(f"[MCP RAG 통합] 주식 요청 대기 상태에서 입력: '{user_prompt}'")
            
            # 입력이 종목명/종목코드인지 확인
            stock_code = self._extract_stock_code_from_prompt(user_prompt)
            if stock_code:
                logger.info(f"[MCP RAG 통합] ✅ 대기 상태에서 종목코드 인식: '{stock_code}'")
                # 대기 상태 해제
                self.clear_pending_state(session_id)
                
                # MCP 서버에 주식 요청
                mcp_data = {}
                try:
                    stock_data = await self._make_mcp_request("stock", {
                        "code": stock_code,
                        "query": user_prompt
                    })
                    if stock_data.get("success"):
                        # 주식 코드를 응답 데이터에 포함
                        mcp_response = stock_data.get("data", {})
                        # 새로운 MCP 응답 형식 처리
                        if "result" in mcp_response and isinstance(mcp_response["result"], dict):
                            stock_response = mcp_response["result"]
                        else:
                            # 기존 형식 지원
                            stock_response = mcp_response
                        stock_response["code"] = stock_code  # 주식 코드 추가
                        mcp_data["stock"] = stock_response
                        logger.info(f"[MCP RAG 통합] ✅ 주식 데이터 성공적으로 추가됨: {stock_code}")
                    else:
                        logger.warning(f"[MCP RAG 통합] 주식 데이터 요청 실패: {stock_data}")
                except Exception as e:
                    logger.warning(f"대기 상태에서 주식 데이터 가져오기 실패: {e}")
                
                # RAG 컨텍스트 검색
                context, context_sources = rag_service.retrieve_context(user_prompt, top_k=3)
                
                # 통합 응답 생성
                logger.info(f"[MCP RAG 통합] 통합 응답 생성 시작 - mcp_data: {list(mcp_data.keys())}")
                response = self._generate_integrated_response(user_prompt, context, mcp_data)
                
                # 세션에 응답 추가
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                
                return response, True
            
            # 종목명/종목코드가 아닌 경우 대화 주제 변경 감지
            if self._should_clear_pending_state_by_ai(user_prompt, model_name):
                logger.info(f"[MCP RAG 통합] 대화 주제 변경 감지, 대기 상태 해제")
                self.clear_pending_state(session_id)
                response = "네, 다른 주제로 대화를 이어가겠습니다. 무엇을 도와드릴까요?"
                if session_id:
                    self.add_message_to_context(session_id, "assistant", response)
                return response, True
            
            # 종목명/종목코드도 아니고 주제 변경도 아닌 경우, 다시 종목명 요청
            logger.info(f"[MCP RAG 통합] 종목명/종목코드가 아닌 입력, 다시 요청")
            response = "📈 주식 정보를 제공하기 위해 종목명이나 종목코드를 알려주세요. (예: 삼성전자, 005930, SK하이닉스, 000660, LG전자, 066570 등)"
            if session_id:
                self.add_message_to_context(session_id, "assistant", response)
            return response, False
        
        # MCP 서비스 요청 데이터 초기화
        mcp_data = {}
        
        # RAG 컨텍스트 검색
        context, context_sources = rag_service.retrieve_context(user_prompt, top_k=3)
        
        try:
            # 2. MCP 서비스 요청 (필요한 경우) - 일반적인 요청 처리
            
            # 날씨 관련 키워드 확인
            from src.config.settings import get_settings
            settings = get_settings()
            weather_keywords = settings.mcp_weather_keywords
            if any(keyword in user_prompt for keyword in weather_keywords):
                logger.info(f"RAG+MCP에서 날씨 관련 키워드 발견: '{user_prompt}' - 매칭된 키워드: {[k for k in weather_keywords if k in user_prompt]}")
                location = self._extract_location_from_prompt(user_prompt)
                
                if location:
                    logger.info(f"[MCP RAG 통합] ✅ 위치 정보 추출 성공: '{location}'")
                    # MCP 서버에 날씨 요청
                    try:
                        weather_data = await self._make_mcp_request("weather", {
                            "location": location,
                            "query": user_prompt
                        })
                        if weather_data.get("success"):
                            # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                            # 실제 MCP 서버 응답은 weather_data["data"]에 있음
                            mcp_response = weather_data.get("data", {})
                            weather_info = mcp_response.get("result", mcp_response)
                            # 위치 정보를 weather_info에 추가
                            weather_info["location"] = location
                            mcp_data["weather"] = weather_info
                            logger.info(f"[MCP RAG 통합] ✅ 날씨 데이터 성공적으로 추가됨: {location}")
                        else:
                            logger.warning(f"[MCP RAG 통합] 날씨 데이터 요청 실패: {weather_data}")
                    except Exception as e:
                        logger.warning(f"[MCP RAG 통합] 날씨 데이터 요청 중 오류: {e}")
                else:
                    logger.info(f"RAG+MCP에서 위치 정보 추출 실패, 사용자에게 입력 요청")
                    # 위치 정보가 없으면 대기 상태 설정
                    self.set_weather_request_pending(session_id)
                    response = "🌤️ 날씨 정보를 제공하기 위해 도시명을 알려주세요. (예: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 제주 등)"
                    if session_id:
                        self.add_message_to_context(session_id, "assistant", response)
                    return response, False
            
            # 주식 관련 키워드 확인
            stock_keywords = settings.mcp_stock_keywords
            if any(keyword in user_prompt for keyword in stock_keywords):
                logger.info(f"RAG+MCP에서 주식 관련 키워드 발견: '{user_prompt}' - 매칭된 키워드: {[k for k in stock_keywords if k in user_prompt]}")
                stock_code = self._extract_stock_code_from_prompt(user_prompt)
                
                if stock_code:
                    logger.info(f"[MCP RAG 통합] ✅ 종목코드 추출 성공: '{stock_code}'")
                    # MCP 서버에 주식 요청
                    try:
                        stock_data = await self._make_mcp_request("stock", {
                            "code": stock_code,
                            "query": user_prompt
                        })
                        if stock_data.get("success"):
                            # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                            # 실제 MCP 서버 응답은 stock_data["data"]에 있음
                            mcp_response = stock_data.get("data", {})
                            # 새로운 MCP 응답 형식 처리
                            if "result" in mcp_response and isinstance(mcp_response["result"], dict):
                                stock_response = mcp_response["result"]
                            else:
                                # 기존 형식 지원
                                stock_response = mcp_response
                            stock_response["code"] = stock_code  # 주식 코드 추가
                            mcp_data["stock"] = stock_response
                            logger.info(f"[MCP RAG 통합] ✅ 주식 데이터 성공적으로 추가됨: {stock_code}")
                        else:
                            logger.warning(f"[MCP RAG 통합] 주식 데이터 요청 실패: {stock_data}")
                    except Exception as e:
                        logger.warning(f"[MCP RAG 통합] 주식 데이터 요청 중 오류: {e}")
                else:
                    logger.info(f"RAG+MCP에서 종목코드 추출 실패, 사용자에게 입력 요청")
                    # 종목코드가 없으면 대기 상태 설정
                    self.set_stock_request_pending(session_id)
                    response = "📈 주식 정보를 제공하기 위해 종목명이나 종목코드를 알려주세요. (예: 삼성전자, 005930, SK하이닉스, 000660, LG전자, 066570 등)"
                    if session_id:
                        self.add_message_to_context(session_id, "assistant", response)
                    return response, False
            
            # 웹 검색 관련 키워드 확인
            search_keywords = settings.mcp_search_keywords
            if any(keyword in user_prompt for keyword in search_keywords):
                logger.info(f"RAG+MCP에서 검색 관련 키워드 발견: '{user_prompt}' - 매칭된 키워드: {[k for k in search_keywords if k in user_prompt]}")
                
                # 검색 쿼리 추출
                search_query = await self._extract_search_query_from_prompt(user_prompt, model_name)
                if search_query and search_query != user_prompt:
                    logger.info(f"[MCP RAG 통합] ✅ 검색 쿼리 추출 성공: '{search_query}'")
                    # MCP 서버에 웹 검색 요청
                    try:
                        search_data = await self._make_mcp_request("search", {
                            "query": search_query,
                            "max_results": 5
                        })
                        if search_data.get("success"):
                            # MCP 서버 응답 구조에 맞게 수정
                            # _make_mcp_request에서 {"success": True, "data": result} 형태로 래핑하므로
                            # 실제 MCP 서버 응답은 search_data["data"]에 있음
                            mcp_response = search_data.get("data", {})
                            result_data = mcp_response.get("result", {})
                            search_results = result_data.get("results", [])
                            
                            # 디버깅을 위한 상세 로그 추가
                            logger.info(f"[MCP RAG 통합] search_data 구조: {list(search_data.keys())}")
                            logger.info(f"[MCP RAG 통합] mcp_response 구조: {list(mcp_response.keys())}")
                            logger.info(f"[MCP RAG 통합] result_data 구조: {list(result_data.keys())}")
                            logger.info(f"[MCP RAG 통합] search_results 타입: {type(search_results)}")
                            logger.info(f"[MCP RAG 통합] search_results 길이: {len(search_results) if search_results else 0}")
                            logger.info(f"[MCP RAG 통합] search_results 내용: {search_results}")
                            
                            mcp_data["search"] = {
                                "query": search_query,
                                "results": search_results,
                                "total_results": result_data.get("total_results", "N/A"),
                                "search_time": result_data.get("search_time", "N/A")
                            }
                            logger.info(f"[MCP RAG 통합] ✅ 검색 데이터 성공적으로 추가됨: {len(search_results)}개 결과")
                        else:
                            logger.warning(f"[MCP RAG 통합] 검색 데이터 요청 실패: {search_data}")
                    except Exception as e:
                        logger.warning(f"[MCP RAG 통합] 검색 데이터 요청 중 오류: {e}")
                else:
                    logger.warning(f"[MCP RAG 통합] 검색 쿼리 추출 실패 또는 원본과 동일")
            
        except Exception as e:
            logger.error(f"[MCP RAG 통합] MCP 서비스 요청 중 오류: {e}")
        
        # 3. 통합 응답 생성
        logger.info(f"[MCP RAG 통합] 통합 응답 생성 시작 - mcp_data: {list(mcp_data.keys())}")
        response = self._generate_integrated_response(user_prompt, context, mcp_data)
        
        # 세션에 응답 추가
        if session_id:
            self.add_message_to_context(session_id, "assistant", response)
        
        return response, True
    
    def _generate_integrated_response(self, user_prompt: str, context: str, mcp_data: Dict[str, Any]) -> str:
        """RAG 컨텍스트와 MCP 데이터를 통합하여 응답을 생성합니다."""
        try:
            logger.info(f"[통합 응답 생성] 시작 - mcp_data 키: {list(mcp_data.keys())}")
            logger.info(f"[통합 응답 생성] RAG 컨텍스트 길이: {len(context) if context else 0}")
            response_parts = []
            
            # MCP 데이터 처리
            if "weather" in mcp_data:
                logger.info(f"[통합 응답 생성] 날씨 데이터 처리 시작")
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
                weather_response = self._format_weather_response(weather_info, location)
                response_parts.append(weather_response)
                logger.info(f"[통합 응답 생성] ✅ 날씨 응답 생성 완료: {location}")
            
            if "stock" in mcp_data:
                logger.info(f"[통합 응답 생성] 주식 데이터 처리 시작")
                stock_info = mcp_data["stock"]
                # stock_info에 code가 없으면 원본 stock_code 사용
                stock_code = stock_info.get("code", stock_info.get("stock_code", "알 수 없는 종목"))
                stock_response = self._format_stock_response(stock_info, stock_code)
                response_parts.append(stock_response)
                logger.info(f"[통합 응답 생성] ✅ 주식 응답 생성 완료: {stock_code}")
            
            if "search" in mcp_data:
                logger.info(f"[통합 응답 생성] 검색 데이터 처리 시작")
                search_data = mcp_data["search"]
                search_response = self._format_search_response(search_data, search_data.get("query", user_prompt))
                response_parts.append(search_response)
                logger.info(f"[통합 응답 생성] ✅ 검색 응답 생성 완료")
            
            # RAG 컨텍스트 처리 로직 추가
            if context and context.strip():
                logger.info(f"[통합 응답 생성] RAG 컨텍스트 처리 시작 - 길이: {len(context)}")
                
                if not response_parts:
                    # MCP 데이터가 없는 경우, RAG 컨텍스트만 사용
                    logger.info(f"[통합 응답 생성] MCP 데이터 없음 - RAG 컨텍스트만 사용")
                    rag_response = f"검색된 정보를 바탕으로 답변드리겠습니다:\n\n{context}"
                    response_parts.append(rag_response)
                    logger.info(f"[통합 응답 생성] ✅ RAG 응답 생성 완료")
                else:
                    # MCP 데이터와 RAG 컨텍스트가 모두 있는 경우, 추가 정보로 제공
                    logger.info(f"[통합 응답 생성] MCP 데이터와 RAG 컨텍스트 모두 있음 - 추가 정보로 제공")
                    rag_supplement = f"\n\n📚 추가 참고 정보:\n{context}"
                    response_parts.append(rag_supplement)
                    logger.info(f"[통합 응답 생성] ✅ RAG 추가 정보 생성 완료")
            
            # 응답 조합
            logger.info(f"[통합 응답 생성] 응답 조합 시작 - response_parts 개수: {len(response_parts)}")
            if response_parts:
                response = "\n\n".join(response_parts)
                logger.info(f"[통합 응답 생성] ✅ 통합 응답 생성 완료 (길이: {len(response)}자)")
            else:
                # MCP 데이터와 RAG 컨텍스트가 모두 없는 경우
                logger.warning(f"[통합 응답 생성] ❌ MCP 데이터와 RAG 컨텍스트 모두 없음 - 폴백 응답 생성")
                if "뭐야" in user_prompt or "무엇" in user_prompt or "어떤" in user_prompt:
                    response = "죄송합니다. MCP 서버에 연결할 수 없어 실시간 정보를 제공할 수 없습니다. 일반적인 질문에 대해서는 AI 모델의 기본 지식으로 답변드리겠습니다."
                else:
                    response = "죄송합니다. 요청하신 정보를 찾을 수 없습니다."
            
            return response
            
        except Exception as e:
            logger.error(f"통합 응답 생성 실패: {e}")
            return "응답을 생성하는 중 오류가 발생했습니다."
    
    def _should_use_mcp(self, query: str, model_name: str = None, session_id: str = None, ui_mcp_enabled: bool = True) -> bool:
        """
        주어진 쿼리가 MCP 서비스를 사용해야 하는지 확인합니다.
        결정 방식에 따라 키워드 기반 또는 AI 기반으로 판단합니다.
        
        Args:
            query: 사용자 쿼리
            model_name: AI 결정 시 사용할 모델명 (None인 경우 기본 모델 사용)
            session_id: 세션 ID (세션별 결정 방식 사용)
            ui_mcp_enabled: UI에서 MCP 사용 여부 (체크박스 상태)
            
        Returns:
            bool: MCP 서비스 사용 여부
        """
        # UI에서 MCP 사용이 비활성화된 경우 즉시 False 반환
        if not ui_mcp_enabled:
            logger.info(f"[MCP 사용 결정] UI에서 MCP 사용이 비활성화됨 - 즉시 False 반환")
            return False
        
        # 세션별 결정 방식 가져오기
        decision_method = self.get_mcp_decision_method(session_id)
        logger.info(f"[MCP 사용 결정] UI 활성화됨, 결정 방식: {decision_method}, 세션: {session_id}, 질문: {query}")
        
        if decision_method == 'ai':
            result = self._should_use_mcp_decision_by_ai(query, model_name)
            logger.info(f"[MCP 사용 결정] AI 기반 결과: {'사용' if result else '사용 안함'}")
            return result
        else:
            result = self._should_use_mcp_keyword_based(query)
            logger.info(f"[MCP 사용 결정] 키워드 기반 결과: {'사용' if result else '사용 안함'}")
            return result
    
    def _determine_mcp_service_type(self, query: str) -> str:
        """
        MCP 서비스 사용이 결정된 후, 어떤 서비스를 사용할지 결정합니다.
        
        Args:
            query: 사용자 쿼리
            
        Returns:
            str: 서비스 타입 ('weather', 'stock', 'search')
        """
        logger.info(f"[MCP 서비스 타입 결정] 질문: {query}")
        
        # 설정에서 키워드 목록 가져오기
        from src.config.settings import get_settings
        settings = get_settings()
        
        # 날씨 관련 키워드 (우선순위 1)
        weather_keywords = settings.mcp_weather_keywords
        if any(keyword in query for keyword in weather_keywords):
            logger.info(f"[MCP 서비스 타입 결정] 날씨 서비스 선택 - 매칭된 키워드: {[k for k in weather_keywords if k in query]}")
            return "weather"
        
        # 주식 관련 키워드 (우선순위 2)
        stock_keywords = settings.mcp_stock_keywords
        if any(keyword in query for keyword in stock_keywords):
            logger.info(f"[MCP 서비스 타입 결정] 주식 서비스 선택 - 매칭된 키워드: {[k for k in stock_keywords if k in query]}")
            return "stock"
        
        # 웹 검색 관련 키워드 (우선순위 3)
        search_keywords = settings.mcp_search_keywords
        if any(keyword in query for keyword in search_keywords):
            logger.info(f"[MCP 서비스 타입 결정] 웹 검색 서비스 선택 - 매칭된 키워드: {[k for k in search_keywords if k in query]}")
            return "search"
        
        # 기본값: 웹 검색 (가장 범용적인 서비스)
        logger.info(f"[MCP 서비스 타입 결정] 기본값으로 웹 검색 서비스 선택")
        return "search"
    
    def _should_use_mcp_keyword_based(self, query: str) -> bool:
        """
        키워드 기반으로 MCP 서비스 사용 여부를 결정합니다.
        
        Args:
            query: 사용자 쿼리
            
        Returns:
            bool: MCP 서비스 사용 여부
        """
        logger.info(f"[MCP 키워드 결정] 🚀 시작 - 질문: '{query}'")
        
        # 설정에서 키워드 목록 가져오기
        from src.config.settings import get_settings
        settings = get_settings()
        
        # 날씨 관련 키워드
        weather_keywords = settings.mcp_weather_keywords
        weather_matches = [keyword for keyword in weather_keywords if keyword in query]
        if weather_matches:
            logger.info(f"[MCP 키워드 매칭] ✅ 날씨 키워드 발견: {weather_matches}")
            return True
        
        # 주식 관련 키워드
        stock_keywords = settings.mcp_stock_keywords
        stock_matches = [keyword for keyword in stock_keywords if keyword in query]
        if stock_matches:
            logger.info(f"[MCP 키워드 매칭] ✅ 주식 키워드 발견: {stock_matches}")
            return True
        
        # 검색 관련 키워드
        search_keywords = settings.mcp_search_keywords
        search_matches = [keyword for keyword in search_keywords if keyword in query]
        if search_matches:
            logger.info(f"[MCP 키워드 매칭] ✅ 검색 키워드 발견: {search_matches}")
            return True
        
        logger.info(f"[MCP 키워드 매칭] ❌ 매칭되는 키워드 없음")
        return False
    
    def _should_use_mcp_decision_by_ai(self, query: str, model_name: str = None) -> bool:
        """
        AI 모델을 사용하여 MCP 서비스 사용 여부를 결정합니다.
        
        Args:
            query: 사용자 쿼리
            model_name: 사용할 AI 모델명 (None인 경우 기본 모델 사용)
            
        Returns:
            bool: MCP 서비스 사용 여부
        """
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            # 사용할 모델 결정
            target_model = model_name or settings.default_model
            logger.info(f"[MCP AI 결정] 🚀 시작 - 모델: {target_model}, 질문: '{query}'")
            
            # AI 결정을 위한 프롬프트 생성
            decision_prompt = f"""다음 질문이 실시간 정보가 필요한지 판단해주세요.

질문: "{query}"

실시간 정보가 필요한 경우:
- 날씨 관련: 날씨, 기온, 습도, 바람, 비, 눈, 더울까, 추울까 등
- 주식 관련: 주가, 주식, 종목, 증시, 삼성전자, SK하이닉스 등
- 최신 정보: 최신, 뉴스, 기사, 통계, 실시간, 요즘, 현재 등

답변: "YES" 또는 "NO"만 작성"""
            
            logger.info(f"[MCP AI 결정] 📝 프롬프트 생성 완료 (길이: {len(decision_prompt)}자)")



            # AI 모델을 사용하여 결정
            try:
                # 방법 1: LangChain OllamaLLM 시도
                logger.info(f"[MCP AI 결정] 🔄 LangChain OllamaLLM 방식 시도")
                llm = OllamaLLM(
                    model=target_model,
                    base_url=settings.ollama_base_url,
                    timeout=settings.ollama_timeout
                )
                response = llm.invoke(decision_prompt)
                logger.info(f"[MCP AI 결정] ✅ LangChain 방식 성공, 응답: '{str(response)}'")
                
            except Exception as e:
                logger.warning(f"[MCP AI 결정] LangChain 방식 실패: {e}")
                
                # 방법 2: 직접 Ollama API 호출
                try:
                    logger.info(f"[MCP AI 결정] 🔄 직접 Ollama API 호출 방식 시도")
                    import requests
                    
                    ollama_response = requests.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": target_model,
                            "prompt": decision_prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,  # 결정을 위해 낮은 temperature 사용
                                "top_p": 0.9,
                                "top_k": 40,
                                "repeat_penalty": 1.1,
                                "seed": -1
                            }
                        },
                        timeout=settings.ollama_timeout
                    )
                    
                    if ollama_response.status_code == 200:
                        response_data = ollama_response.json()
                        response = response_data.get('response', 'NO')
                        logger.info(f"[MCP AI 결정] ✅ 직접 API 호출 성공, 응답: '{str(response)}'")
                    else:
                        logger.error(f"[MCP AI 결정] ❌ Ollama API 오류: HTTP {ollama_response.status_code}")
                        return False
                        
                except Exception as e2:
                    logger.error(f"[MCP AI 결정] ❌ 직접 API 호출 실패: {e2}")
                    return False
            
            # 응답 파싱 및 분석
            response_text = str(response).strip()
            
            # AI 모델 응답에서 특수 토큰들 제거
            response_text = re.sub(r'\n<end_of_turn>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<end_of_turn>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<|endoftext|>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<|im_end|>.*$', '', response_text, flags=re.DOTALL)
            response_text = re.sub(r'<|im_start|>.*$', '', response_text, flags=re.DOTALL)
            
            # 줄바꿈과 공백 정리 후 대문자 변환
            response_text = re.sub(r'\n+', ' ', response_text)
            response_text = re.sub(r'\s+', ' ', response_text).strip().upper()
            
            logger.info(f"[MCP AI 결정] 정규화된 응답: '{response_text}'")
            
            # 응답 내용 분석
            if "YES" in response_text:
                logger.info(f"[MCP AI 결정] ✅ 결과: MCP 서비스 사용 (YES 포함)")
                return True
            else:
                logger.info(f"[MCP AI 결정] ❌ 결과: MCP 서비스 사용 안함 (YES 없음)")
                return False
                
        except Exception as e:
            logger.error(f"❌ AI 기반 MCP 결정 중 오류: {e}")
            # 오류 발생 시 키워드 기반으로 폴백
            logger.info("🔄 AI 결정 실패, 키워드 기반으로 폴백")
            fallback_result = self._should_use_mcp_keyword_based(query)
            logger.info(f"[MCP AI 결정 폴백] 키워드 기반 결과: {'사용' if fallback_result else '사용 안함'}")
            return fallback_result     

    def get_service_status(self) -> Dict[str, Any]:
        """MCP 서비스의 상태를 반환합니다."""
        try:
            return {
                "status": "active",
                "server_url": self.mcp_server_url,
                "model_name": "N/A", # model_name 파라미터가 제거되어 기본값 사용
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "active_sessions": len(self.session_contexts),
                "mcp_decision_method": self.mcp_decision_method
            }
        except Exception as e:
            logger.error(f"MCP 서비스 상태 확인 중 오류: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def check_mcp_server_status(self) -> Dict[str, Any]:
        """MCP 서버 연결 상태를 확인합니다."""
        try:
            import httpx
            logger.info(f"[MCP 서버 상태 확인] 서버 URL: {self.mcp_server_url}")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.mcp_server_url}/health")
                logger.info(f"[MCP 서버 상태 확인] HTTP 상태 코드: {response.status_code}")
                logger.info(f"[MCP 서버 상태 확인] 응답 시간: {response.elapsed.total_seconds()}초")
                
                if response.status_code == 200:
                    logger.info(f"[MCP 서버 상태 확인] ✅ 서버 연결 성공")
                    return {
                        "status": "connected",
                        "server_url": self.mcp_server_url,
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    logger.warning(f"[MCP 서버 상태 확인] ❌ 서버 오류: HTTP {response.status_code}")
                    return {
                        "status": "error",
                        "server_url": self.mcp_server_url,
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            logger.error(f"[MCP 서버 상태 확인] ❌ 연결 실패: {e}")
            return {
                "status": "disconnected",
                "server_url": self.mcp_server_url,
                "error": str(e)
            }

# 전역 인스턴스 생성
mcp_client_service = MCPClientService()

