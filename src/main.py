from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import time
import logging
import os

from src.config.settings import settings
from src.utils.env_loader import validate_settings
from src.models.schemas import HealthResponse, ModelsResponse, ModelInfo
from src.services.session_service import session_service
from src.services.document_service import document_service
from src.api.chat_router import chat_router
from src.api.document_router import document_router
from src.api.config_router import config_router

# FastAPI 앱 생성
app = FastAPI(
    title="Ollama RAG Interface",
    description="LangChain과 RAG를 사용한 Ollama 웹 인터페이스",
    version="2.0.0"
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

# 라우터 등록
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(config_router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("app.html", {"request": request})

@app.get("/api/models")
async def get_models():
    """사용 가능한 모델 목록 반환"""
    try:
        # Ollama에서 실제 모델 목록 가져오기
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            ollama_models = response.json().get('models', [])
            # 실제 설치된 모델과 미리 정의된 모델 정보 매칭
            available_models = []
            for model_info in settings.available_models:
                for ollama_model in ollama_models:
                    if model_info['name'] == ollama_model['name']:
                        available_models.append(ModelInfo(
                            name=model_info['name'],
                            size=model_info['size'],
                            id=model_info['id'],
                            modified_at=ollama_model.get('modified_at'),
                            size_bytes=ollama_model.get('size')
                        ))
                        break
            return ModelsResponse(models=available_models)
        else:
            # Ollama 서버 연결 실패시 기본 모델 목록 반환
            models = [ModelInfo(**model) for model in settings.available_models]
            return ModelsResponse(models=models)
    except Exception as e:
        logger.error(f"모델 목록 가져오기 실패: {e}")
        models = [ModelInfo(**model) for model in settings.available_models]
        return ModelsResponse(models=models)

@app.get("/api/sessions")
async def get_sessions():
    """활성 세션 목록 반환"""
    try:
        # 빈 세션 자동 정리
        session_service.cleanup_empty_sessions()
        
        sessions = session_service.get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"세션 목록 가져오기 실패: {e}")
        return {"sessions": []}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """특정 세션의 대화 히스토리 반환"""
    try:
        session_data = session_service.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {
            "session_id": session_data.session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "model": msg.model,
                    "sources": msg.sources
                }
                for msg in session_data.messages
            ],
            "created_at": session_data.created_at.isoformat(),
            "last_active": session_data.last_active.isoformat()
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
        success = session_service.delete_session(session_id)
        if success:
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
        session_id = session_service.create_session_id()
        session_service.get_or_create_session(session_id)
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/api/health")
async def health_check():
    """서버 및 Ollama 연결 상태 확인"""
    try:
        # Ollama 서버 연결 테스트
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        ollama_status = response.status_code == 200
        
        # 벡터 저장소 상태 확인
        vectorstore_status = document_service.get_vectorstore_status()
        
        return HealthResponse(
            server="running",
            ollama_connected=ollama_status,
            ollama_url=settings.ollama_base_url,
            active_sessions=session_service.get_active_session_count(),
            vectorstore_status=vectorstore_status,
            timestamp=time.time()
        )
    except Exception as e:
        return HealthResponse(
            server="running",
            ollama_connected=False,
            ollama_url=settings.ollama_base_url,
            active_sessions=session_service.get_active_session_count(),
            vectorstore_status="error",
            timestamp=time.time(),
            error=str(e)
        )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=404, content={"error": "엔드포인트를 찾을 수 없습니다."})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=500, content={"error": "내부 서버 오류"})

if __name__ == "__main__":
    import uvicorn
    
    # 설정 파일 검증
    print("🔍 env.settings 파일 검증 중...")
    if not validate_settings():
        print("⚠️  env.settings 파일에 문제가 있습니다. 기본 설정을 사용합니다.")
    
    # 서버 시작 시 빈 세션 정리
    print("🧹 기존 빈 세션 정리 중...")
    cleaned_count = session_service.cleanup_empty_sessions()
    if cleaned_count > 0:
        print(f"✅ {cleaned_count}개의 빈 세션이 정리되었습니다.")
    
    print("🚀 Ollama RAG 인터페이스 서버 시작...")
    print("📍 서버 주소: http://1.237.52.240:11040")
    print("🔗 Ollama 서버: http://1.237.52.240:11434")
    print("💬 RAG 기능이 활성화되었습니다!")
    print("📚 LangChain과 ChromaDB가 통합되었습니다!")
    print("⚙️  env.settings 파일에서 설정을 로드합니다!")
    print("⚠️  Ollama가 실행 중인지 확인해주세요!")
    
    uvicorn.run(app, host=settings.host, port=settings.port) 