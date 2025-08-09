"""
워드 파일 임베딩 서비스
RAG 워크플로우를 통한 워드 문서 처리 및 임베딩 생성
"""

import logging
import re
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken
import pandas as pd

# 워드 문서 처리
from docx import Document

# 한국어 자연어 처리
try:
    from konlpy.tag import Okt, Mecab, Komoran
    KONLPY_AVAILABLE = True
except ImportError:
    KONLPY_AVAILABLE = False
    logging.warning("KoNLPy가 설치되지 않았습니다. 기본 텍스트 처리만 사용합니다.")

# 임베딩 및 벡터 DB
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# 설정 import
from src.config.settings import settings

# 워드 프로세서 import
from src.services.word_processor import word_processor

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """문서 청크 정보"""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    token_count: int


class WordEmbeddingService:
    """워드 파일 임베딩 서비스"""
    
    def __init__(self, 
                 embedding_model_name: str = None,
                 chunk_size: int = None,
                 chunk_overlap: int = None,
                 vector_db_path: str = None):
        """
        워드 임베딩 서비스 초기화
        
        Args:
            embedding_model_name: 임베딩 모델명
            chunk_size: 청크 크기 (토큰 수)
            chunk_overlap: 청크 간 겹침 (토큰 수)
            vector_db_path: 벡터 DB 저장 경로
        """
        # 설정에서 기본값 가져오기
        self.embedding_model_name = embedding_model_name or settings.embedding_model_name
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.vector_db_path = vector_db_path or settings.chroma_persist_directory
        
        # 임베딩 모델 초기화 (설정/인자 반영)
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        # 벡터 DB 초기화
        self._init_vector_db()
        
        # 토큰화기 초기화
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # 한국어 형태소 분석기 초기화
        self._init_korean_analyzers()
    
    def _init_vector_db(self):
        """벡터 DB 초기화"""
        try:
            # Chroma DB 클라이언트 생성
            self.chroma_client = self._create_chroma_client()
            
            # 워드 문서용 컬렉션 생성
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata=settings.chroma_collection_metadata
            )
            logger.info(f"워드 벡터 DB 초기화 완료 (모드: {settings.chroma_mode})")
            
        except Exception as e:
            logger.error(f"워드 벡터 DB 초기화 실패: {e}")
            raise
    
    def _create_chroma_client(self):
        """Chroma DB 클라이언트 생성"""
        config = settings.get_chroma_client_config()
        
        if config["mode"] == "local":
            # 로컬 모드
            os.makedirs(config["path"], exist_ok=True)
            return chromadb.PersistentClient(
                path=config["path"],
                settings=chromadb.config.Settings(**config["settings"])
            )
        elif config["mode"] == "http":
            # HTTP 모드 (외부 서버)
            return chromadb.HttpClient(
                host=config["host"],
                port=config["port"],
                username=config["username"],
                password=config["password"],
                ssl=config["ssl"]
            )
        else:
            raise ValueError(f"지원하지 않는 Chroma DB 모드입니다: {config['mode']}")
    
    def _init_korean_analyzers(self):
        """한국어 형태소 분석기 초기화"""
        self.analyzers = {}
        
        if not KONLPY_AVAILABLE:
            logger.warning("KoNLPy를 사용할 수 없습니다. 기본 텍스트 처리만 사용합니다.")
            return
        
        try:
            # Okt (Open Korean Text) - 가장 안정적
            self.analyzers['okt'] = Okt()
            logger.info("Okt 형태소 분석기 초기화 완료")
        except Exception as e:
            logger.warning(f"Okt 초기화 실패: {e}")
        
        try:
            # Mecab - 가장 빠르고 정확
            self.analyzers['mecab'] = Mecab()
            logger.info("Mecab 형태소 분석기 초기화 완료")
        except Exception as e:
            logger.warning(f"Mecab 초기화 실패: {e}")
        
        try:
            # Komoran - 형태소 분석에 특화
            self.analyzers['komoran'] = Komoran()
            logger.info("Komoran 형태소 분석기 초기화 완료")
        except Exception as e:
            logger.warning(f"Komoran 초기화 실패: {e}")
    
    def extract_text_from_word(self, file_path: str) -> str:
        """
        워드 문서에서 텍스트 추출 (word_processor 사용)
        
        Args:
            file_path: 워드 파일 경로
            
        Returns:
            추출된 텍스트
        """
        return word_processor.extract_text_from_word(file_path)
    
    def preprocess_text(self, text: str) -> str:
        """
        텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        # 1. 기본 정제
        # 줄 바꿈, 탭을 공백으로 변환
        text = re.sub(r'[\n\t\r]+', ' ', text)
        
        # 2. 특수 문자 정제
        # 다양한 대시 문자를 하이픈으로 통일
        text = re.sub(r'[—–−]', '-', text)
        
        # 다양한 불릿 문자 통일
        text = re.sub(r'[•·∙]', '•', text)
        
        # 다양한 따옴표 통일
        text = re.sub(r'[""""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        
        # 기타 특수 문자 제거 (한글, 영문, 숫자, 기본 문장부호 제외)
        text = re.sub(r'[^\w\s\.,!?;:()\-_가-힣•"\'"]', ' ', text)
        
        # 3. 반복된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 4. 앞뒤 공백 제거
        text = text.strip()
        
        # 5. 연속된 문장부호 정리
        text = re.sub(r'[.,!?;:]{2,}', lambda m: m.group()[0], text)
        
        # 6. 공백과 문장부호 사이 정리
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        # 7. 괄호 내부 공백 정리
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        
        # 8. 최종 정리
        text = text.strip()
        
        # 9. 한국어 형태소 분석을 통한 주요 품사 추출
        if self.analyzers:
            text = self._extract_key_pos(text)
        
        return text
    
    def _extract_key_pos(self, text: str) -> str:
        """
        형태소 분석을 통한 주요 품사 추출
        
        Args:
            text: 원본 텍스트
            
        Returns:
            주요 품사가 추출된 텍스트
        """
        try:
            # Okt 사용 (가장 안정적)
            if 'okt' in self.analyzers:
                okt = self.analyzers['okt']
                pos_result = okt.pos(text, norm=True, stem=True)
                
                # 주요 품사만 추출 (명사, 동사, 형용사, 부사)
                key_words = []
                for word, pos in pos_result:
                    if pos in ['Noun', 'Verb', 'Adjective', 'Adverb']:
                        key_words.append(word)
                
                return ' '.join(key_words)
            
            # Mecab 사용 (더 정확)
            elif 'mecab' in self.analyzers:
                mecab = self.analyzers['mecab']
                pos_result = mecab.pos(text)
                
                # 주요 품사만 추출
                key_words = []
                for word, pos in pos_result:
                    if pos.startswith(('NNG', 'NNP', 'VV', 'VA', 'MAG')):  # 명사, 동사, 형용사, 부사
                        key_words.append(word)
                
                return ' '.join(key_words)
            
            # Komoran 사용
            elif 'komoran' in self.analyzers:
                komoran = self.analyzers['komoran']
                pos_result = komoran.pos(text)
                
                # 주요 품사만 추출
                key_words = []
                for word, pos in pos_result:
                    if pos in ['NNG', 'NNP', 'VV', 'VA', 'MAG']:  # 명사, 동사, 형용사, 부사
                        key_words.append(word)
                
                return ' '.join(key_words)
            
            else:
                return text
                
        except Exception as e:
            logger.warning(f"형태소 분석 실패: {e}")
            return text
    
    def split_document(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        문서를 청크로 분할
        
        Args:
            text: 전처리된 텍스트
            metadata: 문서 메타데이터
            
        Returns:
            문서 청크 리스트
        """
        chunks = []
        
        # 토큰화
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= self.chunk_size:
            # 문서가 청크 크기보다 작은 경우
            chunk_text = self.tokenizer.decode(tokens)
            chunk = DocumentChunk(
                content=chunk_text,
                metadata=metadata,
                chunk_id=f"{metadata.get('file_name', 'unknown')}_chunk_0",
                token_count=len(tokens)
            )
            chunks.append(chunk)
        else:
            # 문서를 청크로 분할
            chunk_id = 0
            start = 0
            
            while start < len(tokens):
                end = start + self.chunk_size
                chunk_tokens = tokens[start:end]
                
                # 청크 텍스트 생성
                chunk_text = self.tokenizer.decode(chunk_tokens)
                
                # 청크 메타데이터 생성
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_id': chunk_id,
                    'start_token': start,
                    'end_token': end,
                    'total_chunks': (len(tokens) + self.chunk_size - 1) // self.chunk_size
                })
                
                chunk = DocumentChunk(
                    content=chunk_text,
                    metadata=chunk_metadata,
                    chunk_id=f"{metadata.get('file_name', 'unknown')}_chunk_{chunk_id}",
                    token_count=len(chunk_tokens)
                )
                chunks.append(chunk)
                
                # 다음 청크 시작 위치 (겹침 고려)
                start = end - self.chunk_overlap
                chunk_id += 1
                
                # 마지막 청크인 경우 종료
                if start >= len(tokens):
                    break
        
        logger.info(f"문서 분할 완료: {len(chunks)}개 청크 생성")
        return chunks
    
    def create_embeddings(self, chunks: List[DocumentChunk]) -> List[List[float]]:
        """
        문서 청크들의 임베딩 생성
        
        Args:
            chunks: 문서 청크 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            # 청크 텍스트 추출
            texts = [chunk.content for chunk in chunks]
            
            # 임베딩 생성
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            logger.info(f"임베딩 생성 완료: {len(embeddings)}개 벡터")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    def store_embeddings(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        """
        임베딩을 벡터 DB에 저장
        
        Args:
            chunks: 문서 청크 리스트
            embeddings: 임베딩 벡터 리스트
        """
        try:
            # 벡터 DB에 저장할 데이터 준비
            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            
            # 벡터 DB에 추가
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"벡터 DB 저장 완료: {len(chunks)}개 청크")
            
        except Exception as e:
            logger.error(f"벡터 DB 저장 실패: {e}")
            raise
    
    def process_word_document(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        워드 문서 전체 처리 워크플로우
        
        Args:
            file_path: 워드 파일 경로
            metadata: 추가 메타데이터
            
        Returns:
            처리 결과 정보
        """
        try:
            # 기본 메타데이터 설정
            if metadata is None:
                metadata = {}
            
            file_name = os.path.basename(file_path)
            metadata.update({
                'file_name': file_name,
                'file_path': file_path,
                'file_type': 'word',
                'document_type': 'word',
                'processing_timestamp': str(pd.Timestamp.now())
            })
            
            logger.info(f"워드 문서 처리 시작: {file_name}")
            
            # 1. 텍스트 추출
            logger.info("1단계: 텍스트 추출")
            raw_text = self.extract_text_from_word(file_path)
            logger.info(f"텍스트 추출 완료: {len(raw_text)} 문자")
            
            # 2. 전처리
            logger.info("2단계: 텍스트 전처리")
            processed_text = self.preprocess_text(raw_text)
            logger.info(f"전처리 완료: {len(processed_text)} 문자")
            
            # 3. 문서 분할
            logger.info("3단계: 문서 분할")
            chunks = self.split_document(processed_text, metadata)
            logger.info(f"문서 분할 완료: {len(chunks)}개 청크")
            
            # 4. 임베딩 생성
            logger.info("4단계: 임베딩 생성")
            embeddings = self.create_embeddings(chunks)
            logger.info(f"임베딩 생성 완료: {len(embeddings)}개 벡터")
            
            # 5. 벡터 DB 저장
            logger.info("5단계: 벡터 DB 저장")
            self.store_embeddings(chunks, embeddings)
            logger.info("벡터 DB 저장 완료")
            
            # 결과 반환
            result = {
                'file_name': file_name,
                'total_chunks': len(chunks),
                'total_tokens': sum(chunk.token_count for chunk in chunks),
                'embedding_dimension': len(embeddings[0]) if embeddings else 0,
                'processing_success': True,
                'metadata': metadata
            }
            
            logger.info(f"워드 문서 처리 완료: {file_name}")
            return result
            
        except Exception as e:
            logger.error(f"워드 문서 처리 실패: {e}")
            return {
                'file_name': file_name if 'file_name' in locals() else 'unknown',
                'processing_success': False,
                'error': str(e)
            }
    
    def search_similar_chunks(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        유사한 문서 청크 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            
        Returns:
            유사한 청크 리스트
        """
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedding_model.encode([query])
            
            # 벡터 DB에서 유사한 청크 검색
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results
            )
            
            # 결과 포맷팅
            formatted_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None,
                    'id': results['ids'][0][i]
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"유사 청크 검색 실패: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        벡터 DB 컬렉션 통계 정보 반환
        
        Returns:
            컬렉션 통계 정보
        """
        try:
            count = self.collection.count()
            return {
                'total_chunks': count,
                'collection_name': 'word_documents',
                'embedding_model': self.embedding_model_name
            }
        except Exception as e:
            logger.error(f"컬렉션 통계 조회 실패: {e}")
            return {'error': str(e)} 