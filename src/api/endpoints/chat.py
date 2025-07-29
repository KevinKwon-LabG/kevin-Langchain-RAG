"""
채팅 관련 API 엔드포인트
Ollama 모델과의 대화, 세션 관리 등을 제공합니다.
"""

import logging
import json
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from src.models.schemas import ChatRequest
from src.utils.session_manager import (
    get_or_create_session,
    add_message_to_session,
    get_session,
    delete_session,
    get_all_sessions,
    build_conversation_prompt
)
from src.services.weather_service import weather_service

from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Ollama 서버 설정
OLLAMA_BASE_URL = "http://1.237.52.240:11434"

# 사용 가능한 모델 목록
AVAILABLE_MODELS = [
    {"name": "gemma3:12b-it-qat", "size": "8.9 GB", "id": "5d4fa005e7bb"},
    {"name": "llama3.1:8b", "size": "4.9 GB", "id": "46e0c10c039e"},
    {"name": "llama3.2-vision:11b-instruct-q4_K_M", "size": "7.8 GB", "id": "6f2f9757ae97"},    
    {"name": "qwen3:14b-q8_0", "size": "15 GB", "id": "304bf7349c71"},
    {"name": "deepseek-r1:14b", "size": "9.0 GB", "id": "c333b7232bdb"},
    {"name": "deepseek-v2:16b-lite-chat-q8_0", "size": "16 GB", "id": "1d62ef756269"},        
]

@router.post("/")
async def chat(request: ChatRequest):
    """
    Ollama 모델과 대화를 수행합니다.
    날씨 관련 질문인 경우 MCP 서버에 요청하여 답변합니다.
    
    Args:
        request: 채팅 요청 (모델, 메시지, 세션 ID 등 포함)
    
    Returns:
        스트리밍 응답 또는 일반 응답
    """
    try:
        # 세션 관리
        session = get_or_create_session(request.session_id)
        
        # 사용자 메시지를 세션에 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        
        # 날씨 관련 질문인지 확인
        weather_info = weather_service.get_weather_info(request.message)
        
        if weather_info["is_weather_question"]:
            # 날씨 관련 질문인 경우 MCP 서버에 요청
            logger.info(f"날씨 관련 질문 감지: {request.message}")
            
            weather_response = await weather_service.get_weather_response(request.message)
            
            if weather_response["success"]:
                # 성공적인 날씨 응답
                response_text = weather_response["response"]
                
                # 어시스턴트 메시지를 세션에 추가
                add_message_to_session(
                    session.session_id, 
                    "assistant", 
                    response_text, 
                    request.model
                )
                
                # 스트리밍 응답 생성
                def generate_weather_response():
                    yield f"data: {json.dumps({'response': response_text})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'weather_info': weather_info})}\n\n"
                
                return StreamingResponse(generate_weather_response(), media_type="text/plain")
            else:
                # 날씨 정보 요청 실패 시 일반 모델 사용
                logger.warning(f"날씨 정보 요청 실패, 일반 모델 사용: {weather_response['error']}")
        
        # 일반 대화 또는 날씨 요청 실패 시 Ollama 모델 사용
        conversation_prompt = build_conversation_prompt(
            session.session_id, 
            request.message, 
            request.system
        )
        
        # Ollama API 호출
        ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": request.model,
            "prompt": conversation_prompt,
            "stream": True,
            "options": request.options or {}
        }
        
        def generate():
            """스트리밍 응답 생성"""
            try:
                response = requests.post(ollama_url, json=payload, stream=True)
                response.raise_for_status()
                
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if data.get('done', False):
                            # 응답에서 "Assistant:" 접두사 제거
                            cleaned_response = full_response
                            if full_response.startswith("Assistant:"):
                                cleaned_response = full_response.replace("Assistant:", "").strip()
                            
                            # 응답 완료 시 어시스턴트 메시지를 세션에 추가
                            add_message_to_session(
                                session.session_id, 
                                "assistant", 
                                cleaned_response, 
                                request.model
                            )
                            break
                        
                        if 'response' in data:
                            chunk = data['response']
                            full_response += chunk
                            yield f"data: {json.dumps({'response': chunk})}\n\n"
                
                # 최종 응답 전송
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                logger.error(f"Ollama API 호출 중 오류: {e}")
                error_response = f"data: {json.dumps({'error': f'AI 모델 응답 생성 중 오류가 발생했습니다: {str(e)}'})}\n\n"
                yield error_response
        
        return StreamingResponse(generate(), media_type="text/plain")
        
    except Exception as e:
        logger.error(f"채팅 요청 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/analyze-request")
