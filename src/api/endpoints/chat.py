"""
채팅 관련 API 엔드포인트
Ollama 모델과의 대화, 세션 관리 등을 제공합니다.
"""

import logging
import json
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from src.models.schemas import ChatRequest
from src.utils.session_manager import (
    get_or_create_session,
    add_message_to_session,
    get_session,
    delete_session,
    get_all_sessions
)
from src.services.rag_service import rag_service
from src.services.mcp_client_service import mcp_client_service
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Ollama 서버 설정
from src.config.settings import settings
OLLAMA_BASE_URL = settings.ollama_base_url

@router.post("/")
async def chat(request: ChatRequest):
    """
    Ollama 모델과 대화를 수행합니다.
    
    Args:
        request: 채팅 요청 (모델, 메시지, 세션 ID 등 포함)
    
    Returns:
        스트리밍 응답
    """
    try:
        # 세션 관리
        session = get_or_create_session(request.session_id)
        
        # RAG 사용 여부 확인
        use_rag = getattr(request, 'use_rag', True)
        
        # 외부 RAG 사용 여부 확인
        use_external_rag = getattr(request, 'use_external_rag', True)
        
        # MCP 사용 여부 확인
        use_mcp = getattr(request, 'use_mcp', True)
        
        # AI 응답 생성
        return await _generate_ai_response(request, session, use_rag, use_external_rag, use_mcp)
        
    except Exception as e:
        logger.error(f"채팅 요청 처리 중 오류: {e}", exc_info=True)
        
        def generate_error_response():
            error_message = f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {str(e)}"
            chunk_size = 50
            for i in range(0, len(error_message), chunk_size):
                chunk = error_message[i:i + chunk_size]
                yield f"data: {json.dumps({'response': chunk, 'session_id': request.session_id})}\n\n"
            
            yield f"data: {json.dumps({'done': True, 'session_id': request.session_id, 'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_error_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )

async def _generate_ai_response(request: ChatRequest, session, use_rag: bool, use_external_rag: bool, use_mcp: bool):
    """
    AI 응답을 생성합니다.
    
    Args:
        request: 채팅 요청
        session: 세션 정보
        use_rag: RAG 사용 여부
        use_mcp: MCP 사용 여부
    
    Returns:
        StreamingResponse: 스트리밍 응답
    """
    try:
        # 대기 상태 확인
        pending_state = mcp_client_service.get_pending_state(session.session_id)
        if pending_state["weather_request_pending"] or pending_state["stock_request_pending"]:
            logger.info(f"MCP 요청 대기 상태 감지: weather={pending_state['weather_request_pending']}, stock={pending_state['stock_request_pending']}")
            return await _generate_mcp_response(request, session, use_rag, use_external_rag)
        
        # MCP 서비스 사용 여부 확인 - UI 설정을 우선적으로 고려
        if use_mcp and mcp_client_service._should_use_mcp(request.message, request.model, session.session_id, ui_mcp_enabled=use_mcp):
            logger.info(f"[채팅 API] MCP 서비스 사용 (UI에서 MCP 사용 허용됨) - 질문: {request.message}")
            return await _generate_mcp_response(request, session, use_rag, use_external_rag)
        elif use_mcp:
            logger.info(f"[채팅 API] UI에서 MCP 사용이 허용되었지만, 쿼리 분석 결과 MCP 서비스 사용이 불필요함 - 질문: {request.message}")
        else:
            logger.info(f"[채팅 API] UI에서 MCP 사용이 비활성화됨 - 질문: {request.message}")
        
        # RAG 사용 여부에 따른 응답 생성
        if use_rag:
            # RAG 응답 생성 (MCP 통합) - UI의 MCP 사용 여부를 명시적으로 전달
            rag_result = await rag_service.generate_rag_response(
                query=request.message,
                model_name=request.model,
                use_rag=True,
                top_k=getattr(request, 'rag_top_k', 5),
                system_prompt=getattr(request, 'system', settings.default_system_prompt),
                use_mcp=use_mcp,  # UI 체크박스 상태
                session_id=session.session_id,
                use_external_rag=use_external_rag  # 외부 RAG 사용 여부
            )
            
            response = rag_result.get('response', 'RAG 응답을 생성할 수 없습니다.')
            context_used = rag_result.get('rag_used', False)
            external_rag_used = rag_result.get('external_rag_used', False)
            context_score = rag_result.get('context_score', 0.0)
            context_quality = rag_result.get('context_quality', 'low')
            mcp_used = rag_result.get('mcp_used', False)
            
        else:
            # 일반 AI 응답 생성 (Ollama 직접 호출)
            try:
                async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
                    ollama_response = await client.post(
                        f"{OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": request.model,
                            "prompt": request.message,
                            "stream": False,
                            "options": {
                                "temperature": getattr(request, 'temperature', settings.default_temperature),
                                "top_p": getattr(request, 'top_p', settings.default_top_p),
                                "top_k": getattr(request, 'top_k', settings.default_top_k),
                                "repeat_penalty": getattr(request, 'repeat_penalty', settings.default_repeat_penalty),
                                "seed": getattr(request, 'seed', settings.default_seed)
                            }
                        }
                    )

                if ollama_response.status_code == 200:
                    response_data = ollama_response.json()
                    response = response_data.get('response', '응답을 생성할 수 없습니다.')
                else:
                    response = f"Ollama 서버 오류: {ollama_response.status_code}"

            except Exception as e:
                response = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
            
            context_used = False
            external_rag_used = False
            context_score = 0.0
            context_quality = 'none'
            mcp_used = False
        
        # 세션에 메시지 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        add_message_to_session(session.session_id, "assistant", response, request.model)
        
        def generate():
            try:
                # 응답 스트리밍
                chunk_size = 50
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i + chunk_size]
                    yield f"data: {json.dumps({'response': chunk, 'session_id': request.session_id})}\n\n"
                
                # 완료 메시지 (RAG 및 MCP 정보 포함)
                completion_data = {
                    'done': True, 
                    'session_id': request.session_id, 
                    'service': 'ai',
                    'rag_used': context_used,
                    'external_rag_used': external_rag_used,
                    'mcp_used': mcp_used,
                    'context_score': context_score,
                    'context_quality': context_quality
                }
                
                yield f"data: {json.dumps(completion_data)}\n\n"
                
            except Exception as e:
                error_message = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
                yield f"data: {json.dumps({'error': error_message, 'session_id': request.session_id})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': request.session_id})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"AI 응답 생성 중 오류: {e}", exc_info=True)
        
        def generate_error_response(error_exception):
            error_message = f"AI 응답을 생성하는 중 오류가 발생했습니다: {str(error_exception)}"
            chunk_size = 50
            for i in range(0, len(error_message), chunk_size):
                chunk = error_message[i:i + chunk_size]
                yield f"data: {json.dumps({'response': chunk, 'session_id': request.session_id})}\n\n"
            
            yield f"data: {json.dumps({'done': True, 'session_id': request.session_id, 'error': str(error_exception)})}\n\n"
        
        return StreamingResponse(
            generate_error_response(e),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )

