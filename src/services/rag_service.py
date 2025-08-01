import json
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_ollama import OllamaLLM

from src.config.settings import settings
from src.services.document_service import document_service

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.rag_directory = Path("static/RAG")
        
        # 개선된 프롬프트 템플릿 - RAG 데이터와 일반 지식의 균형
        self.context_template = PromptTemplate(
            input_variables=["context", "question", "time_context"],
            template="""
당신은 도움이 되는 AI 어시스턴트입니다. 다음 지침을 따라 답변해주세요:

1. 제공된 컨텍스트 정보가 있다면 우선적으로 참고하세요
2. 컨텍스트에 없는 정보는 일반적인 지식으로 답변하세요
3. 컨텍스트와 일반 지식을 적절히 조합하여 완전한 답변을 제공하세요
4. 컨텍스트 정보가 부정확하거나 오래된 경우, 최신 정보를 우선시하세요
5. 답변할 때 정보의 출처를 명확히 구분해주세요

시간 컨텍스트: {time_context}

참고 컨텍스트:
{context}

질문: {question}

답변:"""
        )
        
        # 하이브리드 응답을 위한 일반 프롬프트
        self.general_template = PromptTemplate(
            input_variables=["question"],
            template="""
당신은 도움이 되는 AI 어시스턴트입니다. 
다음 질문에 대해 정확하고 유용한 답변을 제공해주세요.

질문: {question}

답변:"""
        )
        
        # 설정값들
        self.similarity_threshold = 0.5  # 유사도 임계값 상향 조정
        self.context_weight = 0.7  # 컨텍스트 가중치
        self.min_context_length = 50  # 최소 컨텍스트 길이
        
        # RAG 디렉토리 초기화 및 문서 로드
        self._initialize_rag_documents()
    
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
            logger.error(f"RAG 디렉토리 초기화 실패: {e}")
    
    def _is_document_already_processed(self, filename: str) -> bool:
        """문서가 이미 처리되었는지 확인합니다."""
        try:
            # 벡터 저장소에서 해당 파일명으로 검색 (필터 없이)
            results = document_service.search_documents(
                query=filename,
                top_k=1
            )
            # 파일명이 메타데이터에 포함되어 있는지 확인
            for result in results:
                if filename in str(result.get("metadata", {})):
                    return True
            return False
        except Exception as e:
            logger.error(f"문서 처리 상태 확인 실패: {e}")
            return False
    
    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        """쿼리에 관련된 컨텍스트를 검색합니다."""
        try:
            # 필터 없이 모든 문서에서 검색 (RAG 문서 우선)
            docs = document_service.search_documents(
                query=query, 
                top_k=top_k
            )
            
            if not docs:
                logger.warning(f"쿼리에 대한 관련 문서를 찾을 수 없습니다: {query}")
                return ""
            
            # 컨텍스트 구성 - 임계값 없이 모든 결과 포함
            context_parts = []
            total_score = 0
            valid_docs = 0
            
            for doc in docs:
                content = doc.get("content", "")
                score = doc.get("score", 0.0)
                filename = doc.get("metadata", {}).get("filename", "unknown")
                
                # 임계값 없이 모든 문서 포함 (디버깅용)
                context_parts.append(f"[{filename}] {content}")
                total_score += score
                valid_docs += 1
            
            # 컨텍스트 품질 평가
            if not context_parts:
                logger.info("검색된 문서가 없습니다.")
                return ""
            
            avg_score = total_score / valid_docs if valid_docs > 0 else 0
            context = "\n\n".join(context_parts)
            
            logger.info(f"컨텍스트 검색 완료 - {len(context_parts)}개 문서, 평균 유사도: {avg_score:.3f}, 길이: {len(context)} 문자")
            
            return context
            
        except Exception as e:
            logger.error(f"컨텍스트 검색 실패: {e}")
            return ""
    
    def build_context_prompt(self, context: str, question: str, time_context: str = "") -> str:
        """컨텍스트를 포함한 프롬프트를 구성합니다."""
        return self.context_template.format(
            context=context, 
            question=question, 
            time_context=time_context
        )
    
    def build_general_prompt(self, question: str) -> str:
        """일반 응답을 위한 프롬프트를 구성합니다."""
        return self.general_template.format(question=question)
    
    def generate_hybrid_response(self, query: str, model: str, top_k: int = 5, system_prompt: Optional[str] = None) -> str:
        """하이브리드 응답 시스템 - RAG와 일반 지식 조합"""
        try:
            logger.info(f"하이브리드 응답 생성 시작 - 쿼리: {query[:100]}...")
            
            # RAG 컨텍스트 검색
            rag_context = self.retrieve_context(query, top_k=top_k)
            
            # 컨텍스트 품질 평가
            context_quality = self._evaluate_context_quality(rag_context)
            
            # 응답 전략 결정
            if context_quality == "high":
                # 고품질 컨텍스트가 있는 경우 - RAG 중심 응답
                logger.info("고품질 컨텍스트 발견 - RAG 중심 응답 생성")
                return self._generate_rag_centered_response(query, model, rag_context, system_prompt)
            
            elif context_quality == "medium":
                # 중간 품질 컨텍스트가 있는 경우 - 하이브리드 응답
                logger.info("중간 품질 컨텍스트 발견 - 하이브리드 응답 생성")
                return self._generate_hybrid_response_internal(query, model, rag_context, system_prompt)
            
            else:
                # 컨텍스트가 없거나 품질이 낮은 경우 - 일반 응답
                logger.info("컨텍스트 없음 또는 낮은 품질 - 일반 응답 생성")
                return self._generate_general_response(query, model, system_prompt)
                
        except Exception as e:
            logger.error(f"하이브리드 응답 생성 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    def _evaluate_context_quality(self, context: str) -> str:
        """컨텍스트 품질을 평가합니다."""
        if not context:
            return "low"
        
        # 컨텍스트 길이와 내용 품질 평가
        context_length = len(context)
        
        if context_length < self.min_context_length:
            return "low"
        elif context_length < 500:
            return "medium"
        else:
            return "high"
    
    def _generate_rag_centered_response(self, query: str, model: str, context: str, system_prompt: Optional[str] = None) -> str:
        """RAG 중심 응답 생성"""
        try:
            # RAG 프롬프트 구성
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n참고 컨텍스트:\n{context}\n\n질문: {query}\n\n답변:"
            else:
                full_prompt = self.build_context_prompt(context, query, "")
            
            # LLM 호출
            llm = OllamaLLM(
                model=model,
                base_url=settings.ollama_base_url,
                temperature=0.7
            )
            
            logger.info("RAG 중심 응답 생성 중...")
            response = llm.invoke(full_prompt)
            
            logger.info(f"RAG 중심 응답 생성 완료 - {len(response)} 문자")
            return response
            
        except Exception as e:
            logger.error(f"RAG 중심 응답 생성 실패: {e}")
            return self._generate_general_response(query, model, system_prompt)
    
    def _generate_hybrid_response_internal(self, query: str, model: str, context: str, system_prompt: Optional[str] = None) -> str:
        """하이브리드 응답 생성 (내부 메서드)"""
        try:
            # 컨텍스트와 일반 지식을 조합한 프롬프트
            hybrid_prompt = f"""
당신은 도움이 되는 AI 어시스턴트입니다. 다음 지침을 따라 답변해주세요:

1. 제공된 컨텍스트 정보를 참고하되, 일반적인 지식도 함께 활용하세요
2. 컨텍스트 정보가 부족한 부분은 일반 지식으로 보완하세요
3. 정보의 출처를 명확히 구분하여 답변하세요
4. 컨텍스트 정보가 오래되었거나 부정확할 수 있음을 고려하세요

참고 컨텍스트:
{context}

질문: {query}

답변:"""
            
            if system_prompt:
                hybrid_prompt = f"{system_prompt}\n\n{hybrid_prompt}"
            
            # LLM 호출
            llm = OllamaLLM(
                model=model,
                base_url=settings.ollama_base_url,
                temperature=0.7
            )
            
            logger.info("하이브리드 응답 생성 중...")
            response = llm.invoke(hybrid_prompt)
            
            logger.info(f"하이브리드 응답 생성 완료 - {len(response)} 문자")
            return response
            
        except Exception as e:
            logger.error(f"하이브리드 응답 생성 실패: {e}")
            return self._generate_general_response(query, model, system_prompt)
    
    def _generate_general_response(self, query: str, model: str, system_prompt: Optional[str] = None) -> str:
        """일반 응답 생성"""
        try:
            # 일반 프롬프트 구성
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n질문: {query}\n\n답변:"
            else:
                full_prompt = self.build_general_prompt(query)
            
            # LLM 호출
            llm = OllamaLLM(
                model=model,
                base_url=settings.ollama_base_url,
                temperature=0.7
            )
            
            logger.info("일반 응답 생성 중...")
            response = llm.invoke(full_prompt)
            
            logger.info(f"일반 응답 생성 완료 - {len(response)} 문자")
            return response
            
        except Exception as e:
            logger.error(f"일반 응답 생성 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    def generate_response_with_rag(self, query: str, model: str, top_k: int = 5, system_prompt: Optional[str] = None) -> str:
        """기존 메서드 - 하이브리드 응답으로 대체"""
        return self.generate_hybrid_response(query, model, top_k, system_prompt)
    
    def get_rag_status(self) -> Dict[str, Any]:
        """RAG 서비스 상태를 반환합니다."""
        try:
            total_docs = document_service.get_document_count()
            rag_docs = len([doc for doc in document_service.get_all_documents() 
                          if doc.get("metadata", {}).get("source") == "rag"])
            
            return {
                "status": "active" if self.rag_directory.exists() else "inactive",
                "total_documents": total_docs,
                "rag_documents": rag_docs,
                "rag_directory": str(self.rag_directory),
                "vectorstore_status": f"active ({total_docs} documents)",
                "settings": {
                    "similarity_threshold": self.similarity_threshold,
                    "context_weight": self.context_weight,
                    "min_context_length": self.min_context_length
                }
            }
        except Exception as e:
            logger.error(f"RAG 상태 조회 실패: {e}")
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
    
    def update_settings(self, similarity_threshold: Optional[float] = None, 
                       context_weight: Optional[float] = None,
                       min_context_length: Optional[int] = None) -> Dict[str, Any]:
        """RAG 설정을 업데이트합니다."""
        try:
            if similarity_threshold is not None:
                self.similarity_threshold = similarity_threshold
                logger.info(f"유사도 임계값 업데이트: {similarity_threshold}")
            
            if context_weight is not None:
                self.context_weight = context_weight
                logger.info(f"컨텍스트 가중치 업데이트: {context_weight}")
            
            if min_context_length is not None:
                self.min_context_length = min_context_length
                logger.info(f"최소 컨텍스트 길이 업데이트: {min_context_length}")
            
            return {
                "status": "success",
                "message": "설정이 성공적으로 업데이트되었습니다.",
                "current_settings": {
                    "similarity_threshold": self.similarity_threshold,
                    "context_weight": self.context_weight,
                    "min_context_length": self.min_context_length
                }
            }
            
        except Exception as e:
            logger.error(f"설정 업데이트 실패: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# 전역 RAG 서비스 인스턴스
rag_service = RAGService() 