from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from src.services.config_service import config_service

logger = logging.getLogger(__name__)

config_router = APIRouter(prefix="/api/config", tags=["Configuration"])

@config_router.get("/")
async def get_all_config():
    """모든 설정 반환"""
    try:
        return config_service.get_all_config()
    except Exception as e:
        logger.error(f"설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"설정 조회 실패: {str(e)}")

@config_router.get("/models")
async def get_model_config():
    """모델 관련 설정 반환"""
    try:
        return config_service.get_model_config()
    except Exception as e:
        logger.error(f"모델 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 설정 조회 실패: {str(e)}")

@config_router.get("/rag")
async def get_rag_config():
    """RAG 관련 설정 반환"""
    try:
        return config_service.get_rag_config()
    except Exception as e:
        logger.error(f"RAG 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 설정 조회 실패: {str(e)}")

@config_router.get("/system-prompts")
async def get_system_prompts():
    """시스템 프롬프트 설정 반환"""
    try:
        return config_service.get_system_prompts()
    except Exception as e:
        logger.error(f"시스템 프롬프트 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 프롬프트 설정 조회 실패: {str(e)}")

@config_router.get("/advanced-settings")
async def get_advanced_settings():
    """고급 설정 반환"""
    try:
        return config_service.get_advanced_settings()
    except Exception as e:
        logger.error(f"고급 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"고급 설정 조회 실패: {str(e)}")

@config_router.get("/server")
async def get_server_config():
    """서버 설정 반환"""
    try:
        return config_service.get_server_config()
    except Exception as e:
        logger.error(f"서버 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 설정 조회 실패: {str(e)}")

@config_router.get("/document")
async def get_document_config():
    """문서 처리 설정 반환"""
    try:
        return config_service.get_document_config()
    except Exception as e:
        logger.error(f"문서 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 설정 조회 실패: {str(e)}")

@config_router.get("/session")
async def get_session_config():
    """세션 관리 설정 반환"""
    try:
        return config_service.get_session_config()
    except Exception as e:
        logger.error(f"세션 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"세션 설정 조회 실패: {str(e)}")

@config_router.get("/cors")
async def get_cors_config():
    """CORS 설정 반환"""
    try:
        return config_service.get_cors_config()
    except Exception as e:
        logger.error(f"CORS 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"CORS 설정 조회 실패: {str(e)}")

@config_router.get("/logging")
async def get_logging_config():
    """로깅 설정 반환"""
    try:
        return config_service.get_logging_config()
    except Exception as e:
        logger.error(f"로깅 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"로깅 설정 조회 실패: {str(e)}")

@config_router.get("/temperature-presets")
async def get_temperature_presets():
    """Temperature 프리셋 반환"""
    try:
        from src.config.settings import settings
        return {
            "presets": settings.get_temperature_presets(),
            "min": settings.temperature_min,
            "max": settings.temperature_max,
            "step": settings.temperature_step,
            "default": settings.default_temperature
        }
    except Exception as e:
        logger.error(f"Temperature 프리셋 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Temperature 프리셋 조회 실패: {str(e)}")

@config_router.get("/top-p-presets")
async def get_top_p_presets():
    """Top P 프리셋 반환"""
    try:
        from src.config.settings import settings
        return {
            "presets": settings.get_top_p_presets(),
            "min": settings.top_p_min,
            "max": settings.top_p_max,
            "step": settings.top_p_step,
            "default": settings.default_top_p
        }
    except Exception as e:
        logger.error(f"Top P 프리셋 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Top P 프리셋 조회 실패: {str(e)}")

@config_router.get("/top-k-presets")
async def get_top_k_presets():
    """Top K 프리셋 반환"""
    try:
        from src.config.settings import settings
        return {
            "presets": settings.get_top_k_presets(),
            "min": settings.top_k_min,
            "max": settings.top_k_max,
            "step": settings.top_k_step,
            "default": settings.default_top_k
        }
    except Exception as e:
        logger.error(f"Top K 프리셋 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Top K 프리셋 조회 실패: {str(e)}")

@config_router.get("/max-tokens-presets")
async def get_max_tokens_presets():
    """Max Tokens 프리셋 반환"""
    try:
        from src.config.settings import settings
        return {
            "presets": settings.get_max_tokens_presets(),
            "min": settings.max_tokens_min,
            "max": settings.max_tokens_max,
            "step": settings.max_tokens_step,
            "default": settings.max_tokens
        }
    except Exception as e:
        logger.error(f"Max Tokens 프리셋 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Max Tokens 프리셋 조회 실패: {str(e)}")

@config_router.get("/repeat-penalty-presets")
async def get_repeat_penalty_presets():
    """Repeat Penalty 프리셋 반환"""
    try:
        from src.config.settings import settings
        return {
            "presets": settings.get_repeat_penalty_presets(),
            "min": settings.repeat_penalty_min,
            "max": settings.repeat_penalty_max,
            "step": settings.repeat_penalty_step,
            "default": settings.default_repeat_penalty
        }
    except Exception as e:
        logger.error(f"Repeat Penalty 프리셋 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Repeat Penalty 프리셋 조회 실패: {str(e)}")

@config_router.get("/rag-top-k-presets")
async def get_rag_top_k_presets():
    """RAG Top K 프리셋 반환"""
    try:
        from src.config.settings import settings
        return {
            "presets": settings.get_rag_top_k_presets(),
            "min": settings.rag_top_k_min,
            "max": settings.rag_top_k_max,
            "step": settings.rag_top_k_step,
            "default": settings.default_top_k_documents
        }
    except Exception as e:
        logger.error(f"RAG Top K 프리셋 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"RAG Top K 프리셋 조회 실패: {str(e)}")

@config_router.get("/system-prompt-templates")
async def get_system_prompt_templates():
    """시스템 프롬프트 템플릿 반환"""
    try:
        from src.config.settings import settings
        return {
            "templates": settings.get_system_prompt_templates(),
            "default": settings.default_system_prompt,
            "rag_default": settings.rag_system_prompt
        }
    except Exception as e:
        logger.error(f"시스템 프롬프트 템플릿 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 프롬프트 템플릿 조회 실패: {str(e)}")

@config_router.get("/available-models")
async def get_available_models():
    """사용 가능한 모델 목록 반환"""
    try:
        from src.config.settings import settings
        return {
            "models": settings.get_available_models(),
            "default": settings.default_model
        }
    except Exception as e:
        logger.error(f"사용 가능한 모델 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용 가능한 모델 목록 조회 실패: {str(e)}") 