async def _generate_mcp_response(request: ChatRequest, session, use_rag: bool, use_external_rag: bool):
    """
    MCP 서비스를 사용하여 응답을 생성합니다.
    
    Args:
        request: 채팅 요청
        session: 세션 정보
        use_rag: RAG 사용 여부
    
    Returns:
        StreamingResponse: 스트리밍 응답
    """
    try:
        # MCP 서비스 요청
        if use_rag:
            # RAG와 MCP 통합
            logger.info(f"[채팅 API] RAG와 MCP 통합 요청 - 질문: {request.message}")
            mcp_response, mcp_success = await mcp_client_service.process_rag_with_mcp(
                request.message, rag_service, session.session_id, request.model
            )
        else:
            # MCP만 사용 - MCP 서비스의 결정 로직 사용 (UI 설정 고려)
            if mcp_client_service._should_use_mcp(request.message, request.model, session.session_id, ui_mcp_enabled=True):
                # MCP 서비스가 사용되어야 한다고 판단된 경우
                service_type = mcp_client_service._determine_mcp_service_type(request.message)
                logger.info(f"[채팅 API] MCP 서비스 타입 결정: {service_type} - 질문: {request.message}")
                
                if service_type == "weather":
                    logger.info(f"[채팅 API] 날씨 서비스 요청 - 질문: {request.message}")
                    mcp_response, mcp_success = await mcp_client_service.process_weather_request(
                        request.message, session.session_id, request.model
                    )
                elif service_type == "stock":
                    logger.info(f"[채팅 API] 주식 서비스 요청 - 질문: {request.message}")
                    mcp_response, mcp_success = await mcp_client_service.process_stock_request(
                        request.message, session.session_id, request.model
                    )
                elif service_type == "search":
                    logger.info(f"[채팅 API] 웹 검색 서비스 요청 - 질문: {request.message}")
                    mcp_response, mcp_success = await mcp_client_service.process_web_search_request(
                        request.message, session.session_id, request.model
                    )
                else:
                    # 기본값: 웹 검색
                    logger.info(f"[채팅 API] 기본 웹 검색 서비스 요청 - 질문: {request.message}")
                    mcp_response, mcp_success = await mcp_client_service.process_web_search_request(
                        request.message, session.session_id, request.model
                    )
            else:
                # 일반 AI 응답으로 폴백
                logger.info(f"[채팅 API] MCP 사용하지 않음, 일반 AI 응답으로 폴백 - 질문: {request.message}")
                return await _generate_ai_response(request, session, use_rag, use_external_rag, False)
        
        # MCP 응답 결과 로깅
        logger.info(f"[채팅 API] MCP 응답 완료 - 성공: {mcp_success}")
        logger.info(f"[채팅 API] MCP 응답 내용: {mcp_response}")
        
        # 세션에 메시지 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        add_message_to_session(session.session_id, "assistant", mcp_response, request.model)
        
        def generate():
            try:
                # 응답 스트리밍
                chunk_size = 50
                for i in range(0, len(mcp_response), chunk_size):
                    chunk = mcp_response[i:i + chunk_size]
                    yield f"data: {json.dumps({'response': chunk, 'session_id': request.session_id})}\n\n"
                
                # 완료 메시지
                completion_data = {
                    'done': True, 
                    'session_id': request.session_id, 
                    'service': 'mcp',
                    'mcp_used': True,
                    'rag_used': use_rag
                }
                
                yield f"data: {json.dumps(completion_data)}\n\n"
                
            except Exception as e:
                error_message = f"MCP 응답 생성 중 오류가 발생했습니다: {str(e)}"
                yield f"data: {json.dumps({'error': error_message, 'session_id': request.session_id})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': request.session_id})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"MCP 응답 생성 중 오류: {e}", exc_info=True)
        # 오류 발생 시 일반 AI 응답으로 폴백
        return await _generate_ai_response(request, session, use_rag, use_external_rag, False)

