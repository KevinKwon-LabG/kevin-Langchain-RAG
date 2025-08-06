"""
웹 검색 서비스 - 더미 버전
웹 검색 관련 요청을 처리하는 전용 서비스입니다 (더미 버전).
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("web_search_debug")

class WebSearchService:
    """
    웹 검색을 처리하는 서비스 (더미 버전)
    """
    
    def __init__(self):
        self.service_name = "web_search_service"
        debug_logger.info("🔍 웹 검색 서비스 초기화 완료 (더미 버전)")
    
    async def process_web_search_request(self, user_prompt: str, session_id: Optional[str] = None) -> str:
        """
        웹 검색 요청을 처리합니다 (더미 버전).
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID (사용되지 않음)
            
        Returns:
            str: 처리 결과 메시지
        """
        try:
            debug_logger.debug(f"🔍 웹 검색 요청 처리 (더미): {user_prompt}")
            
            # 더미 응답 반환
            response = "죄송합니다. 현재 웹 검색 서비스를 사용할 수 없습니다. 일반적인 질문에 대해 답변드리겠습니다."
            
            debug_logger.debug("✅ 웹 검색 요청 처리 완료 (더미)")
            return response
            
        except Exception as e:
            debug_logger.error(f"❌ 웹 검색 요청 처리 중 오류 (더미): {e}")
            return f"웹 검색을 처리하는 중 오류가 발생했습니다: {str(e)}"
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        웹 검색을 수행합니다 (더미 버전).
        
        Args:
            query: 검색어
            max_results: 최대 결과 수
            
        Returns:
            List[Dict[str, Any]]: 검색 결과 (더미 데이터)
        """
        debug_logger.debug(f"🔍 웹 검색 수행 (더미): {query}")
        
        # 더미 검색 결과 반환
        results = []
        for i in range(min(max_results, 3)):
            results.append({
                "title": f"더미 검색 결과 {i+1} - {query}",
                "url": f"https://dummy.com/result{i+1}",
                "snippet": f"이것은 '{query}'에 대한 더미 검색 결과 {i+1}입니다.",
                "status": "더미 데이터"
            })
        
        return results
    
    def search_news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        뉴스 검색을 수행합니다 (더미 버전).
        
        Args:
            query: 검색어
            max_results: 최대 결과 수
            
        Returns:
            List[Dict[str, Any]]: 뉴스 검색 결과 (더미 데이터)
        """
        debug_logger.debug(f"📰 뉴스 검색 수행 (더미): {query}")
        
        # 더미 뉴스 검색 결과 반환
        results = []
        for i in range(min(max_results, 3)):
            results.append({
                "title": f"더미 뉴스 {i+1} - {query}",
                "url": f"https://dummy-news.com/article{i+1}",
                "snippet": f"이것은 '{query}'에 대한 더미 뉴스 {i+1}입니다.",
                "published_date": "2024-01-01",
                "status": "더미 데이터"
            })
        
        return results

# 전역 인스턴스 생성
web_search_service = WebSearchService() 