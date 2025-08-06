"""
주식 관련 서비스 - 더미 버전
한국 주식 시장 정보를 처리하는 서비스 (더미 버전)
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("stock_service_debug")
debug_logger.setLevel(logging.DEBUG)

class StockService:
    """
    한국 주식 시장 정보를 처리하는 서비스 (더미 버전)
    """
    
    def __init__(self):
        """주식 서비스 초기화 (더미 버전)"""
        debug_logger.info("🔧 주식 서비스 초기화 완료 (더미 버전)")
    
    def extract_stock_keywords(self, user_prompt: str) -> Dict[str, Any]:
        """
        사용자 프롬프트에서 주식 관련 키워드를 추출합니다 (더미 버전).
        
        Args:
            user_prompt: 사용자 프롬프트
            
        Returns:
            Dict[str, Any]: 추출된 키워드 정보
        """
        debug_logger.debug(f"📈 주식 키워드 추출 (더미): {user_prompt}")
        
        # 더미 키워드 추출 결과
        return {
            "stock_name": None,
            "stock_code": None,
            "sector": None,
            "action": None,
            "confidence": 0.0,
            "extracted": False
        }
    
    def process_stock_request(self, user_prompt: str, session_id: Optional[str] = None) -> str:
        """
        주식 관련 요청을 처리합니다 (더미 버전).
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID (사용되지 않음)
            
        Returns:
            str: 처리 결과 메시지
        """
        try:
            debug_logger.debug(f"📈 주식 요청 처리 (더미): {user_prompt}")
            
            # 더미 응답 반환
            response = "죄송합니다. 현재 주식 정보 서비스를 사용할 수 없습니다. 일반적인 질문에 대해 답변드리겠습니다."
            
            debug_logger.debug("✅ 주식 요청 처리 완료 (더미)")
            return response
            
        except Exception as e:
            debug_logger.error(f"❌ 주식 요청 처리 중 오류 (더미): {e}")
            return f"주식 정보를 처리하는 중 오류가 발생했습니다: {str(e)}"
    
    def get_stock_info(self, stock_name: str = None, stock_code: str = None) -> Dict[str, Any]:
        """
        주식 정보를 조회합니다 (더미 버전).
        
        Args:
            stock_name: 주식명
            stock_code: 주식 코드
            
        Returns:
            Dict[str, Any]: 주식 정보 (더미 데이터)
        """
        debug_logger.debug(f"📈 주식 정보 조회 (더미): {stock_name} / {stock_code}")
        
        # 더미 주식 정보 반환
        return {
            "name": stock_name or "더미주식",
            "code": stock_code or "000000",
            "price": "0",
            "change": "0",
            "change_rate": "0%",
            "volume": "0",
            "market_cap": "0",
            "status": "더미 데이터"
        }
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        주식을 검색합니다 (더미 버전).
        
        Args:
            keyword: 검색 키워드
            
        Returns:
            List[Dict[str, Any]]: 검색 결과 (더미 데이터)
        """
        debug_logger.debug(f"🔍 주식 검색 (더미): {keyword}")
        
        # 더미 검색 결과 반환
        return [
            {
                "name": f"더미주식_{keyword}",
                "code": "000000",
                "sector": "더미섹터",
                "price": "0",
                "change": "0",
                "change_rate": "0%"
            }
        ]

# 전역 인스턴스 생성
stock_service = StockService() 