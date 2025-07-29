"""
Langchain Decision Service
사용자 질문을 분석하여 적절한 서비스를 결정하는 서비스
"""

import logging
import json
from typing import Dict, Any, Optional
from langchain_ollama import OllamaLLM
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class LangchainDecisionService:
    """
    사용자 질문을 분석하여 적절한 서비스를 결정하는 서비스
    """
    
    def __init__(self, model_name: str = "gemma3:12b-it-qat"):
        """
        LangchainDecisionService 초기화
        
        Args:
            model_name: 사용할 AI 모델 이름 (기본값: gemma3:12b-it-qat)
        """
        self.model_name = model_name
        
        self.llm = OllamaLLM(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.1
        )
        
        # 판단을 위한 시스템 프롬프트
        self.decision_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 사용자의 질문을 분석하여 어떤 AI 모델에게 답변을 요청할 건지 아니면 MCP 서버에 특정 정보 서비스를 요청할 것인지 판단하여 답변하는 AI입니다.

답변 종류:
- MODEL_ONLY: AI 모델에게 답변을 요청
- MCP_SERVER-WEB: MCP 서버에 WEB 검색 요청 (최신 정보, 뉴스, 실시간 데이터 등)
- MCP_SERVER-STOCK: MCP 서버에 주식 정보 요청 (주가, 종목, 시세, KOSPI, KOSDAQ 등)
- MCP_SERVER-WEATHER: MCP 서버에 날씨 정보 요청 (날씨, 기온, 일기예보 등)

판단 기준:
- 일반적인 개념 질문 (정의, 역사, 원리 등) → MODEL_ONLY
- 수학적 계산 (더하기, 곱하기, 나누기, 빼기, 통계 함수, 삼각 함수, 제곱, 방적식, 지수 함수, 확률 등) → MODEL_ONLY
- 주식 관련 질문 (주가, 종목, 시세, KOSPI, KOSDAQ 등) → MCP_SERVER-STOCK
- 날씨 관련 질문 (날씨, 기온, 일기예보 등) → MCP_SERVER-WEATHER
- 최신 정보 요청 (오늘, 최신, 최근, 현재 등) → MCP_SERVER-WEB
- 뉴스나 기사 정보 요청 (최신, 최근, 뉴스, 기사, 현재 등) → MCP_SERVER-WEB
- 명시적 검색 요청 (검색해줘, 찾아줘 등) → MCP_SERVER-WEB

