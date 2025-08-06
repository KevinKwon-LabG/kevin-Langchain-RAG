"""
웹 검색 서비스 API 엔드포인트 - 더미 버전
웹 검색 관련 요청을 처리하는 API (더미 버전)
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.services.web_search_service import web_search_service

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("web_search_api_debug")

router = APIRouter(prefix="/api/web-search", tags=["Web Search"])

class SearchQueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = "gemma3:12b-it-qat"
    max_results: Optional[int] = 5

class DirectSearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    search_engine: Optional[str] = "google"

@router.post("/")
async def web_search_request(request: SearchQueryRequest):
    """
    웹 검색 요청을 처리합니다 (더미 버전).
    
    Args:
        request: 웹 검색 요청 정보
    
    Returns:
        검색 결과 (더미 데이터)
    """
    try:
        debug_logger.debug(f"🔍 웹 검색 요청 처리 (더미): {request.message}")
        
        # 더미 웹 검색 서비스를 통해 처리
        response = await web_search_service.process_web_search_request(
            request.message, 
            request.session_id
        )
        
        return {
            "status": "success",
            "response": response,
            "session_id": request.session_id,
            "service": "web_search",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 웹 검색 요청 처리 중 오류: {e}")
        return {
            "status": "error",
            "response": f"웹 검색을 처리하는 중 오류가 발생했습니다: {str(e)}",
            "service": "web_search",
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }

@router.post("/extract-query")
async def extract_search_query(request: SearchQueryRequest):
    """
    검색어를 추출합니다 (더미 버전).
    
    Args:
        request: 검색어 추출 요청
    
    Returns:
        추출된 검색어 (더미 데이터)
    """
    try:
        debug_logger.debug(f"🔍 검색어 추출 (더미): {request.message}")
        
        # 더미 검색어 반환
        extracted_query = f"더미 검색어: {request.message}"
        
        return {
            "status": "success",
            "extracted_query": extracted_query,
            "original_message": request.message,
            "confidence": 0.0,
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 검색어 추출 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }

@router.post("/search")
async def direct_search(request: DirectSearchRequest):
    """
    직접 웹 검색을 수행합니다 (더미 버전).
    
    Args:
        request: 직접 검색 요청
    
    Returns:
        검색 결과 (더미 데이터)
    """
    try:
        debug_logger.debug(f"🔍 직접 웹 검색 (더미): {request.query}")
        
        # 더미 검색 결과 반환
        results = web_search_service.search_web(
            request.query, 
            request.max_results
        )
        
        return {
            "status": "success",
            "query": request.query,
            "results": results,
            "total_count": len(results),
            "search_engine": request.search_engine,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 직접 웹 검색 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/info")
async def get_web_search_service_info():
    """
    웹 검색 서비스 정보를 반환합니다.
    
    Returns:
        서비스 정보
    """
    try:
        debug_logger.debug("📋 웹 검색 서비스 정보 조회")
        
        info = {
            "service_name": "web_search_service",
            "version": "1.0.0",
            "status": "dummy_mode",
            "description": "웹 검색 서비스 (더미 버전)",
            "features": [
                "더미 웹 검색 결과 제공",
                "검색어 추출 (더미)",
                "직접 검색 (더미)",
                "서비스 정보 조회"
            ],
            "supported_engines": ["더미엔진"],
            "max_results_limit": 10
        }
        
        return {
            "status": "success",
            "info": info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 웹 검색 서비스 정보 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/engines")
async def get_supported_search_engines():
    """
    지원하는 검색 엔진 목록을 반환합니다 (더미 버전).
    
    Returns:
        검색 엔진 목록 (더미 데이터)
    """
    try:
        debug_logger.debug("📋 지원 검색 엔진 목록 조회 (더미)")
        
        engines = [
            {
                "name": "더미엔진1",
                "description": "더미 검색 엔진 1",
                "status": "available"
            },
            {
                "name": "더미엔진2",
                "description": "더미 검색 엔진 2", 
                "status": "available"
            }
        ]
        
        return {
            "status": "success",
            "engines": engines,
            "total_count": len(engines),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 검색 엔진 목록 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 