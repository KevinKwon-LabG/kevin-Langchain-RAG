"""
웹 검색 관련 API 엔드포인트
웹 검색, 웹페이지 내용 가져오기 등을 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.models.schemas import WebSearchRequest
from src.services.integrated_mcp_client import OptimizedIntegratedMCPClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/web", tags=["Web"])

@router.get("/search")
async def web_search(
    q: str = Query(..., description="검색할 키워드"),
    max_results: int = Query(5, description="최대 결과 수", ge=1, le=20)
):
    """
    키워드 기반 웹 검색을 수행합니다.
    
    Args:
        q: 검색할 키워드
        max_results: 최대 결과 수 (1-20, 기본값: 5)
    
    Returns:
        검색 결과 목록
    
    Raises:
        HTTPException: 검색어가 비어있거나 서비스 오류가 발생한 경우
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")
    
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.web_search(q, max_results)
            return result
    except Exception as e:
        logger.error(f"웹 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"웹 검색 중 오류가 발생했습니다: {str(e)}")

@router.post("/search")
async def web_search_post(request: WebSearchRequest):
    """
    POST 요청으로 웹 검색을 수행합니다.
    
    Args:
        request: 웹 검색 요청 모델
    
    Returns:
        검색 결과 목록
    """
    return await web_search(request.query, request.max_results)

@router.get("/fetch")
async def fetch_webpage(url: str = Query(..., description="가져올 웹페이지 URL")):
    """
    웹페이지 내용을 가져옵니다.
    
    Args:
        url: 가져올 웹페이지 URL
    
    Returns:
        웹페이지 내용
    
    Raises:
        HTTPException: URL이 유효하지 않거나 접근할 수 없는 경우
    """
    if not url.strip():
        raise HTTPException(status_code=400, detail="URL을 입력해주세요.")
    
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.fetch_webpage(url)
            return result
    except Exception as e:
        logger.error(f"웹페이지 가져오기 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"웹페이지 가져오기 중 오류가 발생했습니다: {str(e)}")

@router.post("/fetch")
async def fetch_webpage_post(url: str):
    """
    POST 요청으로 웹페이지 내용을 가져옵니다.
    
    Args:
        url: 가져올 웹페이지 URL
    
    Returns:
        웹페이지 내용
    """
    return await fetch_webpage(url)

@router.get("/search/advanced")
async def advanced_web_search(
    q: str = Query(..., description="검색할 키워드"),
    max_results: int = Query(5, description="최대 결과 수", ge=1, le=20),
    language: str = Query("ko", description="검색 언어 (ko, en, ja 등)"),
    region: str = Query("KR", description="검색 지역 (KR, US, JP 등)"),
    time_range: str = Query("all", description="시간 범위 (day, week, month, year, all)")
):
    """
    고급 웹 검색을 수행합니다.
    
    Args:
        q: 검색할 키워드
        max_results: 최대 결과 수
        language: 검색 언어
        region: 검색 지역
        time_range: 시간 범위
    
    Returns:
        고급 검색 결과
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")
    
    try:
        async with OptimizedIntegratedMCPClient() as client:
            # 기본 검색 수행
            result = await client.web_search(q, max_results)
            
            # 고급 검색 메타데이터 추가
            advanced_result = {
                "query": q,
                "max_results": max_results,
                "language": language,
                "region": region,
                "time_range": time_range,
                "search_results": result,
                "search_metadata": {
                    "total_results": len(result.get("results", [])),
                    "search_time": "2024-01-01T12:00:00Z",
                    "search_engine": "integrated"
                }
            }
            return advanced_result
    except Exception as e:
        logger.error(f"고급 웹 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"고급 웹 검색 중 오류가 발생했습니다: {str(e)}")

@router.get("/trending")
async def get_trending_searches():
    """
    인기 검색어를 반환합니다.
    
    Returns:
        인기 검색어 목록
    """
    trending_searches = [
        {"keyword": "인공지능", "category": "기술", "trend": "up"},
        {"keyword": "주식 투자", "category": "금융", "trend": "up"},
        {"keyword": "코로나19", "category": "건강", "trend": "down"},
        {"keyword": "환경 보호", "category": "사회", "trend": "up"},
        {"keyword": "디지털 전환", "category": "비즈니스", "trend": "up"},
        {"keyword": "원격 근무", "category": "직장", "trend": "stable"},
        {"keyword": "전기차", "category": "자동차", "trend": "up"},
        {"keyword": "메타버스", "category": "기술", "trend": "up"},
        {"keyword": "암호화폐", "category": "금융", "trend": "down"},
        {"keyword": "건강 관리", "category": "라이프스타일", "trend": "up"}
    ]
    return {"trending_searches": trending_searches}

@router.get("/search/history")
async def get_search_history(limit: int = Query(10, description="조회할 검색 기록 수", ge=1, le=100)):
    """
    검색 기록을 조회합니다.
    
    Args:
        limit: 조회할 검색 기록 수
    
    Returns:
        검색 기록 목록
    """
    # 실제 구현에서는 사용자별 검색 기록을 데이터베이스에서 조회
    search_history = [
        {
            "query": "파이썬 프로그래밍",
            "timestamp": "2024-01-01T10:30:00Z",
            "results_count": 5
        },
        {
            "query": "FastAPI 튜토리얼",
            "timestamp": "2024-01-01T09:15:00Z",
            "results_count": 3
        },
        {
            "query": "주식 투자 전략",
            "timestamp": "2024-01-01T08:45:00Z",
            "results_count": 7
        }
    ]
    return {"search_history": search_history[:limit]} 