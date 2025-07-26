from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import logging
import os
from typing import List

from src.models.schemas import DocumentUploadRequest, SearchRequest, SearchResponse
from src.services.document_service import document_service
from src.config.settings import settings

logger = logging.getLogger(__name__)

document_router = APIRouter(prefix="/api/documents", tags=["Documents"])

@document_router.post("/upload")
async def upload_document(request: DocumentUploadRequest):
    """문서 업로드 및 처리"""
    try:
        # 문서 처리 및 벡터 저장소에 저장
        doc_id = document_service.process_document(
            content=request.content,
            filename=request.filename,
            metadata=request.metadata
        )
        
        return {
            "message": "문서가 성공적으로 업로드되었습니다.",
            "doc_id": doc_id,
            "filename": request.filename
        }
        
    except Exception as e:
        logger.error(f"문서 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 업로드 실패: {str(e)}")

@document_router.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 및 처리"""
    try:
        # 파일 확장자 검증
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {settings.allowed_extensions}"
            )
        
        # 파일 크기 검증
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"파일 크기가 너무 큽니다. 최대 크기: {settings.max_file_size // (1024*1024)}MB"
            )
        
        # 파일 내용 읽기
        content = await file.read()
        
        # 텍스트 파일인 경우
        if file_extension == '.txt':
            text_content = content.decode('utf-8')
        else:
            # 임시 파일로 저장 후 처리
            temp_path = os.path.join(settings.upload_folder, file.filename)
            os.makedirs(settings.upload_folder, exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            try:
                text_content = document_service.load_document(temp_path)
            finally:
                # 임시 파일 삭제
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # 문서 처리 및 벡터 저장소에 저장
        doc_id = document_service.process_document(
            content=text_content,
            filename=file.filename,
            metadata={"source": "file_upload", "file_size": len(content)}
        )
        
        return {
            "message": "파일이 성공적으로 업로드되었습니다.",
            "doc_id": doc_id,
            "filename": file.filename,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@document_router.post("/search")
async def search_documents(request: SearchRequest):
    """문서 검색"""
    try:
        results = document_service.search_documents(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=request.filter_metadata
        )
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"문서 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 검색 실패: {str(e)}")

@document_router.get("/count")
async def get_document_count():
    """저장된 문서 수 반환"""
    try:
        count = document_service.get_document_count()
        return {"document_count": count}
    except Exception as e:
        logger.error(f"문서 수 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 수 조회 실패: {str(e)}")

@document_router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """문서 삭제"""
    try:
        success = document_service.delete_document(doc_id)
        if success:
            return {"message": "문서가 성공적으로 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 삭제 실패: {str(e)}")

@document_router.get("/status")
async def get_document_status():
    """문서 처리 상태 확인"""
    try:
        vectorstore_status = document_service.get_vectorstore_status()
        document_count = document_service.get_document_count()
        
        return {
            "vectorstore_status": vectorstore_status,
            "document_count": document_count,
            "upload_folder": settings.upload_folder,
            "allowed_extensions": settings.allowed_extensions
        }
    except Exception as e:
        logger.error(f"문서 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 상태 조회 실패: {str(e)}") 