import json
import logging
from typing import List, Dict, Any, Optional
import requests

from langchain.prompts import PromptTemplate
from langchain.schema import Document

from src.config.settings import settings
from src.services.document_service import document_service
from src.services.llm_decision_service import llm_decision_service
from src.services.websearch_service import websearch_service

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.context_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""
다음 컨텍스트를 사용하여 질문에 답변해주세요. 
구글 검색 결과가 있다면 최신 정보를 우선적으로 참고하세요.
컨텍스트에서 정보를 찾을 수 없는 경우, "컨텍스트에서 해당 정보를 찾을 수 없습니다."라고 답변하세요.

컨텍스트:
{context}

질문: {question}

답변:"""
        )

    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        docs = document_service.search_documents(query, top_k=top_k)
        context = "\n".join([doc.page_content for doc in docs])
        return context

    def build_context_prompt(self, context: str, question: str) -> str:
        return self.context_template.format(context=context, question=question)

    def generate_response_with_rag(self, query: str, model: str, top_k: int = 5, system_prompt: Optional[str] = None) -> str:
        # 1. 검색 필요성 판단
        needs_search = llm_decision_service.needs_web_search(query, model_name=model)
        web_context = ""
        if needs_search:
            # 2. 구글 검색
            web_context = websearch_service.search_web(query)
            logger.info(f"구글 검색 결과 사용: {len(web_context)} 문자")
        # 3. 기존 RAG context
        rag_context = self.retrieve_context(query, top_k=top_k)
        # 4. context 합치기 (구글 검색 결과를 우선 배치)
        context_parts = []
        if web_context:
            context_parts.append(f"🌐 [실시간 구글 검색 결과 - 최신 정보]\n{web_context}")
        if rag_context:
            context_parts.append(f"📄 [내부 문서]\n{rag_context}")
        
        full_context = "\n\n".join(context_parts) if context_parts else "검색된 정보가 없습니다."
        
        prompt = self.build_context_prompt(full_context, query)
        # 5. LLM 호출
        from langchain_community.llms import Ollama
        llm = Ollama(model=model)
        response = llm.invoke(prompt)
        return response

rag_service = RAGService() 