"""
세션 관리 유틸리티
채팅 세션의 생성, 조회, 업데이트, 삭제를 담당합니다.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.models.schemas import SessionData, Message, SessionInfo

logger = logging.getLogger(__name__)

# 전역 세션 저장소 (실제 운영에서는 Redis나 데이터베이스 사용 권장)
sessions: Dict[str, SessionData] = {}

def create_session_id() -> str:
    """새로운 세션 ID를 생성합니다."""
    return str(uuid.uuid4())

def get_or_create_session(session_id: Optional[str] = None) -> SessionData:
    """
    세션을 가져오거나 새로 생성합니다.
    
    Args:
        session_id: 세션 ID (None이면 새로 생성)
    
    Returns:
        SessionData: 세션 데이터
    """
    if session_id is None:
        session_id = create_session_id()
    
    if session_id not in sessions:
        current_time = datetime.now().isoformat()
        sessions[session_id] = SessionData(
            session_id=session_id,
            messages=[],
            created_at=current_time,
            last_active=current_time
        )
        logger.info(f"새 세션 생성: {session_id}")
    
    return sessions[session_id]

def add_message_to_session(
    session_id: str, 
    role: str, 
    content: str, 
    model: Optional[str] = None
) -> None:
    """
    세션에 메시지를 추가합니다.
    
    Args:
        session_id: 세션 ID
        role: 메시지 역할 (user/assistant)
        content: 메시지 내용
        model: 사용된 모델 (선택사항)
    """
    session = get_or_create_session(session_id)
    
    message = Message(
        role=role,
        content=content,
        timestamp=datetime.now().isoformat(),
        model=model
    )
    
    session.messages.append(message)
    session.last_active = datetime.now().isoformat()
    
    logger.debug(f"세션 {session_id}에 메시지 추가: {role}")

def get_session(session_id: str) -> Optional[SessionData]:
    """
    세션을 조회합니다.
    
    Args:
        session_id: 세션 ID
    
    Returns:
        SessionData 또는 None
    """
    return sessions.get(session_id)

def delete_session(session_id: str) -> bool:
    """
    세션을 삭제합니다.
    
    Args:
        session_id: 세션 ID
    
    Returns:
        bool: 삭제 성공 여부
    """
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f"세션 삭제: {session_id}")
        return True
    return False

def get_all_sessions() -> List[SessionInfo]:
    """
    모든 세션 정보를 조회합니다.
    
    Returns:
        List[SessionInfo]: 세션 정보 목록
    """
    session_infos = []
    
    for session_id, session_data in sessions.items():
        # 미리보기 생성 (마지막 메시지의 일부)
        preview = ""
        if session_data.messages:
            last_message = session_data.messages[-1]
            preview = last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content
        
        session_info = SessionInfo(
            session_id=session_id,
            created_at=session_data.created_at,
            last_active=session_data.last_active,
            message_count=len(session_data.messages),
            preview=preview
        )
        session_infos.append(session_info)
    
    # 최근 활동 순으로 정렬
    session_infos.sort(key=lambda x: x.last_active, reverse=True)
    return session_infos

def build_conversation_prompt(
    session_id: str, 
    new_message: str, 
    system_prompt: Optional[str] = None
) -> str:
    """
    대화 프롬프트를 구성합니다.
    
    Args:
        session_id: 세션 ID
        new_message: 새로운 메시지
        system_prompt: 시스템 프롬프트
    
    Returns:
        str: 구성된 대화 프롬프트
    """
    session = get_session(session_id)
    if not session:
        return new_message
    
    # 시스템 프롬프트 설정
    if system_prompt is None:
        system_prompt = "You are a helpful assistant."
    
    # 대화 히스토리 구성
    conversation = f"System: {system_prompt}\n\n"
    
    for message in session.messages:
        role = "User" if message.role == "user" else "Assistant"
        conversation += f"{role}: {message.content}\n"
    
    # 새로운 메시지 추가
    conversation += f"User: {new_message}\n"
    conversation += "Assistant: "
    
    return conversation

def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """
    오래된 세션을 정리합니다.
    
    Args:
        max_age_hours: 최대 보관 시간 (시간)
    
    Returns:
        int: 삭제된 세션 수
    """
    current_time = datetime.now()
    deleted_count = 0
    sessions_to_delete = []
    
    for session_id, session_data in sessions.items():
        last_active = datetime.fromisoformat(session_data.last_active)
        age_hours = (current_time - last_active).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            sessions_to_delete.append(session_id)
    
    for session_id in sessions_to_delete:
        delete_session(session_id)
        deleted_count += 1
    
    if deleted_count > 0:
        logger.info(f"{deleted_count}개의 오래된 세션 정리 완료")
    
    return deleted_count

def get_session_stats() -> Dict[str, Any]:
    """
    세션 통계를 조회합니다.
    
    Returns:
        Dict[str, Any]: 세션 통계 정보
    """
    total_sessions = len(sessions)
    total_messages = sum(len(session.messages) for session in sessions.values())
    
    if total_sessions > 0:
        avg_messages_per_session = total_messages / total_sessions
    else:
        avg_messages_per_session = 0
    
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "avg_messages_per_session": round(avg_messages_per_session, 2),
        "last_cleanup": datetime.now().isoformat()
    } 