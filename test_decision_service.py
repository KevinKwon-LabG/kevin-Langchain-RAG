#!/usr/bin/env python3
"""
Langchain Decision Service 테스트 스크립트
"""

import asyncio
import os
import sys
from typing import List

# src 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.langchain_decision_service import LangchainDecisionService


async def test_decision_service():
    """의사결정 서비스 테스트"""
    
    # Ollama 서비스 연결 확인 (선택사항)
    print("🔍 Ollama 서비스 연결 확인 중...")
    
    # 테스트할 prompt들
    test_prompts = [
        "오늘 서울 날씨는 어때?",
        "내일 비 올 확률은?",
        "삼성전자 주가가 어떻게 되나요?",
        "KOSPI 지수는 현재 몇 점인가요?",
        "2024년 최신 아이폰 가격은?",
        "파이썬이란 무엇인가요?",
        "세계에서 가장 큰 나라는?",
        "현재 시간이 몇 시인가요?",
        "오늘 날짜는?",
        "인공지능의 정의는?"
    ]
    
    # 의사결정 서비스 초기화
    decision_service = LangchainDecisionService()
    
    print("🚀 Langchain Decision Service 테스트 시작\n")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"테스트 {i}: {prompt}")
        try:
            # 비동기 방식으로 분류
            result = await decision_service.classify_prompt(prompt)
            print(f"결과: {result}")
        except Exception as e:
            print(f"오류: {e}")
        print("-" * 50)
    
    print("\n✅ 테스트 완료!")


def test_sync_decision_service():
    """동기 방식 의사결정 서비스 테스트"""
    
    # Ollama 서비스 연결 확인 (선택사항)
    print("🔍 Ollama 서비스 연결 확인 중...")
    
    # 테스트할 prompt들
    test_prompts = [
        "오늘 날씨는?",
        "삼성전자 주가",
        "파이썬 튜토리얼"
    ]
    
    # 의사결정 서비스 초기화
    decision_service = LangchainDecisionService()
    
    print("🚀 동기 방식 Langchain Decision Service 테스트 시작\n")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"테스트 {i}: {prompt}")
        try:
            # 동기 방식으로 분류
            result = decision_service.classify_prompt_sync(prompt)
            print(f"결과: {result}")
        except Exception as e:
            print(f"오류: {e}")
        print("-" * 50)
    
    print("\n✅ 동기 테스트 완료!")


if __name__ == "__main__":
    print("Langchain Decision Service 테스트")
    print("=" * 50)
    
    # 비동기 테스트
    asyncio.run(test_decision_service())
    
    print("\n" + "=" * 50)
    
    # 동기 테스트
    test_sync_decision_service() 