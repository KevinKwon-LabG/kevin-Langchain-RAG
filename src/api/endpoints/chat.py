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
from src.services.langchain_decision_service import langchain_decision_service, DecisionCategory
from src.services.rag_service import rag_service

from datetime import datetime

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("chat_debug")
debug_logger.setLevel(logging.DEBUG)
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
    RAG 기능이 활성화되어 있으면 static/RAG 디렉토리의 문서를 참고합니다.
    
    Args:
        request: 채팅 요청 (모델, 메시지, 세션 ID 등 포함)
    
    Returns:
        스트리밍 응답
    """
    try:
        debug_logger.debug(f"💬 채팅 요청 시작 - 세션: {request.session_id}, 모델: {request.model}")
        debug_logger.debug(f"📝 사용자 메시지: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
        
        # 세션 관리
        session = get_or_create_session(request.session_id)
        debug_logger.debug(f"🆔 세션 생성/조회 완료: {session.session_id}")
        
        # RAG 사용 여부 확인 (기본적으로 활성화)
        use_rag = getattr(request, 'use_rag', True)
        debug_logger.debug(f"🔍 RAG 사용 여부: {use_rag}")
        
        # RAG가 활성화된 경우 하이브리드 응답 생성
        if use_rag:
            debug_logger.debug("📚 하이브리드 RAG 모드로 응답 생성 시작")
            
            def generate_hybrid_response():
                """하이브리드 RAG를 사용한 스트리밍 응답 생성"""
                try:
                    # 하이브리드 응답 생성 (RAG + 일반 지식 조합)
                    hybrid_response = rag_service.generate_hybrid_response(
                        query=request.message,
                        model=request.model,
                        top_k=request.rag_top_k or 5,
                        system_prompt=request.system
                    )
                    
                    # 응답을 청크로 분할하여 스트리밍
                    chunk_size = 50  # 한 번에 전송할 문자 수
                    for i in range(0, len(hybrid_response), chunk_size):
                        chunk = hybrid_response[i:i + chunk_size]
                        yield f"data: {json.dumps({'response': chunk})}\n\n"
                    
                    # 사용자 메시지를 세션에 추가
                    add_message_to_session(session.session_id, "user", request.message, request.model)
                    debug_logger.debug("💾 사용자 메시지 세션에 저장됨")
                    
                    # 어시스턴트 메시지를 세션에 추가
                    add_message_to_session(
                        session.session_id, 
                        "assistant", 
                        hybrid_response, 
                        request.model
                    )
                    debug_logger.debug("💾 어시스턴트 메시지 세션에 저장됨")
                    
                    # 완료 신호 전송
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    
                except Exception as e:
                    debug_logger.error(f"❌ 하이브리드 응답 생성 중 오류: {e}")
                    error_response = f"data: {json.dumps({'error': f'하이브리드 응답 생성 중 오류가 발생했습니다: {str(e)}'})}\n\n"
                    yield error_response
            
            debug_logger.debug("📤 하이브리드 스트리밍 응답 반환 시작")
            return StreamingResponse(generate_hybrid_response(), media_type="text/plain")
        
        # 기존 Ollama API 호출 (RAG 비활성화된 경우)
        debug_logger.debug("🤖 일반 Ollama API 모드로 응답 생성")
        
        # 세션에서 대화 히스토리를 가져와서 messages 배열 구성
        session_data = get_session(session.session_id)
        messages = []
        
        # 시스템 프롬프트가 있으면 추가
        if request.system:
            messages.append({"role": "system", "content": request.system})
            debug_logger.debug(f"⚙️ 시스템 프롬프트 추가: {request.system[:50]}...")
        
        # 이전 대화 히스토리 추가 (최근 10개 메시지만)
        if session_data and session_data.messages:
            history_count = len(session_data.messages[-10:])
            debug_logger.debug(f"📚 대화 히스토리 {history_count}개 메시지 추가")
            for message in session_data.messages[-10:]:
                messages.append({
                    "role": message.role,
                    "content": message.content
                })
        else:
            debug_logger.debug("🆕 새로운 대화 시작 (히스토리 없음)")
        
        # 현재 사용자 메시지 추가
        messages.append({"role": "user", "content": request.message})
        debug_logger.debug(f"👤 사용자 메시지 추가됨 (총 {len(messages)}개 메시지)")
        
        # Ollama API 호출
        ollama_url = f"{OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": request.model,
            "messages": messages,
            "stream": True,
            "options": request.options or {}
        }
        debug_logger.debug(f"🤖 Ollama API 호출 준비 - URL: {ollama_url}")
        debug_logger.debug(f"📦 페이로드 크기: {len(str(payload))} 문자")
        
        def generate():
            """스트리밍 응답 생성"""
            try:
                debug_logger.debug("🚀 Ollama API 요청 시작...")
                response = requests.post(ollama_url, json=payload, stream=True)
                response.raise_for_status()
                debug_logger.debug("✅ Ollama API 연결 성공")
                
                full_response = ""
                chunk_count = 0
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if data.get('done', False):
                            debug_logger.debug(f"✅ 응답 완료 - 총 {chunk_count}개 청크, {len(full_response)} 문자")
                            
                            # 사용자 메시지를 세션에 추가 (응답 완료 후)
                            add_message_to_session(session.session_id, "user", request.message, request.model)
                            debug_logger.debug("💾 사용자 메시지 세션에 저장됨")
                            
                            # 응답 완료 시 어시스턴트 메시지를 세션에 추가
                            add_message_to_session(
                                session.session_id, 
                                "assistant", 
                                full_response, 
                                request.model
                            )
                            debug_logger.debug("💾 어시스턴트 메시지 세션에 저장됨")
                            break
                        
                        if 'message' in data and 'content' in data['message']:
                            chunk = data['message']['content']
                            full_response += chunk
                            chunk_count += 1
                            if chunk_count % 10 == 0:  # 10개 청크마다 로그
                                debug_logger.debug(f"📦 청크 {chunk_count} 처리 중... (현재 {len(full_response)} 문자)")
                            yield f"data: {json.dumps({'response': chunk})}\n\n"
                        elif 'response' in data:
                            # 하위 호환성을 위해 /api/generate 형식도 지원
                            chunk = data['response']
                            full_response += chunk
                            chunk_count += 1
                            if chunk_count % 10 == 0:  # 10개 청크마다 로그
                                debug_logger.debug(f"📦 청크 {chunk_count} 처리 중... (현재 {len(full_response)} 문자)")
                            yield f"data: {json.dumps({'response': chunk})}\n\n"
                
                # 최종 응답 전송
                debug_logger.debug("🏁 스트리밍 응답 완료")
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                debug_logger.error(f"❌ Ollama API 호출 중 오류: {e}")
                logger.error(f"Ollama API 호출 중 오류: {e}")
                error_response = f"data: {json.dumps({'error': f'AI 모델 응답 생성 중 오류가 발생했습니다: {str(e)}'})}\n\n"
                yield error_response
        
        debug_logger.debug("📤 스트리밍 응답 반환 시작")
        return StreamingResponse(generate(), media_type="text/plain")
        
    except Exception as e:
        debug_logger.error(f"❌ 채팅 요청 처리 중 오류: {e}")
        logger.error(f"채팅 요청 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/analyze-request")
async def analyze_chat_request(request: ChatRequest):
    """
    채팅 요청을 분석하여 적절한 서비스를 결정합니다.
    RAG 통합 Langchain decision 서비스를 사용합니다.
    
    Args:
        request: 채팅 요청 (모델, 메시지, 세션 ID 등 포함)
    
    Returns:
        분석 결과 (서비스 결정, 이유, 신뢰도, RAG 메타데이터 등)
    
    Raises:
        HTTPException: 분석 중 오류가 발생한 경우
    """
    try:
        debug_logger.debug(f"🔍 요청 분석 시작 - 메시지: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
        
        # RAG 사용 여부 확인 (기본적으로 활성화)
        use_rag_for_decision = getattr(request, 'use_rag_for_decision', True)
        debug_logger.debug(f"🔍 Decision Service RAG 사용 여부: {use_rag_for_decision}")
        
        # RAG 통합 Langchain decision 서비스를 사용하여 실제 분석 수행
        debug_logger.debug("🤖 RAG 통합 Langchain 의사결정 서비스 호출 중...")
        
        if use_rag_for_decision:
            # 메타데이터와 함께 분류 수행
            metadata = await langchain_decision_service.classify_prompt_with_metadata(
                request.message, 
                use_rag=True
            )
            decision_result = metadata["classification_result"]
            rag_context_length = metadata.get("rag_context_length", 0)
            rag_context_preview = metadata.get("rag_context_preview", "")
            debug_logger.debug(f"📊 RAG 통합 분류 결과: {decision_result}")
            debug_logger.debug(f"📚 RAG 컨텍스트 길이: {rag_context_length}")
        else:
            # 기존 방식으로 분류 수행
            decision_result = await langchain_decision_service.classify_prompt(
                request.message, 
                use_rag=False
            )
            rag_context_length = 0
            rag_context_preview = ""
            debug_logger.debug(f"📊 기존 분류 결과: {decision_result}")
        
        # 분류 결과에 따른 서비스 타입 결정
        service_type = "unknown"
        decision = "UNKNOWN"
        reason = "분류 실패"
        confidence = 0.0
        
        if "날씨 정보" in decision_result:
            service_type = "weather_service"
            decision = "WEATHER_SERVICE"
            reason = "날씨 관련 정보 요청으로 판단됨"
            confidence = 0.9
        elif "한국 주식" in decision_result:
            service_type = "stock_service"
            decision = "STOCK_SERVICE"
            reason = "한국 주식 시장 정보 요청으로 판단됨"
            confidence = 0.9
        elif "웹 검색" in decision_result:
            service_type = "web_search_service"
            decision = "WEB_SEARCH_NEEDED"
            reason = "최신 정보나 실시간 데이터가 필요한 질문으로 판단됨"
            confidence = 0.8
        elif "바로 답변" in decision_result:
            service_type = "direct_answer"
            decision = "DIRECT_ANSWER"
            reason = "AI 모델이 바로 답변 가능한 질문으로 판단됨"
            confidence = 0.95
        else:
            # 기본값
            service_type = "web_search_service"
            decision = "WEB_SEARCH_NEEDED"
            reason = "분류 결과에 따라 웹 검색이 필요할 것으로 판단됨"
            confidence = 0.7
        
        # RAG 컨텍스트가 있는 경우 신뢰도 향상
        if use_rag_for_decision and rag_context_length > 0:
            confidence = min(confidence + 0.1, 1.0)  # 최대 0.1점 향상
            reason += f" (RAG 컨텍스트 참조: {rag_context_length}자)"
            debug_logger.debug(f"📈 RAG 컨텍스트로 인한 신뢰도 향상: {confidence}")
        
        # 신뢰도 기반 의사결정: 신뢰도가 낮은 경우 웹 검색으로 폴백
        debug_logger.debug(f"🎯 최종 분류 결과 - 서비스: {service_type}, 결정: {decision}, 신뢰도: {confidence}")
        
        if confidence < 0.5:
            original_service_type = service_type
            original_decision = decision
            original_reason = reason
            
            debug_logger.debug(f"⚠️ 신뢰도 낮음({confidence:.2f}), 웹 검색으로 폴백")
            
            service_type = "web_search_service"
            decision = "WEB_SEARCH_NEEDED"
            reason = f"분류 신뢰도가 낮아({confidence:.2f}) 웹 검색을 권장합니다. 원래 분류: {original_decision}"
            confidence = 0.5  # 신뢰도를 0.5로 조정
        else:
            debug_logger.debug(f"✅ 신뢰도 충분({confidence:.2f}), 원래 분류 유지")
        
        # 분석 결과 구성 (RAG 메타데이터 포함)
        result = {
            "chat_request": {
                "message": request.message,
                "model": request.model,
                "session_id": request.session_id
            },
            "analysis": {
                "decision": decision,
                "reason": reason,
                "confidence": confidence,
                "service_type": service_type,
                "decision_result": decision_result,
                "recommended_action": get_recommended_action(service_type),
                "rag_metadata": {
                    "use_rag_for_decision": use_rag_for_decision,
                    "rag_context_length": rag_context_length,
                    "rag_context_preview": rag_context_preview
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        debug_logger.debug(f"📋 분석 완료 - 최종 결정: {decision}, 서비스: {service_type}, RAG 사용: {use_rag_for_decision}")
        return result
        
    except Exception as e:
        logger.error(f"요청 분석 중 오류: {e}")
        # 오류 발생 시 기본 분석 결과 반환
        return {
            "chat_request": {
                "message": request.message,
                "model": request.model,
                "session_id": request.session_id
            },
            "analysis": {
                "decision": "WEB_SEARCH_NEEDED",
                "reason": f"분석 중 오류 발생: {str(e)}",
                "confidence": 0.0,
                "service_type": "web_search_service",
                "decision_result": "정확한 답변을 위해서는 웹 검색이 필요합니다.",
                "recommended_action": "웹 검색 서비스 사용을 권장합니다."
            },
            "timestamp": datetime.now().isoformat()
        }


def get_recommended_action(service_type: str) -> str:
    """
    서비스 타입에 따른 권장 액션을 반환합니다.
    
    Args:
        service_type: 서비스 타입
        
    Returns:
        권장 액션 문자열
    """
    actions = {
        "weather_service": "날씨 API 서비스를 호출하여 실시간 날씨 정보를 제공합니다.",
        "stock_service": "주식 API 서비스를 호출하여 실시간 주가 정보를 제공합니다.",
        "web_search_service": "웹 검색 서비스를 호출하여 최신 정보를 검색합니다.",
        "direct_answer": "AI 모델을 사용하여 바로 답변을 제공합니다.",
        "unknown": "웹 검색 서비스를 사용하여 정보를 검색합니다."
    }
    return actions.get(service_type, "웹 검색 서비스를 사용하여 정보를 검색합니다.")

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
        
        # RAG 상태 확인
        rag_status = rag_service.get_rag_status()
        
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ollama_server": ollama_status,
            "ollama_url": OLLAMA_BASE_URL,
            "session_stats": session_stats,
            "available_models": len(AVAILABLE_MODELS),
            "rag_status": rag_status
        }
        return health_info
    except Exception as e:
        logger.error(f"헬스 체크 중 오류: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.post("/rag/reload")
async def reload_rag_documents():
    """
    RAG 문서들을 다시 로드합니다.
    
    Returns:
        재로드 결과
    """
    try:
        debug_logger.debug("🔄 RAG 문서 재로드 요청")
        result = rag_service.reload_rag_documents()
        debug_logger.debug(f"✅ RAG 문서 재로드 완료: {result}")
        return result
    except Exception as e:
        debug_logger.error(f"❌ RAG 문서 재로드 실패: {e}")
        logger.error(f"RAG 문서 재로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 문서 재로드 중 오류가 발생했습니다: {str(e)}")

@router.get("/rag/status")
async def get_rag_status():
    """
    RAG 서비스 상태를 조회합니다.
    
    Returns:
        RAG 상태 정보
    """
    try:
        debug_logger.debug("📊 RAG 상태 조회")
        status = rag_service.get_rag_status()
        debug_logger.debug(f"✅ RAG 상태 조회 완료: {status}")
        return status
    except Exception as e:
        debug_logger.error(f"❌ RAG 상태 조회 실패: {e}")
        logger.error(f"RAG 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 상태 조회 중 오류가 발생했습니다: {str(e)}")

@router.put("/rag/settings")
async def update_rag_settings(
    similarity_threshold: Optional[float] = None,
    context_weight: Optional[float] = None,
    min_context_length: Optional[int] = None
):
    """
    RAG 설정을 동적으로 업데이트합니다.
    
    Args:
        similarity_threshold: 유사도 임계값 (0.0 ~ 1.0)
        context_weight: 컨텍스트 가중치 (0.0 ~ 1.0)
        min_context_length: 최소 컨텍스트 길이 (문자 수)
    
    Returns:
        업데이트된 설정 정보
    """
    try:
        debug_logger.debug("⚙️ RAG 설정 업데이트 요청")
        debug_logger.debug(f"📝 업데이트할 설정: similarity_threshold={similarity_threshold}, context_weight={context_weight}, min_context_length={min_context_length}")
        
        # 입력값 검증
        if similarity_threshold is not None and not (0.0 <= similarity_threshold <= 1.0):
            raise HTTPException(status_code=400, detail="유사도 임계값은 0.0과 1.0 사이여야 합니다.")
        
        if context_weight is not None and not (0.0 <= context_weight <= 1.0):
            raise HTTPException(status_code=400, detail="컨텍스트 가중치는 0.0과 1.0 사이여야 합니다.")
        
        if min_context_length is not None and min_context_length < 0:
            raise HTTPException(status_code=400, detail="최소 컨텍스트 길이는 0 이상이어야 합니다.")
        
        # 설정 업데이트
        result = rag_service.update_settings(
            similarity_threshold=similarity_threshold,
            context_weight=context_weight,
            min_context_length=min_context_length
        )
        
        debug_logger.debug(f"✅ RAG 설정 업데이트 완료: {result}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        debug_logger.error(f"❌ RAG 설정 업데이트 실패: {e}")
        logger.error(f"RAG 설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 설정 업데이트 중 오류가 발생했습니다: {str(e)}")

@router.get("/rag/settings")
async def get_rag_settings():
    """
    현재 RAG 설정을 조회합니다.
    
    Returns:
        현재 RAG 설정 정보
    """
    try:
        debug_logger.debug("⚙️ RAG 설정 조회")
        status = rag_service.get_rag_status()
        
        if "settings" in status:
            settings = status["settings"]
            debug_logger.debug(f"✅ RAG 설정 조회 완료: {settings}")
            return {
                "status": "success",
                "settings": settings,
                "description": {
                    "similarity_threshold": "유사도 임계값 (0.0 ~ 1.0) - 높을수록 더 관련성 높은 문서만 포함",
                    "context_weight": "컨텍스트 가중치 (0.0 ~ 1.0) - RAG 데이터의 중요도",
                    "min_context_length": "최소 컨텍스트 길이 (문자 수) - 이보다 짧으면 일반 응답으로 폴백"
                }
            }
        else:
            return {
                "status": "error",
                "message": "설정 정보를 가져올 수 없습니다."
            }
            
    except Exception as e:
        debug_logger.error(f"❌ RAG 설정 조회 실패: {e}")
        logger.error(f"RAG 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 설정 조회 중 오류가 발생했습니다: {str(e)}")