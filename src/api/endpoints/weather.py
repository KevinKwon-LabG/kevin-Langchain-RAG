"""
날씨 관련 API 엔드포인트
도시별 실시간 날씨 정보를 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException
from src.models.schemas import WeatherRequest
from src.services.integrated_mcp_client import OptimizedIntegratedMCPClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/weather", tags=["Weather"])

@router.get("/{city}")
async def get_weather(city: str):
    """
    도시별 실시간 날씨 정보를 조회합니다.
    
    Args:
        city: 날씨를 조회할 도시명 (예: 서울, 부산, 대구 등)
    
    Returns:
        현재 날씨 정보 (온도, 습도, 날씨 상태, 풍속 등)
    
    Raises:
        HTTPException: 도시를 찾을 수 없거나 서비스 오류가 발생한 경우
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.get_weather(city)
            return result
    except Exception as e:
        logger.error(f"날씨 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"날씨 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/")
async def get_weather_by_query(city: str):
    """
    쿼리 파라미터로 날씨 정보를 조회합니다.
    
    Args:
        city: 날씨를 조회할 도시명
    
    Returns:
        현재 날씨 정보
    """
    return await get_weather(city)

@router.post("/")
async def get_weather_by_post(request: WeatherRequest):
    """
    POST 요청으로 날씨 정보를 조회합니다.
    
    Args:
        request: 날씨 요청 모델 (도시명 포함)
    
    Returns:
        현재 날씨 정보
    """
    return await get_weather(request.city)

@router.get("/cities/popular")
async def get_popular_cities():
    """
    인기 도시 목록을 반환합니다.
    
    Returns:
        인기 도시 목록
    """
    popular_cities = [
        {"name": "서울", "country": "대한민국", "region": "수도권"},
        {"name": "부산", "country": "대한민국", "region": "부산"},
        {"name": "대구", "country": "대한민국", "region": "대구"},
        {"name": "인천", "country": "대한민국", "region": "수도권"},
        {"name": "광주", "country": "대한민국", "region": "전라도"},
        {"name": "대전", "country": "대한민국", "region": "충청도"},
        {"name": "울산", "country": "대한민국", "region": "울산"},
        {"name": "제주", "country": "대한민국", "region": "제주도"},
        {"name": "수원", "country": "대한민국", "region": "수도권"},
        {"name": "고양", "country": "대한민국", "region": "수도권"}
    ]
    return {"cities": popular_cities}

@router.get("/forecast/{city}")
async def get_weather_forecast(city: str, days: int = 5):
    """
    도시의 날씨 예보를 조회합니다.
    
    Args:
        city: 예보를 조회할 도시명
        days: 예보 일수 (기본값: 5일)
    
    Returns:
        날씨 예보 정보
    """
    try:
        # 현재는 기본 날씨 정보만 반환
        # 실제로는 예보 API를 연동해야 함
        async with OptimizedIntegratedMCPClient() as client:
            current_weather = await client.get_weather(city)
            
            # 예보 데이터 시뮬레이션 (실제 구현에서는 예보 API 사용)
            forecast_data = {
                "city": city,
                "forecast_days": days,
                "current": current_weather,
                "forecast": [
                    {
                        "date": f"2024-01-{i+1:02d}",
                        "temperature": {"min": 15 + i, "max": 25 + i},
                        "condition": "맑음",
                        "humidity": 60 + (i % 20),
                        "wind_speed": 5 + (i % 10)
                    }
                    for i in range(days)
                ]
            }
            return forecast_data
    except Exception as e:
        logger.error(f"날씨 예보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"날씨 예보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/air-quality/{city}")
async def get_air_quality(city: str):
    """
    도시의 대기질 정보를 조회합니다.
    
    Args:
        city: 대기질을 조회할 도시명
    
    Returns:
        대기질 정보 (PM10, PM2.5, 오존 등)
    """
    try:
        # 현재는 기본 정보만 반환
        # 실제로는 대기질 API를 연동해야 함
        air_quality_data = {
            "city": city,
            "timestamp": "2024-01-01T12:00:00Z",
            "pm10": 45,
            "pm25": 25,
            "o3": 0.03,
            "no2": 0.02,
            "so2": 0.005,
            "co": 0.5,
            "aqi": 65,
            "status": "보통"
        }
        return air_quality_data
    except Exception as e:
        logger.error(f"대기질 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"대기질 정보 조회 중 오류가 발생했습니다: {str(e)}") 