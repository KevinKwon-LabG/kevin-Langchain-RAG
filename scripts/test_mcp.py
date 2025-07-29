#!/usr/bin/env python3
"""
MCP 서비스 테스트 스크립트
외부 MCP 서버와의 연결을 테스트합니다.
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.mcp_service import mcp_service
from src.config.settings import settings

async def test_mcp_connection():
    """MCP 서버 연결 테스트"""
    print("=" * 50)
    print("MCP 서버 연결 테스트")
    print("=" * 50)
    
    print(f"MCP 서버 URL: {settings.mcp_server_url}")
    print(f"MCP 서비스 활성화: {settings.mcp_enabled}")
    print()
    
    if not settings.mcp_enabled:
        print("❌ MCP 서비스가 비활성화되어 있습니다.")
        return
    
    try:
        # 1. 헬스 체크
        print("1. 서버 상태 확인 중...")
        health_info = await mcp_service.health_check()
        print(f"✅ 헬스 체크 결과: {health_info}")
        print()
        
        # 2. 모델 목록 조회
        print("2. 사용 가능한 모델 목록 조회 중...")
        models = await mcp_service.get_models()
        print(f"✅ 사용 가능한 모델 수: {len(models)}")
        for i, model in enumerate(models[:5], 1):  # 처음 5개만 표시
            print(f"   {i}. {model.get('name', 'Unknown')}")
        if len(models) > 5:
            print(f"   ... 및 {len(models) - 5}개 더")
        print()
        
        # 3. 간단한 채팅 테스트 (모델이 있는 경우)
        if models:
            test_model = models[0].get('name', 'default')
            print(f"3. 채팅 완성 테스트 (모델: {test_model})...")
            
            messages = [
                {"role": "user", "content": "안녕하세요! 간단한 테스트입니다."}
            ]
            
            try:
                response = await mcp_service.chat_completion(
                    model=test_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=100
                )
                print("✅ 채팅 완성 테스트 성공")
                print(f"   응답: {response.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100]}...")
            except Exception as e:
                print(f"❌ 채팅 완성 테스트 실패: {e}")
        else:
            print("3. 사용 가능한 모델이 없어 채팅 테스트를 건너뜁니다.")
        
        print()
        print("✅ MCP 서버 연결 테스트 완료!")
        
    except Exception as e:
        print(f"❌ MCP 서버 연결 테스트 실패: {e}")
        print(f"   오류 타입: {type(e).__name__}")
    
    finally:
        # 세션 정리
        await mcp_service.close()

async def test_mcp_config():
    """MCP 설정 정보 출력"""
    print("=" * 50)
    print("MCP 설정 정보")
    print("=" * 50)
    
    print(f"서버 호스트: {settings.mcp_server_host}")
    print(f"서버 포트: {settings.mcp_server_port}")
    print(f"서버 URL: {settings.mcp_server_url}")
    print(f"타임아웃: {settings.mcp_timeout}초")
    print(f"최대 재시도: {settings.mcp_max_retries}회")
    print(f"활성화 상태: {settings.mcp_enabled}")
    print()

async def main():
    """메인 함수"""
    print("MCP 서비스 테스트 시작")
    print()
    
    await test_mcp_config()
    await test_mcp_connection()
    
    print("테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main()) 