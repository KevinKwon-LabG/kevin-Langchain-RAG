import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

def load_env_settings() -> Dict[str, Any]:
    """env.settings 파일을 로드하고 파싱합니다."""
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / "env.settings"
    
    if not env_file.exists():
        raise FileNotFoundError(f"env.settings 파일을 찾을 수 없습니다: {env_file}")
    
    settings = {}
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석이나 빈 줄 무시
                if not line or line.startswith('#'):
                    continue
                
                # = 구분자로 키-값 분리
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # JSON 배열 파싱 시도
                    if value.startswith('[') and value.endswith(']'):
                        try:
                            settings[key] = json.loads(value)
                        except json.JSONDecodeError:
                            settings[key] = value
                    # 불린 값 파싱
                    elif value.lower() in ('true', 'false'):
                        settings[key] = value.lower() == 'true'
                    # 숫자 파싱 시도
                    elif value.replace('.', '').replace('-', '').isdigit():
                        if '.' in value:
                            settings[key] = float(value)
                        else:
                            settings[key] = int(value)
                    else:
                        settings[key] = value
        
        return settings
        
    except Exception as e:
        raise Exception(f"env.settings 파일 파싱 실패: {e}")

def get_setting(key: str, default: Any = None) -> Any:
    """특정 설정 값을 반환합니다."""
    try:
        settings = load_env_settings()
        return settings.get(key, default)
    except Exception:
        return default

def get_model_settings() -> Dict[str, Any]:
    """모델 관련 설정을 반환합니다."""
    settings = load_env_settings()
    return {
        "default_model": settings.get("DEFAULT_MODEL", "gemma3:12b-it-qat"),
        "default_temperature": settings.get("DEFAULT_TEMPERATURE", 0.7),
        "default_top_p": settings.get("DEFAULT_TOP_P", 0.9),
        "default_top_k": settings.get("DEFAULT_TOP_K", 40),
        "default_repeat_penalty": settings.get("DEFAULT_REPEAT_PENALTY", 1.1),
        "default_seed": settings.get("DEFAULT_SEED", -1),
        "available_models": settings.get("AVAILABLE_MODELS", [])
    }

def get_rag_settings() -> Dict[str, Any]:
    """RAG 관련 설정을 반환합니다."""
    settings = load_env_settings()
    return {
        "default_use_rag": settings.get("DEFAULT_USE_RAG", True),
        "default_top_k_documents": settings.get("DEFAULT_TOP_K_DOCUMENTS", 5),
        "default_similarity_threshold": settings.get("DEFAULT_SIMILARITY_THRESHOLD", 0.7),
        "rag_top_k_presets": settings.get("RAG_TOP_K_PRESETS", [3, 5, 7, 10, 15, 20])
    }

def get_server_settings() -> Dict[str, Any]:
    """서버 관련 설정을 반환합니다."""
    settings = load_env_settings()
    return {
        "host": settings.get("HOST", "0.0.0.0"),
        "port": settings.get("PORT", 11040),
        "debug": settings.get("DEBUG", True),
        "log_level": settings.get("LOG_LEVEL", "INFO"),
        "ollama_base_url": settings.get("OLLAMA_BASE_URL", "http://1.237.52.240:11434"),
        "ollama_timeout": settings.get("OLLAMA_TIMEOUT", 120),
        "ollama_max_retries": settings.get("OLLAMA_MAX_RETRIES", 3)
    }

def get_document_settings() -> Dict[str, Any]:
    """문서 처리 관련 설정을 반환합니다."""
    settings = load_env_settings()
    return {
        "chunk_size": settings.get("CHUNK_SIZE", 1000),
        "chunk_overlap": settings.get("CHUNK_OVERLAP", 200),
        "max_tokens": settings.get("MAX_TOKENS", 4000),
        "upload_folder": settings.get("UPLOAD_FOLDER", "data/documents"),
        "max_file_size": settings.get("MAX_FILE_SIZE", 16 * 1024 * 1024),
        "allowed_extensions": settings.get("ALLOWED_EXTENSIONS", [".pdf", ".txt", ".docx", ".md"]),
        "chroma_persist_directory": settings.get("CHROMA_PERSIST_DIRECTORY", "data/vectorstore"),
        "embedding_model_name": settings.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"),
        "embedding_device": settings.get("EMBEDDING_DEVICE", "cpu")
    }

