"""
엑셀 파일 임베딩 API 엔드포인트
RAG 워크플로우를 통한 엑셀 문서 처리 및 검색 기능
"""

import logging
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 엑셀 임베딩 서비스 import
from src.services.excel_embedding_service import ExcelEmbeddingService

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api/excel-embedding", tags=["Excel Embedding"])

# 엑셀 임베딩 서비스 인스턴스 (전역)
excel_embedding_service = None


def get_excel_embedding_service() -> ExcelEmbeddingService:
    """엑셀 임베딩 서비스 인스턴스 반환"""
    global excel_embedding_service
    if excel_embedding_service is None:
        try:
            excel_embedding_service = ExcelEmbeddingService()
            logger.info("엑셀 임베딩 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"엑셀 임베딩 서비스 초기화 실패: {e}")
            raise HTTPException(status_code=500, detail=f"서비스 초기화 실패: {str(e)}")
    return excel_embedding_service


# Pydantic 모델들
class ProcessingResult(BaseModel):
    """처리 결과 모델"""
    file_name: str
    total_chunks: int
    total_tokens: int
    embedding_dimension: int
    processing_success: bool
    metadata: Dict[str, Any]
    error: Optional[str] = None


class SearchResult(BaseModel):
    """검색 결과 모델"""
    content: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None
    id: str


class SearchRequest(BaseModel):
    """검색 요청 모델"""
    query: str
    n_results: int = 5


@router.post("/upload", response_model=ProcessingResult)
async def upload_excel_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(300, description="청크 크기 (토큰 수)"),
    chunk_overlap: int = Form(50, description="청크 간 겹침 (토큰 수)"),
    custom_metadata: Optional[str] = Form(None, description="추가 메타데이터 (JSON 문자열)")
):
    """
    엑셀 문서 업로드 및 임베딩 처리
    
    Args:
        file: 업로드할 엑셀 파일
        chunk_size: 청크 크기
        chunk_overlap: 청크 간 겹침
        custom_metadata: 추가 메타데이터
        
    Returns:
        처리 결과
    """
    try:
        # 파일 확장자 검증
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="엑셀 문서(.xlsx, .xls, .csv)만 업로드 가능합니다.")
        
        # 임시 파일 저장
        temp_dir = "./data/temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 메타데이터 파싱
        metadata = {}
        if custom_metadata:
            try:
                import json
                metadata = json.loads(custom_metadata)
            except json.JSONDecodeError:
                logger.warning("메타데이터 JSON 파싱 실패, 기본값 사용")
        
        # 엑셀 임베딩 서비스 가져오기
        service = get_excel_embedding_service()
        
        # 문서 처리
        result = service.process_excel_document(temp_file_path, metadata)
        
        # 임시 파일 삭제
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {e}")
        
        return ProcessingResult(**result)
        
    except Exception as e:
        logger.error(f"엑셀 문서 업로드 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 처리 실패: {str(e)}")


@router.post("/search", response_model=List[SearchResult])
async def search_similar_chunks(request: SearchRequest):
    """
    유사한 엑셀 청크 검색
    
    Args:
        request: 검색 요청
        
    Returns:
        유사한 청크 리스트
    """
    try:
        service = get_excel_embedding_service()
        results = service.search_similar_chunks(request.query, request.n_results)
        
        return [SearchResult(**result) for result in results]
        
    except Exception as e:
        logger.error(f"엑셀 문서 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


@router.get("/search", response_model=List[SearchResult])
async def search_similar_chunks_get(
    query: str = Query(..., description="검색 쿼리"),
    n_results: int = Query(5, description="반환할 결과 수")
):
    """
    유사한 엑셀 청크 검색 (GET 방식)
    
    Args:
        query: 검색 쿼리
        n_results: 반환할 결과 수
        
    Returns:
        유사한 청크 리스트
    """
    try:
        service = get_excel_embedding_service()
        results = service.search_similar_chunks(query, n_results)
        
        return [SearchResult(**result) for result in results]
        
    except Exception as e:
        logger.error(f"엑셀 문서 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}") 