"""
채팅 관련 API 엔드포인트
Ollama 모델과의 대화, 세션 관리 등을 제공합니다.
"""

import logging
import json
import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from src.models.schemas import ChatRequest, SessionInfo
from src.utils.session_manager import (
    get_or_create_session,
    add_message_to_session,
    get_session,
    delete_session,
    get_all_sessions,
    build_conversation_prompt
)

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

# 웹 검색 모드 저장소 (실제 운영에서는 Redis나 데이터베이스 사용 권장)
web_search_mode = "model_only"  # 기본값

def get_web_search_mode():
    """현재 웹 검색 모드를 반환합니다."""
    return web_search_mode

def set_web_search_mode(mode: str):
    """웹 검색 모드를 설정합니다."""
    global web_search_mode
    web_search_mode = mode



async def perform_mcp_search_with_decision(query: str, service_decision: Dict[str, Any], model_name: Optional[str] = None) -> str:
    """
    이미 결정된 서비스 타입을 사용하여 MCP 서버 검색을 수행합니다.
    
    Args:
        query: 검색 쿼리
        service_decision: 이미 결정된 서비스 결정 결과
        model_name: 사용할 AI 모델 이름 (None이면 기본 모델 사용)
    
    Returns:
        검색 결과 문자열
    """
    try:
        # 이미 결정된 서비스 타입에 따라 적절한 MCP 서비스 호출
        decision = service_decision.get("decision", "MODEL_ONLY")
        
        if decision == "MCP_SERVER-STOCK":
            return await perform_stock_search(query, model_name)
        elif decision == "MCP_SERVER-WEATHER":
            return await perform_weather_search(query)
        elif decision == "MCP_SERVER-WEB":
            return await perform_web_search(query)
        else:
            # 기본적으로 웹 검색 수행
            return await perform_web_search(query)
                
    except Exception as e:
        logger.error(f"MCP 서버 검색 오류: {e}")
        return f"MCP 서버 검색 중 오류가 발생했습니다: {str(e)}"


async def perform_mcp_search(query: str, model_name: Optional[str] = None) -> str:
    """
    MCP 서버를 사용하여 지능적인 검색을 수행합니다.
    Langchain decision 서비스를 사용하여 적절한 서비스를 선택합니다.
    
    Args:
        query: 검색 쿼리
        model_name: 사용할 AI 모델 이름 (None이면 기본 모델 사용)
    
    Returns:
        검색 결과 문자열
    """
    try:
        # 1단계: Langchain decision 서비스로 서비스 분류 (사용자가 선택한 모델 사용)
        from src.services.langchain_decision_service import langchain_decision_service
        service_decision = langchain_decision_service.decide_search_method(query, "mcp_server", model_name)
        
        # 2단계: 분류된 서비스에 따라 적절한 MCP 서비스 호출
        return await perform_mcp_search_with_decision(query, service_decision, model_name)
                
    except Exception as e:
        logger.error(f"MCP 서버 검색 오류: {e}")
        return f"MCP 서버 검색 중 오류가 발생했습니다: {str(e)}"