def get_advanced_settings() -> Dict[str, Any]:
    """고급 설정을 반환합니다."""
    settings = load_env_settings()
    return {
        "temperature": {
            "min": settings.get("TEMPERATURE_MIN", 0.0),
            "max": settings.get("TEMPERATURE_MAX", 2.0),
            "step": settings.get("TEMPERATURE_STEP", 0.1),
            "presets": settings.get("TEMPERATURE_PRESETS", [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2]),
            "default": settings.get("DEFAULT_TEMPERATURE", 0.7)
        },
        "top_p": {
            "min": settings.get("TOP_P_MIN", 0.1),
            "max": settings.get("TOP_P_MAX", 1.0),
            "step": settings.get("TOP_P_STEP", 0.05),
            "presets": settings.get("TOP_P_PRESETS", [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]),
            "default": settings.get("DEFAULT_TOP_P", 0.9)
        },
        "top_k": {
            "min": settings.get("TOP_K_MIN", 1),
            "max": settings.get("TOP_K_MAX", 100),
            "step": settings.get("TOP_K_STEP", 1),
            "presets": settings.get("TOP_K_PRESETS", [10, 20, 40, 60, 80, 100]),
            "default": settings.get("DEFAULT_TOP_K", 40)
        },
        "max_tokens": {
            "min": settings.get("MAX_TOKENS_MIN", 100),
            "max": settings.get("MAX_TOKENS_MAX", 8192),
            "step": settings.get("MAX_TOKENS_STEP", 100),
            "presets": settings.get("MAX_TOKENS_PRESETS", [512, 1024, 2048, 4096, 6144, 8192]),
            "default": settings.get("MAX_TOKENS", 4000)
        },
        "repeat_penalty": {
            "min": settings.get("REPEAT_PENALTY_MIN", 1.0),
            "max": settings.get("REPEAT_PENALTY_MAX", 2.0),
            "step": settings.get("REPEAT_PENALTY_STEP", 0.1),
            "presets": settings.get("REPEAT_PENALTY_PRESETS", [1.0, 1.1, 1.2, 1.3, 1.5, 1.8]),
            "default": settings.get("DEFAULT_REPEAT_PENALTY", 1.1)
        }
    }

def get_system_prompt_settings() -> Dict[str, Any]:
    """시스템 프롬프트 관련 설정을 반환합니다."""
    settings = load_env_settings()
    return {
        "default_system_prompt": settings.get("DEFAULT_SYSTEM_PROMPT", "You are a helpful assistant."),
        "rag_system_prompt": settings.get("RAG_SYSTEM_PROMPT", "You are a helpful assistant."),
        "templates": settings.get("SYSTEM_PROMPT_TEMPLATES", [])
    }

def validate_settings() -> bool:
    """설정 파일의 유효성을 검증합니다."""
    try:
        settings = load_env_settings()
        required_keys = [
            "HOST", "PORT", "OLLAMA_BASE_URL", "DEFAULT_MODEL",
            "DEFAULT_TEMPERATURE", "DEFAULT_TOP_P", "MAX_TOKENS"
        ]
        
        missing_keys = [key for key in required_keys if key not in settings]
        
        if missing_keys:
            print(f"❌ 필수 설정이 누락되었습니다: {', '.join(missing_keys)}")
            return False
        
        print("✅ 설정 파일이 유효합니다.")
        return True
        
    except Exception as e:
        print(f"❌ 설정 파일 검증 실패: {e}")
        return False 