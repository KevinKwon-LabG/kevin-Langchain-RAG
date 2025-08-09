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
    service_host: str = "1.237.52.240"
    service_port: int = 11040
    service_url: str = "http://1.237.52.240:11040"
    
    # =============================================================================
    # Ollama 설정
    # =============================================================================
    ollama_base_url: str = "http://1.237.52.240:11434"
    ollama_timeout: int = 120
    ollama_max_retries: int = 3
    

    
    # =============================================================================
    # 벡터 데이터베이스 설정
    # =============================================================================
    # Chroma DB 연결 설정
    chroma_mode: str = "local"  # "local" 또는 "http"
    chroma_persist_directory: str = "data/vectorstore"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_username: Optional[str] = None
    chroma_password: Optional[str] = None
    chroma_ssl: bool = False
    chroma_anonymized_telemetry: bool = False
    
    # 임베딩 모델 설정
    embedding_model_name: str = "all-MiniLM-L6-v2"  # 384차원 임베딩 모델 (외부 RAG 호환)
    embedding_device: str = "cpu"
    huggingface_api_key: Optional[str] = None
    
    # Chroma DB 컬렉션 설정
    chroma_collection_name: str = "documents"
    chroma_collection_metadata: Dict[str, Any] = {"description": "문서 임베딩 컬렉션"}
    
    # =============================================================================
    # 문서 처리 설정
    # =============================================================================
    chunk_size: int = 1000
    chunk_overlap: int = 200
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
    default_similarity_threshold: float = 0.85  # KURE 임베딩 모델에 적합한 엄격한 임계값

    # 로컬/외부 RAG 평균 점수 임계값 (env.settings에서 주입)
    min_avg_score_for_rag_local: float = 0.96
    min_avg_score_for_rag_external: float = 0.96

    # 로컬 RAG 컨텍스트 구성/절단 규칙
    local_max_context_chunks: int = 4
    local_max_context_length: int = 1500
    local_chunk_truncate_length: int = 500

    # 외부 RAG 컨텍스트 구성/절단 규칙
    external_max_context_chunks: int = 4
    external_max_context_length: int = 1500
    external_chunk_truncate_length: int = 500
    
    # =============================================================================
    # 시스템 프롬프트 설정
    # =============================================================================
    default_system_prompt: str = "You are a helpful assistant. Answer questions based on the provided context when available. If the context doesn't contain relevant information, use your general knowledge to provide accurate and helpful answers. Always be informative and helpful."
    rag_system_prompt: str = "You are a helpful assistant. Use the provided context to answer questions accurately when relevant information is available. If the context doesn't contain relevant information, use your general knowledge to provide accurate and helpful answers. Do not limit yourself to only the provided context."
    
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
    # UI 기본 선택값 (env.settings의 MAX_TOKENS_DEFAULT로 설정 가능)
    max_tokens_default: int = 1024
    
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
        {"name": "기본", "prompt": "You are a helpful assistant. Answer questions based on the provided context when available. If the context doesn't contain relevant information, use your general knowledge to provide accurate and helpful answers. Always be informative and helpful."},
        {"name": "한국어", "prompt": "당신은 도움이 되는 한국어 어시스턴트입니다. 제공된 컨텍스트를 기반으로 질문에 답변하세요. 컨텍스트에서 관련 정보를 찾을 수 없는 경우 일반적인 지식을 사용하여 정확하고 도움이 되는 답변을 제공하세요. 항상 유익하고 도움이 되도록 답변하세요."},
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
    log_level: str = "INFO"
    
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
    # 외부 RAG 서버 설정
    # =============================================================================
    external_rag_enabled: bool = True  # 외부 RAG 서비스 활성화
    external_rag_url: str = "http://1.237.52.240:8600"
    external_rag_tenant_id: str = "550e8400-e29b-41d4-a716-446655440000"
    external_rag_db_name: str = "default-db"
    external_rag_collection_id: str = "0d6ca41b-cd1c-4c84-a90e-ba2d4527c81a"
    external_rag_timeout: int = 30
    external_rag_fallback_to_local: bool = True  # 외부 RAG 실패 시 로컬 RAG로 폴백
    external_rag_max_retries: int = 3
    external_rag_health_check_interval: int = 300  # 5분마다 헬스 체크
    
    # 외부 RAG 사용 통계
    external_rag_stats_enabled: bool = True
    external_rag_stats_file: str = "data/external_rag_stats.json"
    
    # =============================================================================
    # MCP 서버 설정
    # =============================================================================
    mcp_server_host: str = "1.237.52.240"
    mcp_server_port: str = "20010"
    mcp_server_url: str = "http://1.237.52.240:20010"
    mcp_timeout: str = "30"
    mcp_max_retries: str = "3"
    mcp_enabled: str = "true"
    
    # MCP 서비스 사용 결정 방식 설정
    mcp_decision_method: str = "ai"  # "keyword" 또는 "ai"
    mcp_decision_methods: List[Dict[str, str]] = [
        {"value": "keyword", "label": "키워드 기반", "description": "미리 정의된 키워드 매칭으로 MCP 서비스 사용 여부 결정"},
        {"value": "ai", "label": "AI 기반", "description": "AI 모델을 사용하여 MCP 서비스 사용 여부 결정"}
    ]

    # =============================================================================
    # MCP 키워드 설정
    # =============================================================================
    # 날씨 관련 키워드 목록
    mcp_weather_keywords: List[str] = [
        "날씨", "기온", "습도", "비", "눈", "맑음", "흐림", "온도", "바람", "더울까", "추울까",
        "강수", "강설", "안개", "구름", "맑음", "흐림", "비올까", "눈올까", "바람불까",
        "체감온도", "최고기온", "최저기온", "일교차", "습도", "강수확률", "풍속", "풍향"
    ]

    # 주식 관련 키워드 목록
    mcp_stock_keywords: List[str] = [
        "주가", "주식", "종목", "증시", "코스피", "코스닥", "시가", "종가", "현재가",
        "삼성전자", "SK하이닉스", "LG전자", "포스코", "NAVER", "카카오", "현대차", "기아",
        "LG에너지솔루션", "삼성바이오로직스", "POSCO홀딩스", "삼성SDI", "LG화학", "현대모비스"
    ]

    # 웹 검색 관련 키워드 목록
    mcp_search_keywords: List[str] = [
        "검색", "찾기", "최신", "뉴스", "유행", "기사", "통계", "실시간", "최근",
        "알려줘", "알려주세요", "찾아줘", "찾아주세요", "무엇인가요", "어떻게요",
        "궁금해", "알고 싶어", "현재 상황", "지금 뭐가", "요즘 뭐가", "최근에 뭐가"
    ]

    @field_validator('mcp_weather_keywords', mode='before')
    @classmethod
    def parse_mcp_weather_keywords(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [keyword.strip() for keyword in v.split(',')]
        return v

    @field_validator('mcp_stock_keywords', mode='before')
    @classmethod
    def parse_mcp_stock_keywords(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [keyword.strip() for keyword in v.split(',')]
        return v

    @field_validator('mcp_search_keywords', mode='before')
    @classmethod
    def parse_mcp_search_keywords(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [keyword.strip() for keyword in v.split(',')]
        return v
    
    # =============================================================================
    # 주식 데이터 설정
    # =============================================================================
    stocks_data_file: str = "data/stocks_data.json"
    
    # =============================================================================
    # 날씨 도시 데이터 설정
    # =============================================================================
    weather_cities_csv_file: str = "data/weather_cities.csv"
    weather_cities_json_file: str = "data/weather_cities.json"
    
    # =============================================================================
    # 기본 도시 목록 설정
    # =============================================================================
    default_cities: List[str] = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "수원", "성남", "의정부", "안양", "부천", "광명", "평택", "동두천",
        "안산", "고양", "과천", "구리", "남양주", "오산", "시흥", "군포",
        "의왕", "하남", "용인", "파주", "이천", "안성", "김포", "화성",
        "광주", "여주", "양평", "양주", "포천", "연천", "가평",
        "춘천", "원주", "강릉", "태백", "속초", "삼척", "동해", "횡성",
        "영월", "평창", "정선", "철원", "화천", "양구", "인제", "고성",
        "양양", "홍천", "태안", "당진", "서산", "논산", "계룡", "공주",
        "보령", "아산", "서천", "천안", "예산", "금산", "부여",
        "청양", "홍성", "제주", "서귀포", "포항", "경주", "김천", "안동",
        "구미", "영주", "영천", "상주", "문경", "경산", "군산", "익산",
        "정읍", "남원", "김제", "완주", "진안", "무주", "장수", "임실",
        "순창", "고창", "부안", "여수", "순천", "나주", "광양", "담양",
        "곡성", "구례", "고흥", "보성", "화순", "장흥", "강진", "해남",
        "영암", "무안", "함평", "영광", "장성", "완도", "진도", "신안"
    ]
    
    @field_validator('default_cities', mode='before')
    @classmethod
    def parse_default_cities(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [city.strip() for city in v.split(',')]
        return v
    
    # =============================================================================
    # 기본 주식 종목 매핑 설정
    # =============================================================================
    default_stock_mapping: Dict[str, str] = {
        "삼성전자": "005930",
        "SK하이닉스": "000660",
        "NAVER": "035420",
        "카카오": "035720",
        "LG에너지솔루션": "373220",
        "삼성바이오로직스": "207940",
        "현대차": "005380",
        "기아": "000270",
        "POSCO홀딩스": "005490",
        "삼성SDI": "006400",
        "LG화학": "051910",
        "현대모비스": "012330",
        "KB금융": "105560",
        "신한지주": "055550",
        "하나금융지주": "086790",
        "우리금융지주": "316140",
        "LG전자": "066570",
        "삼성물산": "028260",
        "SK이노베이션": "096770",
        "아모레퍼시픽": "090430"
    }
    
    @field_validator('default_stock_mapping', mode='before')
    @classmethod
    def parse_default_stock_mapping(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    
    @field_validator('mcp_decision_methods', mode='before')
    @classmethod
    def parse_mcp_decision_methods(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    

    

    

    
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
        # 향후 필요시 구현 예정
        return
    
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

    def get_default_max_tokens(self) -> int:
        """Max Tokens 기본값을 반환합니다."""
        return self.max_tokens_default
    
    def get_repeat_penalty_presets(self) -> List[float]:
        """Repeat Penalty 프리셋을 반환합니다."""
        return self.repeat_penalty_presets
    
    def get_rag_top_k_presets(self) -> List[int]:
        """RAG Top K 프리셋을 반환합니다."""
        return self.rag_top_k_presets
    
    def get_chroma_client_config(self) -> Dict[str, Any]:
        """Chroma DB 클라이언트 설정을 반환합니다."""
        if self.chroma_mode == "local":
            return {
                "mode": "local",
                "path": self.chroma_persist_directory,
                "settings": {
                    "anonymized_telemetry": self.chroma_anonymized_telemetry
                }
            }
        elif self.chroma_mode == "http":
            return {
                "mode": "http",
                "host": self.chroma_host,
                "port": self.chroma_port,
                "username": self.chroma_username,
                "password": self.chroma_password,
                "ssl": self.chroma_ssl
            }
        else:
            raise ValueError(f"지원하지 않는 Chroma DB 모드입니다: {self.chroma_mode}")
    
    def get_chroma_url(self) -> str:
        """Chroma DB URL을 반환합니다."""
        if self.chroma_mode == "local":
            return f"file://{self.chroma_persist_directory}"
        elif self.chroma_mode == "http":
            protocol = "https" if self.chroma_ssl else "http"
            return f"{protocol}://{self.chroma_host}:{self.chroma_port}"
        else:
            raise ValueError(f"지원하지 않는 Chroma DB 모드입니다: {self.chroma_mode}")
    

    
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
                "similarity_threshold": self.default_similarity_threshold,
                "min_avg_score_for_rag_local": self.min_avg_score_for_rag_local,
                "min_avg_score_for_rag_external": self.min_avg_score_for_rag_external,
                "local_max_context_chunks": self.local_max_context_chunks,
                "local_max_context_length": self.local_max_context_length,
                "local_chunk_truncate_length": self.local_chunk_truncate_length,
                "external_max_context_chunks": self.external_max_context_chunks,
                "external_max_context_length": self.external_max_context_length,
                "external_chunk_truncate_length": self.external_chunk_truncate_length
            },
            "chroma_db": {
                "mode": self.chroma_mode,
                "url": self.get_chroma_url(),
                "collection_name": self.chroma_collection_name
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