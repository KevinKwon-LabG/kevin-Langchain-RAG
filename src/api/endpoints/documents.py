"""
문서 관리 API 엔드포인트
파일 업로드, 목록 조회, 삭제 기능을 제공합니다.
"""

import os
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from datetime import datetime
import asyncio

from src.services.document_service import document_service
from src.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 업로드 디렉토리 설정
UPLOAD_DIR = "static/RAG"
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.md', '.json', '.csv', '.xlsx', '.xls'}

class DocumentInfo(BaseModel):
    filename: str
    size: int
    upload_time: str
    file_type: str

class ProcessingStatus(BaseModel):
    queue_size: int
    processing_thread_alive: bool
    message: str

# 처리 중인 문서 상태 저장
processing_documents: Dict[str, Dict[str, Any]] = {}

def ensure_upload_dir():
    """업로드 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_file_extension(filename: str) -> str:
    """파일 확장자를 반환합니다."""
    return os.path.splitext(filename)[1].lower()

def is_allowed_file(filename: str) -> bool:
    """허용된 파일 형식인지 확인합니다."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

def document_processing_callback(success: bool, doc_id: Optional[str], error: Optional[str]):
    """문서 처리 완료 콜백"""
    if success:
        logger.info(f"문서 처리 완료: {doc_id}")
        # 처리 완료된 문서 상태 업데이트
        for filename, status in list(processing_documents.items()):
            if status.get("doc_id") == "processing":
                processing_documents[filename]["status"] = "completed"
                processing_documents[filename]["doc_id"] = doc_id
                processing_documents[filename]["completed_at"] = datetime.now().isoformat()
                
                # RAG 문서 자동 재로드
                try:
                    logger.info(f"문서 '{filename}' 처리 완료 후 RAG 자동 재로드 시작")
                    rag_result = rag_service.reload_rag_documents()
                    logger.info(f"RAG 자동 재로드 완료: {rag_result}")
                except Exception as e:
                    logger.error(f"RAG 자동 재로드 실패: {e}")
                
                # 30초 후 처리 완료된 문서 제거
                import threading
                def remove_completed_document():
                    import time
                    time.sleep(30)
                    if filename in processing_documents:
                        del processing_documents[filename]
                        logger.info(f"처리 완료된 문서 '{filename}'을 목록에서 제거했습니다.")
                
                threading.Thread(target=remove_completed_document, daemon=True).start()
                break
    else:
        logger.error(f"문서 처리 실패: {error}")
        # 처리 실패된 문서 상태 업데이트
        for filename, status in list(processing_documents.items()):
            if status.get("doc_id") == "processing":
                processing_documents[filename]["status"] = "failed"
                processing_documents[filename]["error"] = error
                processing_documents[filename]["failed_at"] = datetime.now().isoformat()
                # 30초 후 처리 실패한 문서 제거
                import threading
                def remove_failed_document():
                    import time
                    time.sleep(30)
                    if filename in processing_documents:
                        del processing_documents[filename]
                        logger.info(f"처리 실패한 문서 '{filename}'을 목록에서 제거했습니다.")
                
                threading.Thread(target=remove_failed_document, daemon=True).start()
                break

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
    문서를 업로드하고 벡터 저장소에 처리합니다.
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
        
        # 문서 처리 시작 (비동기)
        try:
            content = document_service.load_document(file_path)
            
            # 처리 상태 초기화
            processing_documents[filename] = {
                "status": "processing",
                "doc_id": "processing",
                "started_at": datetime.now().isoformat(),
                "filename": filename
            }
            
            # 비동기 처리 시작
            doc_id = document_service.process_document(
                content=content,
                filename=filename,
                metadata={
                    "source": "upload",
                    "file_size": file.size,
                    "file_type": get_file_extension(filename)
                },
                callback=document_processing_callback
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "문서가 업로드되었고 처리 중입니다.",
                    "filename": filename,
                    "doc_id": doc_id,
                    "status": "processing"
                }
            )
            
        except Exception as e:
            logger.error(f"문서 처리 시작 실패: {e}")
            # 파일 삭제
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"문서 처리 중 오류가 발생했습니다: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 업로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 업로드 중 오류가 발생했습니다.")

@router.get("/api/documents/processing-status")
async def get_processing_status() -> ProcessingStatus:
    """
    문서 처리 상태를 반환합니다.
    """
    try:
        queue_status = document_service.get_queue_status()
        
        return ProcessingStatus(
            queue_size=queue_status["queue_size"],
            processing_thread_alive=queue_status["processing_thread_alive"],
            message=f"큐 크기: {queue_status['queue_size']}, 처리 스레드: {'활성' if queue_status['processing_thread_alive'] else '비활성'}"
        )
    except Exception as e:
        logger.error(f"처리 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="처리 상태 조회 중 오류가 발생했습니다.")

@router.get("/api/documents/processing-documents")
async def get_processing_documents() -> Dict[str, Any]:
    """
    처리 중인 문서 목록을 반환합니다.
    """
    try:
        return {
            "processing_documents": processing_documents,
            "count": len(processing_documents)
        }
    except Exception as e:
        logger.error(f"처리 중인 문서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="처리 중인 문서 목록 조회 중 오류가 발생했습니다.")

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
        
        # 벡터 저장소에서 해당 문서 삭제 시도
        try:
            # 파일명으로 문서 ID 찾기 (메타데이터에서 검색)
            search_results = document_service.search_documents(
                query="", 
                top_k=1000, 
                filter_metadata={"filename": filename}
            )
            
            # 해당 문서의 모든 청크 삭제
            for result in search_results:
                doc_id = result.get("id")
                if doc_id and doc_id != "unknown":
                    document_service.delete_document(doc_id)
                    logger.info(f"벡터 저장소에서 문서 삭제 완료: {doc_id}")
                    break
                    
        except Exception as e:
            logger.warning(f"벡터 저장소에서 문서 삭제 실패 (파일은 삭제됨): {e}")
        
        # 파일 삭제
        os.remove(file_path)
        
        # 처리 중인 문서 목록에서도 제거
        if filename in processing_documents:
            del processing_documents[filename]
        
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