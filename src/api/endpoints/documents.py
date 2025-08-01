"""
문서 관리 API 엔드포인트
파일 업로드, 목록 조회, 삭제 기능을 제공합니다.
"""

import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# 업로드 디렉토리 설정
UPLOAD_DIR = "static/RAG"
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.doc', '.docx', '.md', '.json', '.csv', '.xlsx', '.xls'}

class DocumentInfo(BaseModel):
    filename: str
    size: int
    upload_time: str
    file_type: str

def ensure_upload_dir():
    """업로드 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_file_extension(filename: str) -> str:
    """파일 확장자를 반환합니다."""
    return os.path.splitext(filename)[1].lower()

def is_allowed_file(filename: str) -> bool:
    """허용된 파일 형식인지 확인합니다."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

@router.get("/api/documents", response_model=List[DocumentInfo])
async def get_documents():
    """
    업로드된 문서 목록을 반환합니다.
    """
    try:
        ensure_upload_dir()
        documents = []
        
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                documents.append(DocumentInfo(
                    filename=filename,
                    size=stat.st_size,
                    upload_time=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    file_type=get_file_extension(filename)
                ))
        
        # 파일명 순으로 정렬
        documents.sort(key=lambda x: x.filename)
        return documents
        
    except Exception as e:
        logger.error(f"문서 목록 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 목록을 불러오는 중 오류가 발생했습니다.")

@router.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    문서를 업로드합니다.
    """
    try:
        ensure_upload_dir()
        
        # 파일 형식 검증
        if not is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 파일 크기 검증 (50MB 제한)
        if file.size and file.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 50MB를 초과할 수 없습니다.")
        
        # 파일명 중복 처리
        filename = file.filename
        file_path = os.path.join(UPLOAD_DIR, filename)
        counter = 1
        
        while os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            counter += 1
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"문서 업로드 완료: {filename}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "문서가 성공적으로 업로드되었습니다.",
                "filename": filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 업로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 업로드 중 오류가 발생했습니다.")

@router.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """
    문서를 삭제합니다.
    """
    try:
        ensure_upload_dir()
        
        # 경로 순회 공격 방지
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
        
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail="파일이 아닙니다.")
        
        # 파일 삭제
        os.remove(file_path)
        
        logger.info(f"문서 삭제 완료: {filename}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "문서가 성공적으로 삭제되었습니다.",
                "filename": filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 삭제 중 오류가 발생했습니다.")

@router.get("/api/documents/{filename}/download")
async def download_document(filename: str):
    """
    문서를 다운로드합니다.
    """
    try:
        ensure_upload_dir()
        
        # 경로 순회 공격 방지
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
        
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail="파일이 아닙니다.")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 다운로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 다운로드 중 오류가 발생했습니다.") 