@router.post("/mcp/weather")
async def mcp_weather(request: ChatRequest):
    """
    MCP 서비스를 통해 날씨 정보를 가져옵니다.
    
    Args:
        request: 채팅 요청
    
    Returns:
        날씨 정보 응답
    """
    try:
        # 세션 관리
        session = get_or_create_session(request.session_id)
        
        # 날씨 요청 처리
        response, success = await mcp_client_service.process_weather_request(
            request.message, session.session_id
        )
        
        # 세션에 메시지 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        add_message_to_session(session.session_id, "assistant", response, request.model)
        
        return {
            "status": "success",
            "response": response,
            "service": "mcp_weather",
            "session_id": request.session_id,
            "success": success
        }
        
    except Exception as e:
        logger.error(f"날씨 요청 처리 중 오류: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id
        }

@router.post("/mcp/stock")
async def mcp_stock(request: ChatRequest):
    """
    MCP 서비스를 통해 주식 정보를 가져옵니다.
    
    Args:
        request: 채팅 요청
    
    Returns:
        주식 정보 응답
    """
    try:
        # 세션 관리
        session = get_or_create_session(request.session_id)
        
        # 주식 요청 처리
        response, success = await mcp_client_service.process_stock_request(
            request.message, session.session_id
        )
        
        # 세션에 메시지 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        add_message_to_session(session.session_id, "assistant", response, request.model)
        
        return {
            "status": "success",
            "response": response,
            "service": "mcp_stock",
            "session_id": request.session_id,
            "success": success
        }
        
    except Exception as e:
        logger.error(f"주식 요청 처리 중 오류: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id
        }

@router.post("/mcp/search")
async def mcp_search(request: ChatRequest):
    """
    MCP 서비스를 통해 웹 검색을 수행합니다.
    
    Args:
        request: 채팅 요청
    
    Returns:
        검색 결과 응답
    """
    try:
        # 세션 관리
        session = get_or_create_session(request.session_id)
        
        # 검색 요청 처리
        response, success = await mcp_client_service.process_web_search_request(
            request.message, session.session_id, request.model
        )
        
        # 세션에 메시지 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        add_message_to_session(session.session_id, "assistant", response, request.model)
        
        return {
            "status": "success",
            "response": response,
            "service": "mcp_search",
            "session_id": request.session_id,
            "success": success
        }
        
    except Exception as e:
        logger.error(f"검색 요청 처리 중 오류: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id
        }

@router.post("/mcp/integrated")
async def mcp_integrated(request: ChatRequest):
    """
    RAG와 MCP를 통합하여 응답을 생성합니다.
    
    Args:
        request: 채팅 요청
    
    Returns:
        통합 응답
    """
    try:
        # 세션 관리
        session = get_or_create_session(request.session_id)
        
        # RAG와 MCP 통합 요청 처리
        response, success = await mcp_client_service.process_rag_with_mcp(
            request.message, rag_service, session.session_id, request.model
        )
        
        # 세션에 메시지 추가
        add_message_to_session(session.session_id, "user", request.message, request.model)
        add_message_to_session(session.session_id, "assistant", response, request.model)
        
        return {
            "status": "success",
            "response": response,
            "service": "mcp_integrated",
            "session_id": request.session_id,
            "success": success
        }
        
    except Exception as e:
        logger.error(f"통합 요청 처리 중 오류: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id
        }

