from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# 시간 파서 및 웹 검색 서비스 import
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.utils.time_parser import time_parser
    from src.services.websearch_service import websearch_service
    TIME_PARSER_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"시간 파서 또는 웹 검색 서비스를 불러올 수 없습니다: {e}")
    TIME_PARSER_AVAILABLE = False

# FastAPI 앱 생성
app = FastAPI(
    title="Ollama Conversation Interface",
    description="FastAPI 기반 Ollama 대화형 인터페이스",
    version="1.0.0"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama 서버 설정
OLLAMA_BASE_URL = "http://1.237.52.240:11434"

# 사용 가능한 모델 목록
AVAILABLE_MODELS = [
    {"name": "gemma3:12b-it-qat", "size": "8.9 GB", "id": "5d4fa005e7bb"},
    {"name": "llama3.1:8b", "size": "4.9 GB", "id": "46e0c10c039e"},
    {"name": "llama3.2-vision:11b-instruct-q4_K_M", "size": "7.8 GB", "id": "6f2f9757ae97"},    
    {"name": "qwen3:14b-q8_0", "size": "15 GB", "id": "304bf7349c71"},
    {"name": "deepseek-r1:14b", "size": "9.0 GB", "id": "c333b7232bdb"},
    {"name": "deepseek-v2:16b-lite-chat-q8_0", "size": "16 GB", "id": "1d62ef756269"},        
]

# Pydantic 모델 정의
class ChatRequest(BaseModel):
    model: str
    message: str
    session_id: Optional[str] = None
    system: Optional[str] = "You are a helpful assistant."
    options: Optional[Dict[str, Any]] = {}

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_active: str
    message_count: int
    preview: str

class Message(BaseModel):
    role: str
    content: str
    timestamp: str
    model: Optional[str] = None

class SessionData(BaseModel):
    session_id: str
    messages: List[Message]
    created_at: str
    last_active: str

# 메모리 기반 대화 세션 저장 (실제 환경에서는 데이터베이스 사용 권장)
chat_sessions = {}

def create_session_id():
    """새로운 세션 ID 생성"""
    return f"session_{int(time.time() * 1000)}"

def get_or_create_session(session_id=None):
    """세션 가져오기 또는 생성"""
    if not session_id or session_id not in chat_sessions:
        session_id = create_session_id()
        chat_sessions[session_id] = {
            'messages': [],
            'created_at': datetime.now(),
            'last_active': datetime.now()
        }
    else:
        chat_sessions[session_id]['last_active'] = datetime.now()
    
    return session_id

def add_message_to_session(session_id, role, content, model=None):
    """세션에 메시지 추가"""
    if session_id in chat_sessions:
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'model': model
        }
        chat_sessions[session_id]['messages'].append(message)

def build_conversation_prompt(session_id, new_message, system_prompt=None):
    """대화 히스토리를 포함한 프롬프트 구성"""
    if session_id not in chat_sessions:
        return new_message
    
    messages = chat_sessions[session_id]['messages']
    
    # 시스템 프롬프트가 있으면 시작에 추가
    conversation = ""
    if system_prompt:
        conversation += f"System: {system_prompt}\n\n"
    
    # 시간 정보 파싱 및 웹 검색
    web_search_context = ""
    time_info = None
    if TIME_PARSER_AVAILABLE:
        try:
            # 시간 정보 파싱
            time_info = time_parser.parse_time_expressions(new_message)
            time_context = time_parser.get_time_context(new_message)
            
            # 시간 정보가 있으면 시스템 프롬프트에 시간 지시사항 추가
            if time_info.get('time_expressions'):
                current_date = time_info['current_time'].strftime('%Y년 %m월 %d일')
                time_instruction = f"\nSystem: 현재 시간은 {current_date}입니다. 시간 관련 질문에 답할 때는 이 날짜를 기준으로 답변하세요.\n\n"
                conversation += time_instruction
            
            # 웹 검색 실행
            if time_info['time_expressions']:
                logger.info(f"시간 정보 발견: {time_info['time_expressions']}")
                web_search_result = websearch_service.search_web(new_message)
                if web_search_result and "검색 중 오류가 발생했습니다" not in web_search_result:
                    # 시간 정보를 더 명확하게 전달
                    current_date = time_info['current_time'].strftime('%Y년 %m월 %d일')
                    web_search_context = f"\n\n[중요: 현재 시간은 {current_date}입니다]\n[실시간 웹 검색 결과]\n{web_search_result}\n\n[지시사항: 위의 웹 검색 결과를 바탕으로 사용자의 질문에 답변하세요. 검색 결과에 관련 정보가 있으면 그것을 활용하고, 없으면 그 사실을 명시하세요.]\n"
                    logger.info("웹 검색 결과를 프롬프트에 추가했습니다.")
        except Exception as e:
            logger.error(f"시간 파싱 또는 웹 검색 중 오류: {e}")
    
    # 이전 대화 히스토리 추가
    for msg in messages[-10:]:  # 최근 10개 메시지만 포함 (컨텍스트 길이 제한)
        if msg['role'] == 'user':
            conversation += f"Human: {msg['content']}\n\n"
        elif msg['role'] == 'assistant':
            conversation += f"Assistant: {msg['content']}\n\n"
    
    # 새로운 사용자 메시지 추가
    if web_search_context:
        conversation += f"Human: {new_message}\n\n{web_search_context}\nAssistant: "
    else:
        conversation += f"Human: {new_message}\n\nAssistant: "
    
    return conversation

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("app.html", {"request": request})

