"""
엑셀 파일 임베딩 서비스
RAG 워크플로우를 통한 엑셀 문서 처리 및 임베딩 생성
"""

import logging
import re
import os
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken

# 엑셀 문서 처리
import pandas as pd

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

# 엑셀 프로세서 import
from src.services.excel_processor import excel_processor

logger = logging.getLogger(__name__)


@dataclass
class ExcelChunk:
    """엑셀 청크 정보"""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    token_count: int
    sheet_name: str
    row_info: str


class ExcelEmbeddingService:
    """엑셀 파일 임베딩 서비스"""
    
    def __init__(self, 
                 embedding_model_name: str = None,
                 chunk_size: int = None,
                 chunk_overlap: int = None,
                 vector_db_path: str = None):
        """
        엑셀 임베딩 서비스 초기화
        
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
        
        # 임베딩 모델 초기화
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        # 벡터 DB 초기화
        self._init_vector_db()
        
        # 토큰화기 초기화
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # 한국어 형태소 분석기 초기화
        self._init_korean_analyzers()
    
    def _init_vector_db(self):
        """벡터 DB 초기화"""
        try:
            # 디렉토리 생성 및 권한 설정
            import os
            os.makedirs(self.vector_db_path, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(
                path=self.vector_db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 엑셀 문서용 컬렉션 생성
            self.collection = self.chroma_client.get_or_create_collection(
                name="documents",
                metadata={"description": "문서 임베딩 컬렉션 (통합)"}
            )
            logger.info("엑셀 벡터 DB 초기화 완료")
            
        except Exception as e:
            logger.error(f"엑셀 벡터 DB 초기화 실패: {e}")
            raise
    
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
    
    def extract_text_from_excel(self, file_path: str) -> str:
        """
        엑셀 문서에서 텍스트 추출 (excel_processor 사용)
        
        Args:
            file_path: 엑셀 파일 경로
            
        Returns:
            추출된 텍스트
        """
        return excel_processor.extract_text_from_excel(file_path)
    
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
    
    def split_excel_document(self, text: str, metadata: Dict[str, Any]) -> List[ExcelChunk]:
        """
        엑셀 문서를 청크로 분할 (행 단위 처리)
        
        Args:
            text: 전처리된 텍스트
            metadata: 문서 메타데이터
            
        Returns:
            엑셀 청크 리스트
        """
        chunks = []
        
        # 시트별로 분할
        sheet_sections = text.split("=== 시트:")
        
        for section in sheet_sections:
            if not section.strip():
                continue
            
            # 시트 이름과 내용 분리
            lines = section.strip().split('\n', 1)
            if len(lines) < 2:
                continue
            
            sheet_name = lines[0].replace(" ===", "").strip()
            sheet_content = lines[1]
            
            # 행별로 분할
            rows = sheet_content.split('\n')
            current_chunk = []
            chunk_id = 0
            
            for row in rows:
                if not row.strip():
                    continue
                
                # 행 정보 추출
                if row.startswith("행"):
                    row_info = row.split(":", 1)[0] if ":" in row else row
                    row_content = row.split(":", 1)[1] if ":" in row else row
                else:
                    row_info = "헤더"
                    row_content = row
                
                # 토큰 수 확인
                row_tokens = self.tokenizer.encode(row_content)
                
                if len(row_tokens) <= self.chunk_size:
                    # 단일 행이 청크 크기보다 작은 경우
                    chunk = ExcelChunk(
                        content=row_content,
                        metadata=metadata.copy(),
                        chunk_id=f"{metadata.get('file_name', 'unknown')}_{sheet_name}_chunk_{chunk_id}",
                        token_count=len(row_tokens),
                        sheet_name=sheet_name,
                        row_info=row_info
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                else:
                    # 긴 행을 토큰 단위로 분할
                    tokens = self.tokenizer.encode(row_content)
                    start = 0
                    
                    while start < len(tokens):
                        end = start + self.chunk_size
                        chunk_tokens = tokens[start:end]
                        
                        chunk_text = self.tokenizer.decode(chunk_tokens)
                        
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            'sheet_name': sheet_name,
                            'row_info': row_info,
                            'chunk_id': chunk_id,
                            'start_token': start,
                            'end_token': end
                        })
                        
                        chunk = ExcelChunk(
                            content=chunk_text,
                            metadata=chunk_metadata,
                            chunk_id=f"{metadata.get('file_name', 'unknown')}_{sheet_name}_chunk_{chunk_id}",
                            token_count=len(chunk_tokens),
                            sheet_name=sheet_name,
                            row_info=row_info
                        )
                        chunks.append(chunk)
                        
                        start = end - self.chunk_overlap
                        chunk_id += 1
                        
                        if start >= len(tokens):
                            break
        
        logger.info(f"엑셀 문서 분할 완료: {len(chunks)}개 청크 생성")
        return chunks
    
    def create_embeddings(self, chunks: List[ExcelChunk]) -> List[List[float]]:
        """
        엑셀 청크들의 임베딩 생성
        
        Args:
            chunks: 엑셀 청크 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            # 청크 텍스트 추출
            texts = [chunk.content for chunk in chunks]
            
            # 임베딩 생성
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            logger.info(f"엑셀 임베딩 생성 완료: {len(embeddings)}개 벡터")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"엑셀 임베딩 생성 실패: {e}")
            raise
    
    def store_embeddings(self, chunks: List[ExcelChunk], embeddings: List[List[float]]):
        """
        임베딩을 벡터 DB에 저장
        
        Args:
            chunks: 엑셀 청크 리스트
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
            
            logger.info(f"엑셀 벡터 DB 저장 완료: {len(chunks)}개 청크")
            
        except Exception as e:
            logger.error(f"엑셀 벡터 DB 저장 실패: {e}")
            raise
    
    def process_excel_document(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        엑셀 문서 전체 처리 워크플로우
        
        Args:
            file_path: 엑셀 파일 경로
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
                'file_type': 'excel',
                'document_type': 'excel',
                'processing_timestamp': str(pd.Timestamp.now())
            })
            
            logger.info(f"엑셀 문서 처리 시작: {file_name}")
            
            # 1. 텍스트 추출
            logger.info("1단계: 텍스트 추출")
            raw_text = self.extract_text_from_excel(file_path)
            logger.info(f"텍스트 추출 완료: {len(raw_text)} 문자")
            
            # 2. 전처리
            logger.info("2단계: 텍스트 전처리")
            processed_text = self.preprocess_text(raw_text)
            logger.info(f"전처리 완료: {len(processed_text)} 문자")
            
            # 3. 문서 분할
            logger.info("3단계: 문서 분할")
            chunks = self.split_excel_document(processed_text, metadata)
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
            
            logger.info(f"엑셀 문서 처리 완료: {file_name}")
            return result
            
        except Exception as e:
            logger.error(f"엑셀 문서 처리 실패: {e}")
            return {
                'file_name': file_name if 'file_name' in locals() else 'unknown',
                'processing_success': False,
                'error': str(e)
            }
    
    def search_similar_chunks(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        유사한 엑셀 청크 검색
        
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
            logger.error(f"유사 엑셀 청크 검색 실패: {e}")
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
                'collection_name': 'excel_documents',
                'embedding_model': self.embedding_model_name
            }
        except Exception as e:
            logger.error(f"엑셀 컬렉션 통계 조회 실패: {e}")
            return {'error': str(e)} 