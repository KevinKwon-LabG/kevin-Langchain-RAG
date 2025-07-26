from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
import os
import json

class Settings(BaseSettings):
    # =============================================================================
    # 서버 설정
    # =============================================================================
    host: str = "0.0.0.0"
    port: int = 11040
    debug: bool = True
    log_level: str = "INFO"
    
    # =============================================================================
    # Ollama 설정
    # =============================================================================
    ollama_base_url: str = "http://1.237.52.240:11434"
    ollama_timeout: int = 120
    ollama_max_retries: int = 3
    
    # =============================================================================
    # 벡터 데이터베이스 설정
    # =============================================================================
    chroma_persist_directory: str = "data/vectorstore"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    
    # =============================================================================
    # 문서 처리 설정
    # =============================================================================
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens: int = 4000
    upload_folder: str = "data/documents"
    max_file_size: int = 16 * 1024 * 1024  # 16MB
    allowed_extensions: List[str] = [".pdf", ".txt", ".docx", ".md"]
    
    # =============================================================================
    # LLM 모델 설정 (기본값)
    # =============================================================================
    default_model: str = "gemma3:12b-it-qat"
    default_temperature: float = 0.7
    default_top_p: float = 0.9
    default_top_k: int = 40
    default_repeat_penalty: float = 1.1
    default_seed: int = -1
    
    # =============================================================================
    # RAG 설정
    # =============================================================================
    default_use_rag: bool = True
    default_top_k_documents: int = 5
    default_similarity_threshold: float = 0.7
    
    # =============================================================================
    # 시스템 프롬프트 설정
    # =============================================================================
    default_system_prompt: str = "You are a helpful assistant. Answer questions based on the provided context. If you cannot find relevant information in the context, say so clearly."
    rag_system_prompt: str = "You are a helpful assistant. Use the provided context to answer questions accurately. If the context doesn't contain relevant information, say \"컨텍스트에서 해당 정보를 찾을 수 없습니다.\""
    
    # =============================================================================
    # 세션 관리 설정
    # =============================================================================
    max_session_age_hours: int = 24
    max_messages_per_session: int = 100
    session_cleanup_interval_hours: int = 6
    
    # =============================================================================
    # 고급 설정 - Temperature 범위
    # =============================================================================
    temperature_min: float = 0.0
    temperature_max: float = 2.0
    temperature_step: float = 0.1
    temperature_presets: List[float] = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2]
    
    # =============================================================================
    # 고급 설정 - Top P 범위
    # =============================================================================
    top_p_min: float = 0.1
    top_p_max: float = 1.0
    top_p_step: float = 0.05
    top_p_presets: List[float] = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    
    # =============================================================================
    # 고급 설정 - Top K 범위
    # =============================================================================
    top_k_min: int = 1
    top_k_max: int = 100
    top_k_step: int = 1
    top_k_presets: List[int] = [10, 20, 40, 60, 80, 100]
    
    # =============================================================================
    # 고급 설정 - 최대 토큰 수 범위
    # =============================================================================
    max_tokens_min: int = 100
    max_tokens_max: int = 8192
    max_tokens_step: int = 100
    max_tokens_presets: List[int] = [512, 1024, 2048, 4096, 6144, 8192]
    
    # =============================================================================
    # 고급 설정 - Repeat Penalty 범위
    # =============================================================================
    repeat_penalty_min: float = 1.0
    repeat_penalty_max: float = 2.0
    repeat_penalty_step: float = 0.1
    repeat_penalty_presets: List[float] = [1.0, 1.1, 1.2, 1.3, 1.5, 1.8]
    
    # =============================================================================
    # 고급 설정 - RAG 관련 범위
    # =============================================================================
    rag_top_k_min: int = 1
    rag_top_k_max: int = 20
    rag_top_k_step: int = 1
    rag_top_k_presets: List[int] = [3, 5, 7, 10, 15, 20]
    
    # =============================================================================
    # 사용 가능한 모델 목록
    # =============================================================================
    available_models: List[Dict[str, Any]] = [
        {"name": "gemma3:12b-it-qat", "size": "8.9 GB", "id": "5d4fa005e7bb", "description": "Google의 Gemma 3 12B 모델 (양자화됨)"},
        {"name": "llama3.1:8b", "size": "4.9 GB", "id": "46e0c10c039e", "description": "Meta의 Llama 3.1 8B 모델"},
        {"name": "llama3.2-vision:11b-instruct-q4_K_M", "size": "7.8 GB", "id": "6f2f9757ae97", "description": "Meta의 Llama 3.2 Vision 11B 모델"},
        {"name": "qwen3:14b-q8_0", "size": "15 GB", "id": "304bf7349c71", "description": "Alibaba의 Qwen 3 14B 모델"},
        {"name": "deepseek-r1:14b", "size": "9.0 GB", "id": "c333b7232bdb", "description": "DeepSeek의 R1 14B 모델"},
        {"name": "deepseek-v2:16b-lite-chat-q8_0", "size": "16 GB", "id": "1d62ef756269", "description": "DeepSeek의 V2 16B Lite 모델"}
    ]
    
    # =============================================================================
    # 시스템 프롬프트 템플릿
    # =============================================================================
    system_prompt_templates: List[Dict[str, str]] = [
        {"name": "기본", "prompt": "You are a helpful assistant. Answer questions based on the provided context. If you cannot find relevant information in the context, say so clearly."},
        {"name": "한국어", "prompt": "당신은 도움이 되는 한국어 어시스턴트입니다. 제공된 컨텍스트를 기반으로 질문에 답변하세요. 컨텍스트에서 관련 정보를 찾을 수 없는 경우 명확히 말씀해 주세요."},
        {"name": "코딩", "prompt": "You are a helpful programming assistant. Provide clear, well-documented code examples and explanations. Always consider best practices and security."},
        {"name": "번역", "prompt": "You are a professional translator. Provide accurate and natural translations while preserving the original meaning and context."},
        {"name": "코딩", "prompt": "You are a summarization expert. Provide concise, accurate summaries that capture the key points and main ideas."},
        {"name": "분석", "prompt": "You are an analytical assistant. Provide detailed analysis with supporting evidence and logical reasoning."}
    ]
    
    # =============================================================================
    # 보안 설정
    # =============================================================================
    cors_allow_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    cors_allow_headers: str = "*"
    
    # =============================================================================
    # 로깅 설정
    # =============================================================================
    log_file: str = "logs/app.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = "env.settings"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """환경 변수에서 모델 목록을 파싱하거나 기본값 반환"""
        try:
            # 환경 변수에서 JSON 문자열로 설정된 경우 파싱
            if hasattr(self, '_available_models_env'):
                return json.loads(self._available_models_env)
        except (json.JSONDecodeError, AttributeError):
            pass
        return self.available_models
    
    def get_system_prompt_templates(self) -> List[Dict[str, str]]:
        """환경 변수에서 시스템 프롬프트 템플릿을 파싱하거나 기본값 반환"""
        try:
            # 환경 변수에서 JSON 문자열로 설정된 경우 파싱
            if hasattr(self, '_system_prompt_templates_env'):
                return json.loads(self._system_prompt_templates_env)
        except (json.JSONDecodeError, AttributeError):
            pass
        return self.system_prompt_templates
    
    def get_temperature_presets(self) -> List[float]:
        """환경 변수에서 Temperature 프리셋을 파싱하거나 기본값 반환"""
        try:
            if hasattr(self, '_temperature_presets_env'):
                return [float(x.strip()) for x in self._temperature_presets_env.split(',')]
        except (ValueError, AttributeError):
            pass
        return self.temperature_presets
    
    def get_top_p_presets(self) -> List[float]:
        """환경 변수에서 Top P 프리셋을 파싱하거나 기본값 반환"""
        try:
            if hasattr(self, '_top_p_presets_env'):
                return [float(x.strip()) for x in self._top_p_presets_env.split(',')]
        except (ValueError, AttributeError):
            pass
        return self.top_p_presets
    
    def get_top_k_presets(self) -> List[int]:
        """환경 변수에서 Top K 프리셋을 파싱하거나 기본값 반환"""
        try:
            if hasattr(self, '_top_k_presets_env'):
                return [int(x.strip()) for x in self._top_k_presets_env.split(',')]
        except (ValueError, AttributeError):
            pass
        return self.top_k_presets
    
    def get_max_tokens_presets(self) -> List[int]:
        """환경 변수에서 Max Tokens 프리셋을 파싱하거나 기본값 반환"""
        try:
            if hasattr(self, '_max_tokens_presets_env'):
                return [int(x.strip()) for x in self._max_tokens_presets_env.split(',')]
        except (ValueError, AttributeError):
            pass
        return self.max_tokens_presets
    
    def get_repeat_penalty_presets(self) -> List[float]:
        """환경 변수에서 Repeat Penalty 프리셋을 파싱하거나 기본값 반환"""
        try:
            if hasattr(self, '_repeat_penalty_presets_env'):
                return [float(x.strip()) for x in self._repeat_penalty_presets_env.split(',')]
        except (ValueError, AttributeError):
            pass
        return self.repeat_penalty_presets
    
    def get_rag_top_k_presets(self) -> List[int]:
        """환경 변수에서 RAG Top K 프리셋을 파싱하거나 기본값 반환"""
        try:
            if hasattr(self, '_rag_top_k_presets_env'):
                return [int(x.strip()) for x in self._rag_top_k_presets_env.split(',')]
        except (ValueError, AttributeError):
            pass
        return self.rag_top_k_presets

settings = Settings() 