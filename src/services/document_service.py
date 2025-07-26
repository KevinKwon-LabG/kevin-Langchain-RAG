import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

from src.config.settings import settings

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model_name,
            model_kwargs={'device': 'cpu'}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )
        self.vectorstore = None
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """벡터 저장소 초기화"""
        try:
            os.makedirs(settings.chroma_persist_directory, exist_ok=True)
            self.vectorstore = Chroma(
                persist_directory=settings.chroma_persist_directory,
                embedding_function=self.embeddings
            )
            logger.info("벡터 저장소가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"벡터 저장소 초기화 실패: {e}")
            raise
    
    def load_document(self, file_path: str) -> str:
        """문서 로드"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.pdf':
                loader = PyPDFLoader(file_path)
            elif file_extension == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_extension == '.docx':
                loader = Docx2txtLoader(file_path)
            elif file_extension == '.md':
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {file_extension}")
            
            documents = loader.load()
            return "\n".join([doc.page_content for doc in documents])
        
        except Exception as e:
            logger.error(f"문서 로드 실패: {e}")
            raise
    
    def process_document(self, content: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """문서 처리 및 벡터 저장소에 저장"""
        try:
            # 문서 ID 생성
            doc_id = str(uuid.uuid4())
            
            # 기본 메타데이터 설정
            base_metadata = {
                "filename": filename,
                "doc_id": doc_id,
                "created_at": datetime.now().isoformat(),
                "source": "upload"
            }
            
            if metadata:
                base_metadata.update(metadata)
            
            # 문서를 청크로 분할
            chunks = self.text_splitter.split_text(content)
            
            # LangChain Document 객체 생성
            documents = [
                Document(
                    page_content=chunk,
                    metadata={**base_metadata, "chunk_index": i}
                )
                for i, chunk in enumerate(chunks)
            ]
            
            # 벡터 저장소에 저장
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()
            
            logger.info(f"문서 '{filename}'이 {len(chunks)}개 청크로 처리되어 저장되었습니다.")
            return doc_id
            
        except Exception as e:
            logger.error(f"문서 처리 실패: {e}")
            raise
    
    def search_documents(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """문서 검색"""
        try:
            # 벡터 저장소에서 유사한 문서 검색
            results = self.vectorstore.similarity_search_with_score(
                query, 
                k=top_k,
                filter=filter_metadata
            )
            
            # 결과 포맷팅
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "id": doc.metadata.get("doc_id", "unknown"),
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
    
    def get_document_count(self) -> int:
        """저장된 문서 수 반환"""
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            logger.error(f"문서 수 조회 실패: {e}")
            return 0
    
    def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        try:
            # 해당 문서의 모든 청크 삭제
            self.vectorstore._collection.delete(
                where={"doc_id": doc_id}
            )
            logger.info(f"문서 '{doc_id}'가 삭제되었습니다.")
            return True
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}")
            return False
    
    def get_vectorstore_status(self) -> str:
        """벡터 저장소 상태 확인"""
        try:
            count = self.get_document_count()
            return f"active ({count} documents)"
        except Exception as e:
            return f"error: {str(e)}"

# 싱글톤 인스턴스
document_service = DocumentService() 