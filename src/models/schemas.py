"""
Pydantic 모델과 스키마 정의
FastAPI에서 사용하는 요청/응답 모델들을 정의합니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    model: str = Field(..., description="사용할 모델명")
    message: str = Field(..., description="사용자 메시지")
    session_id: Optional[str] = Field(None, description="세션 ID")
    system: Optional[str] = Field("You are a helpful assistant.", description="시스템 프롬프트")
    options: Optional[Dict[str, Any]] = Field({}, description="추가 옵션")
    use_rag: Optional[bool] = Field(True, description="RAG 기능 사용 여부")
    rag_top_k: Optional[int] = Field(5, description="RAG 검색 시 가져올 문서 수")
    # 의사결정 서비스 제거됨

class SessionInfo(BaseModel):
    """세션 정보 모델"""
    session_id: str = Field(..., description="세션 ID")
    created_at: str = Field(..., description="생성 시간")
    last_active: str = Field(..., description="마지막 활동 시간")
    message_count: int = Field(..., description="메시지 수")
    preview: str = Field(..., description="미리보기")

class Message(BaseModel):
    """메시지 모델"""
    role: str = Field(..., description="메시지 역할 (user/assistant)")
    content: str = Field(..., description="메시지 내용")
    timestamp: str = Field(..., description="타임스탬프")
    model: Optional[str] = Field(None, description="사용된 모델")

class SessionData(BaseModel):
    """세션 데이터 모델"""
    session_id: str = Field(..., description="세션 ID")
    messages: List[Message] = Field(..., description="메시지 목록")
    created_at: str = Field(..., description="생성 시간")
    last_active: str = Field(..., description="마지막 활동 시간")
    # MCP 요청 대기 상태 관리
    weather_request_pending: bool = Field(False, description="날씨 요청 대기 상태")
    stock_request_pending: bool = Field(False, description="주식 요청 대기 상태")
    pending_location: Optional[str] = Field(None, description="대기 중인 위치 정보")
    pending_stock_symbol: Optional[str] = Field(None, description="대기 중인 주식 심볼")

class FileWriteRequest(BaseModel):
    """파일 쓰기 요청 모델"""
    content: str = Field(..., description="파일 내용")

class UserRequest(BaseModel):
    """사용자 요청 모델"""
    name: str = Field(..., description="사용자 이름")
    email: str = Field(..., description="이메일")

class NoteRequest(BaseModel):
    """노트 요청 모델"""
    title: str = Field(..., description="노트 제목")
    content: str = Field(..., description="노트 내용")
    user_id: Optional[int] = Field(None, description="사용자 ID")

class WebSearchRequest(BaseModel):
    """웹 검색 요청 모델"""
    query: str = Field(..., description="검색어")
    max_results: int = Field(5, description="최대 결과 수")

class FileSearchRequest(BaseModel):
    """파일 검색 요청 모델"""
    pattern: str = Field(..., description="검색 패턴")
    directory: str = Field(".", description="검색 디렉토리")

class DatabaseQueryRequest(BaseModel):
    """데이터베이스 쿼리 요청 모델"""
    query: str = Field(..., description="SQL 쿼리")

class HealthResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str = Field(..., description="상태")
    timestamp: str = Field(..., description="타임스탬프")
    version: str = Field(..., description="버전")
    services: Dict[str, str] = Field(..., description="서비스 상태")

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
    timestamp: str = Field(..., description="에러 발생 시간") 