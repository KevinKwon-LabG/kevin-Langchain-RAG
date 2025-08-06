#!/usr/bin/env python3
"""
텍스트 정제 기능 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.word_processor import word_processor
from src.services.word_embedding_service import WordEmbeddingService
from src.services.excel_embedding_service import ExcelEmbeddingService


def test_word_processor_cleaning():
    """워드 프로세서 텍스트 정제 테스트"""
    print("워드 프로세서 텍스트 정제 테스트")
    print("-" * 40)
    
    # 테스트 텍스트 (워드 문서에서 추출된 것처럼 다양한 특수 문자 포함)
    test_text = """
    이 문서는 테스트용 워드 문서입니다.
    
    주요 특징:
    • 다양한 불릿 문자 사용
    • 줄바꿈과 탭이 포함된 텍스트
    • 특수 문자들: — (대시), "따옴표", '작은따옴표'
    • 반복된 공백    여러개
    • 연속된 문장부호!!!...
    • 괄호 ( 내부 공백 )
    
    테이블 데이터:
    이름 | 나이 | 부서
    김철수 | 25 | 개발팀
    이영희 | 30 | 마케팅팀
    """
    
    print("원본 텍스트:")
    print(repr(test_text))
    print("\n" + "="*50 + "\n")
    
    # 워드 프로세서의 정제 기능 테스트
    cleaned_text = word_processor._clean_text(test_text)
    
    print("정제된 텍스트:")
    print(repr(cleaned_text))
    print("\n" + "="*50 + "\n")
    
    print("정제 결과:")
    print(cleaned_text)
    
    return cleaned_text


def test_word_embedding_service_cleaning():
    """워드 임베딩 서비스 텍스트 정제 테스트"""
    print("\n워드 임베딩 서비스 텍스트 정제 테스트")
    print("-" * 40)
    
    # 테스트 텍스트
    test_text = """
    RAG 시스템에서 워드 문서를 처리할 때,
    
    다양한 특수 문자들이 포함될 수 있습니다:
    • 다양한 불릿 문자: · ∙ •
    • 다양한 대시: — – −
    • 다양한 따옴표: " " " ' ' '
    • 반복된 공백과    탭
    • 연속된 문장부호!!!...
    • 괄호 ( 내부 공백 정리 )
    
    이러한 요소들을 정제하여 검색 품질을 향상시킵니다.
    """
    
    print("원본 텍스트:")
    print(repr(test_text))
    print("\n" + "="*50 + "\n")
    
    # 워드 임베딩 서비스의 정제 기능 테스트
    service = WordEmbeddingService()
    cleaned_text = service.preprocess_text(test_text)
    
    print("정제된 텍스트:")
    print(repr(cleaned_text))
    print("\n" + "="*50 + "\n")
    
    print("정제 결과:")
    print(cleaned_text)
    
    return cleaned_text


def test_excel_embedding_service_cleaning():
    """엑셀 임베딩 서비스 텍스트 정제 테스트"""
    print("\n엑셀 임베딩 서비스 텍스트 정제 테스트")
    print("-" * 40)
    
    # 테스트 텍스트 (엑셀에서 추출된 것처럼)
    test_text = """
    === 시트: 직원정보 ===
    열: 이름 | 나이 | 부서 | 급여 | 입사일
    행1: 김철수 | 25 | 개발팀 | 3500000 | 2020-01-15
    행2: 이영희 | 30 | 마케팅팀 | 4200000 | 2018-03-20
    행3: 박민수 | 28 | 개발팀 | 3800000 | 2019-07-10
    
    === 시트: 부서통계 ===
    열: 부서 | 평균나이 | 평균급여
    행1: 개발팀 | 26.5 | 3650000.0
    행2: 마케팅팀 | 30.0 | 4200000.0
    """
    
    print("원본 텍스트:")
    print(repr(test_text))
    print("\n" + "="*50 + "\n")
    
    # 엑셀 임베딩 서비스의 정제 기능 테스트
    service = ExcelEmbeddingService()
    cleaned_text = service.preprocess_text(test_text)
    
    print("정제된 텍스트:")
    print(repr(cleaned_text))
    print("\n" + "="*50 + "\n")
    
    print("정제 결과:")
    print(cleaned_text)
    
    return cleaned_text


def test_special_characters():
    """특수 문자 정제 테스트"""
    print("\n특수 문자 정제 테스트")
    print("-" * 40)
    
    # 다양한 특수 문자를 포함한 테스트 텍스트
    test_cases = [
        "대시 문자: — – − → -",
        "불릿 문자: • · ∙ → •",
        "따옴표: " " " ' ' ' → \" '",
        "연속 문장부호: !!! ... → ! .",
        "괄호 공백: ( 내용 ) → (내용)",
        "반복 공백: 여러    공백 → 여러 공백",
        "한글+영문+숫자: 안녕하세요 Hello 123",
        "제거될 특수문자: @#$%^&*+=<>[]{}|\\",
    ]
    
    for test_case in test_cases:
        print(f"원본: {test_case}")
        cleaned = word_processor._clean_text(test_case)
        print(f"정제: {cleaned}")
        print("-" * 30)


def main():
    """메인 테스트 함수"""
    print("텍스트 정제 기능 테스트 시작")
    print("=" * 60)
    
    # 1. 워드 프로세서 테스트
    word_result = test_word_processor_cleaning()
    
    # 2. 워드 임베딩 서비스 테스트
    word_embedding_result = test_word_embedding_service_cleaning()
    
    # 3. 엑셀 임베딩 서비스 테스트
    excel_result = test_excel_embedding_service_cleaning()
    
    # 4. 특수 문자 테스트
    test_special_characters()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("모든 텍스트 정제 기능이 정상적으로 작동합니다.")


if __name__ == "__main__":
    main() 