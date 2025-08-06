#!/usr/bin/env python3
"""
MCP 서버에서 주가 정보를 요청할 때 반환되는 raw data를 보여주는 테스트 스크립트
"""

import asyncio
import json
from src.services.mcp_client_service import MCPClientService

async def test_stock_raw_data():
    """MCP 서버에서 주가 정보 raw data를 테스트합니다."""
    
    # MCP 클라이언트 서비스 초기화
    mcp_service = MCPClientService()
    
    print("=" * 80)
    print("MCP 서버 주가 정보 Raw Data 테스트")
    print("=" * 80)
    
    # 테스트할 종목들
    test_stocks = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "035420", "name": "NAVER"},
        {"code": "035720", "name": "카카오"}
    ]
    
    for stock in test_stocks:
        print(f"\n📈 {stock['name']} ({stock['code']}) 주가 정보 Raw Data")
        print("-" * 60)
        
        try:
            # MCP 서버에 직접 요청
            stock_data = await mcp_service._make_mcp_request("stock", {
                "code": stock['code'],
                "query": f"{stock['name']} 주가"
            })
            
            if stock_data.get("success"):
                raw_data = stock_data.get("data", {})
                
                print("🔍 Raw Data (JSON):")
                print(json.dumps(raw_data, indent=2, ensure_ascii=False))
                
                print(f"\n📊 포맷된 응답:")
                # 포맷된 응답도 확인
                formatted_response = mcp_service._format_stock_response(raw_data, stock['code'])
                print(formatted_response)
                
            else:
                print(f"❌ 요청 실패: {stock_data}")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("\n" + "=" * 80)

async def test_stock_request_flow():
    """전체 주식 요청 플로우를 테스트합니다."""
    
    print("\n" + "=" * 80)
    print("전체 주식 요청 플로우 테스트")
    print("=" * 80)
    
    mcp_service = MCPClientService()
    
    # 사용자 프롬프트로 테스트
    test_prompts = [
        "삼성전자 주가 알려줘",
        "005930 주식 정보",
        "SK하이닉스 현재가",
        "NAVER 주가 조회"
    ]
    
    for prompt in test_prompts:
        print(f"\n💬 사용자 요청: {prompt}")
        print("-" * 60)
        
        try:
            response, completed = await mcp_service.process_stock_request(prompt, "test_session")
            print(f"✅ 응답: {response}")
            print(f"✅ 완료 여부: {completed}")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("\n" + "-" * 80)

if __name__ == "__main__":
    print("MCP 서버 주가 정보 Raw Data 테스트를 시작합니다...")
    
    # 비동기 실행
    asyncio.run(test_stock_raw_data())
    asyncio.run(test_stock_request_flow())
    
    print("\n✅ 테스트 완료!") 