async def perform_stock_search(query: str, model_name: Optional[str] = None) -> str:
    """
    주식 관련 검색을 수행합니다.
    
    Args:
        query: 검색 쿼리
        model_name: 사용할 AI 모델 이름 (None이면 기본 모델 사용)
    
    Returns:
        주식 검색 결과
    """
    try:
        from src.services.stock_keyword_extractor import stock_keyword_extractor
        
        # 통합 메서드로 키워드 추출 → 검색 → 상세 정보 조회 (사용자가 선택한 모델 사용)
        result = await stock_keyword_extractor.extract_and_get_stock_info(query, model_name)
        
        if not result.get('success', False):
            return f"❌ 주식 정보 조회 실패: {result.get('error', '알 수 없는 오류')}"
        
        # 결과 구성
        results = []
        results.append(f"📈 주식 정보 검색 결과:")
        
        # 추출 정보
        extraction_result = result.get('extraction_result', {})
        extracted_keyword = extraction_result.get('keyword', '')
        results.append(f"🔍 추출된 키워드: '{extracted_keyword}' (신뢰도: {extraction_result.get('confidence', 0):.1%})")
        
        # 처리 방식에 따른 결과 표시
        processing_type = result.get('processing_type', '')
        
        if processing_type == 'direct_stock_code':
            # 주식 코드로 직접 조회한 경우
            stock_info = result.get('stock_info', {})
            if stock_info and stock_info.get('success', True):
                basic_info = stock_info.get('Basic Information', {})
                financial_data = stock_info.get('Financial Data', {})
                
                results.append(f"\n🔸 종목코드: {extracted_keyword}")
                results.append(f"   회사명: {basic_info.get('Company Name', 'N/A')}")
                results.append(f"   시장: {basic_info.get('Listed Market', 'N/A')}")
                results.append(f"   업종: {basic_info.get('Industry Classification', 'N/A')}")
                results.append(f"   현재가: {financial_data.get('Latest Stock Price', 'N/A'):,}원" if isinstance(financial_data.get('Latest Stock Price'), (int, float)) else f"   현재가: {financial_data.get('Latest Stock Price', 'N/A')}")
                results.append(f"   PER: {financial_data.get('Price-Earnings Ratio', 'N/A')}")
                results.append(f"   PBR: {financial_data.get('Price-Book Ratio', 'N/A')}")
                results.append(f"   배당수익률: {financial_data.get('Dividend Yield', 'N/A')}%")
            else:
                error_msg = stock_info.get('error', '조회 실패') if isinstance(stock_info, dict) else '조회 실패'
                results.append(f"\n❌ 종목코드 {extracted_keyword}: {error_msg}")
                
        elif processing_type == 'keyword_search_then_detail':
            # 키워드 검색 후 상세 정보 조회한 경우
            search_results = result.get('search_results', {})
            stock_info = result.get('stock_info', {})
            selected_stock_code = result.get('selected_stock_code', '')
            selected_stock_name = result.get('selected_stock_name', '')
            
            # 검색 결과 요약
            results.append(f"\n🔍 '{extracted_keyword}' 검색 결과 ({search_results.get('result_count', 0)}개):")
            results.append(f"📋 선택된 종목: {selected_stock_name} ({selected_stock_code})")
            
            # 상세 정보
            if stock_info and stock_info.get('success', True):
                basic_info = stock_info.get('Basic Information', {})
                financial_data = stock_info.get('Financial Data', {})
                
                results.append(f"\n🔸 상세 정보:")
                results.append(f"   회사명: {basic_info.get('Company Name', 'N/A')}")
                results.append(f"   시장: {basic_info.get('Listed Market', 'N/A')}")
                results.append(f"   업종: {basic_info.get('Industry Classification', 'N/A')}")
                results.append(f"   현재가: {financial_data.get('Latest Stock Price', 'N/A'):,}원" if isinstance(financial_data.get('Latest Stock Price'), (int, float)) else f"   현재가: {financial_data.get('Latest Stock Price', 'N/A')}")
                results.append(f"   PER: {financial_data.get('Price-Earnings Ratio', 'N/A')}")
                results.append(f"   PBR: {financial_data.get('Price-Book Ratio', 'N/A')}")
                results.append(f"   배당수익률: {financial_data.get('Dividend Yield', 'N/A')}%")
            else:
                error_msg = stock_info.get('error', '상세 정보 조회 실패') if isinstance(stock_info, dict) else '상세 정보 조회 실패'
                results.append(f"\n❌ 상세 정보 조회 실패: {error_msg}")
            
            # 나머지 검색 결과도 표시
            if search_results.get("results"):
                for i, stock in enumerate(search_results["results"][1:5], 2):
                    results.append(f"\n{i}. {stock.get('company_name', 'N/A')} ({stock.get('stock_code', 'N/A')})")
                    results.append(f"   시장: {stock.get('market', 'N/A')}")
        
        # 추출 정보 추가
        results.append(f"\n📋 추출 정보:")
        results.append(f"   원본 질문: {extraction_result.get('original_prompt', 'N/A')}")
        results.append(f"   추출 방식: {extraction_result.get('extraction_type', 'N/A')}")
        results.append(f"   처리 방식: {processing_type}")
        if extraction_result.get('reason'):
            results.append(f"   추출 이유: {extraction_result.get('reason', 'N/A')}")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"주식 검색 오류: {e}")
        return f"주식 검색 중 오류가 발생했습니다: {str(e)}"