중요: 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{
    "decision": "MODEL_ONLY|MCP_SERVER-WEB|MCP_SERVER-STOCK|MCP_SERVER-WEATHER",
    "reason": "판단 이유",
    "confidence": 0.9
}"""),
            ("human", "사용자 질문: {user_message}")
        ])
    
    def update_model(self, model_name: str):
        """
        사용할 AI 모델을 동적으로 변경합니다.
        
        Args:
            model_name: 새로운 모델 이름
        """
        self.model_name = model_name
        self.llm = OllamaLLM(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.1
        )
        logger.info(f"LangchainDecisionService 모델이 {model_name}으로 변경되었습니다.")
    
    def decide_search_method(self, user_message: str, current_mode: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        사용자 질문을 분석하여 검색 방식을 결정합니다.
        
        Args:
            user_message: 사용자 메시지
            current_mode: 현재 모드
            model_name: 사용할 모델 이름 (None이면 기존 모델 사용)
        """
        logger.info(f"새로운 판단 요청: '{user_message[:50]}...' (모드: {current_mode}, 모델: {model_name or self.model_name})")
        
        # 모델이 지정된 경우 업데이트
        if model_name and model_name != self.model_name:
            self.update_model(model_name)
        
        # 모델 데이터만 사용 모드인 경우 판단 스킵
        if current_mode == "model_only":
            logger.info("모델 데이터만 사용 모드: 판단 스킵")
            return {
                "decision": "MODEL_ONLY",
                "reason": "사용자가 모델 데이터만 사용 모드를 선택함",
                "confidence": 1.0,
                "skip_llm_decision": True
            }
        
        try:
            # Langchain을 사용하여 판단
            messages = self.decision_prompt.format_messages(user_message=user_message)
            response = self.llm.invoke(messages)
            
            # JSON 응답 파싱
            try:
                # 응답에서 JSON 부분만 추출
                response_text = response.content.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                decision_data = json.loads(response_text.strip())
                logger.info(f"Langchain 판단 결과: {decision_data}")
                return {
                    "decision": decision_data.get("decision", "MODEL_ONLY"),
                    "reason": decision_data.get("reason", "기본값"),
                    "confidence": decision_data.get("confidence", 0.5),
                    "skip_llm_decision": False
                }
            except json.JSONDecodeError as e:
                # JSON 파싱 실패시 응답 텍스트에서 키워드 추출
                logger.warning(f"JSON 파싱 실패, 텍스트 분석으로 대체: {response.content}, 오류: {e}")
                return self._fallback_decision(response.content, user_message)
                
        except Exception as e:
            logger.error(f"Langchain 판단 중 오류: {e}")
            return self._fallback_decision("", user_message)
    
    def _fallback_decision(self, response_text: str, user_message: str) -> Dict[str, Any]:
        """Langchain 판단 실패시 키워드 기반으로 대체 판단"""
        message_lower = user_message.lower()
        
        # 주식 관련 키워드
        stock_keywords = ["주가", "주식", "종목", "시세", "종가", "시작가", "고가", "저가", "상한가", "하한가", "현재가", "등락", "거래량", "시가총액", "PER", "PBR", "배당", "코스피", "코스닥", "KOSPI", "KOSDAQ", "삼성전자", "현대차", "기아", "LG", "SK", "네이버", "카카오"]
        if any(keyword in message_lower for keyword in stock_keywords):
            return {
                "decision": "MCP_SERVER-STOCK",
                "reason": "주식 관련 질문 감지",
                "confidence": 0.8,
                "skip_llm_decision": False
            }
        
        # 날씨 관련 키워드
        weather_keywords = ["날씨", "기온", "강수", "습도", "기압", "풍속", "일기예보", "날씨예보", "기상", "온도", "비", "눈", "맑음", "흐림", "구름", "바람", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "제주", "수원", "고양", "체감온도", "미세먼지", "초미세먼지", "대기질"]
        if any(keyword in message_lower for keyword in weather_keywords):
            return {
                "decision": "MCP_SERVER-WEATHER",
                "reason": "날씨 관련 질문 감지",
                "confidence": 0.8,
                "skip_llm_decision": False
            }
        
        # 웹 검색 관련 키워드
        web_search_keywords = ["검색", "찾아", "최신", "최근", "현재", "오늘", "뉴스", "기사", "정보", "검색해줘", "찾아줘", "알려줘"]
        if any(keyword in message_lower for keyword in web_search_keywords):
            return {
                "decision": "MCP_SERVER-WEB",
                "reason": "웹 검색 관련 질문 감지",
                "confidence": 0.7,
                "skip_llm_decision": False
            }
        
        # 기본값
        return {
            "decision": "MODEL_ONLY",
            "reason": "일반적인 질문으로 판단",
            "confidence": 0.6,
            "skip_llm_decision": False
        }
    
    def should_use_mcp_server(self, decision_result: Dict[str, Any], current_mode: str) -> bool:
        """MCP 서버 사용 여부 결정"""
        if current_mode != "mcp_server":
            return False
        
        decision = decision_result.get("decision", "")
        return decision.startswith("MCP_SERVER-")
    
    def should_use_web_search(self, decision_result: Dict[str, Any], current_mode: str) -> bool:
        """웹 검색 사용 여부 결정"""
        if current_mode == "model_only":
            return False
        
        return decision_result.get("decision", "") == "MCP_SERVER-WEB"
    
    def should_use_stock_service(self, decision_result: Dict[str, Any], current_mode: str) -> bool:
        """주식 서비스 사용 여부 결정"""
        if current_mode != "mcp_server":
            return False
        
        return decision_result.get("decision", "") == "MCP_SERVER-STOCK"
    
    def should_use_weather_service(self, decision_result: Dict[str, Any], current_mode: str) -> bool:
        """날씨 서비스 사용 여부 결정"""
        if current_mode != "mcp_server":
            return False
        
        return decision_result.get("decision", "") == "MCP_SERVER-WEATHER"
    
    def get_service_type(self, decision_result: Dict[str, Any]) -> str:
        """결정 결과에서 서비스 타입을 추출"""
        decision = decision_result.get("decision", "")
        
        if decision == "MODEL_ONLY":
            return "model_only"
        elif decision == "MCP_SERVER-WEB":
            return "web_search"
        elif decision == "MCP_SERVER-STOCK":
            return "stock"
        elif decision == "MCP_SERVER-WEATHER":
            return "weather"
        else:
            return "model_only"

# 전역 인스턴스 생성
langchain_decision_service = LangchainDecisionService() 