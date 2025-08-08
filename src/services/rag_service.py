import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_ollama import OllamaLLM

from src.config.settings import settings
from src.services.document_service import document_service
from src.services.mcp_client_service import mcp_client_service
from src.services.external_rag_service import ExternalRAGService

logger = logging.getLogger(__name__)

class VectorStoreRetriever:
    """벡터 저장소 기반 검색기"""
    
    def __init__(self, document_service, top_k: int = 5, similarity_threshold: float = 0.85):
        self._document_service = document_service
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold
    
    @property
    def top_k(self) -> int:
        return self._top_k
    
    @top_k.setter
    def top_k(self, value: int):
        self._top_k = value
    
    @property
    def similarity_threshold(self) -> float:
        return self._similarity_threshold
    
    @similarity_threshold.setter
    def similarity_threshold(self, value: float):
        self._similarity_threshold = value
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """쿼리에 관련된 문서들을 검색합니다."""
        try:
            # 벡터 저장소에서 유사한 문서 검색
            search_results = self._document_service.search_documents(
                query=query,
                top_k=self._top_k
            )
            
            # 유사도 임계값 필터링
            filtered_results = []
            for result in search_results:
                if result.get('score', 0) >= self._similarity_threshold:
                    # LangChain Document 객체로 변환
                    doc = Document(
                        page_content=result['content'],
                        metadata=result['metadata']
                    )
                    filtered_results.append(doc)
            
            logger.info(f"RAG 검색 결과: {len(filtered_results)}개 문서 (임계값: {self._similarity_threshold})")
            return filtered_results
            
        except Exception as e:
            logger.error(f"벡터 저장소 검색 실패: {e}")
            return []
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """비동기 버전의 문서 검색"""
        return self.get_relevant_documents(query)

