"""
Web Search Mode API 엔드포인트
웹 검색 모드 설정 및 관리를 위한 API를 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

@router.get("/api/web-search-modes")
async def get_web_search_modes():
    """
    웹 검색 모드 목록을 반환합니다.
    
    Returns:
        웹 검색 모드 목록과 현재 선택된 모드
    """
    try:
        from src.api.endpoints.chat import get_web_search_mode
        
        modes = [
            {
                "value": "model_only",
                "label": "모델에서만 답변",
                "description": "AI 모델의 지식만으로 답변합니다"
            },
            {
                "value": "mcp_server",
                "label": "MCP 서버 통합 검색",
                "description": "MCP 서버의 지능형 서비스 (주식, 날씨, 웹 검색)를 자동으로 선택하여 활용합니다"
            }
        ]
        return {
            "modes": modes,
            "current_mode": get_web_search_mode()  # 실제 현재 모드
        }
    except Exception as e:
        logger.error(f"웹 검색 모드 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"웹 검색 모드 조회 실패: {str(e)}")

@router.post("/api/web-search-mode")
async def set_web_search_mode(request: Request):
    """
    웹 검색 모드를 설정합니다.
    
    Args:
        request: FastAPI 요청 객체 (JSON body에 mode 포함)
    
    Returns:
        설정 결과
    """
    try:
        body = await request.json()
        mode = body.get("mode")
        
        if not mode:
            raise HTTPException(status_code=400, detail="모드가 필요합니다")
        
        # 채팅 엔드포인트의 웹 검색 모드 설정 함수 호출
        from src.api.endpoints.chat import set_web_search_mode
        set_web_search_mode(mode)
        
        logger.info(f"웹 검색 모드 변경: {mode}")
        
        return {
            "success": True,
            "message": f"웹 검색 모드가 '{mode}'로 변경되었습니다",
            "mode": mode
        }
    except Exception as e:
        logger.error(f"웹 검색 모드 설정 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"웹 검색 모드 설정 실패: {str(e)}")

@router.get("/api/web-search-mode/current")
async def get_current_web_search_mode():
    """
    현재 설정된 웹 검색 모드를 반환합니다.
    
    Returns:
        현재 웹 검색 모드 정보
    """
    try:
        from src.api.endpoints.chat import get_web_search_mode
        
        current_mode = get_web_search_mode()
        
        return {
            "current_mode": current_mode,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"현재 웹 검색 모드 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"현재 웹 검색 모드 조회 실패: {str(e)}")

@router.get("/api/web-search-mode/history")
async def get_web_search_mode_history():
    """
    웹 검색 모드 변경 이력을 반환합니다.
    
    Returns:
        웹 검색 모드 변경 이력
    """
    try:
        # 실제 구현에서는 데이터베이스에서 모드 변경 이력을 가져옵니다
        history = [
            {
                "mode": "duckduckgo",
                "changed_at": "2024-01-15T10:30:00Z",
                "user": "system"
            },
            {
                "mode": "model_only",
                "changed_at": "2024-01-14T15:20:00Z",
                "user": "system"
            }
        ]
        
        return {
            "history": history,
            "total_changes": len(history)
        }
    except Exception as e:
        logger.error(f"웹 검색 모드 이력 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"웹 검색 모드 이력 조회 실패: {str(e)}") 