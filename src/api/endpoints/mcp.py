from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from src.services.mcp_service import mcp_service
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])

# Pydantic 모델들
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1

class TextCompletionRequest(BaseModel):
    model: str
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1

class EmbeddingsRequest(BaseModel):
    model: str
    input: List[str]

@router.get("/health")
async def mcp_health_check():
    """MCP 서버 상태 확인"""
    try:
        if not settings.mcp_enabled:
            return {
                "status": "disabled",
                "message": "MCP 서비스가 비활성화되어 있습니다.",
                "server_url": settings.mcp_server_url
            }
        
        health_info = await mcp_service.health_check()
        return {
            "status": "success",
            "mcp_server": settings.mcp_server_url,
            "health_check": health_info
        }
    except Exception as e:
        logger.error(f"MCP 상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 서버 상태 확인 실패: {str(e)}")

@router.get("/tools")
async def get_mcp_tools():
    """MCP 서버에서 사용 가능한 도구 목록 조회"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        tools = await mcp_service.get_tools()
        return {
            "status": "success",
            "tools": tools,
            "total_count": len(tools)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 도구 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"도구 목록 조회 실패: {str(e)}")

@router.post("/tools/{tool_name}")
async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]):
    """MCP 서버의 특정 도구 호출"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        response = await mcp_service.call_tool(tool_name, arguments)
        return {
            "status": "success",
            "tool_name": tool_name,
            "response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 도구 호출 실패: {e}")
        raise HTTPException(status_code=500, detail=f"도구 호출 실패: {str(e)}")

@router.get("/models")
async def get_mcp_models():
    """MCP 서버에서 사용 가능한 모델 목록 조회 (하위 호환성)"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        models = await mcp_service.get_models()
        return {
            "status": "success",
            "models": models,
            "total_count": len(models)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 모델 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")

@router.get("/models/{model_name}")
async def get_mcp_model_info(model_name: str):
    """특정 MCP 모델 정보 조회"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        model_info = await mcp_service.get_model_info(model_name)
        if not model_info:
            raise HTTPException(status_code=404, detail=f"모델 '{model_name}'을 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "model": model_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 모델 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 정보 조회 실패: {str(e)}")

@router.post("/chat/completions")
async def mcp_chat_completion(request: ChatCompletionRequest):
    """MCP 서버를 통한 채팅 완성"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        # Pydantic 모델을 딕셔너리로 변환
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        response = await mcp_service.chat_completion(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            top_k=request.top_k,
            repeat_penalty=request.repeat_penalty
        )
        
        return {
            "status": "success",
            "response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 채팅 완성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"채팅 완성 실패: {str(e)}")

@router.post("/completions")
async def mcp_text_completion(request: TextCompletionRequest):
    """MCP 서버를 통한 텍스트 완성"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        response = await mcp_service.text_completion(
            model=request.model,
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            top_k=request.top_k,
            repeat_penalty=request.repeat_penalty
        )
        
        return {
            "status": "success",
            "response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 텍스트 완성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 완성 실패: {str(e)}")

@router.post("/embeddings")
async def mcp_embeddings(request: EmbeddingsRequest):
    """MCP 서버를 통한 임베딩 생성"""
    try:
        if not settings.mcp_enabled:
            raise HTTPException(status_code=400, detail="MCP 서비스가 비활성화되어 있습니다.")
        
        response = await mcp_service.embeddings(
            model=request.model,
            input_texts=request.input
        )
        
        return {
            "status": "success",
            "response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 임베딩 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"임베딩 생성 실패: {str(e)}")

@router.get("/config")
async def get_mcp_config():
    """MCP 설정 정보 조회"""
    return {
        "enabled": settings.mcp_enabled,
        "server_url": settings.mcp_server_url,
        "server_host": settings.mcp_server_host,
        "server_port": settings.mcp_server_port,
        "timeout": settings.mcp_timeout,
        "max_retries": settings.mcp_max_retries
    } 