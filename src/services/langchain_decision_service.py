"""
Langchain Decision Service
사용자 질문을 분석하여 적절한 서비스를 결정하는 서비스
"""

import logging
import json
from typing import Dict, Any, Optional, Literal
from langchain_ollama import OllamaLLM
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import os
from enum import Enum


logger = logging.getLogger(__name__)

# 디버그 로깅을 위한 추가 로거
debug_logger = logging.getLogger("langchain_decision_debug")
debug_logger.setLevel(logging.DEBUG)

class DecisionCategory(Enum):
    WEATHER = "weather"
    KOREAN_STOCK = "korean_stock"
    WEB_SEARCH_NEEDED = "web_search_needed"
    DIRECT_ANSWER = "direct_answer"


class LangchainDecisionService:
    """
    사용자 질문을 분석하여 적절한 서비스를 결정하는 서비스
    """
    
    def __init__(self, model_name: str = "gemma3:12b-it-qat"):
        """
        Langchain 기반 의사결정 서비스 초기화
        
        Args:
            model_name: 사용할 Ollama 모델명
        """
        self.model_name = model_name
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            base_url="http://1.237.52.240:11434"  # env.settings의 OLLAMA_BASE_URL과 동일
        )
        
        # 의사결정을 위한 프롬프트 템플릿
        self.decision_prompt = ChatPromptTemplate.from_template("""
당신은 사용자의 질문을 분석하여 다음 4가지 카테고리 중 하나로 분류하는 전문가입니다.

분류 기준:
1. 날씨 관련 정보 요청: 날씨, 기온, 강수, 날씨 예보, 기후 등과 관련된 질문
2. 한국 주식 시장 종목 주가 정보 요청: 한국 주식, KOSPI, KOSDAQ, 특정 종목 주가, 주식 시장 등과 관련된 질문
3. 웹 검색 필요: 최신 정보, 최신 기사, 최신 뉴스, 실시간 데이터, 특정 사이트 정보, 현재 시점의 구체적인 정보가 필요한 질문
4. 바로 답변 가능: 일반적인 지식, 개념 설명, 역사적 사실, 공식 등 AI가 가진 정보로 답변 가능한 질문

사용자 질문: {user_prompt}

위 기준에 따라 다음 중 하나로 분류해주세요:
- weather: 날씨 관련 정보 요청
- korean_stock: 한국 주식 시장 종목 주가 정보 요청  
- web_search_needed: 웹 검색이 필요한 질문
- direct_answer: 바로 답변 가능한 질문

분류 결과만 출력해주세요 (예: weather, korean_stock, web_search_needed, direct_answer)
""")
        
        # 응답 메시지 매핑
        self.response_messages = {
            DecisionCategory.WEATHER: "날씨 정보를 요청하셨습니다.",
            DecisionCategory.KOREAN_STOCK: "한국 주식 시장에 상장되어 있는 종목의 주가 관련 정보를 요청하셨습니다.",
            DecisionCategory.WEB_SEARCH_NEEDED: "정확한 답변을 위해서는 웹 검색이 필요합니다.",
            DecisionCategory.DIRECT_ANSWER: "바로 답변드리겠습니다"
        }
        
        # Langchain 체인 구성
        self.chain = (
            {"user_prompt": RunnablePassthrough()}
            | self.decision_prompt
            | self.llm
            | StrOutputParser()
        )
    
    async def classify_prompt(self, user_prompt: str) -> str:
        """
        사용자의 prompt를 분류하고 해당하는 응답 메시지를 반환
        
        Args:
            user_prompt: 사용자가 입력한 prompt
            
        Returns:
            str: 분류 결과에 따른 응답 메시지
        """
        try:
            debug_logger.debug(f"🔍 사용자 질문 분석 시작: {user_prompt}")
            
            # Langchain을 사용하여 분류 수행
            debug_logger.debug("🤖 Langchain 체인 실행 중...")
            classification_result = await self.chain.ainvoke(user_prompt)
            debug_logger.debug(f"📊 원본 분류 결과: '{classification_result}'")
            
            # 결과 정리 (공백 제거, 소문자 변환)
            classification_result = classification_result.strip().lower()
            debug_logger.debug(f"🧹 정리된 분류 결과: '{classification_result}'")
            
            # 분류 결과에 따른 응답 메시지 반환
            if "weather" in classification_result:
                debug_logger.debug("🌤️ 날씨 관련 질문으로 분류됨")
                return self.response_messages[DecisionCategory.WEATHER]
            elif "korean_stock" in classification_result or "stock" in classification_result:
                debug_logger.debug("📈 한국 주식 관련 질문으로 분류됨")
                return self.response_messages[DecisionCategory.KOREAN_STOCK]
            elif "web_search" in classification_result or "search" in classification_result:
                debug_logger.debug("🔍 웹 검색 필요 질문으로 분류됨")
                return self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED]
            elif "direct_answer" in classification_result or "direct" in classification_result:
                debug_logger.debug("💬 바로 답변 가능한 질문으로 분류됨")
                return self.response_messages[DecisionCategory.DIRECT_ANSWER]
            else:
                # 기본값으로 웹 검색 필요로 분류
                debug_logger.debug("❓ 분류 불가능, 기본값(웹 검색)으로 설정")
                return self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED]
                
        except Exception as e:
            debug_logger.error(f"❌ 분류 중 오류 발생: {e}")
            logger.error(f"분류 중 오류 발생: {e}")
            # 오류 발생 시 기본값 반환
            return self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED]
    
    def classify_prompt_sync(self, user_prompt: str) -> str:
        """
        동기 방식으로 사용자의 prompt를 분류하고 해당하는 응답 메시지를 반환
        
        Args:
            user_prompt: 사용자가 입력한 prompt
            
        Returns:
            str: 분류 결과에 따른 응답 메시지
        """
        try:
            debug_logger.debug(f"🔍 사용자 질문 분석 시작 (동기): {user_prompt}")
            
            # Langchain을 사용하여 분류 수행
            debug_logger.debug("🤖 Langchain 체인 실행 중 (동기)...")
            classification_result = self.chain.invoke(user_prompt)
            debug_logger.debug(f"📊 원본 분류 결과 (동기): '{classification_result}'")
            
            # 결과 정리 (공백 제거, 소문자 변환)
            classification_result = classification_result.strip().lower()
            debug_logger.debug(f"🧹 정리된 분류 결과 (동기): '{classification_result}'")
            
            # 분류 결과에 따른 응답 메시지 반환
            if "weather" in classification_result:
                debug_logger.debug("🌤️ 날씨 관련 질문으로 분류됨 (동기)")
                return self.response_messages[DecisionCategory.WEATHER]
            elif "korean_stock" in classification_result or "stock" in classification_result:
                debug_logger.debug("📈 한국 주식 관련 질문으로 분류됨 (동기)")
                return self.response_messages[DecisionCategory.KOREAN_STOCK]
            elif "web_search" in classification_result or "search" in classification_result:
                debug_logger.debug("🔍 웹 검색 필요 질문으로 분류됨 (동기)")
                return self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED]
            elif "direct_answer" in classification_result or "direct" in classification_result:
                debug_logger.debug("💬 바로 답변 가능한 질문으로 분류됨 (동기)")
                return self.response_messages[DecisionCategory.DIRECT_ANSWER]
            else:
                # 기본값으로 웹 검색 필요로 분류
                debug_logger.debug("❓ 분류 불가능, 기본값(웹 검색)으로 설정 (동기)")
                return self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED]
                
        except Exception as e:
            debug_logger.error(f"❌ 분류 중 오류 발생 (동기): {e}")
            logger.error(f"분류 중 오류 발생: {e}")
            # 오류 발생 시 기본값 반환
            return self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED]
    


# 전역 인스턴스 생성
langchain_decision_service = LangchainDecisionService() 