"""
Ollama 대화형 인터페이스 - 메인 실행 파일
새로운 모듈화된 구조를 사용합니다.
"""

import warnings
# PyTorch FutureWarning 억제
warnings.filterwarnings('ignore', category=FutureWarning)

import uvicorn
import argparse
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from src.main import app
except ImportError as e:
    print(f"❌ 모듈 import 오류: {e}")
    print(f"📁 현재 디렉토리: {current_dir}")
    print(f"🐍 Python 경로: {sys.path}")
    sys.exit(1)

def create_custom_log_config(debug_mode: bool):
    """
    uvicorn용 커스텀 로그 설정을 생성합니다.
    
    Args:
        debug_mode: 디버그 모드 여부
        
    Returns:
        dict: uvicorn 로그 설정
    """
    if debug_mode:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "access": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "app_debug.log",
                    "mode": "a",
                    "maxBytes": 10*1024*1024,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8"
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                },
                "access_file": {
                    "formatter": "access",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "app_debug.log",
                    "mode": "a",
                    "maxBytes": 10*1024*1024,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8"
                }
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default", "file"],
                    "level": "WARNING",
                    "propagate": False
                },
                "uvicorn.error": {
                    "handlers": ["default", "file"],
                    "level": "WARNING",
                    "propagate": False
                },
                "uvicorn.access": {
                    "handlers": ["access", "access_file"],
                    "level": "INFO",
                    "propagate": False
                },
                "fastapi": {
                    "handlers": ["default", "file"],
                    "level": "INFO",
                    "propagate": False
                },
                "watchfiles": {
                    "handlers": ["default", "file"],
                    "level": "WARNING",
                    "propagate": False
                }
            },
            "root": {
                "handlers": ["default", "file"],
                "level": "DEBUG"
            }
        }
    else:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                }
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": "ERROR",
                    "propagate": False
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": "ERROR",
                    "propagate": False
                },
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": "ERROR",
                    "propagate": False
                },
                "fastapi": {
                    "handlers": ["default"],
                    "level": "ERROR",
                    "propagate": False
                }
            },
            "root": {
                "handlers": ["default"],
                "level": "ERROR"
            }
        }

def setup_logging(debug_mode: bool):
    """
    로깅 설정을 구성합니다. 
    
    Args:
        debug_mode: 디버그 모드 여부
    """
    if debug_mode:
        # 기존 로깅 설정 초기화
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # 디버그 모드: 상세한 로그 설정
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                RotatingFileHandler(
                    'app_debug.log', 
                    mode='a', 
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5,
                    encoding='utf-8'
                )
            ],
            force=True
        )
        
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 모든 debug 로거 설정
        debug_loggers = [
            # 디버그 로거 목록
            "chat_debug",
            "weather_debug",
            "stock_debug",
            "web_search_debug",
            "weather_api_debug",
            "stock_api_debug",
            "web_search_api_debug",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "fastapi",
            "watchfiles",
            "src",
            "src.api",
            "src.api.endpoints",
            "src.services"
        ]
        
        for logger_name in debug_loggers:
            logger = logging.getLogger(logger_name)
            if logger_name == "watchfiles":
                logger.setLevel(logging.WARNING)  # watchfiles는 WARNING 레벨로 설정
            elif logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
                logger.setLevel(logging.WARNING)  # uvicorn 로그는 WARNING 레벨로 설정
            else:
                logger.setLevel(logging.DEBUG)
            logger.propagate = True  # 부모 로거로 전파
            
            # 기존 핸들러 제거
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
        
        print("🔍 Debug 모드로 실행 중...")
        print("📝 상세한 로그가 콘솔과 app_debug.log 파일에 기록됩니다.")
        print(f"📁 로그 파일 위치: {os.path.abspath('app_debug.log')}")
        
    else:
        # 일반 모드: 로그 비활성화
        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True
        )
        
        # uvicorn 로그도 비활성화
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_logger.setLevel(logging.ERROR)
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        uvicorn_access_logger.setLevel(logging.ERROR)
        uvicorn_error_logger = logging.getLogger("uvicorn.error")
        uvicorn_error_logger.setLevel(logging.ERROR)

def main():
    """메인 실행 함수"""
    try:
        parser = argparse.ArgumentParser(description="Ollama 대화형 인터페이스")
        parser.add_argument(
            "-d", "--debug",
            action="store_true",
            help="디버그 모드로 실행 (상세한 로그 출력)"
        )
        
        args = parser.parse_args()
        
        # 로깅 설정
        setup_logging(args.debug)
        
        # 서버 실행 설정
        log_level = "info" if args.debug else "error"  # debug 대신 info 사용
        
        # 환경 설정에서 서비스 정보 가져오기
        try:
            from src.config.settings import get_settings
            settings = get_settings()
        except Exception as e:
            print(f"❌ 설정 로드 오류: {e}")
            sys.exit(1)
        
        print(f"🚀 Ollama 대화형 인터페이스 시작 중...")
        print(f"🌐 서버 주소: {settings.service_url}")
        print(f"🔧 로그 레벨: {log_level}")
        
        if not args.debug:
            print("💡 상세한 로그를 보려면 '-d' 옵션을 사용하세요.")
        
        # 커스텀 로그 설정 생성
        log_config = create_custom_log_config(args.debug)
        
        # 개발 서버 실행
        uvicorn.run(
            "src.main:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            reload_dirs=["src", "templates"],  # 감시할 디렉토리 명시
            log_level=log_level,
            access_log=args.debug,  # 디버그 모드에서만 access 로그 활성화
            log_config=log_config  # 커스텀 로그 설정 사용
        )
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 애플리케이션 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()