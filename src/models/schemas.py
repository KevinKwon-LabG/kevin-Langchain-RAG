from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    model: str = Field(..., description="사용할 모델 이름")
    message: str = Field(..., description="사용자 메시지")
    session_id: Optional[str] = Field(None, description="세션 ID")
    system: Optional[str] = Field("You are a helpful assistant.", description="시스템 프롬프트")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="모델 옵션")
    use_rag: Optional[bool] = Field(True, description="RAG 사용 여부")
    top_k: Optional[int] = Field(5, description="검색할 문서 수")

class DocumentUploadRequest(BaseModel):
    filename: str = Field(..., description="파일명")
    content: str = Field(..., description="문서 내용")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="문서 메타데이터")

class DocumentResponse(BaseModel):
    id: str
    filename: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    chunk_count: int

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    top_k: int = Field(5, description="검색할 문서 수")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_count: int
    query: str

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    last_active: datetime
    message_count: int
    preview: str

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime
    model: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None

class SessionData(BaseModel):
    session_id: str
    messages: List[Message]
    created_at: datetime
    last_active: datetime

class HealthResponse(BaseModel):
    server: str
    ollama_connected: bool
    ollama_url: str
    active_sessions: int
    vectorstore_status: str
    timestamp: float
    error: Optional[str] = None

class ModelInfo(BaseModel):
    name: str
    size: str
    id: str
    modified_at: Optional[str] = None
    size_bytes: Optional[int] = None

class ModelsResponse(BaseModel):
    models: List[ModelInfo] 