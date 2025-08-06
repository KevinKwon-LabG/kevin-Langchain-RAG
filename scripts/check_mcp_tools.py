#!/usr/bin/env python3
"""
MCP 서버에서 사용 가능한 모든 도구들을 조회하는 스크립트
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import httpx

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import get_settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPToolsChecker:
    """MCP 서버의 사용 가능한 도구들을 확인하는 클래스"""
    
    def __init__(self):
        """초기화"""
        settings = get_settings()
        self.mcp_server_url = settings.mcp_server_url
        self.timeout = 30
        
        logger.info(f"MCP 서버 URL: {self.mcp_server_url}")
    
    async def check_available_tools(self) -> Dict[str, Any]:
        """
        MCP 서버에서 사용 가능한 모든 도구들을 확인합니다.
        
        Returns:
            Dict[str, Any]: 도구 정보
        """
        logger.info("MCP 서버에서 사용 가능한 도구들을 확인합니다...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # MCP 서버의 도구 목록 조회 - 여러 방법 시도
                endpoints_to_try = [
                    f"{self.mcp_server_url}/tools",
                    f"{self.mcp_server_url}/tools/list",
                    f"{self.mcp_server_url}/tools/available",
                    f"{self.mcp_server_url}/api/tools",
                    f"{self.mcp_server_url}/",
                    f"{self.mcp_server_url}/health",
                    f"{self.mcp_server_url}/status"
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        logger.info(f"엔드포인트 시도: {endpoint}")
                        
                        # GET 요청으로 도구 목록 조회
                        response = await client.get(endpoint)
                        
                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"MCP 서버 응답 (GET): {data}")
                            
                            # 응답에서 도구 정보 추출
                            tools_info = self._extract_tools_from_response(data)
                            if tools_info:
                                return tools_info
                        
                        # POST 요청으로도 시도
                        request_data_list = [
                            {"request": "list_tools"},
                            {"action": "get_tools"},
                            {"query": "사용 가능한 도구 목록을 알려주세요"},
                            {"request": "tools"},
                            {"action": "list_available_tools"}
                        ]
                        
                        for request_data in request_data_list:
                            try:
                                response = await client.post(endpoint, json=request_data)
                                
                                if response.status_code == 200:
                                    data = response.json()
                                    logger.info(f"MCP 서버 응답 (POST): {data}")
                                    
                                    # 응답에서 도구 정보 추출
                                    tools_info = self._extract_tools_from_response(data)
                                    if tools_info:
                                        return tools_info
                                        
                            except Exception as e:
                                logger.debug(f"POST 요청 실패: {endpoint} - {request_data}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.debug(f"엔드포인트 실패: {endpoint}: {e}")
                        continue
                
                # 모든 시도가 실패한 경우
                logger.warning("MCP 서버에서 도구 목록을 가져올 수 없습니다.")
                return {"error": "MCP 서버에서 도구 목록을 가져올 수 없습니다."}
                    
        except Exception as e:
            logger.error(f"도구 목록 조회 실패: {e}")
            return {"error": f"도구 목록 조회 실패: {e}"}
    
    def _extract_tools_from_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP 서버 응답에서 도구 정보를 추출합니다.
        
        Args:
            response_data: MCP 서버 응답 데이터
            
        Returns:
            Dict[str, Any]: 도구 정보
        """
        try:
            # 다양한 응답 형식에 대응
            if isinstance(response_data, dict):
                # 직접 도구 목록이 있는 경우
                if "tools" in response_data:
                    return {"tools": response_data["tools"]}
                elif "available_tools" in response_data:
                    return {"tools": response_data["available_tools"]}
                elif "data" in response_data and isinstance(response_data["data"], dict):
                    if "tools" in response_data["data"]:
                        return {"tools": response_data["data"]["tools"]}
                elif "result" in response_data and isinstance(response_data["result"], dict):
                    if "tools" in response_data["result"]:
                        return {"tools": response_data["result"]["tools"]}
                    elif "data" in response_data["result"] and isinstance(response_data["result"]["data"], dict):
                        if "tools" in response_data["result"]["data"]:
                            return {"tools": response_data["result"]["data"]["tools"]}
                
                # 응답이 문자열인 경우 (JSON 파싱 필요)
                elif "message" in response_data:
                    message = response_data["message"]
                    # JSON 형태의 문자열에서 도구 정보 추출 시도
                    try:
                        import re
                        # JSON 배열 패턴 찾기
                        json_pattern = r'\[.*?\]'
                        matches = re.findall(json_pattern, message, re.DOTALL)
                        for match in matches:
                            try:
                                parsed = json.loads(match)
                                if isinstance(parsed, list):
                                    return {"tools": parsed}
                            except json.JSONDecodeError:
                                continue
                    except Exception:
                        pass
                
                # 응답이 리스트인 경우
                elif isinstance(response_data, list):
                    return {"tools": response_data}
                
                # 전체 응답을 반환
                return {"full_response": response_data}
            
            return {"error": "응답 데이터 형식을 인식할 수 없습니다."}
            
        except Exception as e:
            logger.error(f"도구 정보 추출 실패: {e}")
            return {"error": f"도구 정보 추출 실패: {e}"}
    
    async def test_specific_tools(self) -> Dict[str, Any]:
        """
        특정 도구들이 존재하는지 테스트합니다.
        
        Returns:
            Dict[str, Any]: 테스트 결과
        """
        logger.info("특정 도구들의 존재 여부를 테스트합니다...")
        
        tools_to_test = [
            "get_current_weather",
            "get_stock_info", 
            "get_stock_price",
            "google_web_search",
            "web_search",
            "search"
        ]
        
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for tool in tools_to_test:
                    try:
                        # 도구별 엔드포인트 테스트
                        endpoints = [
                            f"{self.mcp_server_url}/tools/{tool}",
                            f"{self.mcp_server_url}/{tool}",
                            f"{self.mcp_server_url}/api/{tool}"
                        ]
                        
                        tool_result = {"exists": False, "endpoints": []}
                        
                        for endpoint in endpoints:
                            try:
                                response = await client.get(endpoint)
                                if response.status_code == 200:
                                    tool_result["exists"] = True
                                    tool_result["endpoints"].append(endpoint)
                                    tool_result["response"] = response.json()
                                    break
                                elif response.status_code == 404:
                                    tool_result["endpoints"].append(f"{endpoint} (404)")
                                else:
                                    tool_result["endpoints"].append(f"{endpoint} ({response.status_code})")
                            except Exception as e:
                                tool_result["endpoints"].append(f"{endpoint} (error: {e})")
                        
                        results[tool] = tool_result
                        
                    except Exception as e:
                        results[tool] = {"exists": False, "error": str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"도구 테스트 실패: {e}")
            return {"error": f"도구 테스트 실패: {e}"}

