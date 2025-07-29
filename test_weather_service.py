#!/usr/bin/env python3
"""
날씨 서비스 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.weather_service import weather_service

async def test_weather_service():
    """날씨 서비스 테스트"""
    
    # 테스트 메시지들
    test_messages = [
        "서울 날씨 어때?",
        "부산 기온은?",
        "내일 대구 날씨 예보",
        "주말 제주도 날씨",
        "오늘 인천 기상 상황",
        "What's the weather like in Seoul?",
        "How's the temperature in Busan?",
        "일반적인 대화 메시지",
        "코딩 관련 질문입니다",
        "서울 오늘 날씨와 내일 날씨 비교",
        "부산 비 올 확률",
        "대구 바람 세기",
        "제주 습도 정보"
    ]
    
    print("=== 날씨 서비스 테스트 ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"테스트 {i}: {message}")
        
        # 날씨 질문 분석
        weather_info = weather_service.get_weather_info(message)
        print(f"  - 날씨 질문 여부: {weather_info['is_weather_question']}")
        print(f"  - 추출된 위치: {weather_info['location']}")
        print(f"  - 발견된 키워드: {weather_info['keywords_found']}")
        
        # 날씨 질문인 경우 MCP 서버에 요청
        if weather_info['is_weather_question']:
            print("  - MCP 서버에 날씨 정보 요청 중...")
            try:
                weather_response = await weather_service.get_weather_response(message)
                if weather_response['success']:
                    print(f"  - 응답: {weather_response['response'][:100]}...")
                else:
                    print(f"  - 오류: {weather_response['error']}")
            except Exception as e:
                print(f"  - 예외 발생: {e}")
        
        print()

async def test_specific_weather_query():
    """특정 날씨 질문 테스트"""
    print("=== 특정 날씨 질문 테스트 ===\n")
    
    test_message = "서울 오늘 날씨 어때?"
    print(f"테스트 메시지: {test_message}")
    
    # 날씨 정보 요청
    weather_response = await weather_service.get_weather_response(test_message)
    
    print(f"성공 여부: {weather_response['success']}")
    if weather_response['success']:
        print(f"위치: {weather_response.get('location', 'N/A')}")
        print(f"응답: {weather_response['response']}")
        print(f"소스: {weather_response['source']}")
    else:
        print(f"오류: {weather_response.get('error', 'Unknown error')}")

async def main():
    """메인 테스트 함수"""
    print("날씨 서비스 테스트를 시작합니다...")
    
    # 기본 테스트
    await test_weather_service()
    
    # 특정 질문 테스트
    await test_specific_weather_query()
    
    print("테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main()) 