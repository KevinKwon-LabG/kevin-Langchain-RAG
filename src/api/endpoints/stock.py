"""
주식 서비스 API 엔드포인트 - 더미 버전
주식 관련 요청을 처리하는 API (더미 버전)
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.services.stock_service import stock_service

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("stock_api_debug")

router = APIRouter(prefix="/api/stock", tags=["Stock"])

class StockRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = "gemma3:12b-it-qat"

class StockParamsRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@router.post("/")
async def stock_request(request: StockRequest):
    """
    주식 정보 요청을 처리합니다 (더미 버전).
    
    Args:
        request: 주식 요청 정보
    
    Returns:
        주식 정보 (더미 데이터)
    """
    try:
        debug_logger.debug(f"📈 주식 요청 처리 (더미): {request.message}")
        
        # 더미 주식 서비스를 통해 처리
        response = stock_service.process_stock_request(
            request.message, 
            request.session_id
        )
        
        return {
            "status": "success",
            "response": response,
            "session_id": request.session_id,
            "service": "stock",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 주식 요청 처리 중 오류: {e}")
        return {
            "status": "error",
            "response": f"주식 정보를 처리하는 중 오류가 발생했습니다: {str(e)}",
            "service": "stock",
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }

@router.post("/params")
async def extract_stock_params(request: StockParamsRequest):
    """
    주식 파라미터를 추출합니다 (더미 버전).
    
    Args:
        request: 파라미터 추출 요청
    
    Returns:
        추출된 파라미터 (더미 데이터)
    """
    try:
        debug_logger.debug(f"🔍 주식 파라미터 추출 (더미): {request.message}")
        
        # 더미 파라미터 반환
        params = {
            "stock_name": "더미주식",
            "stock_code": "000000",
            "sector": "더미섹터",
            "action": "정보조회",
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
        debug_logger.error(f"❌ 주식 파라미터 추출 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/info")
async def get_stock_service_info():
    """
    주식 서비스 정보를 반환합니다.
    
    Returns:
        서비스 정보
    """
    try:
        debug_logger.debug("📋 주식 서비스 정보 조회")
        
        info = {
            "service_name": "stock_service",
            "version": "1.0.0",
            "status": "dummy_mode",
            "description": "주식 정보 서비스 (더미 버전)",
            "features": [
                "더미 주식 정보 제공",
                "파라미터 추출 (더미)",
                "서비스 정보 조회"
            ],
            "supported_stocks": ["더미주식"],
            "supported_sectors": ["더미섹터"]
        }
        
        return {
            "status": "success",
            "info": info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 주식 서비스 정보 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/stocks")
async def get_supported_stocks():
    """
    지원하는 주식 목록을 반환합니다 (더미 버전).
    
    Returns:
        주식 목록 (더미 데이터)
    """
    try:
        debug_logger.debug("📋 지원 주식 목록 조회 (더미)")
        
        stocks = [
            {
                "name": "더미주식1",
                "code": "000001",
                "sector": "더미섹터1"
            },
            {
                "name": "더미주식2", 
                "code": "000002",
                "sector": "더미섹터2"
            }
        ]
        
        return {
            "status": "success",
            "stocks": stocks,
            "total_count": len(stocks),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 주식 목록 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/sectors")
async def get_supported_sectors():
    """
    지원하는 섹터 목록을 반환합니다 (더미 버전).
    
    Returns:
        섹터 목록 (더미 데이터)
    """
    try:
        debug_logger.debug("📋 지원 섹터 목록 조회 (더미)")
        
        sectors = [
            "더미섹터1",
            "더미섹터2",
            "더미섹터3"
        ]
        
        return {
            "status": "success",
            "sectors": sectors,
            "total_count": len(sectors),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 섹터 목록 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/sectors/{sector}")
async def get_stocks_by_sector(sector: str):
    """
    특정 섹터의 주식 목록을 반환합니다 (더미 버전).
    
    Args:
        sector: 섹터명
    
    Returns:
        해당 섹터의 주식 목록 (더미 데이터)
    """
    try:
        debug_logger.debug(f"📋 섹터별 주식 목록 조회 (더미): {sector}")
        
        stocks = [
            {
                "name": f"더미주식_{sector}1",
                "code": "000001",
                "sector": sector
            },
            {
                "name": f"더미주식_{sector}2",
                "code": "000002", 
                "sector": sector
            }
        ]
        
        return {
            "status": "success",
            "sector": sector,
            "stocks": stocks,
            "total_count": len(stocks),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        debug_logger.error(f"❌ 섹터별 주식 목록 조회 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 