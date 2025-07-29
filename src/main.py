"""
메인 FastAPI 애플리케이션
Ollama 대화형 인터페이스의 진입점입니다.
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime


# API 엔드포인트 라우터들 import
from src.api.endpoints import chat, health, models, sessions, settings, mcp


# 로깅 설정
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# FastAPI 앱 생성
app = FastAPI(
    title="Ollama Conversation Interface",
    description="FastAPI 기반 Ollama 대화형 인터페이스 - 주식, 날씨, 웹 검색, 파일 시스템, 데이터베이스 통합 서비스",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# API 라우터 등록 - 각 기능별 라우터를 FastAPI 앱에 등록하여 모듈화된 API 구조 구성
app.include_router(chat.router, prefix="", tags=["Chat"]) # 채팅 기능 라우터 - Ollama 모델과의 대화, 세션 관리 등
app.include_router(health.router, prefix="", tags=["Health"]) # 헬스 체크 라우터 - 애플리케이션 상태 확인, 서비스 모니터링, 시스템 정보 등
app.include_router(models.router, prefix="", tags=["Models"]) # 모델 관리 라우터 - Ollama 모델 목록 조회, 모델 상세 정보, 모델 다운로드/삭제 등
app.include_router(sessions.router, prefix="", tags=["Sessions"]) # 세션 관리 라우터 - 채팅 세션 생성, 조회, 삭제, 제목 업데이트 등
app.include_router(settings.router, prefix="", tags=["Settings"]) # 설정 관리 라우터 - 설정 조회, 리로드, 검증, 프리셋 관리 등
app.include_router(mcp.router, prefix="", tags=["MCP"]) # MCP 서버 라우터 - 외부 MCP 서버와의 통신, 모델 완성, 임베딩 등


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    메인 페이지를 반환합니다.
    
    Args:
        request: FastAPI 요청 객체
    
    Returns:
        HTML 응답
    """
    return templates.TemplateResponse("app.html", {"request": request})





@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """
    404 에러 핸들러
    
    Args:
        request: FastAPI 요청 객체
        exc: HTTP 예외 객체
    
    Returns:
        JSON 응답
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": "요청한 리소스를 찾을 수 없습니다.",
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """
    500 에러 핸들러
    
    Args:
        request: FastAPI 요청 객체
        exc: HTTP 예외 객체
    
    Returns:
        JSON 응답
    """
    logger.error(f"내부 서버 오류: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "내부 서버 오류가 발생했습니다.",
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    HTTP 요청 로깅 미들웨어
    
    Args:
        request: FastAPI 요청 객체
        call_next: 다음 미들웨어 호출 함수
    
    Returns:
        응답 객체
    """
    start_time = datetime.now()
    
    # 요청 로깅
    logger.info(f"요청 시작: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # 응답 로깅
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"요청 완료: {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}초)")
    
    return response


if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=11040,
        reload=True,
        log_level="info"
    ) 