async def perform_weather_search(query: str) -> str:
    """
    날씨 관련 검색을 수행합니다.
    
    Args:
        query: 검색 쿼리
    
    Returns:
        날씨 검색 결과
    """
    try:
        from src.services.integrated_mcp_client import safe_mcp_call, OptimizedIntegratedMCPClient
        
        # 도시명 추출
        cities = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "제주", "수원", "고양"]
        found_city = None
        
        for city in cities:
            if city in query:
                found_city = city
                break
        
        if not found_city:
            # 기본값으로 서울 사용
            found_city = "서울"
        
        async with OptimizedIntegratedMCPClient() as client:
            results = []
            results.append(f"🌤️ {found_city} 날씨 정보:")
            
            try:
                weather_info = await safe_mcp_call(client, client.get_weather, found_city)
                if weather_info:
                    results.append(f"\n🌡️ 현재온도: {weather_info.get('temperature', 'N/A')}°C")
                    results.append(f"💧 습도: {weather_info.get('humidity', 'N/A')}%")
                    results.append(f"🌪️ 풍속: {weather_info.get('wind_speed', 'N/A')}m/s")
                    results.append(f"☁️ 날씨상태: {weather_info.get('description', 'N/A')}")
                    
                    # 미세먼지 정보도 추가
                    try:
                        air_quality = await safe_mcp_call(client, client.get_air_quality, found_city)
                        if air_quality:
                            results.append(f"😷 미세먼지: {air_quality.get('pm10', 'N/A')}㎍/㎥")
                            results.append(f"😷 초미세먼지: {air_quality.get('pm25', 'N/A')}㎍/㎥")
                    except:
                        pass  # 미세먼지 정보가 없어도 계속 진행
                else:
                    results.append(f"\n❌ {found_city} 날씨 정보를 찾을 수 없습니다.")
            except Exception as e:
                results.append(f"\n❌ 날씨 정보 조회 실패: {str(e)}")
            
            return "\n".join(results)
            
    except Exception as e:
        logger.error(f"날씨 검색 오류: {e}")
        return f"날씨 검색 중 오류가 발생했습니다: {str(e)}"

async def perform_web_search(query: str) -> str:
    """
    웹 검색을 수행합니다.
    
    Args:
        query: 검색 쿼리
    
    Returns:
        웹 검색 결과
    """
    try:
        from src.services.integrated_mcp_client import safe_mcp_call, OptimizedIntegratedMCPClient
        
        async with OptimizedIntegratedMCPClient() as client:
            # 웹 검색 수행
            search_results = await safe_mcp_call(
                client, 
                client.web_search, 
                query, 
                max_results=5
            )
            
            if search_results and "results" in search_results:
                results = []
                results.append(f"🔍 '{query}' 웹 검색 결과:")
                
                for i, result in enumerate(search_results["results"][:5], 1):
                    title = result.get("title", "제목 없음")
                    snippet = result.get("snippet", "내용 없음")
                    url = result.get("url", "")
                    
                    results.append(f"\n{i}. {title}")
                    results.append(f"   {snippet}")
                    if url:
                        results.append(f"   🔗 {url}")
                
                return "\n".join(results)
            else:
                return f"'{query}'에 대한 웹 검색 결과를 찾을 수 없습니다."
                
    except Exception as e:
        logger.error(f"웹 검색 오류: {e}")
        return f"웹 검색 중 오류가 발생했습니다: {str(e)}"

