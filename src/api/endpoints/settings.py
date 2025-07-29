"""
Settings API 엔드포인트
애플리케이션 설정 관리 및 조회를 위한 API를 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

@router.get("/api/settings")
async def get_settings():
    """
    현재 애플리케이션 설정을 반환합니다.
    
    Returns:
        현재 설정 정보
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        return {
            "settings": settings.get_config_summary(),
            "validation": settings.validate_settings(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"설정 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"설정 조회 실패: {str(e)}")

@router.post("/api/settings/reload")
async def reload_settings():
    """
    설정을 다시 로드합니다.
    
    Returns:
        리로드 결과
    """
    try:
        from src.config.settings import reload_settings
        settings = reload_settings()
        
        logger.info("설정이 성공적으로 리로드되었습니다")
        
        return {
            "success": True,
            "message": "설정이 성공적으로 리로드되었습니다",
            "timestamp": datetime.now().isoformat(),
            "settings": settings.get_config_summary()
        }
    except Exception as e:
        logger.error(f"설정 리로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"설정 리로드 실패: {str(e)}")

@router.get("/api/settings/validation")
async def validate_settings():
    """
    현재 설정의 유효성을 검증합니다.
    
    Returns:
        검증 결과
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        validation_result = settings.validate_settings()
        
        return {
            "validation": validation_result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"설정 검증 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"설정 검증 실패: {str(e)}")

@router.get("/api/settings/summary")
async def get_settings_summary():
    """
    설정 요약 정보를 반환합니다.
    
    Returns:
        설정 요약 정보
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        return {
            "summary": settings.get_config_summary(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"설정 요약 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"설정 요약 조회 실패: {str(e)}")

@router.get("/api/settings/models")
async def get_available_models():
    """
    사용 가능한 모델 목록을 반환합니다.
    
    Returns:
        모델 목록
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        return {
            "models": settings.get_available_models(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"모델 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")

@router.get("/api/settings/prompts")
async def get_system_prompts():
    """
    시스템 프롬프트 템플릿을 반환합니다.
    
    Returns:
        프롬프트 템플릿 목록
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        return {
            "prompts": settings.get_system_prompt_templates(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"프롬프트 템플릿 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프롬프트 템플릿 조회 실패: {str(e)}")

@router.get("/api/settings/presets")
async def get_all_presets():
    """
    모든 프리셋 값을 반환합니다.
    
    Returns:
        프리셋 값들
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        return {
            "temperature_presets": settings.get_temperature_presets(),
            "top_p_presets": settings.get_top_p_presets(),
            "top_k_presets": settings.get_top_k_presets(),
            "max_tokens_presets": settings.get_max_tokens_presets(),
            "repeat_penalty_presets": settings.get_repeat_penalty_presets(),
            "rag_top_k_presets": settings.get_rag_top_k_presets(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"프리셋 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프리셋 조회 실패: {str(e)}") 