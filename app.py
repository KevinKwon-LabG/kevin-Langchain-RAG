"""
Ollama 대화형 인터페이스 - 메인 실행 파일
새로운 모듈화된 구조를 사용합니다.
"""

import uvicorn
from src.main import app

if __name__ == "__main__":
    # 개발 서버 실행
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=11040,
        reload=True,
        log_level="info"
    )