"""
Sessions API 엔드포인트
채팅 세션 관리 및 조회를 위한 API를 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

@router.get("/api/sessions")
async def get_sessions():
    """
    사용자의 채팅 세션 목록을 반환합니다.
    
    Returns:
        세션 목록
    """
    try:
        # 실제 구현에서는 데이터베이스에서 세션 목록을 가져옵니다
        from src.utils.session_manager import get_all_sessions
        sessions = get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"세션 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 목록 조회 실패: {str(e)}")

@router.post("/api/sessions")
async def create_session():
    """
    새로운 채팅 세션을 생성합니다.
    
    Returns:
        생성된 세션 정보
    """
    try:
        # 실제 구현에서는 데이터베이스에 새 세션을 생성합니다
        session_id = f"session_{datetime.now().timestamp()}"
        session = {
            "id": session_id,
            "title": "새 대화",
            "created_at": datetime.now().isoformat()
        }
        return session
    except Exception as e:
        logger.error(f"세션 생성 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")

@router.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """
    특정 세션의 상세 정보를 반환합니다.
    
    Args:
        session_id: 세션 ID
    
    Returns:
        세션 상세 정보
    """
    try:
        from src.utils.session_manager import get_session
        session = get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        return {
            "session_id": session.session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "model": msg.model
                }
                for msg in session.messages
            ],
            "created_at": session.created_at,
            "last_active": session.last_active
        }
    except Exception as e:
        logger.error(f"세션 상세 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 상세 조회 실패: {str(e)}")

@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    특정 세션을 삭제합니다.
    
    Args:
        session_id: 세션 ID
    
    Returns:
        삭제 결과
    """
    try:
        # 실제 구현에서는 데이터베이스에서 세션을 삭제합니다
        from src.utils.session_manager import delete_session as delete_session_util
        success = delete_session_util(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        return {
            "success": True,
            "message": f"세션 '{session_id}'가 성공적으로 삭제되었습니다",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"세션 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")

@router.put("/api/sessions/{session_id}/title")
async def update_session_title(session_id: str, request: Request):
    """
    세션의 제목을 업데이트합니다.
    
    Args:
        session_id: 세션 ID
        request: FastAPI 요청 객체 (JSON body에 title 포함)
    
    Returns:
        업데이트 결과
    """
    try:
        body = await request.json()
        title = body.get("title")
        
        if not title:
            raise HTTPException(status_code=400, detail="제목이 필요합니다")
        
        # 실제 구현에서는 데이터베이스에서 세션 제목을 업데이트합니다
        from src.utils.session_manager import update_session_title as update_title_util
        success = update_title_util(session_id, title)
        
        if not success:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        return {
            "success": True,
            "message": f"세션 제목이 '{title}'로 업데이트되었습니다",
            "session_id": session_id,
            "title": title
        }
    except Exception as e:
        logger.error(f"세션 제목 업데이트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 제목 업데이트 실패: {str(e)}") 