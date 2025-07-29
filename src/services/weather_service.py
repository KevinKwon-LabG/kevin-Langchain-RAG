"""
날씨 서비스
날씨 관련 질문을 감지하고 MCP 서버에 요청하여 답변을 생성합니다.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.services.mcp_service import mcp_service
from src.config.settings import settings

logger = logging.getLogger(__name__)

class WeatherService:
    """날씨 관련 질문을 처리하는 서비스"""
    
    def __init__(self):
        self.weather_keywords = [
            # 한국어 날씨 키워드
            "날씨", "기온", "온도", "습도", "강수", "비", "눈", "바람", "풍속", "기압",
            "맑음", "흐림", "구름", "안개", "천둥", "번개", "우박", "서리", "결빙",
            "더위", "추위", "폭염", "한파", "장마", "태풍", "홍수", "가뭄",
            "일기예보", "기상예보", "날씨예보", "기상정보", "기상상황",
            "오늘날씨", "내일날씨", "주말날씨", "이번주날씨", "다음주날씨",
            "서울날씨", "부산날씨", "대구날씨", "인천날씨", "광주날씨", "대전날씨", "울산날씨",
            "제주날씨", "강릉날씨", "춘천날씨", "청주날씨", "전주날씨", "포항날씨",
            
            # 영어 날씨 키워드
            "weather", "temperature", "humidity", "precipitation", "rain", "snow", 
            "wind", "pressure", "sunny", "cloudy", "foggy", "thunder", "lightning",
            "hail", "frost", "heat", "cold", "heatwave", "coldwave", "monsoon",
            "typhoon", "flood", "drought", "forecast", "climate", "atmosphere",
            "today weather", "tomorrow weather", "weekend weather", "this week weather",
            "seoul weather", "busan weather", "daegu weather", "incheon weather",
            "gwangju weather", "daejeon weather", "ulsan weather", "jeju weather"
        ]
        
        self.weather_patterns = [
            # 한국어 패턴
            r"(.+날씨)",
            r"(.+기온)",
            r"(.+온도)",
            r"(.+기상)",
            r"(.+일기)",
            r"(.+기후)",
            r"(.+강수)",
            r"(.+습도)",
            r"(.+바람)",
            r"(.+풍속)",
            r"(.+기압)",
            r"(.+예보)",
            r"(.+정보)",
            r"(.+상황)",
            
            # 영어 패턴
            r"(.+weather)",
            r"(.+temperature)",
            r"(.+climate)",
            r"(.+forecast)",
            r"(.+precipitation)",
            r"(.+humidity)",
            r"(.+wind)",
            r"(.+pressure)",
            r"(.+atmosphere)"
        ]
        
        self.location_keywords = [
            # MCP 서버에서 제공하는 한국 도시 목록 (158개)
            # 수도권
            "서울", "인천", "인천시", "부평", "계양", "서구", "미추홀", "연수", "남동", "중구", "동구", 
            "강화", "옹진", "세종", "성남", "성남시", "수원", "수원시", "의정부", "안양", "부천", 
            "광명", "평택", "동두천", "안산", "고양", "고양시", "과천", "구리", "남양주", "오산", 
            "시흥", "군포", "의왕", "하남", "용인", "용인시", "파주", "이천", "안성", "김포", 
            "화성", "여주", "양평",
            
            # 부산권
            "부산", "부산시", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", 
            "금정구", "강서구", "연제구", "수영구", "사상구", "기장군",
            
            # 대구권
            "대구",
            
            # 광주권
            "광주",
            
            # 대전권
            "대전",
            
            # 울산권
            "울산",
            
            # 제주권
            "제주", "제주시", "서귀포",
            
            # 강원도
            "강릉", "춘천", "원주", "속초", "동해", "태백", "삼척", "정선",
            
            # 충청북도
            "청주", "충주", "제천", "보은", "옥천", "영동",
            
            # 충청남도
            "천안", "공주", "보령", "아산", "서산", "논산", "계룡", "당진",
            
            # 전라북도
            "전주", "군산", "익산", "정읍", "남원", "김제", "완주",
            
            # 전라남도
            "목포", "여수", "순천", "나주", "광양", "담양", "곡성", "구례", "고흥", "보성", 
            "화순", "장흥", "강진", "해남", "영암", "무안", "함평", "영광", "장성", "완도", 
            "진도", "신안",
            
            # 경상북도
            "포항", "경주", "김천", "안동", "구미", "영주", "영천", "상주", "문경", "경산", 
            "군위", "의성", "청송", "영양", "영덕", "청도", "고령", "성주", "칠곡", "예천", 
            "봉화", "울진", "울릉",
            
            # 경상남도
            "창원", "진주", "통영", "사천", "김해", "밀양", "거제", "양산", "의령", "함안", 
            "창녕", "고성", "남해", "하동", "산청", "함양", "거창", "합천",
            
            # 영어 도시명 (주요 도시)
            "seoul", "busan", "daegu", "incheon", "gwangju", "daejeon", "ulsan", "sejong",
            "jeju", "gangneung", "chuncheon", "cheongju", "jeonju", "pohang", "changwon", "suwon"
        ]
    
    def is_weather_question(self, message: str) -> bool:
        """
        메시지가 날씨 관련 질문인지 확인합니다.
        
        Args:
            message: 사용자 메시지
            
        Returns:
            날씨 관련 질문 여부
        """
        message_lower = message.lower()
        
        # 키워드 기반 검사
        for keyword in self.weather_keywords:
            if keyword.lower() in message_lower:
                return True
        
        # 패턴 기반 검사
        for pattern in self.weather_patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    def extract_location(self, message: str) -> Optional[str]:
        """
        메시지에서 위치 정보를 추출합니다.
        
        Args:
            message: 사용자 메시지
            
        Returns:
            추출된 위치 정보 또는 None
        """
        message_lower = message.lower()
        
        # 위치 키워드 검사
        for location in self.location_keywords:
            if location.lower() in message_lower:
                return location
        
        # 패턴 매칭으로 위치 추출
        location_patterns = [
            r"(.+?)날씨",
            r"(.+?)기온",
            r"(.+?)온도",
            r"(.+?)기상",
            r"(.+?)일기",
            r"(.+?)기후",
            r"(.+?)weather",
            r"(.+?)temperature",
            r"(.+?)climate"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message_lower)
            if match:
                location = match.group(1).strip()
                # 위치 키워드에 있는지 확인
                if location in self.location_keywords:
                    return location
        
        return None
    
    def create_weather_prompt(self, message: str, location: Optional[str] = None) -> str:
        """
        날씨 정보 요청을 위한 프롬프트를 생성합니다.
        
        Args:
            message: 사용자 메시지
            location: 추출된 위치 정보
            
        Returns:
            MCP 서버에 전송할 프롬프트
        """
        if location:
            prompt = f"""
