"""
Models API 엔드포인트
Ollama 모델 관리 및 조회를 위한 API를 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

@router.get("/api/models")
async def get_models():
    """
    사용 가능한 Ollama 모델 목록을 반환합니다.
    
    Returns:
        모델 목록
    """
    try:
        # 실제 구현에서는 Ollama API를 호출하여 모델 목록을 가져옵니다
        models = [
            {"name": "gemma3:12b-it-qat", "size": "8.9 GB", "id": "5d4fa005e7bb"},
            {"name": "deepseek-v2:16b-lite-chat-q8_0", "size": "16 GB", "id": "1d62ef756269"},
            {"name": "qwen3:14b-q8_0", "size": "15 GB", "id": "304bf7349c71"},
            {"name": "deepseek-r1:14b", "size": "9.0 GB", "id": "c333b7232bdb"},
            {"name": "llama3.2-vision:11b-instruct-q4_K_M", "size": "7.8 GB", "id": "6f2f9757ae97"},
            {"name": "llama3.1:8b", "size": "4.9 GB", "id": "46e0c10c039e"}
        ]
        return {"models": models}
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