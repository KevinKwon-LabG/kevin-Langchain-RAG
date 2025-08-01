from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List, Dict, Any
import os
import json
from pathlib import Path

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
    embedding_model_name: str = "nlpai-lab/KURE-v1"  # KURE (Korea University Retrieval Embedding)
    embedding_device: str = "cpu"
    chroma_anonymized_telemetry: bool = False
    huggingface_api_key: Optional[str] = None
    
    # =============================================================================
    # 문서 처리 설정
    # =============================================================================
    chunk_size: int = 500
    chunk_overlap: int = 100
    max_tokens: int = 4000
    upload_folder: str = "data/documents"
    max_file_size: int = 16 * 1024 * 1024  # 16MB
    allowed_extensions: List[str] = [".pdf", ".txt", ".docx", ".md"]
    
    @field_validator('allowed_extensions', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 쉼표로 구분된 문자열로 처리
                return [ext.strip() for ext in v.split(',')]
        return v
    
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
    
    @field_validator('temperature_presets', mode='before')
    @classmethod
    def parse_temperature_presets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [float(x.strip()) for x in v.split(',')]
        return v
    
    # =============================================================================
    # 고급 설정 - Top P 범위
    # =============================================================================
    top_p_min: float = 0.1
    top_p_max: float = 1.0
    top_p_step: float = 0.05
    top_p_presets: List[float] = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    
    @field_validator('top_p_presets', mode='before')
    @classmethod
    def parse_top_p_presets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [float(x.strip()) for x in v.split(',')]
        return v
    
    # =============================================================================
    # 고급 설정 - Top K 범위
    # =============================================================================
    top_k_min: int = 1
    top_k_max: int = 100
    top_k_step: int = 1
    top_k_presets: List[int] = [10, 20, 40, 60, 80, 100]
    
    @field_validator('top_k_presets', mode='before')
    @classmethod
    def parse_top_k_presets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [int(x.strip()) for x in v.split(',')]
        return v
    
    # =============================================================================
    # 고급 설정 - 최대 토큰 수 범위
    # =============================================================================
    max_tokens_min: int = 100
    max_tokens_max: int = 8192
    max_tokens_step: int = 100
    max_tokens_presets: List[int] = [1024, 2048, 4096, 6144, 8192]
    
    @field_validator('max_tokens_presets', mode='before')
    @classmethod
    def parse_max_tokens_presets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [int(x.strip()) for x in v.split(',')]
        return v
    
    # =============================================================================
    # 고급 설정 - Repeat Penalty 범위
    # =============================================================================
    repeat_penalty_min: float = 1.0
    repeat_penalty_max: float = 2.0
    repeat_penalty_step: float = 0.1
    repeat_penalty_presets: List[float] = [1.0, 1.1, 1.2, 1.3, 1.5, 1.8]
    
    @field_validator('repeat_penalty_presets', mode='before')
    @classmethod
    def parse_repeat_penalty_presets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [float(x.strip()) for x in v.split(',')]
        return v
    
    # =============================================================================
    # 고급 설정 - RAG 관련 범위
    # =============================================================================
    rag_top_k_min: int = 1
    rag_top_k_max: int = 20
    rag_top_k_step: int = 1
    rag_top_k_presets: List[int] = [3, 5, 7, 10, 15, 20]
    
    @field_validator('rag_top_k_presets', mode='before')
    @classmethod
    def parse_rag_top_k_presets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [int(x.strip()) for x in v.split(',')]
        return v
    
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
    
    @field_validator('available_models', mode='before')
    @classmethod
    def parse_available_models(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    
    # =============================================================================
    # 시스템 프롬프트 템플릿
    # =============================================================================
    system_prompt_templates: List[Dict[str, str]] = [
        {"name": "기본", "prompt": "You are a helpful assistant. Answer questions based on the provided context. If you cannot find relevant information in the context, say so clearly."},
        {"name": "한국어", "prompt": "당신은 도움이 되는 한국어 어시스턴트입니다. 제공된 컨텍스트를 기반으로 질문에 답변하세요. 컨텍스트에서 관련 정보를 찾을 수 없는 경우 명확히 말씀해 주세요."},
        {"name": "코딩", "prompt": "You are a helpful programming assistant. Provide clear, well-documented code examples and explanations. Always consider best practices and security."},
        {"name": "번역", "prompt": "You are a professional translator. Provide accurate and natural translations while preserving the original meaning and context."},
        {"name": "요약", "prompt": "You are a summarization expert. Provide concise, accurate summaries that capture the key points and main ideas."},
        {"name": "분석", "prompt": "You are an analytical assistant. Provide detailed analysis with supporting evidence and logical reasoning."}
    ]
    
    @field_validator('system_prompt_templates', mode='before')
    @classmethod
    def parse_system_prompt_templates(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    
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
    
    # =============================================================================
    # 웹 검색 설정
    # =============================================================================
    default_web_search_mode: str = "model_only"
    web_search_modes: List[Dict[str, str]] = [
        {"value": "model_only", "label": "모델 데이터만 사용", "description": "AI 모델의 학습된 데이터만 사용하여 답변"},        
        {"value": "mcp_server", "label": "MCP 서버 검색", "description": "외부 MCP 서버의 웹 검색 서비스 사용"}
    ]
    
    @field_validator('web_search_modes', mode='before')
    @classmethod
    def parse_web_search_modes(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    
    # =============================================================================
    # MCP 서버 설정
    # =============================================================================
    mcp_server_host: str = "1.237.52.240"
    mcp_server_port: str = "11045"
    mcp_server_url: str = "http://1.237.52.240:11045"
    mcp_timeout: str = "30"
    mcp_max_retries: str = "3"
    mcp_enabled: str = "true"
    

    

    

    
    # =============================================================================
    # 환경 설정
    # =============================================================================
    class Config:
        env_file = "env.settings"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 환경 변수에서 파싱된 값들을 설정
        self._parse_environment_arrays()
    
    def _parse_environment_arrays(self):
        """환경 변수에서 배열 형태의 값들을 파싱합니다."""
        # 이제 field_validator를 사용하므로 이 메서드는 더 이상 필요하지 않습니다.
        pass
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록을 반환합니다."""
        return self.available_models
    
    def get_system_prompt_templates(self) -> List[Dict[str, str]]:
        """시스템 프롬프트 템플릿을 반환합니다."""
        return self.system_prompt_templates
    
    def get_temperature_presets(self) -> List[float]:
        """Temperature 프리셋을 반환합니다."""
        return self.temperature_presets
    
    def get_top_p_presets(self) -> List[float]:
        """Top P 프리셋을 반환합니다."""
        return self.top_p_presets
    
    def get_top_k_presets(self) -> List[int]:
        """Top K 프리셋을 반환합니다."""
        return self.top_k_presets
    
    def get_max_tokens_presets(self) -> List[int]:
        """Max Tokens 프리셋을 반환합니다."""
        return self.max_tokens_presets
    
    def get_repeat_penalty_presets(self) -> List[float]:
        """Repeat Penalty 프리셋을 반환합니다."""
        return self.repeat_penalty_presets
    
    def get_rag_top_k_presets(self) -> List[int]:
        """RAG Top K 프리셋을 반환합니다."""
        return self.rag_top_k_presets
    

    
    def validate_settings(self) -> Dict[str, Any]:
        """설정값들의 유효성을 검증하고 결과를 반환합니다."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 포트 번호 검증
        if not (1024 <= self.port <= 65535):
            validation_results["valid"] = False
            validation_results["errors"].append(f"포트 번호가 유효하지 않습니다: {self.port}")
        
        # Ollama URL 검증
        if not self.ollama_base_url.startswith(('http://', 'https://')):
            validation_results["warnings"].append(f"Ollama URL 형식이 올바르지 않을 수 있습니다: {self.ollama_base_url}")
        
        # 파일 크기 제한 검증
        if self.max_file_size <= 0:
            validation_results["valid"] = False
            validation_results["errors"].append(f"최대 파일 크기가 유효하지 않습니다: {self.max_file_size}")
        
        # Temperature 범위 검증
        if not (self.temperature_min <= self.default_temperature <= self.temperature_max):
            validation_results["warnings"].append(f"기본 Temperature가 범위를 벗어납니다: {self.default_temperature}")
        
        # Top P 범위 검증
        if not (self.top_p_min <= self.default_top_p <= self.top_p_max):
            validation_results["warnings"].append(f"기본 Top P가 범위를 벗어납니다: {self.default_top_p}")
        
        return validation_results
    
    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보를 반환합니다."""
        return {
            "server": {
                "host": self.host,
                "port": self.port,
                "debug": self.debug,
                "log_level": self.log_level
            },
            "ollama": {
                "base_url": self.ollama_base_url,
                "timeout": self.ollama_timeout,
                "max_retries": self.ollama_max_retries
            },
            "model": {
                "default_model": self.default_model,
                "default_temperature": self.default_temperature,
                "default_top_p": self.default_top_p,
                "default_top_k": self.default_top_k
            },
            "rag": {
                "enabled": self.default_use_rag,
                "top_k_documents": self.default_top_k_documents,
                "similarity_threshold": self.default_similarity_threshold
            },

            "session": {
                "max_age_hours": self.max_session_age_hours,
                "max_messages": self.max_messages_per_session
            }
        }

# 전역 설정 인스턴스 생성
_settings_instance = None

def get_settings() -> Settings:
    """설정 인스턴스를 반환합니다. 싱글톤 패턴을 사용합니다."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

def reload_settings() -> Settings:
    """설정을 다시 로드합니다."""
    global _settings_instance
    _settings_instance = Settings()
    return _settings_instance

# 기본 설정 인스턴스 (하위 호환성을 위해 유지)
settings = get_settings() 