다음은 사용자의 날씨 관련 질문입니다:

사용자 질문: {message}
위치: {location}

위치 정보를 포함하여 정확하고 상세한 날씨 정보를 제공해주세요. 
다음 정보들을 포함하여 답변해주세요:
- 현재 날씨 상황
- 기온 (최고/최저)
- 습도
- 강수 확률
- 바람 정보
- 미세먼지 정보 (가능한 경우)
- 일기 예보 (오늘, 내일, 주말 등)

한국어로 친근하고 이해하기 쉽게 답변해주세요.
"""
        else:
            prompt = f"""
다음은 사용자의 날씨 관련 질문입니다:

사용자 질문: {message}

사용자의 질문에 맞는 날씨 정보를 제공해주세요. 
위치가 명시되지 않은 경우, 서울 기준으로 답변하거나 위치를 명확히 해달라고 요청해주세요.

다음 정보들을 포함하여 답변해주세요:
- 현재 날씨 상황
- 기온 (최고/최저)
- 습도
- 강수 확률
- 바람 정보
- 미세먼지 정보 (가능한 경우)
- 일기 예보 (오늘, 내일, 주말 등)

한국어로 친근하고 이해하기 쉽게 답변해주세요.
"""
        
        return prompt.strip()
    
    async def get_weather_response(self, message: str) -> Dict[str, Any]:
        """
        날씨 관련 질문에 대한 응답을 MCP 서버에서 가져옵니다.
        
        Args:
            message: 사용자 메시지
            
        Returns:
            날씨 응답 정보
        """
        try:
            # 위치 정보 추출
            location = self.extract_location(message)
            
            if not location:
                # 위치가 추출되지 않은 경우 서울을 기본값으로 사용
                location = "서울"
                logger.info(f"위치 정보가 추출되지 않아 기본값 '{location}'을 사용합니다.")
            
            # 메시지에서 날씨 유형 판단
            weather_type = self._determine_weather_type(message)
            
            # MCP 서버의 날씨 도구 호출
            if weather_type == "forecast":
                # 날씨 예보 요청
                response = await mcp_service.call_tool("get_weather_forecast", {"city": location})
            else:
                # 현재 날씨 요청
                response = await mcp_service.call_tool("get_current_weather", {"city": location})
            
            # 응답 처리
            if response and isinstance(response, dict):
                # 응답을 사용자 친화적인 형태로 변환
                response_text = self._format_weather_response(response, location, weather_type)
                
                return {
                    "success": True,
                    "response": response_text,
                    "location": location,
                    "weather_type": weather_type,
                    "raw_data": response,
                    "timestamp": datetime.now().isoformat(),
                    "source": "mcp_weather_service"
                }
            else:
                raise Exception("MCP 서버에서 유효하지 않은 응답을 받았습니다.")
            
        except Exception as e:
            logger.error(f"날씨 정보 요청 실패: {e}")
            return {
                "success": False,
                "error": f"날씨 정보를 가져오는 중 오류가 발생했습니다: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "source": "mcp_weather_service"
            }
    
    def _determine_weather_type(self, message: str) -> str:
        """
        메시지에서 날씨 유형을 판단합니다.
        
        Args:
            message: 사용자 메시지
            
        Returns:
            날씨 유형 ("current" 또는 "forecast")
        """
        message_lower = message.lower()
        
        # 예보 관련 키워드
        forecast_keywords = [
            "예보", "내일", "모레", "주말", "다음주", "이번주", "forecast", "tomorrow", 
            "weekend", "next week", "this week", "오늘", "today"
        ]
        
        for keyword in forecast_keywords:
            if keyword in message_lower:
                return "forecast"
        
        return "current"
    
    def _format_weather_response(self, response: Dict[str, Any], location: str, weather_type: str) -> str:
        """
        MCP 서버 응답을 사용자 친화적인 형태로 변환합니다.
        
        Args:
            response: MCP 서버 응답
            location: 위치 정보
            weather_type: 날씨 유형
            
        Returns:
            포맷된 응답 텍스트
        """
        try:
            # MCP 서버 응답 구조 파악
            if isinstance(response, dict):
                # result 필드가 있는 경우 (중첩된 구조)
                if 'result' in response and isinstance(response['result'], dict):
                    result = response['result']
                    
                    # success 필드가 있는 경우
                    if 'success' in result and result['success']:
                        if 'data' in result:
                            # 현재 날씨 데이터
                            data = result['data']
                            return self._format_current_weather(data, location)
                        elif 'city' in result:
                            # 날씨 예보 데이터
                            return self._format_forecast_weather(result, location)
                        else:
                            # 기타 데이터
                            return self._format_generic_weather(result, location, weather_type)
                    else:
                        # 실패한 경우
                        error_msg = result.get('error', '알 수 없는 오류')
                        return f"{location}의 날씨 정보를 가져오는 중 오류가 발생했습니다: {error_msg}"
                
                # 직접 데이터가 있는 경우
                elif 'data' in response:
                    return self._format_current_weather(response['data'], location)
                elif 'city' in response:
                    return self._format_forecast_weather(response, location)
                else:
                    # 기타 구조
                    return self._format_generic_weather(response, location, weather_type)
            
            # 문자열인 경우
            elif isinstance(response, str):
                return f"{location}의 날씨 정보:\n{response}"
            
            # 기타 타입
            else:
                return f"{location}의 날씨 정보:\n{str(response)}"
                
        except Exception as e:
            logger.error(f"날씨 응답 포맷 실패: {e}")
            return f"{location}의 날씨 정보를 처리하는 중 오류가 발생했습니다."
    
    def _format_current_weather(self, data: Dict[str, Any], location: str) -> str:
        """현재 날씨 정보를 포맷팅합니다."""
        try:
            city_name = data.get('city_korean', data.get('city', location))
            
            # 이미 포맷된 content가 있는 경우 우선 사용
            if 'content' in data and isinstance(data['content'], list):
                for item in data['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        return item.get('text', f"📍 {city_name} 현재 날씨")
            
            # 기본 정보
            weather_info = f"📍 {city_name} 현재 날씨\n\n"
            
            # 날씨 상태
            if 'description' in data:
                weather_info += f"🌤️ 날씨: {data['description']}\n"
            elif 'description_korean' in data:
                weather_info += f"🌤️ 날씨: {data['description_korean']}\n"
            elif 'weather' in data:
                weather_info += f"🌤️ 날씨: {data['weather']}\n"
            
            # 기온
            if 'temperature' in data:
                temp = data['temperature']
                if isinstance(temp, (int, float)):
                    weather_info += f"🌡️ 기온: {temp}°C\n"
                elif isinstance(temp, dict):
                    celsius = temp.get('celsius', temp.get('current', temp.get('temp', 'N/A')))
                    fahrenheit = temp.get('fahrenheit', 'N/A')
                    if celsius != 'N/A':
                        weather_info += f"🌡️ 기온: {celsius}°C"
                        if fahrenheit != 'N/A':
                            weather_info += f" ({fahrenheit}°F)"
                        weather_info += "\n"
            
            # 체감온도
            if 'feels_like' in data:
                feels = data['feels_like']
                if isinstance(feels, dict):
                    celsius = feels.get('celsius', feels.get('current', 'N/A'))
                    if celsius != 'N/A':
                        weather_info += f"💨 체감온도: {celsius}°C\n"
            
            # 습도
            if 'humidity' in data:
                humidity = data['humidity']
                if isinstance(humidity, (int, float)):
                    weather_info += f"💧 습도: {humidity}%\n"
                elif isinstance(humidity, dict):
                    current = humidity.get('current', humidity.get('humidity', 'N/A'))
                    weather_info += f"💧 습도: {current}%\n"
            
            # 바람
            if 'wind' in data:
                wind = data['wind']
                if isinstance(wind, dict):
                    speed = wind.get('speed', wind.get('wind_speed', 'N/A'))
                    direction = wind.get('direction', wind.get('wind_direction', 'N/A'))
                    weather_info += f"💨 바람: {speed} m/s ({direction}°)\n"
                else:
                    weather_info += f"💨 바람: {wind}\n"
            
            # 기압
            if 'pressure' in data:
                pressure = data['pressure']
                if isinstance(pressure, (int, float)):
                    weather_info += f"📊 기압: {pressure} hPa\n"
                elif isinstance(pressure, dict):
                    current = pressure.get('current', pressure.get('pressure', 'N/A'))
                    weather_info += f"📊 기압: {current} hPa\n"
            
            # 가시거리
            if 'visibility' in data:
                visibility = data['visibility']
                if isinstance(visibility, (int, float)):
                    weather_info += f"👁️ 가시거리: {visibility} km\n"
                elif isinstance(visibility, dict):
                    current = visibility.get('current', visibility.get('visibility', 'N/A'))
                    weather_info += f"👁️ 가시거리: {current} km\n"
            
            # 구름
            if 'clouds' in data:
                clouds = data['clouds']
                if isinstance(clouds, (int, float)):
                    weather_info += f"☁️ 구름: {clouds}%\n"
            
            # 일출/일몰
            if 'sunrise' in data and 'sunset' in data:
                weather_info += f"🌅 일출: {data['sunrise']} | 🌇 일몰: {data['sunset']}\n"
            
            # 강수 확률
            if 'precipitation' in data:
                precip = data['precipitation']
                if isinstance(precip, dict):
                    probability = precip.get('probability', precip.get('chance', 'N/A'))
                    weather_info += f"🌧️ 강수 확률: {probability}%\n"
                else:
                    weather_info += f"🌧️ 강수: {precip}\n"
            
            # 업데이트 시간
            if 'timestamp' in data:
                weather_info += f"\n🕐 업데이트: {data['timestamp']}"
            elif 'updated_at' in data:
                weather_info += f"\n🕐 업데이트: {data['updated_at']}"
            
            return weather_info
            
        except Exception as e:
            logger.error(f"현재 날씨 포맷 실패: {e}")
            return f"{location}의 현재 날씨 정보를 처리하는 중 오류가 발생했습니다."
    
    def _format_forecast_weather(self, data: Dict[str, Any], location: str) -> str:
        """날씨 예보 정보를 포맷팅합니다."""
        try:
            city_name = data.get('city_korean', data.get('city', location))
            
            # 이미 포맷된 content가 있는 경우 우선 사용
            if 'content' in data and isinstance(data['content'], list):
                for item in data['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        return item.get('text', f"📍 {city_name} 5일 날씨 예보")
            
            weather_info = f"📍 {city_name} 5일 날씨 예보\n\n"
            
            # forecasts 필드가 있는 경우 (구조화된 예보 데이터)
            if 'forecasts' in data and isinstance(data['forecasts'], list):
                for i, day in enumerate(data['forecasts'][:5]):  # 최대 5일
                    if isinstance(day, dict):
                        date = day.get('date', f'Day {i+1}')
                        day_name = day.get('day_name_korean', day.get('day_name', ''))
                        description = day.get('description', 'N/A')
                        
                        # 기온 정보
                        temp_info = day.get('temperature', {})
                        if isinstance(temp_info, dict):
                            temp_min = temp_info.get('min', 'N/A')
                            temp_max = temp_info.get('max', 'N/A')
                            temp_avg = temp_info.get('avg', 'N/A')
                            temp_str = f"{temp_min}°C ~ {temp_max}°C"
                            if temp_avg != 'N/A':
                                temp_str += f" (평균: {temp_avg}°C)"
                        else:
                            temp_str = str(temp_info)
                        
                        humidity = day.get('humidity', 'N/A')
                        wind_speed = day.get('wind_speed', 'N/A')
                        
                        weather_info += f"📅 {day_name} ({date})\n"
                        weather_info += f"   🌡️ {temp_str}\n"
                        weather_info += f"   🌤️ {description}\n"
                        weather_info += f"   💧 습도: {humidity}% | 💨 바람: {wind_speed} m/s\n\n"
            
            # forecast 필드가 있는 경우 (기존 구조)
            elif 'forecast' in data and isinstance(data['forecast'], list):
                for i, day in enumerate(data['forecast'][:5]):  # 최대 5일
                    if isinstance(day, dict):
                        date = day.get('date', f'Day {i+1}')
                        weather = day.get('weather', 'N/A')
                        temp_min = day.get('temp_min', day.get('min_temp', 'N/A'))
                        temp_max = day.get('temp_max', day.get('max_temp', 'N/A'))
                        humidity = day.get('humidity', 'N/A')
                        
                        weather_info += f"📅 {date}\n"
                        weather_info += f"   🌤️ {weather}\n"
                        weather_info += f"   🌡️ {temp_min}°C ~ {temp_max}°C\n"
                        weather_info += f"   💧 습도: {humidity}%\n\n"
            
            # content가 문자열인 경우
            elif 'content' in data and isinstance(data['content'], str):
                weather_info += data['content']
            
            # content가 리스트인 경우 (예: 일별 예보)
            elif 'content' in data and isinstance(data['content'], list):
                for i, day_content in enumerate(data['content'][:5]):
                    if isinstance(day_content, dict):
                        date = day_content.get('date', f'Day {i+1}')
                        weather = day_content.get('weather', 'N/A')
                        temp = day_content.get('temp', 'N/A')
                        
                        weather_info += f"📅 {date}\n"
                        weather_info += f"   🌤️ {weather}\n"
                        weather_info += f"   🌡️ {temp}°C\n\n"
                    elif isinstance(day_content, str):
                        weather_info += f"📅 Day {i+1}: {day_content}\n\n"
            
            # 기타 필드들을 확인
            else:
                # 주요 날씨 관련 필드들을 찾아서 표시
                for key, value in data.items():
                    if key in ['city', 'city_korean', 'success', 'error', 'forecast', 'forecasts']:
                        continue
                    
                    if isinstance(value, (int, float)):
                        if 'temp' in key.lower():
                            weather_info += f"🌡️ {key}: {value}°C\n"
                        elif 'humidity' in key.lower():
                            weather_info += f"💧 {key}: {value}%\n"
                        else:
                            weather_info += f"📊 {key}: {value}\n"
                    elif isinstance(value, str):
                        if 'weather' in key.lower():
                            weather_info += f"🌤️ {key}: {value}\n"
                        else:
                            weather_info += f"📝 {key}: {value}\n"
                    elif isinstance(value, list):
                        weather_info += f"📋 {key}: {len(value)}개 항목\n"
                    elif isinstance(value, dict):
                        weather_info += f"📋 {key}: {str(value)[:100]}...\n"
                
                if weather_info == f"📍 {city_name} 5일 날씨 예보\n\n":
                    weather_info += "예보 정보를 불러오는 중입니다..."
            
            return weather_info
            
        except Exception as e:
            logger.error(f"날씨 예보 포맷 실패: {e}")
            return f"{location}의 날씨 예보 정보를 처리하는 중 오류가 발생했습니다."
    
    def _format_generic_weather(self, data: Dict[str, Any], location: str, weather_type: str) -> str:
        """일반적인 날씨 정보를 포맷팅합니다."""
        try:
            city_name = data.get('city_korean', data.get('city', location))
            
            if weather_type == "forecast":
                weather_info = f"📍 {city_name} 날씨 예보\n\n"
            else:
                weather_info = f"📍 {city_name} 현재 날씨\n\n"
            
            # 주요 필드들을 순회하며 포맷팅
            for key, value in data.items():
                if key in ['city', 'city_korean', 'success', 'error']:
                    continue
                
                if isinstance(value, (int, float)):
                    if 'temp' in key.lower():
                        weather_info += f"🌡️ {key}: {value}°C\n"
                    elif 'humidity' in key.lower():
                        weather_info += f"💧 {key}: {value}%\n"
                    elif 'pressure' in key.lower():
                        weather_info += f"📊 {key}: {value} hPa\n"
                    else:
                        weather_info += f"📊 {key}: {value}\n"
                elif isinstance(value, str):
                    if 'weather' in key.lower():
                        weather_info += f"🌤️ {key}: {value}\n"
                    elif 'wind' in key.lower():
                        weather_info += f"💨 {key}: {value}\n"
                    else:
                        weather_info += f"📝 {key}: {value}\n"
                elif isinstance(value, dict):
                    weather_info += f"📋 {key}: {str(value)[:100]}...\n"
            
            return weather_info
            
        except Exception as e:
            logger.error(f"일반 날씨 포맷 실패: {e}")
            return f"{location}의 날씨 정보:\n{str(data)}"
    
    def get_weather_info(self, message: str) -> Dict[str, Any]:
        """
        날씨 관련 질문인지 확인하고 정보를 반환합니다.
        
        Args:
            message: 사용자 메시지
            
        Returns:
            날씨 관련 정보
        """
        is_weather = self.is_weather_question(message)
        location = self.extract_location(message) if is_weather else None
        
        return {
            "is_weather_question": is_weather,
            "location": location,
            "keywords_found": [kw for kw in self.weather_keywords if kw.lower() in message.lower()],
            "timestamp": datetime.now().isoformat()
        }

# 싱글톤 인스턴스
weather_service = WeatherService() 