@app.get("/api/models")
async def get_models():
    """사용 가능한 모델 목록 반환"""
    try:
        # Ollama에서 실제 모델 목록 가져오기
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            ollama_models = response.json().get('models', [])
            # 실제 설치된 모델과 미리 정의된 모델 정보 매칭
            available_models = []
            for model_info in AVAILABLE_MODELS:
                for ollama_model in ollama_models:
                    if model_info['name'] == ollama_model['name']:
                        available_models.append({
                            **model_info,
                            'modified_at': ollama_model.get('modified_at'),
                            'size_bytes': ollama_model.get('size')
                        })
                        break
            return {"models": available_models}
        else:
            # Ollama 서버 연결 실패시 기본 모델 목록 반환
            return {"models": AVAILABLE_MODELS}
    except Exception as e:
        logger.error(f"모델 목록 가져오기 실패: {e}")
        return {"models": AVAILABLE_MODELS}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """대화형 채팅 API (스트리밍)"""
    try:
        # 세션 관리
        session_id = get_or_create_session(request.session_id)
        
        # 사용자 메시지를 세션에 추가
        user_message = request.message
        add_message_to_session(session_id, 'user', user_message, request.model)
        
        # 대화 히스토리를 포함한 프롬프트 구성
        system_prompt = request.system
        conversation_prompt = build_conversation_prompt(session_id, user_message, system_prompt)
        
        # Ollama API 요청 데이터 구성
        ollama_request = {
            "model": request.model,
            "prompt": conversation_prompt,
            "stream": True,  # 스트리밍 활성화
            "options": request.options or {}
        }
        
        logger.info(f"대화 요청: {ollama_request['model']} 모델, 세션: {session_id}")
        
        def generate():
            assistant_response = ""
            try:
                # Ollama API 호출
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json=ollama_request,
                    stream=True,
                    timeout=120
                )
                
                if response.status_code != 200:
                    error_msg = f'Ollama 서버 오류: {response.status_code}'
                    yield f"data: {json.dumps({'error': error_msg, 'session_id': session_id})}\n\n"
                    return
                
                # 스트리밍 응답 처리
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            # 세션 ID 포함
                            chunk['session_id'] = session_id
                            yield f"data: {json.dumps(chunk)}\n\n"
                            
                            # 응답 텍스트 누적
                            if chunk.get('response'):
                                assistant_response += chunk.get('response')
                            
                            # 생성 완료 체크
                            if chunk.get('done', False):
                                # 어시스턴트 응답을 세션에 추가
                                add_message_to_session(session_id, 'assistant', assistant_response, request.model)
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
            except requests.exceptions.Timeout:
                yield f"data: {json.dumps({'error': '요청 시간 초과', 'session_id': session_id})}\n\n"
            except requests.exceptions.ConnectionError:
                yield f"data: {json.dumps({'error': 'Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인해주세요.', 'session_id': session_id})}\n\n"
            except Exception as e:
                logger.error(f"생성 중 오류: {e}")
                yield f"data: {json.dumps({'error': f'서버 오류: {str(e)}', 'session_id': session_id})}\n\n"
        
        return StreamingResponse(
            generate(), 
            media_type='text/plain; charset=utf-8',
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except Exception as e:
        logger.error(f"채팅 요청 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/api/sessions")
async def get_sessions():
    """활성 세션 목록 반환"""
    try:
        sessions = []
        for session_id, session_data in chat_sessions.items():
            sessions.append({
                'session_id': session_id,
                'created_at': session_data['created_at'].isoformat(),
                'last_active': session_data['last_active'].isoformat(),
                'message_count': len(session_data['messages']),
                'preview': session_data['messages'][0]['content'][:50] + '...' if session_data['messages'] else 'Empty conversation'
            })
        
        # 최근 활동 순으로 정렬
        sessions.sort(key=lambda x: x['last_active'], reverse=True)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"세션 목록 가져오기 실패: {e}")
        return {"sessions": []}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """특정 세션의 대화 히스토리 반환"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        session_data = chat_sessions[session_id]
        return {
            "session_id": session_id,
            "messages": session_data['messages'],
            "created_at": session_data['created_at'].isoformat(),
            "last_active": session_data['last_active'].isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 가져오기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """세션 삭제"""
    try:
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            return {"message": "세션이 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.post("/api/sessions")
async def create_session():
    """새 세션 생성"""
    try:
        session_id = create_session_id()
        chat_sessions[session_id] = {
            'messages': [],
            'created_at': datetime.now(),
            'last_active': datetime.now()
        }
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/api/health")
async def health_check():
    """서버 및 Ollama 연결 상태 확인"""
    try:
        # Ollama 서버 연결 테스트
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        ollama_status = response.status_code == 200
        
        return {
            "server": "running",
            "ollama_connected": ollama_status,
            "ollama_url": OLLAMA_BASE_URL,
            "active_sessions": len(chat_sessions),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "server": "running",
            "ollama_connected": False,
            "ollama_url": OLLAMA_BASE_URL,
            "active_sessions": len(chat_sessions),
            "error": str(e),
            "timestamp": time.time()
        }

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=404, content={"error": "엔드포인트를 찾을 수 없습니다."})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=500, content={"error": "내부 서버 오류"})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Ollama 대화형 인터페이스 서버 시작...")
    print("📍 서버 주소: http://1.237.52.240:11040")
    print("🔗 Ollama 서버: http://1.237.52.240:11434")
    print("💬 대화 기능이 활성화되었습니다!")
    print("⚠️  Ollama가 실행 중인지 확인해주세요!")
    
    uvicorn.run(app, host="0.0.0.0", port=11040)