#!/usr/bin/env python3
"""
PDF 문서 전처리 전용 프로세서
RAG 시스템에서 PDF 파일의 검색 효과를 높이기 위한 전처리 기능
"""

import os
import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

# PDF 처리 라이브러리
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF 문서 전처리 클래스"""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
        self.min_content_length = 10   # 최소 내용 길이
        self.max_page_length = 5000    # 최대 페이지 길이
    
    def process_pdf_file(self, file_path: str) -> str:
        """
        PDF 문서를 전처리하여 검색에 최적화된 텍스트로 변환
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            str: 전처리된 텍스트
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.pdf':
                return self._extract_pdf_with_pypdf(file_path)
            else:
                raise ValueError(f"지원하지 않는 PDF 파일 형식: {file_extension}")
                
        except Exception as e:
            logger.error(f"PDF 파일 처리 실패: {file_path}, 오류: {e}")
            raise
    
    def _extract_pdf_with_pypdf(self, file_path: str) -> str:
        """pypdf를 사용하여 PDF에서 텍스트 추출 및 전처리"""
        try:
            reader = PdfReader(file_path)
            text_content = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    # 텍스트 추출
                    page_text = page.extract_text()
                    
                    if page_text:
                        # 페이지별 전처리
                        cleaned_text = self._preprocess_pdf_text(page_text)
                        if cleaned_text:
                            text_content.append(f"=== 페이지 {page_num + 1} ===\n{cleaned_text}")
                    
                except Exception as e:
                    logger.warning(f"페이지 {page_num + 1} 처리 중 오류: {e}")
                    continue
            
            # 전체 텍스트 결합
            full_text = '\n\n'.join(text_content)
            
            if not full_text.strip():
                logger.warning(f"PDF에서 추출된 텍스트가 없습니다: {file_path}")
                return ""
            
            logger.info(f"PDF 텍스트 추출 완료: {file_path} (페이지 수: {len(reader.pages)})")
            return full_text
            
        except Exception as e:
            logger.error(f"PDF 처리 실패: {file_path}, 오류: {e}")
            raise ValueError(f"PDF 파일을 처리할 수 없습니다: {e}")
    
    def _preprocess_pdf_text(self, text: str) -> str:
        """
        PDF 텍스트 전처리
        - 불필요한 공백 제거
        - 줄바꿈 정리
        - 특수 문자 처리
        """
        if not text or not text.strip():
            return ""
        
        # 1. 기본 정리
        text = text.strip()
        
        # 2. 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 3. 줄바꿈 정리 (단어 중간 줄바꿈 제거)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # 단어 중간 줄바꿈 제거 (하이픈으로 끝나는 경우)
                if line.endswith('-') and len(line) > 1:
                    cleaned_lines.append(line[:-1])  # 하이픈 제거
                else:
                    cleaned_lines.append(line)
        
        text = ' '.join(cleaned_lines)
        
        # 4. 특수 문자 정리
        # 연속된 점 제거
        text = re.sub(r'\.{3,}', '...', text)
        
        # 연속된 하이픈 제거
        text = re.sub(r'-{3,}', '---', text)
        
        # 5. 연속된 줄바꿈 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 6. 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        PDF 파일 정보 조회
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            Dict: 파일 정보
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"파일이 존재하지 않습니다: {file_path}")
            
            # 기본 파일 정보
            file_info = {
                "filename": file_path.name,
                "file_size": file_path.stat().st_size,
                "file_type": file_path.suffix.lower(),
                "supported": file_path.suffix.lower() in self.supported_formats
            }
            
            # PDF 특정 정보
            if file_path.suffix.lower() == '.pdf':
                try:
                    reader = PdfReader(str(file_path))
                    file_info.update({
                        "page_count": len(reader.pages),
                        "pdf_version": reader.metadata.get('/PDFVersion', 'Unknown') if reader.metadata else 'Unknown',
                        "title": reader.metadata.get('/Title', '') if reader.metadata else '',
                        "author": reader.metadata.get('/Author', '') if reader.metadata else '',
                        "subject": reader.metadata.get('/Subject', '') if reader.metadata else '',
                        "creator": reader.metadata.get('/Creator', '') if reader.metadata else '',
                        "producer": reader.metadata.get('/Producer', '') if reader.metadata else '',
                        "creation_date": reader.metadata.get('/CreationDate', '') if reader.metadata else '',
                        "modification_date": reader.metadata.get('/ModDate', '') if reader.metadata else ''
                    })
                except Exception as e:
                    logger.warning(f"PDF 메타데이터 읽기 실패: {e}")
                    file_info["page_count"] = 0
            
            return file_info
            
        except Exception as e:
            logger.error(f"파일 정보 조회 실패: {e}")
            raise
    
    def validate_pdf_file(self, file_path: str) -> bool:
        """
        PDF 파일 유효성 검사
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            bool: 유효한 PDF 파일 여부
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return False
            
            if file_path.suffix.lower() != '.pdf':
                return False
            
            # PDF 파일 열기 테스트
            reader = PdfReader(str(file_path))
            page_count = len(reader.pages)
            
            return page_count > 0
            
        except Exception as e:
            logger.warning(f"PDF 파일 유효성 검사 실패: {file_path}, 오류: {e}")
            return False

# 전역 인스턴스 생성
pdf_processor = PDFProcessor() 