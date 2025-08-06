import time
import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.models.schemas import Message, SessionData

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self):
        self.chat_sessions: Dict[str, SessionData] = {}
    
    def create_session_id(self) -> str:
        """새로운 세션 ID 생성"""
        return f"session_{int(time.time() * 1000)}"
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """세션 가져오기 또는 생성"""
        if not session_id or session_id not in self.chat_sessions:
            session_id = self.create_session_id()
            self.chat_sessions[session_id] = SessionData(
                session_id=session_id,
                messages=[],
                created_at=datetime.now().isoformat(),
                last_active=datetime.now().isoformat()
            )
        else:
            self.chat_sessions[session_id].last_active = datetime.now().isoformat()
        
        # 빈 세션 정리
        self.cleanup_empty_sessions()
        
        return session_id
    
    def add_message_to_session(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        model: Optional[str] = None,
        sources: Optional[List[Dict]] = None
    ) -> bool:
        """세션에 메시지 추가"""
        if session_id not in self.chat_sessions:
            return False
        
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            model=model,
            sources=sources
        )
        
        self.chat_sessions[session_id].messages.append(message)
        self.chat_sessions[session_id].last_active = datetime.now().isoformat()
        
        return True
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """세션 데이터 반환"""
        return self.chat_sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Dict]:
        """모든 세션 목록 반환 (빈 세션 제외)"""
        sessions = []
        for session_id, session_data in self.chat_sessions.items():
            # 메시지가 없는 빈 세션은 제외
            if not session_data.messages:
                continue
                
            # 첫 번째 메시지의 내용을 미리보기로 사용
            first_message = session_data.messages[0]
            preview = first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
            
            # 미리보기가 비어있거나 "Empty conversation"인 경우 제외
            if not preview or preview.strip() == "" or "Empty conversation" in preview:
                continue
            
            sessions.append({
                'session_id': session_id,
                'created_at': session_data.created_at.isoformat(),
                'last_active': session_data.last_active.isoformat(),
                'message_count': len(session_data.messages),
                'preview': preview
            })
        
        # 최근 활동 순으로 정렬
        sessions.sort(key=lambda x: x['last_active'], reverse=True)
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in self.chat_sessions:
            del self.chat_sessions[session_id]
            logger.info(f"세션 '{session_id}'가 삭제되었습니다.")
            return True
        return False
    
    def build_conversation_prompt(self, session_id: str, new_message: str, system_prompt: Optional[str] = None) -> str:
        """대화 히스토리를 포함한 프롬프트 구성"""
        if session_id not in self.chat_sessions:
            return new_message
        
        messages = self.chat_sessions[session_id].messages
        
        # 시스템 프롬프트가 있으면 시작에 추가
        conversation = ""
        if system_prompt:
            conversation += f"System: {system_prompt}\n\n"
        
        # 이전 대화 히스토리 추가 (최근 10개 메시지만)
        for msg in messages[-10:]:
            if msg.role == 'user':
                conversation += f"Human: {msg.content}\n\n"
            elif msg.role == 'assistant':
                conversation += f"Assistant: {msg.content}\n\n"
        
        # 새로운 사용자 메시지 추가
        conversation += f"Human: {new_message}\n\nAssistant: "
        
        return conversation
    
    def get_active_session_count(self) -> int:
        """활성 세션 수 반환"""
        return len(self.chat_sessions)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """오래된 세션 정리"""
        current_time = datetime.now()
        sessions_to_delete = []
        
        for session_id, session_data in self.chat_sessions.items():
            time_diff = current_time - session_data.last_active
            if time_diff.total_seconds() > max_age_hours * 3600:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        logger.info(f"{len(sessions_to_delete)}개의 오래된 세션이 정리되었습니다.")
        return len(sessions_to_delete)
    
    def cleanup_empty_sessions(self) -> int:
        """빈 세션 정리"""
        sessions_to_delete = []
        
        for session_id, session_data in self.chat_sessions.items():
            if not session_data.messages:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        logger.info(f"{len(sessions_to_delete)}개의 빈 세션이 정리되었습니다.")
        return len(sessions_to_delete)

# 싱글톤 인스턴스
session_service = SessionService() 