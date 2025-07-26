import json
import logging
from typing import Dict, List, Any, Optional
from src.config.settings import settings
from src.utils.env_loader import load_env_settings, get_model_settings, get_rag_settings, get_server_settings, get_document_settings, get_advanced_settings, get_system_prompt_settings

logger = logging.getLogger(__name__)

class ConfigService:
    """설정 관리 서비스"""
    
    @staticmethod
    def get_model_config() -> Dict[str, Any]:
        """모델 관련 설정 반환"""
        try:
            return get_model_settings()
        except Exception as e:
            logger.warning(f"env.settings에서 모델 설정을 로드할 수 없습니다. 기본 설정을 사용합니다: {e}")
            return {
                "default_model": settings.default_model,
                "available_models": settings.get_available_models(),
                "default_temperature": settings.default_temperature,
                "default_top_p": settings.default_top_p,
                "default_top_k": settings.default_top_k,
                "default_repeat_penalty": settings.default_repeat_penalty,
                "default_seed": settings.default_seed
            }
    
    @staticmethod
    def get_rag_config() -> Dict[str, Any]:
        """RAG 관련 설정 반환"""
        try:
            return get_rag_settings()
        except Exception as e:
            logger.warning(f"env.settings에서 RAG 설정을 로드할 수 없습니다. 기본 설정을 사용합니다: {e}")
            return {
                "default_use_rag": settings.default_use_rag,
                "default_top_k_documents": settings.default_top_k_documents,
                "default_similarity_threshold": settings.default_similarity_threshold,
                "rag_top_k_presets": settings.get_rag_top_k_presets(),
                "rag_top_k_min": settings.rag_top_k_min,
                "rag_top_k_max": settings.rag_top_k_max,
                "rag_top_k_step": settings.rag_top_k_step
            }
    
    @staticmethod
    def get_system_prompts() -> Dict[str, Any]:
        """시스템 프롬프트 설정 반환"""
        try:
            return get_system_prompt_settings()
        except Exception as e:
            logger.warning(f"env.settings에서 시스템 프롬프트 설정을 로드할 수 없습니다. 기본 설정을 사용합니다: {e}")
            return {
                "default_system_prompt": settings.default_system_prompt,
                "rag_system_prompt": settings.rag_system_prompt,
                "templates": settings.get_system_prompt_templates()
            }
    
    @staticmethod
    def get_advanced_settings() -> Dict[str, Any]:
        """고급 설정 반환"""
        try:
            return get_advanced_settings()
        except Exception as e:
            logger.warning(f"env.settings에서 고급 설정을 로드할 수 없습니다. 기본 설정을 사용합니다: {e}")
            return {
                "temperature": {
                    "min": settings.temperature_min,
                    "max": settings.temperature_max,
                    "step": settings.temperature_step,
                    "presets": settings.get_temperature_presets(),
                    "default": settings.default_temperature
                },
                "top_p": {
                    "min": settings.top_p_min,
                    "max": settings.top_p_max,
                    "step": settings.top_p_step,
                    "presets": settings.get_top_p_presets(),
                    "default": settings.default_top_p
                },
                "top_k": {
                    "min": settings.top_k_min,
                    "max": settings.top_k_max,
                    "step": settings.top_k_step,
                    "presets": settings.get_top_k_presets(),
                    "default": settings.default_top_k
                },
                "max_tokens": {
                    "min": settings.max_tokens_min,
                    "max": settings.max_tokens_max,
                    "step": settings.max_tokens_step,
                    "presets": settings.get_max_tokens_presets(),
                    "default": settings.max_tokens
                },
                "repeat_penalty": {
                    "min": settings.repeat_penalty_min,
                    "max": settings.repeat_penalty_max,
                    "step": settings.repeat_penalty_step,
                    "presets": settings.get_repeat_penalty_presets(),
                    "default": settings.default_repeat_penalty
                }
            }
    
    @staticmethod
    def get_server_config() -> Dict[str, Any]:
        """서버 설정 반환"""
        try:
            return get_server_settings()
        except Exception as e:
            logger.warning(f"env.settings에서 서버 설정을 로드할 수 없습니다. 기본 설정을 사용합니다: {e}")
            return {
                "host": settings.host,
                "port": settings.port,
                "debug": settings.debug,
                "log_level": settings.log_level,
                "ollama_base_url": settings.ollama_base_url,
                "ollama_timeout": settings.ollama_timeout,
                "ollama_max_retries": settings.ollama_max_retries
            }
    
    @staticmethod
    def get_document_config() -> Dict[str, Any]:
        """문서 처리 설정 반환"""
        try:
            return get_document_settings()
        except Exception as e:
            logger.warning(f"env.settings에서 문서 설정을 로드할 수 없습니다. 기본 설정을 사용합니다: {e}")
            return {
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "max_tokens": settings.max_tokens,
                "upload_folder": settings.upload_folder,
                "max_file_size": settings.max_file_size,
                "allowed_extensions": settings.allowed_extensions,
                "chroma_persist_directory": settings.chroma_persist_directory,
                "embedding_model_name": settings.embedding_model_name,
                "embedding_device": settings.embedding_device
            }
    
    @staticmethod
    def get_session_config() -> Dict[str, Any]:
        """세션 관리 설정 반환"""
        return {
            "max_session_age_hours": settings.max_session_age_hours,
            "max_messages_per_session": settings.max_messages_per_session,
            "session_cleanup_interval_hours": settings.session_cleanup_interval_hours
        }
    
    @staticmethod
    def get_cors_config() -> Dict[str, Any]:
        """CORS 설정 반환"""
        return {
            "allow_origins": settings.cors_allow_origins,
            "allow_credentials": settings.cors_allow_credentials,
            "allow_methods": settings.cors_allow_methods,
            "allow_headers": settings.cors_allow_headers
        }
    
    @staticmethod
    def get_logging_config() -> Dict[str, Any]:
        """로깅 설정 반환"""
        return {
            "log_file": settings.log_file,
            "log_max_size": settings.log_max_size,
            "log_backup_count": settings.log_backup_count,
            "log_format": settings.log_format
        }
    
    @staticmethod
    def get_all_config() -> Dict[str, Any]:
        """모든 설정 반환"""
        return {
            "server": ConfigService.get_server_config(),
            "model": ConfigService.get_model_config(),
            "rag": ConfigService.get_rag_config(),
            "system_prompts": ConfigService.get_system_prompts(),
            "advanced_settings": ConfigService.get_advanced_settings(),
            "document": ConfigService.get_document_config(),
            "session": ConfigService.get_session_config(),
            "cors": ConfigService.get_cors_config(),
            "logging": ConfigService.get_logging_config()
        }
    
    @staticmethod
    def validate_temperature(value: float) -> bool:
        """Temperature 값 검증"""
        return settings.temperature_min <= value <= settings.temperature_max
    
    @staticmethod
    def validate_top_p(value: float) -> bool:
        """Top P 값 검증"""
        return settings.top_p_min <= value <= settings.top_p_max
    
    @staticmethod
    def validate_top_k(value: int) -> bool:
        """Top K 값 검증"""
        return settings.top_k_min <= value <= settings.top_k_max
    
    @staticmethod
    def validate_max_tokens(value: int) -> bool:
        """Max Tokens 값 검증"""
        return settings.max_tokens_min <= value <= settings.max_tokens_max
    
    @staticmethod
    def validate_repeat_penalty(value: float) -> bool:
        """Repeat Penalty 값 검증"""
        return settings.repeat_penalty_min <= value <= settings.repeat_penalty_max
    
    @staticmethod
    def validate_rag_top_k(value: int) -> bool:
        """RAG Top K 값 검증"""
        return settings.rag_top_k_min <= value <= settings.rag_top_k_max
    
    @staticmethod
    def get_closest_preset(value: float, preset_list: List[float]) -> float:
        """가장 가까운 프리셋 값 반환"""
        if not preset_list:
            return value
        
        closest = preset_list[0]
        min_diff = abs(value - closest)
        
        for preset in preset_list:
            diff = abs(value - preset)
            if diff < min_diff:
                min_diff = diff
                closest = preset
        
        return closest
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """파일 크기를 읽기 쉬운 형태로 변환"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

# 싱글톤 인스턴스
config_service = ConfigService() 