@router.get("/mcp/status")
async def mcp_status():
    """
    MCP 서비스의 상태를 확인합니다.
    
    Returns:
        MCP 서비스 상태 정보
    """
    try:
        status = mcp_client_service.get_service_status()
        return {
            "status": "success",
            "mcp_service": status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/models")
async def get_models():
    """
    Ollama에서 실제 모델 목록을 가져와서 반환합니다.
    
    Returns:
        모델 목록
    """
    try:
        # Ollama API에서 모델 목록 가져오기
        from src.config.settings import get_settings
        settings = get_settings()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        
        if data.get("models"):
            # Ollama 응답을 우리 형식으로 변환
            models = []
            for model in data["models"]:
                size_gb = model.get("size", 0) / (1024**3)  # 바이트를 GB로 변환
                models.append({
                    "name": model["name"],
                    "size": f"{size_gb:.1f} GB",
                    "id": model.get("digest", model["name"]),
                    "is_current": False
                })
            
            # 첫 번째 모델을 현재 모델로 설정
            if models:
                models[0]["is_current"] = True
            
            return {
                "status": "success",
                "models": models,
                "current_model": models[0]["name"] if models else "unknown",
                "total_count": len(models)
            }
        else:
            return {
                "status": "error",
                "error": "Ollama에서 모델을 찾을 수 없습니다"
            }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/current-model")
async def get_current_model():
    """
    현재 선택된 AI 모델의 상태 정보를 반환합니다.
    
    Returns:
        현재 모델 정보
    """
    try:
        # Ollama API에서 모델 목록 가져오기
        from src.config.settings import get_settings
        settings = get_settings()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        
        if data.get("models") and len(data["models"]) > 0:
            # 첫 번째 모델을 현재 모델로 간주
            current_model = data["models"][0]
            size_gb = current_model.get("size", 0) / (1024**3)  # 바이트를 GB로 변환
            
            # 모델 상태 확인 (간단한 테스트)
            model_status = "unknown"
            try:
                # 모델이 로드되어 있는지 확인
                async with httpx.AsyncClient(timeout=5.0) as client:
                    status_response = await client.get(
                        f"{settings.ollama_base_url}/api/show",
                        params={"name": current_model["name"]}
                    )
                if status_response.status_code == 200:
                    model_status = "loaded"
                else:
                    model_status = "not_loaded"
            except Exception as e:
                model_status = f"error: {str(e)}"
            
            return {
                "status": "success",
                "current_model": {
                    "name": current_model["name"],
                    "size": f"{size_gb:.1f} GB",
                    "id": current_model.get("digest", current_model["name"]),
                    "model_status": model_status,
                    "modified_at": current_model.get("modified_at", "unknown"),
                    "total_models": len(data["models"])
                }
            }
        else:
            return {
                "status": "error",
                "error": "Ollama에서 모델을 찾을 수 없습니다",
                "current_model": None
            }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "current_model": None
        }


@router.get("/sessions")
async def get_sessions():
    """
    모든 세션 목록을 반환합니다.
    
    Returns:
        세션 목록
    """
    try:
        sessions = get_all_sessions()
        
        return {
            "status": "success",
            "sessions": sessions,
            "total_count": len(sessions)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    특정 세션의 정보를 반환합니다.
    
    Args:
        session_id: 세션 ID
    
    Returns:
        세션 정보
    """
    try:
        session = get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "session": session
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """
    특정 세션을 삭제합니다.
    
    Args:
        session_id: 세션 ID
    
    Returns:
        삭제 결과
    """
    try:
        delete_session(session_id)
        
        return {
            "status": "success",
            "message": f"세션 {session_id}가 삭제되었습니다."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

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
            "status": "success",
            "session": session
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/health")
async def health_check():
    """
    서비스 상태를 확인합니다.
    
    Returns:
        서비스 상태 정보
    """
    try:
        # Ollama 서버 연결 확인
        ollama_status = "unknown"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                ollama_status = "healthy"
            else:
                ollama_status = "unhealthy"
        except Exception as e:
            ollama_status = f"error: {str(e)}"
        
        # RAG 상태 확인
        rag_status = rag_service.get_rag_status()
        
        # MCP 상태 확인
        mcp_status = mcp_client_service.get_service_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "ollama": ollama_status,
                "rag": rag_status.get("status", "unknown"),
                "mcp": mcp_status.get("status", "unknown")
            },
            "rag_info": rag_status,
            "mcp_info": mcp_status
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }