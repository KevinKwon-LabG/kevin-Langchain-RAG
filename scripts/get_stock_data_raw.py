#!/usr/bin/env python3
"""
MCP 서버의 load_all_tickers 도구를 호출해서 받은 결과를 그대로 txt 파일로 저장하는 스크립트
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
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

class MCPStockDataCollector:
    """MCP 서버의 load_all_tickers 도구 결과를 수집하는 클래스"""
    
    def __init__(self):
        """초기화"""
        settings = get_settings()
        self.mcp_server_url = settings.mcp_server_url
        self.timeout = 120  # 주식 데이터 로딩은 시간이 걸릴 수 있으므로 타임아웃 증가
        
        logger.info(f"MCP 서버 URL: {self.mcp_server_url}")
    
    async def load_all_tickers(self) -> Dict[str, Any]:
        """
        MCP 서버의 load_all_tickers 도구를 사용하여 모든 주식 종목 정보를 가져옵니다.
        
        Returns:
            Dict[str, Any]: 주식 종목 정보
        """
        logger.info("MCP 서버의 load_all_tickers 도구를 호출합니다...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # load_all_tickers 도구 호출
                endpoint = f"{self.mcp_server_url}/tools/load_all_tickers"
                
                logger.info(f"엔드포인트 호출: {endpoint}")
                
                # POST 요청으로 도구 실행
                request_data = {}
                
                response = await client.post(endpoint, json=request_data)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"MCP 서버 응답: {data}")
                    return data
                else:
                    logger.error(f"load_all_tickers 호출 실패: {response.status_code}")
                    return {"error": f"load_all_tickers 호출 실패: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"load_all_tickers 호출 중 오류: {e}")
            return {"error": f"load_all_tickers 호출 중 오류: {e}"}
    
    def save_to_txt(self, data: Dict[str, Any], output_file: str = "stocks.txt"):
        """
        MCP 서버 응답 데이터를 그대로 TXT 파일로 저장합니다.
        
        Args:
            data: MCP 서버 응답 데이터
            output_file: 출력 파일명
        """
        try:
            output_path = Path("data") / output_file
            
            # JSON 형식으로 저장 (가독성을 위해 들여쓰기 포함)
            with open(output_path, 'w', encoding='utf-8') as txtfile:
                json.dump(data, txtfile, ensure_ascii=False, indent=2)
            
            logger.info(f"주식 데이터가 {output_path}에 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"TXT 파일 저장 실패: {e}")

async def main():
    """메인 함수"""
    logger.info("MCP 서버에서 주식 데이터 수집을 시작합니다...")
    
    # 데이터 디렉토리 생성
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 수집기 초기화
    collector = MCPStockDataCollector()
    
    # load_all_tickers 도구 호출
    print("\n" + "="*60)
    print("MCP 서버 load_all_tickers 도구 호출")
    print("="*60)
    
    result = await collector.load_all_tickers()
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
    else:
        print("✅ load_all_tickers 도구 호출 성공!")
        
        # TXT 파일로 저장
        collector.save_to_txt(result, "stocks.txt")
        
        print(f"📁 결과가 data/stocks.txt 파일에 저장되었습니다.")
        
        # 결과 요약 출력
        if isinstance(result, dict):
            if "result" in result and isinstance(result["result"], dict):
                result_data = result["result"]
                if "total_count" in result_data:
                    print(f"📊 총 {result_data['total_count']}개의 주식 종목 정보를 받았습니다.")
                if "success_count" in result_data:
                    print(f"✅ 성공: {result_data['success_count']}개")
                if "error_count" in result_data:
                    print(f"❌ 오류: {result_data['error_count']}개")
    
    print("\n" + "="*60)
    print("MCP 서버 주식 데이터 수집 완료")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 