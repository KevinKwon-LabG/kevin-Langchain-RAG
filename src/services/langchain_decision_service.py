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
            ("system", """당신은 사용자의 질문을 분석하여 AI 모델에게 답변을 요청할 것인지 판단하여 답변하는 AI입니다.

답변 종류:
- MODEL_ONLY: AI 모델에게 답변을 요청

판단 기준:
- 모든 질문에 대해 AI 모델이 답변하도록 함

중요: 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{
    "decision": "MODEL_ONLY",
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
        """Langchain 판단 실패시 기본값 반환"""
        return {
            "decision": "MODEL_ONLY",
            "reason": "기본값으로 AI 모델 사용",
            "confidence": 0.6,
            "skip_llm_decision": False
        }
    
    def should_use_web_search(self, decision_result: Dict[str, Any], current_mode: str) -> bool:
        """웹 검색 사용 여부 결정"""
        return False
    
    def get_service_type(self, decision_result: Dict[str, Any]) -> str:
        """결정 결과에서 서비스 타입을 추출"""
        return "model_only"

# 전역 인스턴스 생성
langchain_decision_service = LangchainDecisionService() 