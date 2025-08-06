"""
날씨 정보 서비스 - 더미 버전
날씨 관련 요청을 처리하는 전용 서비스입니다 (더미 버전).
"""

import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("weather_debug")

class WeatherService:
    """
    날씨 정보를 처리하는 서비스 (더미 버전)
    """
    
    def __init__(self):
        self.service_name = "weather_service"
        debug_logger.info("🌤️ 날씨 서비스 초기화 완료 (더미 버전)")
    
    async def process_weather_request(self, user_prompt: str, session_id: Optional[str] = None) -> Tuple[str, bool]:
        """
        날씨 관련 요청을 처리합니다 (더미 버전).
        
        Args:
            user_prompt: 사용자 프롬프트
            session_id: 세션 ID (사용되지 않음)
            
        Returns:
            Tuple[str, bool]: (응답 메시지, 완료 여부)
        """
        try:
            debug_logger.debug(f"🌤️ 날씨 요청 처리 (더미): {user_prompt}")
            
            # 더미 응답 반환
            response = "죄송합니다. 현재 날씨 정보 서비스를 사용할 수 없습니다. 일반적인 질문에 대해 답변드리겠습니다."
            
            debug_logger.debug("✅ 날씨 요청 처리 완료 (더미)")
            return response, True
            
        except Exception as e:
            debug_logger.error(f"❌ 날씨 요청 처리 중 오류 (더미): {e}")
            return f"날씨 정보를 처리하는 중 오류가 발생했습니다: {str(e)}", True
    
    def get_weather_info(self, city: str = None, date: str = None) -> Dict[str, Any]:
        """
        날씨 정보를 조회합니다 (더미 버전).
        
        Args:
            city: 도시명
            date: 날짜
            
        Returns:
            Dict[str, Any]: 날씨 정보 (더미 데이터)
        """
        debug_logger.debug(f"🌤️ 날씨 정보 조회 (더미): {city} / {date}")
        
        # 더미 날씨 정보 반환
        return {
            "city": city or "더미도시",
            "date": date or "오늘",
            "temperature": "20°C",
            "condition": "맑음",
            "humidity": "60%",
            "wind_speed": "5km/h",
            "status": "더미 데이터"
        }
    
    def search_city_weather(self, city_name: str) -> Dict[str, Any]:
        """
        도시별 날씨를 검색합니다 (더미 버전).
        
        Args:
            city_name: 도시명
            
        Returns:
            Dict[str, Any]: 날씨 정보 (더미 데이터)
        """
        debug_logger.debug(f"🔍 도시 날씨 검색 (더미): {city_name}")
        
        # 더미 검색 결과 반환
        return {
            "city": city_name,
            "temperature": "20°C",
            "condition": "맑음",
            "humidity": "60%",
            "wind_speed": "5km/h",
            "status": "더미 데이터"
        }

# 전역 인스턴스 생성
weather_service = WeatherService() 