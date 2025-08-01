"""
Langchain Decision Service with RAG Integration
사용자 질문을 분석하여 적절한 서비스를 결정하는 서비스 (RAG 통합)
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

# RAG 서비스 import
from src.services.rag_service import rag_service

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
    사용자 질문을 분석하여 적절한 서비스를 결정하는 서비스 (RAG 통합)
    """
    
    def __init__(self, model_name: str = "gemma3:12b-it-qat"):
        """
        Langchain 기반 의사결정 서비스 초기화 (RAG 통합)
        
        Args:
            model_name: 사용할 Ollama 모델명
        """
        self.model_name = model_name
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            base_url="http://1.237.52.240:11434"  # env.settings의 OLLAMA_BASE_URL과 동일
        )
        
        # RAG 통합 의사결정을 위한 프롬프트 템플릿
        self.decision_prompt_with_rag = ChatPromptTemplate.from_template("""
당신은 사용자의 질문을 분석하여 다음 4가지 카테고리 중 하나로 분류하고, 가능한 경우 직접 답변도 제공하는 전문가입니다.

분류 기준:
1. weather (날씨): 날씨, 기온, 강수, 날씨 예보, 기후, 오늘 날씨, 내일 날씨, 서울 날씨 등과 관련된 질문
2. korean_stock (한국 주식): 한국 주식, KOSPI, KOSDAQ, 특정 종목 주가, 주식 시장, 종목코드 등과 관련된 질문
3. web_search_needed (웹 검색 필요): 최신 정보, 최신 기사, 최신 뉴스, 실시간 데이터, 특정 사이트 정보, 현재 시점의 구체적인 정보가 필요한 질문
4. direct_answer (바로 답변 가능): 일반적인 지식, 개념 설명, 역사적 사실, 공식 등 AI가 가진 정보로 답변 가능한 질문

중요: 날씨 관련 질문은 항상 "weather"로 분류하세요. "오늘 날씨", "서울 날씨", "날씨 어때", "기온", "비", "눈", "맑음", "흐림" 등의 키워드가 있으면 weather로 분류해야 합니다.

참고할 수 있는 관련 문서 정보:
{rag_context}

사용자 질문: {user_prompt}

위 기준과 참고 문서 정보를 고려하여 다음 형식으로 응답해주세요:

분류: [weather/korean_stock/web_search_needed/direct_answer]
답변: [참고 문서 정보를 바탕으로 한 구체적인 답변, 가능한 경우]

만약 참고 문서에서 정확한 답변을 찾을 수 있다면 구체적으로 답변해주세요.
답변할 수 없는 경우에는 "해당 정보를 찾을 수 없습니다."라고 표시해주세요.
""")
        
        # 기존 의사결정을 위한 프롬프트 템플릿 (RAG 없이)
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
        
        # RAG 통합 Langchain 체인 구성
        self.chain_with_rag = (
            {"user_prompt": RunnablePassthrough(), "rag_context": RunnablePassthrough()}
            | self.decision_prompt_with_rag
            | self.llm
            | StrOutputParser()
        )
        
        # 기존 Langchain 체인 구성 (RAG 없이)
        self.chain = (
            {"user_prompt": RunnablePassthrough()}
            | self.decision_prompt
            | self.llm
            | StrOutputParser()
        )
    
    def _get_rag_context_for_decision(self, user_prompt: str, top_k: int = 3) -> str:
        """
        의사결정을 위한 RAG 컨텍스트를 검색합니다.
        
        Args:
            user_prompt: 사용자 질문
            top_k: 검색할 문서 수
            
        Returns:
            str: RAG 컨텍스트
        """
        try:
            debug_logger.debug(f"🔍 의사결정을 위한 RAG 컨텍스트 검색 시작: {user_prompt}")
            
            # RAG 서비스를 사용하여 컨텍스트 검색
            rag_context = rag_service.retrieve_context(user_prompt, top_k=top_k)
            
            if rag_context:
                debug_logger.debug(f"✅ RAG 컨텍스트 발견 (길이: {len(rag_context)} 문자)")
                # 컨텍스트를 간단히 요약하여 의사결정에 활용
                return f"관련 문서 정보: {rag_context[:500]}..."
            else:
                debug_logger.debug("⚠️ 관련 RAG 컨텍스트 없음")
                return "관련 문서 정보: 없음"
                
        except Exception as e:
            debug_logger.error(f"❌ RAG 컨텍스트 검색 실패: {e}")
            return "관련 문서 정보: 검색 실패"
    
    def _parse_rag_response(self, response: str) -> tuple[str, str]:
        """
        RAG 응답을 파싱하여 분류와 답변을 분리합니다.
        
        Args:
            response: RAG 모델의 응답
            
        Returns:
            tuple[str, str]: (분류, 답변)
        """
        try:
            response = response.strip()
            
            # 분류 추출
            classification = ""
            if "분류:" in response:
                classification_part = response.split("분류:")[1].split("\n")[0].strip()
                classification = classification_part.lower()
            
            # 답변 추출
            answer = ""
            if "답변:" in response:
                answer_part = response.split("답변:")[1].strip()
                answer = answer_part
            
            debug_logger.debug(f"🔍 응답 파싱 - 분류: '{classification}', 답변 길이: {len(answer)}")
            
            return classification, answer
            
        except Exception as e:
            debug_logger.error(f"❌ 응답 파싱 실패: {e}")
            return "", ""
    
    async def classify_prompt(self, user_prompt: str, use_rag: bool = True) -> str:
        """
        사용자의 prompt를 분류하고 해당하는 응답 메시지를 반환 (RAG 통합)
        
        Args:
            user_prompt: 사용자가 입력한 prompt
            use_rag: RAG 사용 여부 (기본값: True)
            
        Returns:
            str: 분류 결과에 따른 응답 메시지 또는 직접 답변
        """
        try:
            debug_logger.debug(f"🔍 사용자 질문 분석 시작 (RAG 사용: {use_rag}): {user_prompt}")
            
            if use_rag:
                # RAG 컨텍스트 검색
                rag_context = self._get_rag_context_for_decision(user_prompt)
                
                # RAG 통합 Langchain을 사용하여 분류 및 답변 생성
                debug_logger.debug("🤖 RAG 통합 Langchain 체인 실행 중...")
                result = await self.chain_with_rag.ainvoke({
                    "user_prompt": user_prompt,
                    "rag_context": rag_context
                })
                debug_logger.debug(f"📊 RAG 통합 원본 결과: '{result}'")
                
                # 결과 파싱 (분류와 답변 분리)
                classification_result, direct_answer = self._parse_rag_response(result)
                debug_logger.debug(f"🧹 파싱된 분류: '{classification_result}', 답변: '{direct_answer[:100]}...'")
                
                # 직접 답변이 있는 경우 반환
                if direct_answer and direct_answer.strip() and "찾을 수 없습니다" not in direct_answer:
                    debug_logger.debug("✅ RAG 기반 직접 답변 제공")
                    return direct_answer
                
            else:
                # 기존 Langchain을 사용하여 분류 수행
                debug_logger.debug("🤖 기존 Langchain 체인 실행 중...")
                classification_result = await self.chain.ainvoke(user_prompt)
                debug_logger.debug(f"📊 기존 원본 분류 결과: '{classification_result}'")
                classification_result = classification_result.strip().lower()
            
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
    
    def classify_prompt_sync(self, user_prompt: str, use_rag: bool = True) -> str:
        """
        동기 방식으로 사용자의 prompt를 분류하고 해당하는 응답 메시지를 반환 (RAG 통합)
        
        Args:
            user_prompt: 사용자가 입력한 prompt
            use_rag: RAG 사용 여부 (기본값: True)
            
        Returns:
            str: 분류 결과에 따른 응답 메시지 또는 직접 답변
        """
        try:
            debug_logger.debug(f"🔍 사용자 질문 분석 시작 (동기, RAG 사용: {use_rag}): {user_prompt}")
            
            if use_rag:
                # RAG 컨텍스트 검색
                rag_context = self._get_rag_context_for_decision(user_prompt)
                
                # RAG 통합 Langchain을 사용하여 분류 및 답변 생성
                debug_logger.debug("🤖 RAG 통합 Langchain 체인 실행 중 (동기)...")
                result = self.chain_with_rag.invoke({
                    "user_prompt": user_prompt,
                    "rag_context": rag_context
                })
                debug_logger.debug(f"📊 RAG 통합 원본 결과 (동기): '{result}'")
                
                # 결과 파싱 (분류와 답변 분리)
                classification_result, direct_answer = self._parse_rag_response(result)
                debug_logger.debug(f"🧹 파싱된 분류 (동기): '{classification_result}', 답변: '{direct_answer[:100]}...'")
                
                # 직접 답변이 있는 경우 반환
                if direct_answer and direct_answer.strip() and "찾을 수 없습니다" not in direct_answer:
                    debug_logger.debug("✅ RAG 기반 직접 답변 제공 (동기)")
                    return direct_answer
                
            else:
                # 기존 Langchain을 사용하여 분류 수행
                debug_logger.debug("🤖 기존 Langchain 체인 실행 중 (동기)...")
                classification_result = self.chain.invoke(user_prompt)
                debug_logger.debug(f"📊 기존 원본 분류 결과 (동기): '{classification_result}'")
                classification_result = classification_result.strip().lower()
            
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
    
    async def classify_prompt_with_metadata(self, user_prompt: str, use_rag: bool = True) -> Dict[str, Any]:
        """
        사용자의 prompt를 분류하고 메타데이터와 함께 결과를 반환 (RAG 통합)
        
        Args:
            user_prompt: 사용자가 입력한 prompt
            use_rag: RAG 사용 여부 (기본값: True)
            
        Returns:
            Dict[str, Any]: 분류 결과와 메타데이터
        """
        try:
            debug_logger.debug(f"🔍 사용자 질문 분석 시작 (메타데이터 포함, RAG 사용: {use_rag}): {user_prompt}")
            
            rag_context = ""
            if use_rag:
                # RAG 컨텍스트 검색
                rag_context = self._get_rag_context_for_decision(user_prompt)
            
            # 분류 수행
            classification_result = await self.classify_prompt(user_prompt, use_rag)
            
            # 메타데이터 구성
            metadata = {
                "user_prompt": user_prompt,
                "classification_result": classification_result,
                "use_rag": use_rag,
                "rag_context_length": len(rag_context) if rag_context else 0,
                "rag_context_preview": rag_context[:200] + "..." if len(rag_context) > 200 else rag_context,
                "model_used": self.model_name,
                "timestamp": "2024-01-01T12:00:00"  # 실제로는 datetime.now().isoformat() 사용
            }
            
            return metadata
            
        except Exception as e:
            debug_logger.error(f"❌ 메타데이터 포함 분류 중 오류 발생: {e}")
            return {
                "user_prompt": user_prompt,
                "classification_result": self.response_messages[DecisionCategory.WEB_SEARCH_NEEDED],
                "use_rag": use_rag,
                "error": str(e),
                "model_used": self.model_name,
                "timestamp": "2024-01-01T12:00:00"
            }


# 전역 인스턴스 생성
langchain_decision_service = LangchainDecisionService() 