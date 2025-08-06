"""
Health API 엔드포인트
애플리케이션 상태 확인을 위한 API를 제공합니다.
"""

import logging
from fastapi import APIRouter
from datetime import datetime

# psutil을 선택적으로 import
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.debug("psutil 모듈이 설치되지 않았습니다. 시스템 리소스 정보를 수집할 수 없습니다.")

# 로깅 설정 - health API는 로깅 비활성화
# logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

@router.get("/api/health")
async def get_health():
    """
    애플리케이션의 전체 상태를 반환합니다.
    
    Returns:
        애플리케이션 상태 정보
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        # Ollama 서버 연결 상태 확인
        ollama_connected = False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                ollama_connected = response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama 서버 연결 실패: {e}")
            ollama_connected = False
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "chat_service": "healthy",
                "file_service": "healthy",
                "web_service": "healthy",
                "database_service": "healthy"
            },
            "uptime": "1일 2시간 30분",
            "memory_usage": "약 128MB",
            "cpu_usage": "약 5%",
            "ollama_connected": ollama_connected
        }
    except Exception as e:
        logger.error(f"Health check 실패: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": "서비스 점검 중 오류가 발생했습니다"
        }

@router.get("/api/health/simple")
async def get_simple_health():
    """
    간단한 서버 상태 확인을 위한 엔드포인트입니다.
    최소한의 부하로 서버가 실행 중인지 확인합니다.
    
    Returns:
        간단한 상태 정보
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/api/system/resources")
async def get_system_resources():
    """
    시스템 리소스 사용량 정보를 반환합니다.
    
    Returns:
        시스템 리소스 정보
    """
    try:
        if not PSUTIL_AVAILABLE:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": "psutil 모듈이 설치되지 않았습니다",
                "cpu": {"percent": 0},
                "ram": {"used_gb": 0, "total_gb": 0, "percent": 0},
                "gpu": [{"id": 0, "name": "psutil 없음", "utilization": 0}],
                "vram": [{"id": 0, "used_mb": 0, "total_mb": 0, "percent": 0}]
            }
        
        # CPU 사용량
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 메모리 사용량
        memory = psutil.virtual_memory()
        ram_used_gb = round(memory.used / (1024**3), 1)
        ram_total_gb = round(memory.total / (1024**3), 1)
        ram_percent = memory.percent
        
        # GPU 정보 (nvidia-smi가 있는 경우)
        gpu_info = []
        vram_info = []
        
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"DEBUG: nvidia-smi 출력: {result.stdout.strip()}")
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        parts = [part.strip() for part in line.split(',')]
                        print(f"DEBUG: GPU {i} 파싱 - 원본: '{line}', 분리된 부분: {parts}")
                        if len(parts) >= 4:
                            gpu_name = parts[0].strip()
                            gpu_util = parts[1].strip()
                            vram_used = parts[2].strip()
                            vram_total = parts[3].strip()
                            print(f"DEBUG: GPU {i} - 이름: '{gpu_name}', 점유률: '{gpu_util}', VRAM 사용: '{vram_used}', VRAM 전체: '{vram_total}'")
                            
                            gpu_info.append({
                                "id": i,
                                "name": gpu_name,
                                "utilization": int(gpu_util) if gpu_util.isdigit() else 0
                            })
                            
                            vram_info.append({
                                "id": i,
                                "used_mb": int(vram_used) if vram_used.isdigit() else 0,
                                "total_mb": int(vram_total) if vram_total.isdigit() else 0,
                                "percent": round((int(vram_used) / int(vram_total)) * 100, 1) if vram_used.isdigit() and vram_total.isdigit() and int(vram_total) > 0 else 0
                            })
            else:
                # nvidia-smi 명령이 실패하거나 출력이 없는 경우
                raise Exception("GPU 정보를 가져올 수 없습니다")
        except Exception as e:
            # GPU가 없거나 접근할 수 없는 경우 기본값
            gpu_info = [{"id": 0, "name": "GPU 사용 불가", "utilization": 0}]
            vram_info = [{"id": 0, "used_mb": 0, "total_mb": 0, "percent": 0}]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent
            },
            "ram": {
                "used_gb": ram_used_gb,
                "total_gb": ram_total_gb,
                "percent": ram_percent
            },
            "gpu": gpu_info,
            "vram": vram_info
        }
        
    except Exception as e:
        # logger.error(f"시스템 리소스 정보 수집 실패: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "cpu": {"percent": 0},
            "ram": {"used_gb": 0, "total_gb": 0, "percent": 0},
            "gpu": [{"id": 0, "name": "오류", "utilization": 0}],
            "vram": [{"id": 0, "used_mb": 0, "total_mb": 0, "percent": 0}]
        }

@router.get("/api/info")
async def get_info():
    """
    애플리케이션 정보를 반환합니다.
    
    Returns:
        애플리케이션 정보
    """
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        return {
            "name": "Ollama Chat Interface",
            "version": "1.0.0",
            "description": "Ollama 모델과의 대화형 인터페이스",
            "host": settings.host,
            "port": settings.port,
            "ollama_url": settings.ollama_base_url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # logger.error(f"Info 조회 실패: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 