def extract_search_keywords(query: str) -> str:
    """
    사용자 쿼리에서 검색 키워드를 추출합니다.
    
    Args:
        query: 사용자 쿼리
    
    Returns:
        검색 키워드
    """
    # 일반적인 검색 요청 패턴 제거
    search_patterns = [
        "최신", "뉴스", "찾아줘", "검색해줘", "알려줘", "보여줘",
        "관련", "정보", "소식", "업데이트", "최근"
    ]
    
    keywords = query
    for pattern in search_patterns:
        keywords = keywords.replace(pattern, "").strip()
    
    # 연속된 공백 제거
    import re
    keywords = re.sub(r'\s+', ' ', keywords)
    
    return keywords.strip()

@router.post("/")
async def chat(request: ChatRequest):
    """
    Ollama 모델과 대화를 수행합니다.
    
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
        
        # 웹 검색 모드에 따른 처리
        current_mode = get_web_search_mode()
        enhanced_message = request.message
        
        # "모델에서만 답변" 모드일 때만 langchain decision 스킵
        if current_mode == "model_only":
            logger.info("모델에서만 답변 모드: langchain decision 스킵")
        else:
            # Langchain decision 서비스로 분석 수행 (사용자가 선택한 모델 사용)
            from src.services.langchain_decision_service import langchain_decision_service
            service_decision = langchain_decision_service.decide_search_method(
                request.message, 
                current_mode, 
                model_name=request.model
            )
            logger.info(f"서비스 결정: {service_decision}")
            
            if current_mode == "mcp_server" and service_decision["decision"].startswith("MCP_SERVER-"):
                # MCP 서버 검색 수행 (이미 결정된 서비스 타입 사용)
                try:
                    mcp_results = await perform_mcp_search_with_decision(request.message, service_decision, request.model)
                    if mcp_results:
                        enhanced_message = f"{request.message}\n\n[MCP 서버 검색 결과]\n{mcp_results}"
                        logger.info(f"MCP 서버 검색 수행됨: {service_decision['reason']} ({service_decision['decision']})")
                    else:
                        logger.info("MCP 서버 검색 결과 없음")
                except Exception as e:
                    logger.error(f"MCP 서버 검색 실패: {e}")
                    enhanced_message = f"{request.message}\n\n[MCP 서버 검색 실패: {str(e)}]"
            elif current_mode == "mcp_server" and not service_decision["decision"].startswith("MCP_SERVER-"):
                logger.info(f"MCP 서버 검색 스킵됨: {service_decision['reason']} ({service_decision['decision']})")
        
        # 대화 프롬프트 구성
        conversation_prompt = build_conversation_prompt(
            session.session_id, 
            enhanced_message, 
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
        # 현재 웹 검색 모드 가져오기
        current_mode = get_web_search_mode()
        
        # Langchain decision 서비스로 분석 (사용자가 선택한 모델 사용)
        from src.services.langchain_decision_service import langchain_decision_service
        service_decision = langchain_decision_service.decide_search_method(
            request.message, 
            current_mode, 
            model_name=request.model
        )
        
        # 분석 결과 구성
        result = {
            "chat_request": {
                "message": request.message,
                "model": request.model,
                "session_id": request.session_id
            },
            "analysis": {
                "current_mode": current_mode,
                "decision": service_decision["decision"],
                "reason": service_decision["reason"],
                "confidence": service_decision["confidence"],
                "use_mcp_server": service_decision["decision"].startswith("MCP_SERVER-"),
                "use_web_search": service_decision["decision"] == "MCP_SERVER-WEB",
                "use_stock_service": service_decision["decision"] == "MCP_SERVER-STOCK",
                "use_weather_service": service_decision["decision"] == "MCP_SERVER-WEATHER",
                "service_type": langchain_decision_service.get_service_type(service_decision)
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
            "timestamp": "2024-01-01T12:00:00Z",
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
            "timestamp": "2024-01-01T12:00:00Z",
            "error": str(e)
        } 