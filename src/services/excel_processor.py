#!/usr/bin/env python3
"""
엑셀 문서 텍스트 추출 유틸리티
RAG 시스템에서 엑셀 문서의 텍스트를 추출하는 기본 기능
"""

import logging
import pandas as pd
from typing import Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ExcelProcessor:
    """엑셀 문서 텍스트 추출 클래스"""
    
    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls', '.csv']
    
    def extract_text_from_excel(self, file_path: str) -> str:
        """
        엑셀 문서에서 텍스트 추출
        
        Args:
            file_path: 엑셀 파일 경로
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension not in self.supported_formats:
                raise ValueError(f"지원하지 않는 엑셀 파일 형식: {file_extension}")
            
            logger.info(f"엑셀 파일 텍스트 추출 시작: {file_path}")
            
            if file_extension == '.csv':
                # CSV 파일 처리
                df = pd.read_csv(file_path, na_filter=True)
            else:
                # Excel 파일 처리 (모든 시트 포함)
                excel_file = pd.ExcelFile(file_path)
                all_sheets = []
                
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, na_filter=True)
                    all_sheets.append((sheet_name, df))
                
                # 모든 시트의 데이터를 하나의 텍스트로 결합
                text_parts = []
                for sheet_name, df in all_sheets:
                    sheet_text = self._process_dataframe(df, sheet_name)
                    if sheet_text:
                        text_parts.append(f"=== 시트: {sheet_name} ===\n{sheet_text}")
                
                extracted_text = "\n\n".join(text_parts)
                logger.info(f"텍스트 추출 완료: {len(extracted_text)} 문자")
                return extracted_text
            
            # 단일 시트 처리 (CSV 또는 단일 시트 Excel)
            extracted_text = self._process_dataframe(df, "main")
            logger.info(f"텍스트 추출 완료: {len(extracted_text)} 문자")
            
            return extracted_text
                
        except Exception as e:
            logger.error(f"엑셀 파일 텍스트 추출 실패: {file_path}, 오류: {e}")
            raise
    
    def _process_dataframe(self, df: pd.DataFrame, sheet_name: str) -> str:
        """
        DataFrame을 텍스트로 변환
        
        Args:
            df: pandas DataFrame
            sheet_name: 시트 이름
            
        Returns:
            str: 변환된 텍스트
        """
        if df.empty:
            return ""
        
        text_parts = []
        
        # 열 헤더 추가
        headers = [str(col) for col in df.columns if str(col) != 'nan']
        if headers:
            text_parts.append(f"열: {' | '.join(headers)}")
        
        # 각 행을 텍스트로 변환
        for idx, row in df.iterrows():
            row_text = []
            for col in df.columns:
                value = row[col]
                
                # NaN 값 제외
                if pd.isna(value):
                    continue
                
                # 수식이나 계산된 값 처리
                if isinstance(value, (int, float)):
                    # 숫자 값은 문자열로 변환
                    row_text.append(str(value))
                else:
                    # 문자열 값
                    str_value = str(value).strip()
                    if str_value and str_value != 'nan':
                        row_text.append(str_value)
            
            if row_text:
                text_parts.append(f"행{idx+1}: {' | '.join(row_text)}")
        
        return "\n".join(text_parts)

# 전역 인스턴스
excel_processor = ExcelProcessor() 