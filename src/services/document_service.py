import os
import uuid
import threading
import asyncio
import queue
import warnings
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import logging

# PyTorch FutureWarning 억제
warnings.filterwarnings('ignore', category=FutureWarning)

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
    UnstructuredExcelLoader
)
import docx2txt
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

from src.config.settings import settings

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        # HuggingFace API 키 설정
        if settings.huggingface_api_key:
            os.environ['HUGGINGFACE_API_KEY'] = settings.huggingface_api_key
        
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
        # 스레드 안전성을 위한 락 추가
        self._write_lock = threading.RLock()  # 재진입 가능한 락
        self._read_lock = threading.RLock()   # 읽기 작업용 락
        
        # 비동기 문서 처리를 위한 큐 시스템
        self._processing_queue = queue.Queue()
        self._processing_thread = None
        self._stop_processing = False
        self._start_processing_thread()
        
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """벡터 저장소 초기화"""
        try:
            # PostHog 텔레메트리 비활성화
            if not settings.chroma_anonymized_telemetry:
                os.environ['CHROMA_ANONYMIZED_TELEMETRY'] = 'false'
            
            os.makedirs(settings.chroma_persist_directory, exist_ok=True)
            
            # Chroma 클라이언트 설정
            client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
            
            self.vectorstore = Chroma(
                client=client,
                embedding_function=self.embeddings,
                collection_name="documents"
            )
            logger.info("벡터 저장소가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"벡터 저장소 초기화 실패: {e}")
            raise
    
    def _start_processing_thread(self):
        """문서 처리 스레드 시작"""
        if self._processing_thread is None or not self._processing_thread.is_alive():
            self._processing_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._processing_thread.start()
            logger.info("문서 처리 스레드가 시작되었습니다.")
    
    def _process_queue(self):
        """큐에서 문서 처리 작업을 처리하는 스레드"""
        while not self._stop_processing:
            try:
                # 큐에서 작업 가져오기 (1초 타임아웃)
                task = self._processing_queue.get(timeout=1)
                if task is None:  # 종료 신호
                    break
                
                content, filename, metadata, callback = task
                try:
                    # 실제 문서 처리 수행
                    doc_id = self._process_document_sync(content, filename, metadata)
                    if callback:
                        callback(True, doc_id, None)
                except Exception as e:
                    logger.error(f"문서 처리 실패: {e}")
                    if callback:
                        callback(False, None, str(e))
                finally:
                    self._processing_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"큐 처리 중 오류: {e}")
    
    def _process_document_sync(self, content: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """동기 문서 처리 (내부용)"""
        with self._write_lock:
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
            
            logger.info(f"문서 '{filename}'이 {len(chunks)}개 청크로 처리되어 저장되었습니다.")
            return doc_id
    
    def load_document(self, file_path: str) -> str:
        """문서 로드"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.pdf':
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                return "\n".join([doc.page_content for doc in documents])
            elif file_extension == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
                documents = loader.load()
                return "\n".join([doc.page_content for doc in documents])
            elif file_extension == '.docx':
                # docx2txt를 사용하여 .docx 파일 처리
                try:
                    text = docx2txt.process(file_path)
                    return text
                except Exception as e:
                    logger.error(f".docx 파일 처리 실패: {e}")
                    raise ValueError(f".docx 파일을 처리할 수 없습니다: {e}")

            elif file_extension == '.md':
                loader = UnstructuredMarkdownLoader(file_path)
                documents = loader.load()
                return "\n".join([doc.page_content for doc in documents])
            elif file_extension in ['.xlsx', '.xls']:
                loader = UnstructuredExcelLoader(file_path)
                documents = loader.load()
                return "\n".join([doc.page_content for doc in documents])
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {file_extension}")
        
        except Exception as e:
            logger.error(f"문서 로드 실패: {e}")
            raise
    
    def process_document(self, content: str, filename: str, metadata: Optional[Dict[str, Any]] = None, 
                        callback: Optional[Callable[[bool, Optional[str], Optional[str]], None]] = None) -> str:
        """문서 처리 및 벡터 저장소에 저장 (비동기 처리 지원)"""
        # 콜백이 제공된 경우 비동기 처리
        if callback:
            # 큐에 작업 추가
            self._processing_queue.put((content, filename, metadata, callback))
            return "processing"  # 처리 중임을 나타내는 ID
        
        # 콜백이 없는 경우 동기 처리 (기존 방식)
        return self._process_document_sync(content, filename, metadata)
    
    def search_documents(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """문서 검색 (스레드 안전)"""
        with self._read_lock:  # 읽기 작업 시 락 획득
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
        """저장된 문서 수 반환 (스레드 안전)"""
        with self._read_lock:  # 읽기 작업 시 락 획득
            try:
                return self.vectorstore._collection.count()
            except Exception as e:
                logger.error(f"문서 수 조회 실패: {e}")
                return 0
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """모든 문서 정보 반환 (스레드 안전)"""
        with self._read_lock:  # 읽기 작업 시 락 획득
            try:
                # 모든 문서 조회
                results = self.vectorstore._collection.get()
                
                documents = []
                if results and 'metadatas' in results:
                    for i, metadata in enumerate(results['metadatas']):
                        if metadata:  # None이 아닌 경우만
                            documents.append({
                                "id": metadata.get("doc_id", f"doc_{i}"),
                                "filename": metadata.get("filename", "unknown"),
                                "source": metadata.get("source", "unknown"),
                                "file_type": metadata.get("file_type", "unknown"),
                                "file_size": metadata.get("file_size", 0),
                                "metadata": metadata
                            })
                
                return documents
                
            except Exception as e:
                logger.error(f"모든 문서 조회 실패: {e}")
                return []
    
    def delete_document(self, doc_id: str) -> bool:
        """문서 삭제 (스레드 안전)"""
        with self._write_lock:  # 쓰기 작업 시 락 획득
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
        """벡터 저장소 상태 확인 (스레드 안전)"""
        with self._read_lock:  # 읽기 작업 시 락 획득
            try:
                count = self.get_document_count()
                return f"active ({count} documents)"
            except Exception as e:
                return f"error: {str(e)}"

    def get_queue_status(self) -> Dict[str, Any]:
        """큐 상태 확인"""
        return {
            "queue_size": self._processing_queue.qsize(),
            "processing_thread_alive": self._processing_thread.is_alive() if self._processing_thread else False
        }
    
    def cleanup_processing_queue(self):
        """처리 큐 정리"""
        try:
            while not self._processing_queue.empty():
                try:
                    self._processing_queue.get_nowait()
                    self._processing_queue.task_done()
                except queue.Empty:
                    break
            logger.info("처리 큐가 정리되었습니다.")
        except Exception as e:
            logger.error(f"처리 큐 정리 실패: {e}")
    
    def shutdown(self):
        """서비스 종료"""
        try:
            self._stop_processing = True
            # 종료 신호 전송
            self._processing_queue.put(None)
            
            # 처리 스레드 종료 대기
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5)
            
            logger.info("DocumentService가 종료되었습니다.")
        except Exception as e:
            logger.error(f"DocumentService 종료 실패: {e}")

# 싱글톤 인스턴스
document_service = DocumentService() 