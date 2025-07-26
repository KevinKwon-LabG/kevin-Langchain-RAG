from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging

from src.models.schemas import ChatRequest
from src.services.rag_service import rag_service
from src.services.session_service import session_service

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/api", tags=["Chat"])

@chat_router.post("/chat")
async def chat(request: ChatRequest):
    """RAG + 웹검색 기반 대화형 채팅 API (비동기, 스트리밍 미지원)"""
    try:
        session_id = session_service.get_or_create_session(request.session_id)
        session_service.add_message_to_session(
            session_id, 'user', request.message, request.model
        )
        logger.info(f"대화 요청: {request.model} 모델, 세션: {session_id}")
        # RAG + 웹검색
        answer = rag_service.generate_response_with_rag(
            query=request.message,
            model=request.model,
            top_k=request.top_k,
            system_prompt=request.system
        )
        session_service.add_message_to_session(
            session_id, 'assistant', answer, request.model
        )
        return JSONResponse({
            "response": answer,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"채팅 요청 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}") 