class RAGService:
    def __init__(self):
        self.rag_directory = Path("static/RAG")
        
        # 설정에서 값 가져오기 - RAG 의존도를 낮추기 위해 더 엄격한 설정
        self.similarity_threshold = max(settings.default_similarity_threshold, 0.85)  # 최소 0.85로 설정
        self.context_weight = 0.5  # 컨텍스트 가중치 감소
        self.min_context_length = 150  # 최소 컨텍스트 길이 증가
        self.max_context_length = 1500  # 최대 컨텍스트 길이 감소
        
        # 컨텍스트 품질 평가를 위한 추가 변수
        self.last_context_score = 0.0  # 마지막 검색된 컨텍스트의 평균 유사도 점수
        self.last_context_length = 0   # 마지막 검색된 컨텍스트의 길이
        
        # RAG 사용 여부 판단을 위한 변수들 - 더 엄격하게 설정
        self.min_avg_score_for_rag = 0.96  # RAG 사용을 위한 최소 평균 유사도 점수 증가
        self.max_context_chunks = 4  # 최대 컨텍스트 청크 수 증가
        
        # RAG 사용 빈도 제한을 위한 변수들
        self.rag_usage_count = 0  # RAG 사용 횟수
        self.max_rag_usage_per_session = 3  # 세션당 최대 RAG 사용 횟수
        self.rag_cooldown_queries = 5  # RAG 사용 후 일반 응답으로 전환할 쿼리 수
        
        # LangChain 컴포넌트 초기화
        self.retriever = VectorStoreRetriever(
            document_service=document_service,
            top_k=settings.default_top_k_documents,
            similarity_threshold=self.similarity_threshold
        )
        
        # MCP 서비스 통합
        self.mcp_service = mcp_client_service
        
        # RAG 디렉토리 초기화 및 문서 로드
        self._initialize_rag_documents()
        
        # 외부 RAG 서비스 초기화
        self.external_rag_service = ExternalRAGService(settings)
    
    def _initialize_rag_documents(self):
        """RAG 디렉토리의 문서들을 벡터 저장소에 로드합니다."""
        try:
            if not self.rag_directory.exists():
                logger.warning(f"RAG 디렉토리가 존재하지 않습니다: {self.rag_directory}")
                return
            
            # 기존 문서 수 확인
            existing_count = document_service.get_document_count()
            logger.info(f"기존 문서 수: {existing_count}")
            
            # RAG 디렉토리의 모든 파일 처리
            for file_path in self.rag_directory.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.txt', '.docx', '.md', '.xlsx']:
                    try:
                        # 파일이 이미 처리되었는지 확인
                        if self._is_document_already_processed(file_path.name):
                            logger.info(f"문서가 이미 처리됨: {file_path.name}")
                            continue
                        
                        logger.info(f"RAG 문서 처리 중: {file_path.name}")
                        
                        # 문서 로드 및 처리
                        content = document_service.load_document(str(file_path))
                        
                        # 메타데이터 설정
                        metadata = {
                            "source": "rag",
                            "rag_directory": str(self.rag_directory),
                            "file_type": file_path.suffix.lower(),
                            "file_size": file_path.stat().st_size
                        }
                        
                        # 벡터 저장소에 저장
                        doc_id = document_service.process_document(
                            content=content,
                            filename=file_path.name,
                            metadata=metadata
                        )
                        
                        logger.info(f"RAG 문서 처리 완료: {file_path.name} (ID: {doc_id})")
                        
                    except Exception as e:
                        logger.error(f"RAG 문서 처리 실패 {file_path.name}: {e}")
            
            # 최종 문서 수 확인
            final_count = document_service.get_document_count()
            logger.info(f"RAG 초기화 완료 - 총 문서 수: {final_count}")
            
        except Exception as e:
            logger.error(f"RAG 초기화 중 오류: {e}")
    
    def _is_document_already_processed(self, filename: str) -> bool:
        """문서가 이미 처리되었는지 확인합니다."""
        try:
            # 벡터 저장소에서 해당 파일명으로 검색
            search_results = document_service.search_documents(
                query="", 
                top_k=10, 
                filter_metadata={"filename": filename}
            )
            
            # 검색 결과가 있으면 이미 처리된 것으로 간주
            return len(search_results) > 0
            
        except Exception as e:
            logger.error(f"문서 처리 상태 확인 중 오류: {e}")
            return False
    
    def retrieve_context(self, query: str, top_k: int = 5) -> Tuple[str, List[Dict[str, Any]]]:
        """
        쿼리에 대한 컨텍스트를 검색합니다.
        
        Args:
            query: 검색 쿼리
            top_k: 검색할 문서 수
            
        Returns:
            Tuple[str, List[Dict]]: (컨텍스트 문자열, 검색 결과 리스트)
        """
        try:
            # 검색 결과 가져오기
            search_results = document_service.search_documents(
                query=query,
                top_k=top_k
            )
            
            # 더 엄격한 유사도 임계값 필터링
            filtered_results = []
            total_score = 0.0
            
            for result in search_results:
                score = result.get('score', 0)
                if score >= self.similarity_threshold:
                    filtered_results.append(result)
                    total_score += score
            
            # 컨텍스트 품질 평가
            if filtered_results:
                self.last_context_score = total_score / len(filtered_results)
                self.last_context_length = sum(len(r['content']) for r in filtered_results)
            else:
                self.last_context_score = 0.0
                self.last_context_length = 0
            
            # 컨텍스트 품질이 낮은 경우 빈 결과 반환
            if filtered_results and self.last_context_score < self.min_avg_score_for_rag:
                logger.info(f"컨텍스트 품질이 낮음 (평균 점수: {self.last_context_score:.3f}), RAG 사용하지 않음")
                return "", []
            
            # 컨텍스트 길이 제한 적용
            context_parts = []
            total_length = 0
            
            for i, result in enumerate(filtered_results[:self.max_context_chunks]):
                content = result['content'].strip()
                if content:
                    # 각 청크의 길이 제한
                    if len(content) > 500:
                        content = content[:500] + "..."
                    
                    # 전체 길이 제한 확인
                    if total_length + len(content) > self.max_context_length:
                        break
                    
                    context_parts.append(f"[문서 {i+1}] {content}")
                    total_length += len(content)
            
            context = "\n\n".join(context_parts)
            
            logger.info(f"RAG 컨텍스트 검색 완료: {len(context_parts)}개 청크, 길이: {len(context)} 문자, 평균 점수: {self.last_context_score:.3f}")
            
            return context, filtered_results[:len(context_parts)]
            
        except Exception as e:
            logger.error(f"RAG 컨텍스트 검색 실패: {e}")
            return "", []
    
    async def retrieve_context_with_external_rag(self, query: str, top_k: int = 5, 
                                                use_external_rag: bool = True) -> Tuple[str, List[Dict[str, Any]]]:
        """
        외부 RAG를 우선 사용하여 컨텍스트를 검색합니다.
        
        Args:
            query: 검색 쿼리
            top_k: 검색할 문서 수
            use_external_rag: 외부 RAG 사용 여부
            
        Returns:
            Tuple[str, List[Dict]]: (컨텍스트 문자열, 검색 결과 리스트)
        """
        try:
            # 외부 RAG 우선 시도 (활성화된 경우)
            context = ""
            context_sources = []
            
            if use_external_rag and self.external_rag_service.enabled:
                logger.info("외부 RAG 서비스 시도 중...")
                external_result = await self.external_rag_service.query(query, top_k)
                
                if external_result["success"] and external_result["total_results"] > 0:
                    # 외부 RAG 성공 시 결과 사용
                    context_parts = []
                    
                    for result in external_result["results"]:
                        if result.get("document"):
                            context_parts.append(result["document"])
                    
                    context = "\n\n".join(context_parts)
                    context_sources = [
                        {
                            "content": result.get("document", ""),
                            "metadata": result.get("metadata", {}),
                            "score": 0.9 if result.get("distance") is None else (1.0 - result.get("distance", 0)),  # 외부 RAG는 기본 높은 점수
                            "source": "external_rag"
                        }
                        for result in external_result["results"]
                    ]
                    
                    logger.info(f"외부 RAG 사용: {len(context_sources)}개 결과, 응답시간: {external_result.get('response_time', 0):.3f}초")
                else:
                    logger.info(f"외부 RAG 실패: {external_result.get('message', '알 수 없는 오류')}")
                    
                    # 폴백 설정이 활성화된 경우 로컬 RAG 사용
                    if self.external_rag_service.fallback_to_local:
                        logger.info("로컬 RAG로 폴백...")
                        context, context_sources = self.retrieve_context(query, top_k)
                    else:
                        logger.warning("외부 RAG 실패 및 폴백 비활성화로 인해 컨텍스트 없음")
            else:
                # 외부 RAG 비활성화된 경우 로컬 RAG 사용
                if not use_external_rag:
                    logger.info("외부 RAG 비활성화, 로컬 RAG 사용")
                else:
                    logger.info("외부 RAG 서비스 비활성화, 로컬 RAG 사용")
                
                context, context_sources = self.retrieve_context(query, top_k)
            
            return context, context_sources
            
        except Exception as e:
            logger.error(f"외부 RAG 컨텍스트 검색 실패: {e}")
            # 오류 발생 시 로컬 RAG로 폴백
            return self.retrieve_context(query, top_k)
    
    async def generate_rag_response(self, query: str, model_name: str = None, 
                            use_rag: bool = True, top_k: int = 5,
                            system_prompt: str = None, use_mcp: bool = True, session_id: str = None, 
                            use_external_rag: bool = True) -> Dict[str, Any]:
        """
        RAG를 사용하여 AI 응답을 생성합니다.
        
        Args:
            query: 사용자 질문
            model_name: 사용할 모델명
            use_rag: RAG 사용 여부
            top_k: 검색할 문서 수
            system_prompt: 시스템 프롬프트
            use_mcp: MCP 서비스 사용 여부 (UI 체크박스 상태)
            session_id: 세션 ID (MCP 결정 방식에 사용)
            
        Returns:
            Dict: 응답 정보
        """
        try:
            # MCP 서비스 사용 여부 확인 - UI 설정을 우선적으로 고려
            if use_mcp and self._should_use_mcp(query, model_name, session_id, ui_mcp_enabled=use_mcp):
                logger.info("MCP 서비스와 RAG 통합 사용 (UI에서 MCP 사용 허용됨)")
                return await self._generate_rag_with_mcp_response(query, model_name, top_k, system_prompt, session_id)
            elif use_mcp:
                logger.info("UI에서 MCP 사용이 허용되었지만, 쿼리 분석 결과 MCP 서비스 사용이 불필요함")
            else:
                logger.info("UI에서 MCP 사용이 비활성화됨")
            
            if not use_rag:
                # RAG를 사용하지 않는 경우
                return {
                    "response": "RAG가 비활성화되어 있습니다.",
                    "context": "",
                    "context_sources": [],
                    "rag_used": False,
                    "context_score": 0.0,
                    "context_length": 0
                }
            
            # 외부 RAG 우선 시도 (활성화된 경우)
            context = ""
            context_sources = []
            external_rag_used = False
            
            if use_external_rag and self.external_rag_service.enabled:
                logger.info("외부 RAG 서비스 시도 중...")
                external_result = await self.external_rag_service.query(query, top_k)
                
                if external_result["success"] and external_result["total_results"] > 0:
                    # 외부 RAG 성공 시 결과 사용
                    external_rag_used = True
                    context_parts = []
                    
                    for result in external_result["results"]:
                        if result.get("document"):
                            context_parts.append(result["document"])
                    
                    context = "\n\n".join(context_parts)
                    context_sources = [
                        {
                            "content": result.get("document", ""),
                            "metadata": result.get("metadata", {}),
                            "score": 0.9 if result.get("distance") is None else (1.0 - result.get("distance", 0)),  # 외부 RAG는 기본 높은 점수
                            "source": "external_rag"
                        }
                        for result in external_result["results"]
                    ]
                    
                    # 외부 RAG 점수 계산 및 업데이트
                    if context_sources:
                        total_score = sum(source.get('score', 0) for source in context_sources)
                        self.last_context_score = total_score / len(context_sources)
                        self.last_context_length = len(context)
                    else:
                        self.last_context_score = 0.0
                        self.last_context_length = 0
                    
                    logger.info(f"외부 RAG 사용: {len(context_sources)}개 결과, 응답시간: {external_result.get('response_time', 0):.3f}초, 평균 점수: {self.last_context_score:.3f}")
                else:
                    logger.info(f"외부 RAG 실패: {external_result.get('message', '알 수 없는 오류')}")
                    
                    # 폴백 설정이 활성화된 경우 로컬 RAG 사용
                    if self.external_rag_service.fallback_to_local:
                        logger.info("로컬 RAG로 폴백...")
                        context, context_sources = self.retrieve_context(query, top_k)
                    else:
                        logger.warning("외부 RAG 실패 및 폴백 비활성화로 인해 컨텍스트 없음")
            else:
                # 외부 RAG 비활성화된 경우 로컬 RAG 사용
                if not use_external_rag:
                    logger.info("외부 RAG 비활성화, 로컬 RAG 사용")
                else:
                    logger.info("외부 RAG 서비스 비활성화, 로컬 RAG 사용")
                
                context, context_sources = self.retrieve_context(query, top_k)
            
            # 컨텍스트 품질 평가
            context_quality = self._evaluate_context_quality(context, context_sources)
            
            # RAG 사용 여부 결정
            should_use_rag = self._should_use_rag_for_query(query, context, context_sources, context_quality)
            
            if not should_use_rag:
                logger.info(f"RAG 사용하지 않음 - 컨텍스트 품질: {context_quality}, 평균 점수: {self.last_context_score:.3f}")
                
                # RAG를 사용하지 않을 때도 AI 모델을 통해 응답 생성
                try:
                    logger.info("일반 AI 응답 생성 시도...")
                    
                    # 시스템 프롬프트 설정
                    if not system_prompt:
                        system_prompt = "당신은 친근하고 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 대해 자연스럽고 유용한 답변을 제공해주세요."
                    
                    # 일반 프롬프트 생성
                    general_prompt = f"{system_prompt}\n\n질문: {query}\n\n답변:"
                    
                    # 방법 1: LangChain OllamaLLM 시도
                    try:
                        llm = OllamaLLM(
                            model=model_name or settings.default_model,
                            base_url=settings.ollama_base_url,
                            timeout=settings.ollama_timeout
                        )
                        response = llm.invoke(general_prompt)
                        logger.info("일반 AI 응답 생성 성공")
                        
                    except Exception as e:
                        logger.warning(f"LangChain OllamaLLM 실패: {e}")
                        
                        # 방법 2: 직접 Ollama API 호출
                        try:
                            import requests
                            
                            ollama_response = requests.post(
                                f"{settings.ollama_base_url}/api/generate",
                                json={
                                    "model": model_name or settings.default_model,
                                    "prompt": general_prompt,
                                    "stream": False,
                                    "options": {
                                        "temperature": settings.default_temperature,
                                        "top_p": settings.default_top_p,
                                        "top_k": settings.default_top_k,
                                        "repeat_penalty": settings.default_repeat_penalty,
                                        "seed": settings.default_seed
                                    }
                                },
                                timeout=settings.ollama_timeout
                            )
                            
                            if ollama_response.status_code == 200:
                                response_data = ollama_response.json()
                                response = response_data.get('response', '응답을 생성할 수 없습니다.')
                                logger.info("직접 Ollama API 일반 응답 생성 성공")
                            else:
                                logger.error(f"Ollama API 오류: {ollama_response.status_code}")
                                response = f"Ollama 서버 오류: {ollama_response.status_code}"
                                
                        except Exception as api_error:
                            logger.error(f"직접 Ollama API 호출 실패: {api_error}")
                            response = "죄송합니다. AI 응답을 생성할 수 없습니다."
                            
                except Exception as general_error:
                    logger.error(f"일반 AI 응답 생성 실패: {general_error}")
                    response = "죄송합니다. AI 응답을 생성할 수 없습니다."
                
                return {
                    "response": response,
                    "context": "",
                    "context_sources": [],
                    "rag_used": False,
                    "context_score": 0.0,
                    "context_length": 0,
                    "context_quality": context_quality,
                    "reason": "컨텍스트 품질이 낮거나 관련성이 부족함"
                }
            
            # RAG 사용 횟수 증가
            self.rag_usage_count += 1
            logger.info(f"RAG 사용 (횟수: {self.rag_usage_count}/{self.max_rag_usage_per_session})")
            
            # 시스템 프롬프트 설정
            if not system_prompt:
                system_prompt = settings.rag_system_prompt
            
            # RAG 프롬프트 템플릿 - 더 간결하게 수정
            rag_prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template=f"""{system_prompt}

관련 문서:
{{context}}

질문: {{question}}

위의 관련 문서를 참고하여 질문에 답변해주세요. 문서에 관련 정보가 없는 경우 일반적인 지식을 사용하여 답변하세요."""
            )
            
            # 프롬프트 생성
            prompt = rag_prompt_template.format(context=context, question=query)
            
            # 응답 생성 (여러 방법 시도)
            response = None
            
            # 방법 1: LangChain OllamaLLM 시도
            try:
                logger.info("LangChain OllamaLLM으로 응답 생성 시도...")
                llm = OllamaLLM(
                    model=model_name or settings.default_model,
                    base_url=settings.ollama_base_url,
                    timeout=settings.ollama_timeout
                )
                response = llm.invoke(prompt)
                logger.info("LangChain OllamaLLM 응답 생성 성공")
                
            except Exception as e:
                logger.warning(f"LangChain OllamaLLM 실패: {e}")
                
                # 방법 2: 직접 Ollama API 호출
                try:
                    logger.info("직접 Ollama API로 응답 생성 시도...")
                    import requests
                    
                    ollama_response = requests.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": model_name or settings.default_model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": settings.default_temperature,
                                "top_p": settings.default_top_p,
                                "top_k": settings.default_top_k,
                                "repeat_penalty": settings.default_repeat_penalty,
                                "seed": settings.default_seed
                            }
                        },
                        timeout=settings.ollama_timeout
                    )
                    
                    if ollama_response.status_code == 200:
                        response_data = ollama_response.json()
                        response = response_data.get('response', '응답을 생성할 수 없습니다.')
                        logger.info("직접 Ollama API 응답 생성 성공")
                    else:
                        logger.error(f"Ollama API 오류: {ollama_response.status_code}")
                        response = f"Ollama 서버 오류: {ollama_response.status_code}"
                        
                except Exception as api_error:
                    logger.error(f"직접 Ollama API 호출 실패: {api_error}")
                    
                    # 방법 3: 컨텍스트 기반 간단한 응답 생성
                    try:
                        logger.info("컨텍스트 기반 간단한 응답 생성...")
                        response = self._generate_simple_response(query, context, context_sources)
                        logger.info("컨텍스트 기반 응답 생성 성공")
                        
                    except Exception as simple_error:
                        logger.error(f"간단한 응답 생성 실패: {simple_error}")
                        response = "죄송합니다. AI 응답을 생성할 수 없습니다. 관련 문서는 검색되었지만 응답 생성에 실패했습니다."
            
            return {
                "response": response,
                "context": context,
                "context_sources": context_sources,
                "rag_used": True,
                "external_rag_used": external_rag_used,
                "context_score": self.last_context_score,
                "context_length": self.last_context_length,
                "context_quality": context_quality
            }
            
        except Exception as e:
            logger.error(f"RAG 응답 생성 실패: {e}")
            return {
                "response": f"RAG 응답 생성 중 오류가 발생했습니다: {str(e)}",
                "context": "",
                "context_sources": [],
                "rag_used": False,
                "context_score": 0.0,
                "context_length": 0,
                "error": str(e)
            }
    
    def _should_use_mcp(self, query: str, model_name: str = None, session_id: str = None, ui_mcp_enabled: bool = True) -> bool:
        """쿼리가 MCP 서비스를 사용해야 하는지 확인합니다."""
        # MCP 클라이언트 서비스의 결정 방식 사용 (UI 설정 포함)
        return self.mcp_service._should_use_mcp(query, model_name, session_id, ui_mcp_enabled=ui_mcp_enabled)
    
    async def _generate_rag_with_mcp_response(self, query: str, model_name: str = None, 
                                            top_k: int = 5, system_prompt: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        RAG와 MCP를 함께 사용하여 응답을 생성합니다.
        
        Args:
            query: 사용자 질문
            model_name: 사용할 모델명
            top_k: 검색할 문서 수
            system_prompt: 시스템 프롬프트
            session_id: 세션 ID
            
        Returns:
            Dict: 응답 정보
        """
        try:
            # 1. RAG 컨텍스트 검색 (외부 RAG 우선 사용)
            context, context_sources = await self.retrieve_context_with_external_rag(query, top_k, use_external_rag=True)
            
            # 2. MCP 서비스 요청 (외부 RAG 컨텍스트와 함께)
            mcp_response, mcp_success = await self.mcp_service.process_rag_with_mcp(
                query, self, session_id=session_id, model_name=model_name
            )
            
            # 3. 통합 응답 생성
            if mcp_success and mcp_response:
                # MCP 응답이 있는 경우 - MCP 응답만 사용
                response = mcp_response
                
                # MCP가 성공적으로 응답을 제공한 경우 RAG 컨텍스트는 추가하지 않음
                # (날씨, 주식 등 실시간 정보는 MCP가 더 정확함)
                
                return {
                    "response": response,
                    "context": "",
                    "context_sources": [],
                    "rag_used": False,
                    "mcp_used": True,
                    "context_score": self.last_context_score,
                    "context_length": self.last_context_length,
                    "mcp_response": mcp_response
                }
            else:
                # MCP 응답이 없는 경우 외부 RAG 컨텍스트 사용
                logger.info("MCP 응답 없음, 외부 RAG 컨텍스트 사용")
                
                # 컨텍스트 품질 평가
                context_quality = self._evaluate_context_quality(context, context_sources)
                
                # RAG 사용 여부 결정
                should_use_rag = self._should_use_rag_for_query(query, context, context_sources, context_quality)
                
                if should_use_rag and context:
                    # 외부 RAG 컨텍스트로 응답 생성
                    try:
                        logger.info("외부 RAG 컨텍스트로 AI 응답 생성 시도...")
                        
                        # 시스템 프롬프트 설정
                        if not system_prompt:
                            system_prompt = "당신은 친근하고 도움이 되는 AI 어시스턴트입니다. 제공된 컨텍스트를 바탕으로 사용자의 질문에 대해 정확하고 유용한 답변을 제공해주세요."
                        
                        # RAG 프롬프트 생성
                        rag_prompt = f"{system_prompt}\n\n컨텍스트:\n{context}\n\n질문: {query}\n\n답변:"
                        
                        # AI 모델을 사용하여 응답 생성
                        from src.config.settings import get_settings
                        settings = get_settings()
                        
                        try:
                            # 방법 1: LangChain OllamaLLM 시도
                            llm = OllamaLLM(
                                model=model_name or settings.default_model,
                                base_url=settings.ollama_base_url,
                                timeout=settings.ollama_timeout
                            )
                            response = llm.invoke(rag_prompt)
                            logger.info("외부 RAG 컨텍스트로 AI 응답 생성 성공")
                            
                        except Exception as e:
                            logger.warning(f"LangChain OllamaLLM 실패: {e}")
                            
                            # 방법 2: 직접 Ollama API 호출
                            try:
                                import requests
                                
                                ollama_response = requests.post(
                                    f"{settings.ollama_base_url}/api/generate",
                                    json={
                                        "model": model_name or settings.default_model,
                                        "prompt": rag_prompt,
                                        "stream": False,
                                        "options": {
                                            "temperature": settings.default_temperature,
                                            "top_p": settings.default_top_p,
                                            "top_k": settings.default_top_k,
                                            "repeat_penalty": settings.default_repeat_penalty,
                                            "seed": settings.default_seed
                                        }
                                    },
                                    timeout=settings.ollama_timeout
                                )
                                
                                if ollama_response.status_code == 200:
                                    response_data = ollama_response.json()
                                    response = response_data.get('response', '응답을 생성할 수 없습니다.')
                                    logger.info("외부 RAG 컨텍스트로 AI 응답 생성 성공")
                                else:
                                    logger.error(f"Ollama API 오류: HTTP {ollama_response.status_code}")
                                    response = "외부 RAG 컨텍스트로 응답을 생성할 수 없습니다."
                                    
                            except Exception as e2:
                                logger.error(f"직접 API 호출 실패: {e2}")
                                response = "외부 RAG 컨텍스트로 응답을 생성할 수 없습니다."
                        
                        return {
                            "response": response,
                            "context": context,
                            "context_sources": context_sources,
                            "rag_used": True,
                            "mcp_used": False,
                            "external_rag_used": True,
                            "context_score": self.last_context_score,
                            "context_length": self.last_context_length,
                            "success": True
                        }
                        
                    except Exception as e:
                        logger.error(f"외부 RAG 컨텍스트로 응답 생성 실패: {e}")
                        response = "외부 RAG 컨텍스트로 응답을 생성할 수 없습니다."
                        
                        return {
                            "response": response,
                            "context": context,
                            "context_sources": context_sources,
                            "rag_used": False,
                            "mcp_used": False,
                            "external_rag_used": True,
                            "context_score": self.last_context_score,
                            "context_length": self.last_context_length,
                            "success": False
                        }
                else:
                    # 외부 RAG 컨텍스트도 없는 경우 일반 RAG 사용
                    logger.info("외부 RAG 컨텍스트도 없음, 일반 RAG 사용")
                    return self.generate_rag_response(
                        query, model_name, use_rag=True, top_k=top_k, 
                        system_prompt=system_prompt, use_mcp=False
                    )
                
        except Exception as e:
            logger.error(f"RAG + MCP 응답 생성 실패: {e}")
            # 오류 발생 시 일반 RAG로 폴백
            return self.generate_rag_response(
                query, model_name, use_rag=True, top_k=top_k, 
                system_prompt=system_prompt, use_mcp=False
            )
    
    def _generate_simple_response(self, query: str, context: str, context_sources: List[Dict]) -> str:
        """컨텍스트 기반 간단한 응답 생성"""
        try:
            # 컨텍스트에서 관련 정보 추출
            context_lower = context.lower()
            query_lower = query.lower()
            
            # 질문 유형에 따른 응답 생성
            if "어떻게" in query or "방법" in query or "업로드" in query:
                if "pdf" in context_lower:
                    return "PDF 파일은 pypdf를 사용하여 전처리되며, 텍스트 추출 후 KURE 임베딩 모델로 벡터화되어 ChromaDB에 저장됩니다."
                elif "문서" in context_lower:
                    return "문서는 다양한 형식(PDF, DOCX, TXT, MD)을 지원하며, 자동으로 전처리 후 벡터 저장소에 저장됩니다."
            
            elif "무엇" in query or "모델" in query or "임베딩" in query:
                if "kure" in context_lower or "nlpai-lab" in context_lower:
                    return "이 시스템은 nlpai-lab/KURE-v1 임베딩 모델을 사용합니다. 이는 한국어에 특화된 고성능 임베딩 모델입니다."
                elif "chromadb" in context_lower:
                    return "벡터 저장소로 ChromaDB를 사용하여 고성능 문서 검색을 제공합니다."
            
            elif "기능" in query or "시스템" in query:
                return "이 시스템은 RAG(Retrieval-Augmented Generation) 기능을 제공하는 AI 채팅 시스템입니다. 주요 기능으로는 PDF 문서 업로드 및 전처리, KURE 임베딩 모델을 사용한 벡터화, ChromaDB를 사용한 벡터 저장소, LangChain을 사용한 RAG 응답 생성이 있습니다."
            
            # 기본 응답
            if context_sources:
                source_info = f"검색된 {len(context_sources)}개 문서를 참고하여"
                return f"{source_info} 답변드립니다. 관련 문서에서 해당 정보를 찾을 수 있습니다."
            else:
                return "관련 문서를 찾을 수 없어 일반적인 지식으로 답변합니다."
                
        except Exception as e:
            logger.error(f"간단한 응답 생성 중 오류: {e}")
            return "컨텍스트에서 해당 정보를 찾을 수 없습니다."
    
    def _evaluate_context_quality(self, context: str, context_sources: List[Dict]) -> str:
        """
        컨텍스트 품질을 평가합니다.
        외부 RAG와 로컬 RAG에 대해 다른 기준을 적용합니다.
        
        Returns:
            str: "high", "medium", "low"
        """
        if not context_sources:
            return "low"
        
        # 평균 유사도 점수
        avg_score = sum(r.get('score', 0) for r in context_sources) / len(context_sources)
        
        # 컨텍스트 길이
        context_length = len(context)
        
        # 최고 점수
        max_score = max(r.get('score', 0) for r in context_sources)
        
        # 최저 점수
        min_score = min(r.get('score', 0) for r in context_sources)
        
        # 외부 RAG 여부 확인
        is_external_rag = any(r.get('source') == 'external_rag' for r in context_sources)
        
        if is_external_rag:
            # 외부 RAG에 대한 관대한 기준
            if (avg_score >= 0.8 and context_length >= 100):
                return "high"
            elif (avg_score >= 0.7 and context_length >= 50):
                return "medium"
            else:
                return "low"
        else:
            # 로컬 RAG에 대한 엄격한 기준
            if (avg_score >= 0.98 and max_score >= 0.99 and min_score >= 0.97 
                and context_length >= 200 and context_length <= 1000):
                return "high"
            elif (avg_score >= 0.95 and max_score >= 0.98 and min_score >= 0.93 
                  and context_length >= 150 and context_length <= 800):
                return "medium"
            else:
                return "low"
    
    def get_rag_status(self) -> Dict[str, Any]:
        """RAG 서비스의 상태를 반환합니다."""
        try:
            # 벡터 저장소 상태 확인
            total_documents = document_service.get_document_count()
            
            # RAG 문서 수 확인
            rag_documents = document_service.search_documents(
                query="", 
                top_k=1000, 
                filter_metadata={"source": "rag"}
            )
            rag_document_count = len(rag_documents)
            
            # RAG 디렉토리 파일 수 확인
            rag_files = []
            if self.rag_directory.exists():
                rag_files = [f.name for f in self.rag_directory.glob("*") 
                           if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.docx', '.md', '.xlsx']]
            
            # 외부 RAG 상태 정보 추가
            external_rag_status = self.external_rag_service.get_status()
            
            return {
                "status": "active",
                "total_documents": total_documents,
                "rag_documents": rag_document_count,
                "rag_files": len(rag_files),
                "rag_file_list": rag_files,
                "similarity_threshold": self.similarity_threshold,
                "context_weight": self.context_weight,
                "min_context_length": self.min_context_length,
                "max_context_length": self.max_context_length,
                "min_avg_score_for_rag": self.min_avg_score_for_rag,
                "max_context_chunks": self.max_context_chunks,
                "max_rag_usage_per_session": self.max_rag_usage_per_session,
                "rag_cooldown_queries": self.rag_cooldown_queries,
                "current_rag_usage_count": self.rag_usage_count,
                "last_context_score": self.last_context_score,
                "last_context_length": self.last_context_length,
                "rag_usage_remaining": max(0, self.max_rag_usage_per_session - self.rag_usage_count),
                "external_rag": external_rag_status
            }
            
        except Exception as e:
            logger.error(f"RAG 상태 확인 중 오류: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def reload_rag_documents(self) -> Dict[str, Any]:
        """RAG 문서를 재로드합니다."""
        try:
            logger.info("RAG 문서 재로드 시작")
            
            # 기존 RAG 문서 삭제
            existing_docs = document_service.get_all_documents()
            rag_docs_to_delete = [doc["id"] for doc in existing_docs 
                                if doc.get("metadata", {}).get("source") == "rag"]
            
            for doc_id in rag_docs_to_delete:
                document_service.delete_document(doc_id)
            
            logger.info(f"기존 RAG 문서 {len(rag_docs_to_delete)}개 삭제 완료")
            
            # RAG 문서 재로드
            self._initialize_rag_documents()
            
            # 상태 반환
            status = self.get_rag_status()
            status["message"] = "RAG 문서가 성공적으로 재로드되었습니다."
            
            return status
            
        except Exception as e:
            logger.error(f"RAG 문서 재로드 실패: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def reset_rag_usage_count(self) -> Dict[str, Any]:
        """RAG 사용 횟수를 리셋합니다."""
        try:
            self.rag_usage_count = 0
            logger.info("RAG 사용 횟수가 리셋되었습니다.")
            return {
                "status": "success",
                "message": "RAG 사용 횟수가 리셋되었습니다.",
                "rag_usage_count": self.rag_usage_count
            }
        except Exception as e:
            logger.error(f"RAG 사용 횟수 리셋 중 오류: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def update_settings(self, similarity_threshold: Optional[float] = None, 
                       context_weight: Optional[float] = None,
                       min_context_length: Optional[int] = None,
                       max_context_length: Optional[int] = None,
                       min_avg_score_for_rag: Optional[float] = None,
                       max_context_chunks: Optional[int] = None,
                       max_rag_usage_per_session: Optional[int] = None,
                       rag_cooldown_queries: Optional[int] = None) -> Dict[str, Any]:
        """RAG 설정을 업데이트합니다."""
        try:
            if similarity_threshold is not None:
                self.similarity_threshold = max(similarity_threshold, 0.95)  # 최소 0.95 보장
                # 검색기도 업데이트
                self.retriever.similarity_threshold = self.similarity_threshold
                logger.info(f"유사도 임계값 업데이트: {self.similarity_threshold}")
            
            if context_weight is not None:
                self.context_weight = context_weight
                logger.info(f"컨텍스트 가중치 업데이트: {context_weight}")
            
            if min_context_length is not None:
                self.min_context_length = min_context_length
                logger.info(f"최소 컨텍스트 길이 업데이트: {min_context_length}")
            
            if max_context_length is not None:
                self.max_context_length = max_context_length
                logger.info(f"최대 컨텍스트 길이 업데이트: {max_context_length}")
            
            if min_avg_score_for_rag is not None:
                self.min_avg_score_for_rag = min_avg_score_for_rag
                logger.info(f"RAG 사용 최소 평균 점수 업데이트: {min_avg_score_for_rag}")
            
            if max_context_chunks is not None:
                self.max_context_chunks = max_context_chunks
                logger.info(f"최대 컨텍스트 청크 수 업데이트: {max_context_chunks}")
            
            if max_rag_usage_per_session is not None:
                self.max_rag_usage_per_session = max_rag_usage_per_session
                logger.info(f"세션당 최대 RAG 사용 횟수 업데이트: {max_rag_usage_per_session}")
            
            if rag_cooldown_queries is not None:
                self.rag_cooldown_queries = rag_cooldown_queries
                logger.info(f"RAG 쿨다운 쿼리 수 업데이트: {rag_cooldown_queries}")
            
            return {
                "status": "success",
                "message": "RAG 설정이 업데이트되었습니다.",
                "settings": {
                    "similarity_threshold": self.similarity_threshold,
                    "context_weight": self.context_weight,
                    "min_context_length": self.min_context_length,
                    "max_context_length": self.max_context_length,
                    "min_avg_score_for_rag": self.min_avg_score_for_rag,
                    "max_context_chunks": self.max_context_chunks,
                    "max_rag_usage_per_session": self.max_rag_usage_per_session,
                    "rag_cooldown_queries": self.rag_cooldown_queries,
                    "current_rag_usage_count": self.rag_usage_count
                }
            }
            
        except Exception as e:
            logger.error(f"RAG 설정 업데이트 중 오류: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _load_korean_cities(self) -> List[str]:
        """저장된 파일에서 한국 도시 목록을 로드합니다."""
        try:
            # 먼저 weather_cities.csv 파일 시도
            csv_file = Path("data/weather_cities.csv")
            if csv_file.exists():
                import csv
                cities = []
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        city_name = row.get('city_name', '').strip()
                        if city_name:
                            cities.append(city_name)
                
                if cities:
                    logger.debug(f"CSV 파일에서 도시 목록 로드 완료: {len(cities)}개 도시")
                    return cities
            
            # CSV 파일이 없거나 비어있으면 JSON 파일 시도
            json_file = Path("data/korean_cities.json")
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cities = data.get("cities", [])
                if cities:
                    logger.debug(f"JSON 파일에서 도시 목록 로드 완료: {len(cities)}개 도시")
                    return cities
            
            # 파일이 없거나 비어있으면 기본 도시 목록 사용
            logger.warning("도시 목록 파일이 존재하지 않거나 비어있습니다. 기본 도시 목록을 사용합니다.")
            return self._get_default_cities()
                
        except Exception as e:
            logger.error(f"도시 목록 파일 로드 실패: {e}")
            return self._get_default_cities()
    
    def _get_default_cities(self) -> List[str]:
        """기본 도시 목록을 반환합니다. (파일이 없거나 로드 실패 시 사용)"""
        return [
            "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
            "수원", "성남", "의정부", "안양", "부천", "광명", "평택", "동두천",
            "안산", "고양", "과천", "구리", "남양주", "오산", "시흥", "군포",
            "의왕", "하남", "용인", "파주", "이천", "안성", "김포", "화성",
            "광주", "여주", "양평", "양주", "포천", "연천", "가평",
            "춘천", "원주", "강릉", "태백", "속초", "삼척", "동해", "횡성",
            "영월", "평창", "정선", "철원", "화천", "양구", "인제", "고성",
            "양양", "홍천", "태안", "당진", "서산", "논산", "계룡", "공주",
            "보령", "아산", "서천", "천안", "예산", "금산", "부여",
            "청양", "홍성", "제주", "서귀포", "포항", "경주", "김천", "안동",
            "구미", "영주", "영천", "상주", "문경", "경산", "군산", "익산",
            "정읍", "남원", "김제", "완주", "진안", "무주", "장수", "임실",
            "순창", "고창", "부안", "여수", "순천", "나주", "광양", "담양",
            "곡성", "구례", "고흥", "보성", "화순", "장흥", "강진", "해남",
            "영암", "무안", "함평", "영광", "장성", "완도", "진도", "신안"
        ]

    def _should_use_rag_for_query(self, query: str, context: str, context_sources: List[Dict], context_quality: str) -> bool:
        """
        주어진 쿼리에 대해 RAG를 사용해야 하는지 판단합니다.
        외부 RAG와 로컬 RAG에 대해 다른 기준을 적용합니다.
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            context_sources: 컨텍스트 소스 정보
            context_quality: 컨텍스트 품질
            
        Returns:
            bool: RAG 사용 여부
        """
        # 기본 검증
        if not context or not context_sources:
            return False
        
        # 외부 RAG 여부 확인
        is_external_rag = any(r.get('source') == 'external_rag' for r in context_sources)
        
        if is_external_rag:
            # 외부 RAG에 대한 관대한 기준
            # 컨텍스트 품질이 medium 이상이면 사용
            if context_quality in ["high", "medium"]:
                # 평균 유사도 점수가 적당하면 사용
                if self.last_context_score >= 0.7:
                    # 컨텍스트 길이가 적당하면 사용
                    if len(context) >= 50:
                        return True
            return False
        else:
            # 로컬 RAG에 대한 엄격한 기준
            # 컨텍스트 품질이 high여야 함
            if context_quality != "high":
                return False
            
            # 평균 유사도 점수가 너무 낮은 경우
            if self.last_context_score < self.min_avg_score_for_rag:
                return False
            
            # 컨텍스트 길이 검증
            if len(context) < self.min_context_length or len(context) > self.max_context_length:
                return False
            
            # RAG 사용 빈도 제한
            if self.rag_usage_count >= self.max_rag_usage_per_session:
                return False
            
            # RAG 사용 빈도가 높은 경우 쿨다운 적용
            if self.rag_usage_count > 0:
                # 마지막 RAG 사용 후 일정 쿼리 수만큼 일반 응답 사용
                return False
            
            # RAG가 필요한 특정 질문 패턴만 허용
            rag_required_patterns = [
                "문서", "파일", "업로드", "처리", "벡터", "임베딩", "chromadb", "kure",
                "시스템", "기능", "설정", "구성", "아키텍처", "모델", "전처리"
            ]
            
            query_lower = query.lower()
            has_rag_required_pattern = any(pattern in query_lower for pattern in rag_required_patterns)
            
            # RAG가 필요한 패턴이 없으면 사용하지 않음
            if not has_rag_required_pattern:
                return False
            
            # 일반적인 질문 패턴 확인 (RAG가 불필요한 경우들)
            general_question_patterns = [
                "안녕", "반갑", "고마워", "감사", "좋아", "괜찮", "네", "예",
                "뭐해", "뭐하고", "어떻게", "무엇", "누구", "언제", "어디",
                "날씨", "기온", "습도", "비", "눈", "맑음", "흐림",
                "주가", "주식", "종목", "증시", "코스피", "코스닥",
                "검색", "찾기", "최신", "뉴스", "정보"
            ]
            
            is_general_question = any(pattern in query_lower for pattern in general_question_patterns)
            
            # 일반적인 질문은 RAG 사용하지 않음
            if is_general_question:
                return False
            
            # 컨텍스트 소스가 너무 적거나 많은 경우
            if len(context_sources) < 1 or len(context_sources) > 2:
                return False
        
        # 모든 조건을 만족하는 경우에만 RAG 사용
        return True

# 전역 인스턴스 생성
rag_service = RAGService() 