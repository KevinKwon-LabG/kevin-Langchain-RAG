"""
외부 RAG 서버 API 엔드포인트
Chroma API를 사용한 외부 RAG 서버와의 통신을 담당합니다.
"""

import logging
import httpx
import asyncio
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

# 외부 RAG 서버 설정
CHROMA_API = "http://1.237.52.240:8600"
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
DB_NAME = "default-db"
COLLECTION_ID = "0d6ca41b-cd1c-4c84-a90e-ba2d4527c81a"
QUERY_ENDPOINT = f"{CHROMA_API}/api/v2/tenants/{TENANT_ID}/databases/{DB_NAME}/collections/{COLLECTION_ID}/query"

# 임베딩 모델 초기화 (384차원 모델 사용)
try:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    logger.error(f"임베딩 모델 초기화 실패: {e}")
    embedding_model = None

def text_to_embedding(text: str) -> List[float]:
    """텍스트를 임베딩으로 변환합니다."""
    try:
        if not embedding_model:
            return [0.0] * 384
        
        if not text or text.strip() == "":
            return [0.0] * 384
        
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"텍스트 임베딩 변환 실패: {e}")
        return [0.0] * 384

# Pydantic 모델들
class ExternalRAGQuery(BaseModel):
    """외부 RAG 쿼리 요청 모델"""
    query: str = Field(..., description="검색할 쿼리 텍스트")
    n_results: int = Field(default=5, description="반환할 결과 수")
    include_metadata: bool = Field(default=True, description="메타데이터 포함 여부")
    include_documents: bool = Field(default=True, description="문서 내용 포함 여부")

class ExternalRAGResponse(BaseModel):
    """외부 RAG 응답 모델"""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    response_time: float
    timestamp: datetime
    error_message: Optional[str] = None

class ExternalRAGHealthCheck(BaseModel):
    """외부 RAG 서버 상태 확인 모델"""
    server_status: str
    endpoint: str
    response_time: float
    timestamp: datetime
    error_message: Optional[str] = None

@router.get("/external-rag/health", response_model=ExternalRAGHealthCheck)
async def check_external_rag_health():
    """
    외부 RAG 서버의 상태를 확인합니다.
    """
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Chroma API v2 형식에 맞는 헬스 체크 페이로드
            health_payload = {
                "query_embeddings": [text_to_embedding("")],
                "n_results": 1
            }
            
            response = await client.post(
                QUERY_ENDPOINT,
                json=health_payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                return ExternalRAGHealthCheck(
                    server_status="healthy",
                    endpoint=QUERY_ENDPOINT,
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                return ExternalRAGHealthCheck(
                    server_status="error",
                    endpoint=QUERY_ENDPOINT,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"외부 RAG 서버 헬스 체크 실패: {str(e)}")
        
        return ExternalRAGHealthCheck(
            server_status="unreachable",
            endpoint=QUERY_ENDPOINT,
            response_time=response_time,
            timestamp=datetime.now(),
            error_message=str(e)
        )

@router.post("/external-rag/query", response_model=ExternalRAGResponse)
async def query_external_rag(query_request: ExternalRAGQuery):
    """
    외부 RAG 서버에 쿼리를 전송하고 결과를 반환합니다.
    """
    start_time = datetime.now()
    
    try:
        # Chroma API v2 형식에 맞는 쿼리 페이로드 구성
        payload = {
            "query_embeddings": [text_to_embedding(query_request.query)],
            "n_results": query_request.n_results,
            "include": ["metadatas", "documents"]
        }
        
        # 외부 RAG 서버에 쿼리 전송
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QUERY_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                response_data = response.json()
                
                # 응답 데이터 처리
                results = []
                if "results" in response_data:
                    results_data = response_data["results"]
                    total_results = 0
                    
                    # 결과 수 계산
                    if "ids" in results_data and results_data["ids"]:
                        total_results = len(results_data["ids"][0])
                    
                    for i in range(total_results):
                        result_item = {
                            "rank": i + 1
                        }
                        
                        # ID
                        if "ids" in results_data and results_data["ids"] and len(results_data["ids"][0]) > i:
                            result_item["id"] = results_data["ids"][0][i]
                        
                        # 거리 (유사도)
                        if "distances" in results_data and results_data["distances"] and len(results_data["distances"][0]) > i:
                            distance = results_data["distances"][0][i]
                            result_item["distance"] = distance
                            if distance is not None:
                                result_item["similarity"] = 1 - distance
                        
                        # 메타데이터
                        if "metadatas" in results_data and results_data["metadatas"] and len(results_data["metadatas"][0]) > i:
                            result_item["metadata"] = results_data["metadatas"][0][i]
                        
                        # 문서 내용
                        if "documents" in results_data and results_data["documents"] and len(results_data["documents"][0]) > i:
                            result_item["document"] = results_data["documents"][0][i]
                        
                        results.append(result_item)
                
                return ExternalRAGResponse(
                    success=True,
                    query=query_request.query,
                    results=results,
                    total_results=len(results),
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                response_time = (datetime.now() - start_time).total_seconds()
                error_msg = f"외부 RAG 서버 오류: HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(error_msg)
                
                return ExternalRAGResponse(
                    success=False,
                    query=query_request.query,
                    results=[],
                    total_results=0,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    error_message=error_msg
                )
                
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"외부 RAG 쿼리 실패: {str(e)}"
        logger.error(error_msg)
        
        return ExternalRAGResponse(
            success=False,
            query=query_request.query,
            results=[],
            total_results=0,
            response_time=response_time,
            timestamp=datetime.now(),
            error_message=error_msg
        )

@router.get("/external-rag/info")
async def get_external_rag_info():
    """
    외부 RAG 서버의 설정 정보를 반환합니다.
    """
    return {
        "server_url": CHROMA_API,
        "tenant_id": TENANT_ID,
        "database_name": DB_NAME,
        "collection_id": COLLECTION_ID,
        "query_endpoint": QUERY_ENDPOINT,
        "description": "외부 Chroma RAG 서버 설정 정보"
    }
