"""
날씨 서비스 API 엔드포인트 - 더미 버전
날씨 관련 요청을 처리하는 API (더미 버전)
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from src.services.weather_service import weather_service

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("weather_api_debug")

router = APIRouter(prefix="/api/weather", tags=["Weather"])

class WeatherRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = "gemma3:12b-it-qat"

class WeatherParamsRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@router.post("/")
async def weather_request(request: WeatherRequest):
    """
    날씨 정보 요청을 처리합니다 (더미 버전).
    
    Args:
        request: 날씨 요청 정보
    
    Returns:
        날씨 정보 (더미 데이터)
    """
    try:
        debug_logger.debug(f"🌤️ 날씨 요청 처리 (더미): {request.message}")
        
        # 더미 날씨 서비스를 통해 처리
        response, is_completed = await weather_service.process_weather_request(
            request.message, 
            request.session_id
        )
        
        return {
            "status": "success",
            "response": response,
            "is_completed": is_completed,
            "session_id": request.session_id,
            "service": "weather",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 날씨 요청 처리 중 오류: {e}")
        return {
            "status": "error",
            "response": f"날씨 정보를 처리하는 중 오류가 발생했습니다: {str(e)}",
            "service": "weather",
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }

@router.post("/params")
async def extract_weather_params(request: WeatherParamsRequest):
    """
    날씨 파라미터를 추출합니다 (더미 버전).
    
    Args:
        request: 파라미터 추출 요청
    
    Returns:
        추출된 파라미터 (더미 데이터)
    """
    try:
        debug_logger.debug(f"🔍 날씨 파라미터 추출 (더미): {request.message}")
        
        # 더미 파라미터 반환
        params = {
            "city": "더미도시",
            "date": "오늘",
            "time": "현재",
            "extracted": False,
            "confidence": 0.0
        }
        
        return {
            "status": "success",
            "params": params,
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 날씨 파라미터 추출 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/info")
async def get_weather_service_info():
    """
    날씨 서비스 정보를 반환합니다.
    
    Returns:
        서비스 정보
    """
    try:
        debug_logger.debug("📋 날씨 서비스 정보 조회")
        
        info = {
            "service_name": "weather_service",
            "version": "1.0.0",
            "status": "dummy_mode",
            "description": "날씨 정보 서비스 (더미 버전)",
            "features": [
                "더미 날씨 정보 제공",
                "파라미터 추출 (더미)",
                "서비스 정보 조회"
            ],
            "supported_cities": ["더미도시"],
            "supported_formats": ["더미 데이터"]
        }
        
        return {
            "status": "success",
            "info": info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 날씨 서비스 정보 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 