async def analyze_chat_request(request: ChatRequest):
    """
    채팅 요청을 분석하여 적절한 서비스를 결정합니다.
    Langchain decision 서비스를 사용합니다.
    
    Args:
        request: 채팅 요청 (모델, 메시지, 세션 ID 등 포함)
    
    Returns:
        분석 결과 (서비스 결정, 이유, 신뢰도 등)
    
    Raises:
        HTTPException: 분석 중 오류가 발생한 경우
    """
    try:
        # 분석 결과 구성
        result = {
            "chat_request": {
                "message": request.message,
                "model": request.model,
                "session_id": request.session_id
            },
            "analysis": {
                "decision": "MODEL_ONLY",
                "reason": "AI 모델 사용",
                "confidence": 1.0,
                "service_type": "model_only"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"요청 분석 중 오류: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"분석 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/models")
async def get_models():
    """
    사용 가능한 모델 목록을 조회합니다.
    
    Returns:
        사용 가능한 모델 목록
    """
    try:
        # Ollama 서버에서 실제 모델 목록 조회 시도
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                return {"models": models}
        except Exception as e:
            logger.warning(f"Ollama 서버에서 모델 목록 조회 실패: {e}")
        
        # 기본 모델 목록 반환
        return {"models": AVAILABLE_MODELS}
        
    except Exception as e:
        logger.error(f"모델 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="모델 목록 조회 중 오류가 발생했습니다.")

@router.get("/sessions")
async def get_sessions():
    """
    모든 세션 정보를 조회합니다.
    
    Returns:
        세션 정보 목록
    """
    try:
        sessions = get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"세션 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 목록 조회 중 오류가 발생했습니다.")

@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    특정 세션 정보를 조회합니다.
    
    Args:
        session_id: 조회할 세션 ID
    
    Returns:
        세션 정보
    
    Raises:
        HTTPException: 세션을 찾을 수 없는 경우
    """
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {"session": session}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 조회 중 오류가 발생했습니다.")

@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """
    세션을 삭제합니다.
    
    Args:
        session_id: 삭제할 세션 ID
    
    Returns:
        삭제 결과
    """
    try:
        success = delete_session(session_id)
        if success:
            return {"message": "세션이 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 삭제 중 오류가 발생했습니다.")

@router.post("/sessions")
async def create_session_endpoint():
    """
    새로운 세션을 생성합니다.
    
    Returns:
        생성된 세션 정보
    """
    try:
        session = get_or_create_session()
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "message": "새 세션이 생성되었습니다."
        }
    except Exception as e:
        logger.error(f"세션 생성 중 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 생성 중 오류가 발생했습니다.")

@router.get("/health")
async def health_check():
    """
    채팅 서비스 상태를 확인합니다.
    
    Returns:
        서비스 상태 정보
    """
    try:
        # Ollama 서버 연결 상태 확인
        ollama_status = "unknown"
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            ollama_status = "connected" if response.status_code == 200 else "error"
        except Exception:
            ollama_status = "disconnected"
        
        # 세션 통계
        from src.utils.session_manager import get_session_stats
        session_stats = get_session_stats()
        
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ollama_server": ollama_status,
            "ollama_url": OLLAMA_BASE_URL,
            "session_stats": session_stats,
            "available_models": len(AVAILABLE_MODELS)
        }
        return health_info
    except Exception as e:
        logger.error(f"헬스 체크 중 오류: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.post("/weather/analyze")
async def analyze_weather_question(request: ChatRequest):
    """
    메시지가 날씨 관련 질문인지 분석합니다.
    
    Args:
        request: 채팅 요청
        
    Returns:
        날씨 분석 결과
    """
    try:
        weather_info = weather_service.get_weather_info(request.message)
        return {
            "message": request.message,
            "weather_analysis": weather_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"날씨 질문 분석 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"날씨 질문 분석 중 오류가 발생했습니다: {str(e)}")

@router.post("/weather/query")
async def query_weather(request: ChatRequest):
    """
    날씨 정보를 MCP 서버에 직접 요청합니다.
    
    Args:
        request: 채팅 요청
        
    Returns:
        날씨 정보 응답
    """
    try:
        weather_response = await weather_service.get_weather_response(request.message)
        return {
            "message": request.message,
            "weather_response": weather_response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"날씨 정보 요청 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"날씨 정보 요청 중 오류가 발생했습니다: {str(e)}") 