"""
주식 관련 API 엔드포인트
주식 정보 조회, 검색, 가격 데이터 등을 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.models.schemas import StockQuery
from src.services.integrated_mcp_client import (
    OptimizedIntegratedMCPClient, 
    StockNotFoundError, 
    InvalidStockCodeError, 
    ServiceUnavailableError,
    safe_mcp_call
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["Stock"])

@router.get("/{stock_code}")
async def get_stock_info(stock_code: str):
    """
    주식 코드로 상세 정보를 조회합니다.
    
    Args:
        stock_code: 6자리 주식 코드 (예: 005930)
    
    Returns:
        주식 상세 정보 (회사명, 현재가, 시장구분 등)
    
    Raises:
        HTTPException: 종목을 찾을 수 없거나 잘못된 코드인 경우
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await safe_mcp_call(client, client.get_stock_info, stock_code)
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            if not result.get('success', True):
                error_msg = result.get('error', '알 수 없는 오류가 발생했습니다')
                raise HTTPException(status_code=404, detail=error_msg)
            
            return result
            
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail=f"종목 코드 {stock_code}를 찾을 수 없습니다.")
    except InvalidStockCodeError:
        raise HTTPException(status_code=400, detail=f"잘못된 종목 코드 형식입니다: {stock_code}")
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"서비스를 사용할 수 없습니다: {str(e)}")
    except Exception as e:
        logger.error(f"주식 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="내부 서버 오류가 발생했습니다.")

@router.get("/search/{keyword}")
async def search_stock(keyword: str):
    """
    종목명 또는 키워드로 주식 종목을 검색합니다.
    
    Args:
        keyword: 검색할 종목명 또는 키워드
    
    Returns:
        검색 결과 목록
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await safe_mcp_call(client, client.search_stock, keyword)
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            if not result.get('success', True):
                error_msg = result.get('error', '검색 중 오류가 발생했습니다')
                raise HTTPException(status_code=500, detail=error_msg)
            
            return result
            
    except Exception as e:
        logger.error(f"주식 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail="검색 중 오류가 발생했습니다.")

@router.get("/{stock_code}/price")
async def get_stock_price_data(
    stock_code: str,
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)")
):
    """
    주식 가격 데이터를 조회합니다.
    
    Args:
        stock_code: 6자리 주식 코드
        start_date: 시작 날짜 (선택사항)
        end_date: 종료 날짜 (선택사항)
    
    Returns:
        OHLCV 가격 데이터
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await safe_mcp_call(
                client, 
                client.get_stock_price_data, 
                stock_code, 
                start_date, 
                end_date
            )
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            if not result.get('success', True):
                error_msg = result.get('error', '가격 데이터 조회 중 오류가 발생했습니다')
                raise HTTPException(status_code=404, detail=error_msg)
            
            return result
            
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail=f"종목 코드 {stock_code}를 찾을 수 없습니다.")
    except InvalidStockCodeError:
        raise HTTPException(status_code=400, detail=f"잘못된 종목 코드 형식입니다: {stock_code}")
    except Exception as e:
        logger.error(f"주식 가격 데이터 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="가격 데이터 조회 중 오류가 발생했습니다.")

@router.get("/{stock_code}/market-cap")
async def get_stock_market_cap(
    stock_code: str,
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)")
):
    """
    주식 시가총액 데이터를 조회합니다.
    
    Args:
        stock_code: 6자리 주식 코드
        start_date: 시작 날짜 (선택사항)
        end_date: 종료 날짜 (선택사항)
    
    Returns:
        시가총액 변화 데이터
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await safe_mcp_call(
                client, 
                client.get_stock_market_cap, 
                stock_code, 
                start_date, 
                end_date
            )
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            if not result.get('success', True):
                error_msg = result.get('error', '시가총액 데이터 조회 중 오류가 발생했습니다')
                raise HTTPException(status_code=404, detail=error_msg)
            
            return result
            
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail=f"종목 코드 {stock_code}를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"주식 시가총액 데이터 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="시가총액 데이터 조회 중 오류가 발생했습니다.")

@router.get("/{stock_code}/fundamental")
async def get_stock_fundamental(
    stock_code: str,
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)")
):
    """
    주식 기본 지표 데이터를 조회합니다.
    
    Args:
        stock_code: 6자리 주식 코드
        start_date: 시작 날짜 (선택사항)
        end_date: 종료 날짜 (선택사항)
    
    Returns:
        PER, PBR, 배당수익률 등 기본 지표 데이터
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await safe_mcp_call(
                client, 
                client.get_stock_fundamental, 
                stock_code, 
                start_date, 
                end_date
            )
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            if not result.get('success', True):
                error_msg = result.get('error', '기본 지표 데이터 조회 중 오류가 발생했습니다')
                raise HTTPException(status_code=404, detail=error_msg)
            
            return result
            
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail=f"종목 코드 {stock_code}를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"주식 기본 지표 데이터 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="기본 지표 데이터 조회 중 오류가 발생했습니다.")

