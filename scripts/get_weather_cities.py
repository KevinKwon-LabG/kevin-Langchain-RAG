#!/usr/bin/env python3
"""
MCP 서버에서 날씨 정보를 제공하는 모든 도시 목록을 가져와서 CSV 파일로 저장하는 스크립트
"""

import asyncio
import json
import csv
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

class WeatherCitiesCollector:
    """MCP 서버에서 날씨 정보를 제공하는 도시 목록을 수집하는 클래스"""
    
    def __init__(self):
        """초기화"""
        settings = get_settings()
        self.mcp_server_url = settings.mcp_server_url
        self.timeout = 30
        self.max_retries = 3
        
        logger.info(f"MCP 서버 URL: {self.mcp_server_url}")
    
    async def get_available_cities(self) -> List[str]:
        """
        MCP 서버에서 지원하는 모든 도시 목록을 가져옵니다.
        
        Returns:
            List[str]: 도시 이름 목록
        """
        logger.info("MCP 서버에서 지원하는 도시 목록을 요청합니다...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # MCP 서버에 도시 목록 요청 - 여러 방법 시도
                endpoints_to_try = [
                    f"{self.mcp_server_url}/tools/get_current_weather/cities",
                    f"{self.mcp_server_url}/weather/cities",
                    f"{self.mcp_server_url}/tools/get_current_weather",
                    f"{self.mcp_server_url}/weather"
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        logger.info(f"엔드포인트 시도: {endpoint}")
                        
                        # 다양한 요청 형식 시도
                        request_data_list = [
                            {"request": "get_available_cities"},
                            {"query": "모든 지원 도시 목록을 알려주세요"},
                            {"action": "list_cities"},
                            {"city": "list_all"}
                        ]
                        
                        for request_data in request_data_list:
                            try:
                                response = await client.post(endpoint, json=request_data)
                                
                                if response.status_code == 200:
                                    data = response.json()
                                    logger.info(f"MCP 서버 응답: {data}")
                                    
                                    # 응답에서 도시 목록 추출
                                    cities = self._extract_cities_from_response(data)
                                    if cities:
                                        logger.info(f"총 {len(cities)}개의 도시를 찾았습니다.")
                                        return cities
                                        
                            except Exception as e:
                                logger.debug(f"요청 실패: {endpoint} - {request_data}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.debug(f"엔드포인트 실패: {endpoint}: {e}")
                        continue
                
                # 모든 시도가 실패한 경우, 기본 도시 목록 반환
                logger.warning("MCP 서버에서 도시 목록을 가져올 수 없어 기본 목록을 사용합니다.")
                return self._get_default_cities()
                    
        except Exception as e:
            logger.error(f"도시 목록 요청 실패: {e}")
            return self._get_default_cities()
    
    def _get_default_cities(self) -> List[str]:
        """기본 도시 목록을 반환합니다. (MCP 서버 연결 실패 시 사용)"""
        return [
            "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
            "수원", "성남", "의정부", "안양", "부천", "광명", "평택", "동두천",
            "안산", "고양", "과천", "구리", "남양주", "오산", "시흥", "군포",
            "의왕", "하남", "용인", "파주", "이천", "안성", "김포", "화성",
            "광주", "여주", "양평", "양주", "포천", "연천", "가평",
            "춘천", "원주", "강릉", "태백", "속초", "삼척", "동해", "횡성",
            "영월", "평창", "정선", "철원", "화천", "양구", "인제", "고성",
            "양양", "홍천", "태안", "당진", "서산", "논산", "계룡", "공주",
            "보령", "아산", "서천", "천안", "예산", "금산", "부여",
            "청양", "홍성", "제주", "서귀포", "포항", "경주", "김천", "안동",
            "구미", "영주", "영천", "상주", "문경", "경산", "군산", "익산",
            "정읍", "남원", "김제", "완주", "진안", "무주", "장수", "임실",
            "순창", "고창", "부안", "여수", "순천", "나주", "광양", "담양",
            "곡성", "구례", "고흥", "보성", "화순", "장흥", "강진", "해남",
            "영암", "무안", "함평", "영광", "장성", "완도", "진도", "신안"
        ]
    
    def _extract_cities_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """
        MCP 서버 응답에서 도시 목록을 추출합니다.
        
        Args:
            response_data: MCP 서버 응답 데이터
            
        Returns:
            List[str]: 도시 이름 목록
        """
        cities = []
        
        try:
            # 다양한 응답 형식에 대응
            if isinstance(response_data, dict):
                # 직접 도시 목록이 있는 경우
                if "cities" in response_data:
                    cities = response_data["cities"]
                elif "data" in response_data and isinstance(response_data["data"], dict):
                    if "cities" in response_data["data"]:
                        cities = response_data["data"]["cities"]
                elif "result" in response_data and isinstance(response_data["result"], dict):
                    if "cities" in response_data["result"]:
                        cities = response_data["result"]["cities"]
                    elif "supported_cities" in response_data["result"]:
                        cities = response_data["result"]["supported_cities"]
                    elif "data" in response_data["result"] and isinstance(response_data["result"]["data"], dict):
                        if "cities" in response_data["result"]["data"]:
                            cities = response_data["result"]["data"]["cities"]
                        elif "supported_cities" in response_data["result"]["data"]:
                            cities = response_data["result"]["data"]["supported_cities"]
                
                # 응답이 문자열인 경우 (JSON 파싱 필요)
                elif "message" in response_data:
                    message = response_data["message"]
                    # JSON 형태의 문자열에서 도시 목록 추출 시도
                    try:
                        import re
                        # JSON 배열 패턴 찾기
                        json_pattern = r'\[.*?\]'
                        matches = re.findall(json_pattern, message, re.DOTALL)
                        for match in matches:
                            try:
                                parsed = json.loads(match)
                                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                                    cities.extend(parsed)
                            except json.JSONDecodeError:
                                continue
                    except Exception:
                        pass
                
                # 응답이 리스트인 경우
                elif isinstance(response_data, list):
                    cities = response_data
            
            # 중복 제거 및 정렬
            cities = sorted(list(set(cities)))
            
            # 빈 문자열이나 None 값 제거
            cities = [city for city in cities if city and city.strip()]
            
            logger.info(f"추출된 도시 목록: {cities[:10]}... (총 {len(cities)}개)")
            return cities
            
        except Exception as e:
            logger.error(f"도시 목록 추출 실패: {e}")
            return []
    
    def save_to_csv(self, cities: List[str], output_file: str = "weather_cities.csv"):
        """
        도시 목록을 CSV 파일로 저장합니다.
        
        Args:
            cities: 도시 이름 목록
            output_file: 출력 파일명
        """
        try:
            output_path = Path("data") / output_file
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # 헤더 작성
                writer.writerow(['city_name'])
                
                # 도시 목록 작성
                for city in cities:
                    writer.writerow([city])
            
            logger.info(f"도시 목록이 {output_path}에 저장되었습니다.")
            logger.info(f"총 {len(cities)}개의 도시가 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"CSV 파일 저장 실패: {e}")
    
    def save_to_json(self, cities: List[str], output_file: str = "weather_cities.json"):
        """
        도시 목록을 JSON 파일로 저장합니다.
        
        Args:
            cities: 도시 이름 목록
            output_file: 출력 파일명
        """
        try:
            output_path = Path("data") / output_file
            
            data = {
                "metadata": {
                    "generated_at": str(Path(__file__).stat().st_mtime),
                    "total_cities": len(cities),
                    "source": "MCP Server",
                    "description": "MCP 서버에서 지원하는 날씨 정보 도시 목록"
                },
                "cities": cities
            }
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2)
            
            logger.info(f"도시 목록이 {output_path}에 저장되었습니다.")
            logger.info(f"총 {len(cities)}개의 도시가 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"JSON 파일 저장 실패: {e}")

async def main():
    """메인 함수"""
    logger.info("MCP 서버에서 날씨 정보 도시 목록 수집을 시작합니다...")
    
    # 데이터 디렉토리 생성
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 수집기 초기화
    collector = WeatherCitiesCollector()
    
    # 도시 목록 가져오기
    cities = await collector.get_available_cities()
    
    if cities:
        # CSV 파일로 저장
        collector.save_to_csv(cities, "weather_cities.csv")
        
        # JSON 파일로도 저장
        collector.save_to_json(cities, "weather_cities.json")
        
        logger.info("도시 목록 수집이 완료되었습니다.")
        
        # 처음 10개 도시 출력
        print(f"\n총 {len(cities)}개의 도시를 찾았습니다:")
        for i, city in enumerate(cities[:10], 1):
            print(f"{i:2d}. {city}")
        if len(cities) > 10:
            print(f"... 및 {len(cities) - 10}개 더")
    else:
        logger.error("도시 목록을 가져올 수 없었습니다.")
        print("도시 목록을 가져올 수 없었습니다. MCP 서버 상태를 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(main()) 