"""
파일 시스템 관련 API 엔드포인트
파일 읽기, 쓰기, 목록 조회, 검색 등을 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.models.schemas import FileWriteRequest, FileSearchRequest
from src.services.integrated_mcp_client import OptimizedIntegratedMCPClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/files", tags=["File"])

@router.get("/")
async def list_files(directory: str = Query(".", description="조회할 디렉토리 경로")):
    """
    디렉토리 내 파일 목록을 조회합니다.
    
    Args:
        directory: 조회할 디렉토리 경로 (기본값: 현재 디렉토리)
    
    Returns:
        파일 및 디렉토리 목록
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.list_files(directory)
            return result
    except Exception as e:
        logger.error(f"파일 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 목록 조회 중 오류가 발생했습니다.")

@router.get("/{file_path:path}")
async def read_file(file_path: str):
    """
    파일 내용을 읽어옵니다.
    
    Args:
        file_path: 읽을 파일 경로
    
    Returns:
        파일 내용
    
    Raises:
        HTTPException: 파일을 찾을 수 없거나 읽기 권한이 없는 경우
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.read_file(file_path)
            return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"파일 읽기 권한이 없습니다: {file_path}")
    except Exception as e:
        logger.error(f"파일 읽기 중 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 읽기 중 오류가 발생했습니다.")

@router.post("/{file_path:path}")
async def write_file(file_path: str, request: FileWriteRequest):
    """
    파일에 내용을 씁니다.
    
    Args:
        file_path: 쓸 파일 경로
        request: 파일 쓰기 요청 (내용 포함)
    
    Returns:
        쓰기 결과
    
    Raises:
        HTTPException: 쓰기 권한이 없거나 디렉토리가 존재하지 않는 경우
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.write_file(file_path, request.content)
            return result
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"파일 쓰기 권한이 없습니다: {file_path}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"디렉토리를 찾을 수 없습니다: {file_path}")
    except Exception as e:
        logger.error(f"파일 쓰기 중 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 쓰기 중 오류가 발생했습니다.")

@router.get("/search/{pattern}")
async def search_files(
    pattern: str,
    directory: str = Query(".", description="검색할 디렉토리 경로")
):
    """
    파일명 패턴으로 파일을 검색합니다.
    
    Args:
        pattern: 검색할 파일명 패턴 (예: *.txt, *.py)
        directory: 검색할 디렉토리 경로 (기본값: 현재 디렉토리)
    
    Returns:
        검색 결과 파일 목록
    """
    try:
        async with OptimizedIntegratedMCPClient() as client:
            result = await client.search_files(pattern, directory)
            return result
    except Exception as e:
        logger.error(f"파일 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 검색 중 오류가 발생했습니다.")

@router.delete("/{file_path:path}")
async def delete_file(file_path: str):
    """
    파일을 삭제합니다.
    
    Args:
        file_path: 삭제할 파일 경로
    
    Returns:
        삭제 결과
    
    Raises:
        HTTPException: 파일을 찾을 수 없거나 삭제 권한이 없는 경우
    """
    try:
        # 파일 삭제는 MCP 클라이언트에 구현되어 있지 않으므로
        # 여기서는 기본적인 파일 시스템 작업으로 구현
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"message": f"파일이 삭제되었습니다: {file_path}"}
        else:
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"파일 삭제 권한이 없습니다: {file_path}")
    except Exception as e:
        logger.error(f"파일 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 삭제 중 오류가 발생했습니다.")

@router.get("/info/{file_path:path}")
async def get_file_info(file_path: str):
    """
    파일 정보를 조회합니다.
    
    Args:
        file_path: 조회할 파일 경로
    
    Returns:
        파일 크기, 수정 시간, 권한 등 파일 정보
    """
    try:
        import os
        import stat
        from datetime import datetime
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        stat_info = os.stat(file_path)
        
        return {
            "file_path": file_path,
            "size": stat_info.st_size,
            "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "created_time": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            "is_file": stat.S_ISREG(stat_info.st_mode),
            "is_directory": stat.S_ISDIR(stat_info.st_mode),
            "permissions": oct(stat_info.st_mode)[-3:],
            "owner": stat_info.st_uid,
            "group": stat_info.st_gid
        }
    except Exception as e:
        logger.error(f"파일 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 정보 조회 중 오류가 발생했습니다.") 