@router.post("/batch")
async def get_multiple_stock_info(stock_codes: list[str]):
    """
    여러 주식 정보를 동시에 조회합니다.
    
    Args:
        stock_codes: 주식 코드 목록
    
    Returns:
        각 주식 코드별 정보
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.get_multiple_stock_info(stock_codes)
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            return result
            
    except Exception as e:
        logger.error(f"배치 주식 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="배치 조회 중 오류가 발생했습니다.")

@router.get("/tickers/all")
async def load_all_tickers():
    """
    모든 주식 종목 정보를 로드합니다.
    
    Returns:
        KOSPI/KOSDAQ 모든 종목 정보
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.load_all_tickers()
            
            # 응답 형식 검증
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail="응답 형식이 올바르지 않습니다")
            
            if not result.get('success', True):
                error_msg = result.get('error', '종목 정보 로드 중 오류가 발생했습니다')
                raise HTTPException(status_code=500, detail=error_msg)
            
            return result
            
    except Exception as e:
        logger.error(f"전체 종목 정보 로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail="종목 정보 로드 중 오류가 발생했습니다.")

@router.post("/extract-keyword")
async def extract_stock_keyword(request: dict):
    """
    사용자 프롬프트에서 주식 키워드를 추출합니다.
    
    Args:
        request: {"prompt": "사용자 프롬프트"}
    
    Returns:
        추출된 키워드 정보
    """
    try:
        from src.services.stock_keyword_extractor import stock_keyword_extractor
        
        prompt = request.get("prompt", "")
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="프롬프트를 입력해주세요.")
        
        result = await stock_keyword_extractor.extract_stock_keyword(prompt)
        return result
        
    except Exception as e:
        logger.error(f"키워드 추출 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"키워드 추출 중 오류가 발생했습니다: {str(e)}")

@router.post("/extract-keywords")
async def extract_multiple_stock_keywords(request: dict):
    """
    사용자 프롬프트에서 여러 주식 키워드를 추출합니다.
    
    Args:
        request: {"prompt": "사용자 프롬프트"}
    
    Returns:
        추출된 키워드 목록
    """
    try:
        from src.services.stock_keyword_extractor import stock_keyword_extractor
        
        prompt = request.get("prompt", "")
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="프롬프트를 입력해주세요.")
        
        result = await stock_keyword_extractor.extract_multiple_keywords(prompt)
        return result
        
    except Exception as e:
        logger.error(f"다중 키워드 추출 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"다중 키워드 추출 중 오류가 발생했습니다: {str(e)}")

@router.post("/extract-and-search")
async def extract_and_search_stock(request: dict):
    """
    사용자 프롬프트에서 키워드를 추출하고 주식 검색 및 상세 정보를 조회합니다.
    
    Args:
        request: {"prompt": "사용자 프롬프트"}
    
    Returns:
        키워드 추출 → 검색 → 상세 정보 조회 결과
    """
    try:
        from src.services.stock_keyword_extractor import stock_keyword_extractor
        
        prompt = request.get("prompt", "")
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="프롬프트를 입력해주세요.")
        
        result = await stock_keyword_extractor.extract_and_get_stock_info(prompt)
        return result
        
    except Exception as e:
        logger.error(f"키워드 추출 및 주식 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"키워드 추출 및 주식 검색 중 오류가 발생했습니다: {str(e)}") 