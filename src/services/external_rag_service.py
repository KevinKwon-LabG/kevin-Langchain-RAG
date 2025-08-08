"""
외부 RAG 서비스
Chroma API를 사용한 외부 RAG 서버와의 통신을 담당합니다.
"""

import httpx
import logging
import json
import asyncio
import random
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class ExternalRAGService:
    """외부 RAG 서비스 클래스"""
    
    def __init__(self, settings):
        self.settings = settings
        self.enabled = settings.external_rag_enabled
        self.base_url = settings.external_rag_url
        self.tenant_id = settings.external_rag_tenant_id
        self.db_name = settings.external_rag_db_name
        self.collection_id = settings.external_rag_collection_id
        self.timeout = settings.external_rag_timeout
        self.max_retries = settings.external_rag_max_retries
        self.fallback_to_local = settings.external_rag_fallback_to_local
        self.health_check_interval = settings.external_rag_health_check_interval
        
        # 통계 관련 설정
        self.stats_enabled = settings.external_rag_stats_enabled
        self.stats_file = Path(settings.external_rag_stats_file)
        
        # 쿼리 엔드포인트 구성
        self.query_endpoint = f"{self.base_url}/api/v2/tenants/{self.tenant_id}/databases/{self.db_name}/collections/{self.collection_id}/query"
        
        # 임베딩 모델 초기화 (384차원 모델 사용)
        self.embedding_model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer 모델 로드 성공")
        except ImportError:
            logger.warning("SentenceTransformer가 설치되지 않았습니다. 더미 임베딩을 사용합니다.")
        except Exception as e:
            logger.warning(f"SentenceTransformer 모델 로드 실패: {e}. 더미 임베딩을 사용합니다.")
        
        # 상태 변수들
        self.last_health_check = None
        self.health_status = "unknown"
        self.response_time_avg = 0.0
        self.success_count = 0
        self.failure_count = 0
        self.total_queries = 0
        
        # 통계 초기화
        self._initialize_stats()
        
        # 헬스 체크는 애플리케이션 시작 후 별도로 시작
        self._health_check_task = None
    
    def _text_to_embedding(self, text: str) -> List[float]:
        """
        텍스트를 임베딩으로 변환합니다.
        
        Args:
            text: 변환할 텍스트
            
        Returns:
            List[float]: 임베딩 벡터
        """
        try:
            # 텍스트가 비어있으면 기본 임베딩 반환
            if not text or text.strip() == "":
                # 384차원의 0으로 채워진 벡터 반환
                return [0.0] * 384
            
            # SentenceTransformer 모델이 있으면 사용
            if self.embedding_model is not None:
                embedding = self.embedding_model.encode(text)
                return embedding.tolist()
            else:
                # 더미 임베딩 생성
                return self._generate_dummy_embedding(text, 384)
            
        except Exception as e:
            logger.error(f"텍스트 임베딩 변환 실패: {e}")
            # 오류 시 더미 임베딩 반환
            return self._generate_dummy_embedding(text, 384)
    
    def _generate_dummy_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """간단한 더미 임베딩 벡터 생성 (테스트용)"""
        # 텍스트의 해시값을 기반으로 일관된 임베딩 생성
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # 해시값을 기반으로 시드 설정
        random.seed(int(hash_hex[:8], 16))
        
        # 정규 분포를 시뮬레이션하여 임베딩 벡터 생성
        embedding = []
        for _ in range(dimension):
            # Box-Muller 변환을 사용하여 정규 분포 생성
            u1 = random.random()
            u2 = random.random()
            z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
            embedding.append(z)
        
        # 정규화
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def _initialize_stats(self):
        """통계 파일 초기화"""
        if not self.stats_enabled:
            return
            
        try:
            if not self.stats_file.exists():
                initial_stats = {
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "average_response_time": 0.0,
                    "last_health_check": None,
                    "health_status": "unknown",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                self.stats_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.stats_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_stats, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"외부 RAG 통계 파일 초기화: {self.stats_file}")
        except Exception as e:
            logger.error(f"외부 RAG 통계 파일 초기화 실패: {e}")
    
    async def _start_health_check_loop(self):
        """헬스 체크 루프 시작"""
        while self.enabled:
            try:
                await self.health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"헬스 체크 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    async def health_check(self) -> Dict[str, Any]:
        """
        외부 RAG 서버의 상태를 확인합니다.
        
        Returns:
            Dict: 헬스 체크 결과
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "외부 RAG가 비활성화되어 있습니다.",
                "timestamp": datetime.now().isoformat()
            }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Chroma API v2 형식에 맞는 헬스 체크 페이로드
                health_payload = {
                    "query_embeddings": [self._text_to_embedding("")],
                    "n_results": 1
                }
                
                response = await client.post(
                    self.query_endpoint,
                    json=health_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response_time = time.time() - start_time
                self.last_health_check = datetime.now()
                
                if response.status_code == 200:
                    self.health_status = "healthy"
                    self.response_time_avg = response_time
                    
                    result = {
                        "status": "healthy",
                        "response_time": response_time,
                        "timestamp": self.last_health_check.isoformat(),
                        "endpoint": self.query_endpoint
                    }
                    
                    logger.info(f"외부 RAG 헬스 체크 성공: {response_time:.3f}초")
                    return result
                else:
                    self.health_status = "error"
                    result = {
                        "status": "error",
                        "response_time": response_time,
                        "timestamp": self.last_health_check.isoformat(),
                        "endpoint": self.query_endpoint,
                        "error_message": f"HTTP {response.status_code}: {response.text}"
                    }
                    
                    logger.warning(f"외부 RAG 헬스 체크 실패: HTTP {response.status_code}")
                    return result
                    
        except Exception as e:
            response_time = time.time() - start_time
            self.health_status = "unreachable"
            self.last_health_check = datetime.now()
            
            result = {
                "status": "unreachable",
                "response_time": response_time,
                "timestamp": self.last_health_check.isoformat(),
                "endpoint": self.query_endpoint,
                "error_message": str(e)
            }
            
            logger.error(f"외부 RAG 헬스 체크 실패: {e}")
            return result
    
    async def query(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        외부 RAG 서버에 쿼리를 전송하고 결과를 반환합니다.
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            
        Returns:
            Dict: 쿼리 결과
        """
        if not self.enabled:
            return {
                "success": False,
                "message": "외부 RAG가 비활성화되어 있습니다.",
                "query": query,
                "results": [],
                "total_results": 0
            }
        
        start_time = time.time()
        self.total_queries += 1
        
        try:
            # Chroma API v2 형식에 맞는 쿼리 페이로드 구성
            payload = {
                "query_embeddings": [self._text_to_embedding(query)],
                "n_results": n_results,
                "include": ["metadatas", "documents"]
            }
            
            # 재시도 로직
            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(
                            self.query_endpoint,
                            json=payload,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        response_time = time.time() - start_time
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            processed_results = self._process_response(response_data)
                            
                            # 성공 통계 업데이트
                            self.success_count += 1
                            self.response_time_avg = (self.response_time_avg + response_time) / 2
                            
                            result = {
                                "success": True,
                                "query": query,
                                "results": processed_results["results"],
                                "total_results": processed_results["total_results"],
                                "response_time": response_time,
                                "attempt": attempt + 1
                            }
                            
                            # 통계 저장
                            await self._update_stats(result)
                            
                            logger.info(f"외부 RAG 쿼리 성공: {response_time:.3f}초, {len(processed_results['results'])}개 결과")
                            return result
                        else:
                            error_msg = f"외부 RAG 서버 오류: HTTP {response.status_code}"
                            try:
                                error_detail = response.json()
                                error_msg += f" - {error_detail}"
                            except:
                                error_msg += f" - {response.text}"
                            
                            logger.warning(f"외부 RAG 쿼리 실패 (시도 {attempt + 1}/{self.max_retries}): {error_msg}")
                            
                            if attempt == self.max_retries - 1:
                                # 마지막 시도 실패
                                self.failure_count += 1
                                await self._update_stats({
                                    "success": False,
                                    "query": query,
                                    "error_message": error_msg,
                                    "response_time": response_time
                                })
                                
                                return {
                                    "success": False,
                                    "query": query,
                                    "message": error_msg,
                                    "results": [],
                                    "total_results": 0,
                                    "response_time": response_time
                                }
                            
                            # 재시도 전 잠시 대기
                            await asyncio.sleep(1)
                            
                except httpx.TimeoutException:
                    logger.warning(f"외부 RAG 쿼리 타임아웃 (시도 {attempt + 1}/{self.max_retries})")
                    if attempt == self.max_retries - 1:
                        self.failure_count += 1
                        return {
                            "success": False,
                            "query": query,
                            "message": "외부 RAG 서버 응답 시간 초과",
                            "results": [],
                            "total_results": 0,
                            "response_time": time.time() - start_time
                        }
                    await asyncio.sleep(1)
                    
        except Exception as e:
            response_time = time.time() - start_time
            self.failure_count += 1
            
            error_msg = f"외부 RAG 쿼리 실패: {str(e)}"
            logger.error(error_msg)
            
            await self._update_stats({
                "success": False,
                "query": query,
                "error_message": error_msg,
                "response_time": response_time
            })
            
            return {
                "success": False,
                "query": query,
                "message": error_msg,
                "results": [],
                "total_results": 0,
                "response_time": response_time
            }
    
    def _process_response(self, response_data: Dict) -> Dict[str, Any]:
        """
        외부 RAG 응답 데이터를 처리합니다.
        
        Args:
            response_data: 외부 RAG 서버 응답 데이터
            
        Returns:
            Dict: 처리된 결과
        """
        results = []
        
        # Chroma API v2 응답 구조에 맞게 수정
        # response_data 자체가 results 데이터이거나 response_data["results"]에 있을 수 있음
        results_data = response_data.get("results", response_data)
        
        total_results = 0
        
        # 결과 수 계산 - ids 배열의 첫 번째 요소 길이
        if "ids" in results_data and results_data["ids"] and len(results_data["ids"]) > 0:
            total_results = len(results_data["ids"][0])
        
        logger.info(f"외부 RAG 응답 처리: total_results={total_results}")
        
        for i in range(total_results):
            result_item = {
                "rank": i + 1
            }
            
            # ID
            if "ids" in results_data and results_data["ids"] and len(results_data["ids"]) > 0 and len(results_data["ids"][0]) > i:
                result_item["id"] = results_data["ids"][0][i]
            
            # 거리 (유사도)
            if "distances" in results_data and results_data["distances"] and len(results_data["distances"]) > 0 and len(results_data["distances"][0]) > i:
                distance = results_data["distances"][0][i]
                result_item["distance"] = distance
                if distance is not None:
                    result_item["similarity"] = 1 - distance
            
            # 메타데이터
            if "metadatas" in results_data and results_data["metadatas"] and len(results_data["metadatas"]) > 0 and len(results_data["metadatas"][0]) > i:
                result_item["metadata"] = results_data["metadatas"][0][i]
            
            # 문서 내용
            if "documents" in results_data and results_data["documents"] and len(results_data["documents"]) > 0 and len(results_data["documents"][0]) > i:
                result_item["document"] = results_data["documents"][0][i]
            
            results.append(result_item)
        
        logger.info(f"외부 RAG 응답 처리 완료: {len(results)}개 결과")
        
        return {
            "results": results,
            "total_results": len(results)
        }
    
    async def _update_stats(self, result: Dict[str, Any]):
        """통계 정보를 업데이트합니다."""
        if not self.stats_enabled:
            return
            
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            else:
                stats = {
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "average_response_time": 0.0,
                    "last_health_check": None,
                    "health_status": "unknown",
                    "created_at": datetime.now().isoformat()
                }
            
            # 통계 업데이트
            stats["total_queries"] = self.total_queries
            stats["successful_queries"] = self.success_count
            stats["failed_queries"] = self.failure_count
            stats["average_response_time"] = self.response_time_avg
            stats["last_health_check"] = self.last_health_check.isoformat() if self.last_health_check else None
            stats["health_status"] = self.health_status
            stats["updated_at"] = datetime.now().isoformat()
            
            # 최근 쿼리 기록 (최대 100개)
            if "recent_queries" not in stats:
                stats["recent_queries"] = []
            
            recent_query = {
                "query": result.get("query", ""),
                "success": result.get("success", False),
                "response_time": result.get("response_time", 0),
                "timestamp": datetime.now().isoformat(),
                "results_count": result.get("total_results", 0)
            }
            
            stats["recent_queries"].append(recent_query)
            stats["recent_queries"] = stats["recent_queries"][-100:]  # 최근 100개만 유지
            
            # 파일 저장
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"외부 RAG 통계 업데이트 실패: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 통계 정보를 반환합니다."""
        if not self.stats_enabled or not self.stats_file.exists():
            return {
                "enabled": self.enabled,
                "total_queries": self.total_queries,
                "successful_queries": self.success_count,
                "failed_queries": self.failure_count,
                "average_response_time": self.response_time_avg,
                "health_status": self.health_status,
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None
            }
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            
            stats["enabled"] = self.enabled
            return stats
            
        except Exception as e:
            logger.error(f"외부 RAG 통계 읽기 실패: {e}")
            return {
                "enabled": self.enabled,
                "error": "통계 파일 읽기 실패"
            }
    
    def start_health_check(self):
        """헬스 체크 루프를 시작합니다."""
        if self.enabled and self._health_check_task is None:
            try:
                self._health_check_task = asyncio.create_task(self._start_health_check_loop())
                logger.info("외부 RAG 헬스 체크 루프 시작")
            except RuntimeError:
                logger.warning("이벤트 루프가 실행되지 않아 헬스 체크를 시작할 수 없습니다.")
    
    def stop_health_check(self):
        """헬스 체크 루프를 중지합니다."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            logger.info("외부 RAG 헬스 체크 루프 중지")
    
    def get_status(self) -> Dict[str, Any]:
        """외부 RAG 서비스 상태를 반환합니다."""
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "query_endpoint": self.query_endpoint,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "fallback_to_local": self.fallback_to_local,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "total_queries": self.total_queries,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_response_time": self.response_time_avg,
            "health_check_running": self._health_check_task is not None and not self._health_check_task.done()
        }
