#!/usr/bin/env python3
"""
MCP 로깅 기능 테스트 스크립트
MCP 도구 호출과 응답 로깅을 테스트합니다.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.mcp_client_service import MCPClientService
from src.config.settings import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_mcp_logging():
    """MCP 로깅 기능을 테스트합니다."""
    print("=" * 60)
    print("MCP 로깅 기능 테스트")
    print("=" * 60)
    
    # MCP 클라이언트 서비스 초기화
    mcp_service = MCPClientService()
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "날씨 요청 테스트",
            "prompt": "서울 날씨 어때?",
            "method": "process_weather_request"
        },
        {
            "name": "주식 요청 테스트", 
            "prompt": "삼성전자 주가 알려줘",
            "method": "process_stock_request"
        },
        {
            "name": "웹 검색 요청 테스트",
            "prompt": "최신 AI 뉴스 검색해줘",
            "method": "process_web_search_request"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        print(f"프롬프트: {test_case['prompt']}")
        
        try:
            # MCP 사용 여부 결정 테스트
            should_use = mcp_service._should_use_mcp(test_case['prompt'])
            print(f"MCP 사용 여부: {should_use}")
            
            if should_use:
                # 실제 MCP 요청 테스트
                if test_case['method'] == "process_weather_request":
                    response, success = await mcp_service.process_weather_request(test_case['prompt'])
                elif test_case['method'] == "process_stock_request":
                    response, success = await mcp_service.process_stock_request(test_case['prompt'])
                elif test_case['method'] == "process_web_search_request":
                    response, success = await mcp_service.process_web_search_request(test_case['prompt'])
                
                print(f"응답 성공: {success}")
                print(f"응답 내용 (앞 100자): {response[:100]}...")
            else:
                print("MCP 사용하지 않음")
                
        except Exception as e:
            print(f"테스트 실패: {e}")
    
    print("\n" + "=" * 60)
    print("테스트 완료! 로그 파일을 확인하세요.")
    print("=" * 60)

def show_log_format():
    """로그 형식을 설명합니다."""
    print("\n" + "=" * 60)
    print("MCP 로그 형식 설명")
    print("=" * 60)
    
    print("1. MCP 사용 결정 로그:")
    print("   [MCP 사용 결정] 결정 방식: keyword, 질문: 서울 날씨 어때?...")
    print("   [MCP 사용 결정] 키워드 기반 결과: 사용")
    
    print("\n2. MCP 도구 호출 로그:")
    print("   [MCP 도구 호출] 도구: get_current_weather, 파라미터: {\"city\": \"서울\"}...")
    
    print("\n3. MCP 도구 응답 로그:")
    print("   [MCP 도구 응답] 도구: get_current_weather, 응답: {\"success\": true, \"result\":...")
    
    print("\n4. MCP 요청 처리 로그:")
    print("   [MCP 날씨 요청] 사용자 프롬프트: 서울 날씨 어때?...")
    print("   [MCP 주식 요청] 사용자 프롬프트: 삼성전자 주가 알려줘...")
    print("   [MCP 웹 검색 요청] 사용자 프롬프트: 최신 AI 뉴스 검색해줘...")
    
    print("\n5. 키워드 매칭 로그:")
    print("   [MCP 키워드 매칭] 날씨 키워드 발견: ['날씨']")
    print("   [MCP 키워드 매칭] 주식 키워드 발견: ['주가']")
    print("   [MCP 키워드 매칭] 검색 키워드 발견: ['검색']")

def main():
    """메인 함수"""
    print("MCP 로깅 기능 테스트를 시작합니다...")
    
    # 로그 형식 설명
    show_log_format()
    
    # 실제 테스트 실행
    asyncio.run(test_mcp_logging())
    
    print("\n✅ 테스트가 완료되었습니다!")
    print("로그 파일에서 [MCP] 태그가 포함된 로그를 확인하세요.")

if __name__ == "__main__":
    main()