async def main():
    """메인 함수"""
    logger.info("MCP 서버 도구 확인을 시작합니다...")
    
    # 체커 초기화
    checker = MCPToolsChecker()
    
    # 1. 사용 가능한 도구 목록 조회
    print("\n" + "="*60)
    print("1. MCP 서버 사용 가능한 도구 목록 조회")
    print("="*60)
    
    tools_info = await checker.check_available_tools()
    
    if "error" in tools_info:
        print(f"❌ 오류: {tools_info['error']}")
    else:
        print("✅ 도구 정보를 성공적으로 가져왔습니다:")
        print(json.dumps(tools_info, ensure_ascii=False, indent=2))
    
    # 2. 특정 도구 테스트
    print("\n" + "="*60)
    print("2. 특정 도구 존재 여부 테스트")
    print("="*60)
    
    test_results = await checker.test_specific_tools()
    
    if "error" in test_results:
        print(f"❌ 테스트 오류: {test_results['error']}")
    else:
        print("✅ 도구 테스트 결과:")
        for tool, result in test_results.items():
            status = "✅ 존재" if result.get("exists") else "❌ 없음"
            print(f"\n{tool}: {status}")
            if "endpoints" in result:
                for endpoint in result["endpoints"]:
                    print(f"  - {endpoint}")
            if "error" in result:
                print(f"  - 오류: {result['error']}")
    
    print("\n" + "="*60)
    print("MCP 서버 도구 확인 완료")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 