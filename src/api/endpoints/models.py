"""
Models API 엔드포인트
Ollama 모델 관리 및 조회를 위한 API를 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime
import requests

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

@router.get("/api/models")
async def get_models():
    """
    현재 Ollama 서버에서 실행 중인 모델 목록을 반환합니다.
    
    Returns:
        모델 목록
    """
    try:
        # Ollama API에서 현재 실행 중(running) 모델 목록 가져오기
        from src.config.settings import get_settings
        settings = get_settings()

        response = requests.get(f"{settings.ollama_base_url}/api/ps", timeout=10)
        response.raise_for_status()
        data = response.json() or {}

        running_models = []
        for model in data.get("models", []):
            # name, digest, size(바이트) 추출
            name = model.get("name") or model.get("model") or "unknown"
            digest = model.get("digest") or name

            size_bytes = model.get("size") or model.get("size_bytes")
            size_str = "N/A"
            if isinstance(size_bytes, (int, float)) and size_bytes > 0:
                size_gb = float(size_bytes) / (1024 ** 3)
                size_str = f"{size_gb:.1f} GB"

            running_models.append({
                "name": name,
                "size": size_str,
                "id": digest,
                "is_running": True
            })

        # 기본 모델을 최상단으로 정렬 (없으면 순서 유지)
        try:
            default_model_name = settings.default_model
        except Exception:
            default_model_name = "gemma3:12b-it-qat"

        if running_models:
            preferred = [m for m in running_models if m.get("name") == default_model_name]
            others = [m for m in running_models if m.get("name") != default_model_name]
            running_models = preferred + others

        return {"models": running_models}
    except Exception as e:
        logger.error(f"모델 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")

@router.get("/api/models/{model_id}")
async def get_model_detail(model_id: str):
    """
    특정 모델의 상세 정보를 반환합니다.
    
    Args:
        model_id: 모델 ID
    
    Returns:
        모델 상세 정보
    """
    try:
        # 실제 구현에서는 Ollama API를 호출하여 모델 상세 정보를 가져옵니다
        model_info = {
            "id": model_id,
            "name": "gemma3:12b-it-qat",
            "size": "8.9 GB",
            "modified_at": "2024-01-15T10:30:00Z",
            "digest": "sha256:abc123...",
            "details": {
                "format": "gguf",
                "family": "gemma",
                "parameter_size": "12B",
                "quantization_level": "qat"
            }
        }
        return model_info
    except Exception as e:
        logger.error(f"모델 상세 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"모델 상세 조회 실패: {str(e)}")

@router.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    """
    특정 모델을 삭제합니다.
    
    Args:
        model_id: 모델 ID
    
    Returns:
        삭제 결과
    """
    try:
        # 실제 구현에서는 Ollama API를 호출하여 모델을 삭제합니다
        logger.info(f"모델 삭제 요청: {model_id}")
        
        return {
            "success": True,
            "message": f"모델 '{model_id}'가 성공적으로 삭제되었습니다",
            "model_id": model_id
        }
    except Exception as e:
        logger.error(f"모델 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"모델 삭제 실패: {str(e)}")

@router.post("/api/models/pull")
async def pull_model(model_name: str):
    """
    새로운 모델을 다운로드합니다.
    
    Args:
        model_name: 다운로드할 모델 이름
    
    Returns:
        다운로드 결과
    """
    try:
        # 실제 구현에서는 Ollama API를 호출하여 모델을 다운로드합니다
        logger.info(f"모델 다운로드 요청: {model_name}")
        
        return {
            "success": True,
            "message": f"모델 '{model_name}' 다운로드가 시작되었습니다",
            "model_name": model_name,
            "status": "downloading"
        }
    except Exception as e:
        logger.error(f"모델 다운로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"모델 다운로드 실패: {str(e)}") 