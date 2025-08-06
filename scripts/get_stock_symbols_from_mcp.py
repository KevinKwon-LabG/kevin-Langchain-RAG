#!/usr/bin/env python3
"""
MCP 서버의 load_all_tickers 도구를 사용하여 전체 주식 종목 정보를 가져와서 JSON 파일로 저장하는 스크립트
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

class MCPStockSymbolsCollector:
    """MCP 서버의 load_all_tickers 도구를 사용하여 전체 주식 종목 정보를 수집하는 클래스"""
    
    def __init__(self):
        """초기화"""
        settings = get_settings()
        self.mcp_server_url = settings.mcp_server_url
        self.timeout = 120  # 전체 주식 데이터 로딩은 시간이 걸릴 수 있으므로 타임아웃 증가
        
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
    
    async def get_all_stock_symbols(self) -> List[Dict[str, str]]:
        """
        전체 주식 종목 목록을 가져옵니다.
        
        Returns:
            List[Dict[str, str]]: 전체 주식 종목 정보 목록
        """
        logger.info("전체 주식 종목 목록을 가져옵니다...")
        
        try:
            # 먼저 load_all_tickers를 호출하여 데이터 로드
            load_result = await self.load_all_tickers()
            
            if "error" in load_result:
                logger.error(f"주식 데이터 로드 실패: {load_result['error']}")
                return []
            
            # load_all_tickers 응답에서 직접 종목 목록 추출 시도
            symbols_list = self._extract_symbols_from_load_result(load_result)
            
            if symbols_list:
                logger.info(f"load_all_tickers에서 {len(symbols_list)}개의 종목을 찾았습니다.")
                return symbols_list
            
            # load_all_tickers에서 직접 추출이 안 되면, search_stock을 사용하여 전체 목록 구성
            logger.info("search_stock을 사용하여 전체 종목 목록을 구성합니다...")
            return await self._get_symbols_via_search()
                    
        except Exception as e:
            logger.error(f"전체 주식 종목 목록 가져오기 실패: {e}")
            return []
    
    def _extract_symbols_from_load_result(self, load_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        load_all_tickers 응답에서 종목 목록을 추출합니다.
        
        Args:
            load_result: load_all_tickers 응답 데이터
            
        Returns:
            List[Dict[str, str]]: 종목 정보 목록
        """
        symbols_list = []
        
        try:
            # 다양한 응답 형식에 대응
            if isinstance(load_result, dict):
                # 직접 종목 목록이 있는 경우
                if "tickers" in load_result:
                    tickers = load_result["tickers"]
                elif "symbols" in load_result:
                    tickers = load_result["symbols"]
                elif "stocks" in load_result:
                    tickers = load_result["stocks"]
                elif "data" in load_result and isinstance(load_result["data"], dict):
                    if "tickers" in load_result["data"]:
                        tickers = load_result["data"]["tickers"]
                    elif "symbols" in load_result["data"]:
                        tickers = load_result["data"]["symbols"]
                    elif "stocks" in load_result["data"]:
                        tickers = load_result["data"]["stocks"]
                elif "result" in load_result and isinstance(load_result["result"], dict):
                    if "tickers" in load_result["result"]:
                        tickers = load_result["result"]["tickers"]
                    elif "symbols" in load_result["result"]:
                        tickers = load_result["result"]["symbols"]
                    elif "stocks" in load_result["result"]:
                        tickers = load_result["result"]["stocks"]
                else:
                    # 전체 응답을 문자열로 변환하여 종목 정보 찾기
                    response_str = str(load_result)
                    tickers = self._parse_symbols_from_string(response_str)
                
                # 종목 정보 정규화
                if tickers:
                    for ticker in tickers:
                        if isinstance(ticker, dict):
                            symbol_info = self._normalize_stock_info(ticker)
                            if symbol_info:
                                symbols_list.append(symbol_info)
                        elif isinstance(ticker, str):
                            # 문자열인 경우 종목코드로 간주
                            symbols_list.append({
                                "symbol": ticker,
                                "korean_name": f"종목_{ticker}",
                                "korean_short_name": f"종목_{ticker}",
                                "english_name": f"Stock_{ticker}"
                            })
            
            return symbols_list
            
        except Exception as e:
            logger.error(f"load_result에서 종목 추출 실패: {e}")
            return []
    
    def _parse_symbols_from_string(self, response_str: str) -> List[Dict[str, str]]:
        """
        응답 문자열에서 종목 정보를 파싱합니다.
        
        Args:
            response_str: 응답 문자열
            
        Returns:
            List[Dict[str, str]]: 종목 정보 목록
        """
        symbols_list = []
        
        try:
            import re
            
            # 종목코드 패턴 (6자리 숫자)
            symbol_pattern = r'(\d{6})'
            symbols = re.findall(symbol_pattern, response_str)
            
            # 중복 제거
            unique_symbols = list(set(symbols))
            
            for symbol in unique_symbols:
                symbols_list.append({
                    "symbol": symbol,
                    "korean_name": f"종목_{symbol}",
                    "korean_short_name": f"종목_{symbol}",
                    "english_name": f"Stock_{symbol}"
                })
            
            return symbols_list
            
        except Exception as e:
            logger.error(f"문자열에서 종목 파싱 실패: {e}")
            return []
    
    async def _get_symbols_via_search(self) -> List[Dict[str, str]]:
        """
        search_stock을 사용하여 전체 종목 목록을 구성합니다.
        
        Returns:
            List[Dict[str, str]]: 종목 정보 목록
        """
        symbols_list = []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 대표적인 검색어들로 종목 검색
                search_keywords = [
                    "삼성", "SK", "LG", "현대", "기아", "포스코", "KT", "두산", "한화", "롯데",
                    "CJ", "GS", "LS", "효성", "대우", "동부", "금호", "아시아나", "대한항공",
                    "NAVER", "카카오", "쿠팡", "배달의민족", "토스", "당근마켓", "야놀자"
                ]
                
                for keyword in search_keywords:
                    try:
                        endpoint = f"{self.mcp_server_url}/tools/search_stock"
                        request_data = {"keyword": keyword}
                        
                        response = await client.post(endpoint, json=request_data)
                        
                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"검색어 '{keyword}' 결과: {data}")
                            
                            # 검색 결과에서 종목 정보 추출
                            search_results = self._extract_search_results(data)
                            symbols_list.extend(search_results)
                        
                    except Exception as e:
                        logger.debug(f"검색어 '{keyword}' 검색 실패: {e}")
                        continue
                
                # 중복 제거
                unique_symbols = []
                seen_symbols = set()
                
                for symbol in symbols_list:
                    if symbol["symbol"] not in seen_symbols:
                        unique_symbols.append(symbol)
                        seen_symbols.add(symbol["symbol"])
                
                return unique_symbols
                
        except Exception as e:
            logger.error(f"search_stock을 통한 종목 목록 구성 실패: {e}")
            return []
    
    def _extract_search_results(self, search_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        검색 결과에서 종목 정보를 추출합니다.
        
        Args:
            search_data: 검색 응답 데이터
            
        Returns:
            List[Dict[str, str]]: 종목 정보 목록
        """
        results = []
        
        try:
            if isinstance(search_data, dict):
                # 다양한 응답 형식에 대응
                if "results" in search_data:
                    items = search_data["results"]
                elif "data" in search_data:
                    items = search_data["data"]
                elif "stocks" in search_data:
                    items = search_data["stocks"]
                elif "symbols" in search_data:
                    items = search_data["symbols"]
                elif isinstance(search_data, list):
                    items = search_data
                else:
                    items = [search_data]
                
                for item in items:
                    if isinstance(item, dict):
                        symbol_info = self._normalize_stock_info(item)
                        if symbol_info:
                            results.append(symbol_info)
            
            return results
            
        except Exception as e:
            logger.error(f"검색 결과 추출 실패: {e}")
            return []
    
    def _normalize_stock_info(self, stock_data: Dict[str, Any]) -> Dict[str, str]:
        """
        주식 정보를 정규화합니다.
        
        Args:
            stock_data: 주식 데이터
            
        Returns:
            Dict[str, str]: 정규화된 주식 정보
        """
        try:
            # 종목코드 추출
            symbol = ""
            if "symbol" in stock_data:
                symbol = str(stock_data["symbol"])
            elif "code" in stock_data:
                symbol = str(stock_data["code"])
            elif "stock_code" in stock_data:
                symbol = str(stock_data["stock_code"])
            elif "ticker" in stock_data:
                symbol = str(stock_data["ticker"])
            
            if not symbol:
                return None
            
            # 종목명 추출
            korean_name = ""
            if "name" in stock_data:
                korean_name = str(stock_data["name"])
            elif "stock_name" in stock_data:
                korean_name = str(stock_data["stock_name"])
            elif "company_name" in stock_data:
                korean_name = str(stock_data["company_name"])
            elif "title" in stock_data:
                korean_name = str(stock_data["title"])
            
            if not korean_name:
                korean_name = f"종목_{symbol}"
            
            # 영문명 추출
            english_name = ""
            if "english_name" in stock_data:
                english_name = str(stock_data["english_name"])
            elif "eng_name" in stock_data:
                english_name = str(stock_data["eng_name"])
            elif "name_en" in stock_data:
                english_name = str(stock_data["name_en"])
            else:
                english_name = f"Stock_{symbol}"
            
            return {
                "symbol": symbol,
                "korean_name": korean_name,
                "korean_short_name": korean_name,
                "english_name": english_name
            }
            
        except Exception as e:
            logger.error(f"주식 정보 정규화 실패: {e}")
            return None
    
    def save_to_json(self, symbols: List[Dict[str, str]], output_file: str = "stock_symbols_from_mcp.json"):
        """
        주식 종목 정보를 JSON 파일로 저장합니다.
        
        Args:
            symbols: 주식 종목 정보 목록
            output_file: 출력 파일명
        """
        try:
            output_path = Path("data") / output_file
            
            data = {
                "metadata": {
                    "generated_at": str(Path(__file__).stat().st_mtime),
                    "total_symbols": len(symbols),
                    "source": "MCP Server - load_all_tickers",
                    "description": "MCP 서버의 load_all_tickers 도구를 통해 가져온 전체 주식 종목 목록",
                    "fields": {
                        "symbol": "종목코드",
                        "korean_name": "한글 종목명",
                        "korean_short_name": "한글 종목약명",
                        "english_name": "영문 종목명"
                    }
                },
                "symbols": symbols
            }
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2)
            
            logger.info(f"주식 종목 정보가 {output_path}에 저장되었습니다.")
            logger.info(f"총 {len(symbols)}개의 주식 종목이 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"JSON 파일 저장 실패: {e}")

async def main():
    """메인 함수"""
    logger.info("MCP 서버에서 전체 주식 종목 정보 수집을 시작합니다...")
    
    # 데이터 디렉토리 생성
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 수집기 초기화
    collector = MCPStockSymbolsCollector()
    
    # 1. load_all_tickers 도구 호출
    print("\n" + "="*60)
    print("1. MCP 서버 load_all_tickers 도구 호출")
    print("="*60)
    
    load_result = await collector.load_all_tickers()
    
    if "error" in load_result:
        print(f"❌ 오류: {load_result['error']}")
    else:
        print("✅ load_all_tickers 도구 호출 성공:")
        print(json.dumps(load_result, ensure_ascii=False, indent=2))
    
    # 2. 전체 주식 종목 목록 가져오기
    print("\n" + "="*60)
    print("2. 전체 주식 종목 목록 가져오기")
    print("="*60)
    
    symbols = await collector.get_all_stock_symbols()
    
    if symbols:
        # JSON 파일로 저장
        collector.save_to_json(symbols, "stock_symbols_from_mcp.json")
        
        logger.info("전체 주식 종목 정보 수집이 완료되었습니다.")
        
        # 처음 20개 주식 종목 출력
        print(f"\n총 {len(symbols)}개의 주식 종목을 찾았습니다:")
        for i, symbol in enumerate(symbols[:20], 1):
            print(f"{i:2d}. {symbol['symbol']} - {symbol['korean_name']} ({symbol['korean_short_name']})")
        if len(symbols) > 20:
            print(f"... 및 {len(symbols) - 20}개 더")
    else:
        logger.error("주식 종목 정보를 가져올 수 없었습니다.")
        print("주식 종목 정보를 가져올 수 없었습니다.")
    
    print("\n" + "="*60)
    print("MCP 서버 전체 주식 종목 정보 수집 완료")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 