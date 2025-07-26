import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TimeParser:
    def __init__(self):
        # 한국어 시간 표현 패턴
        self.time_patterns = {
            # 오늘, 어제, 내일
            'today': r'오늘|오늘자|오늘날|오늘의',
            'yesterday': r'어제|어제자|어제날|어제의',
            'tomorrow': r'내일|내일자|내일날|내일의',
            
            # 요일
            'this_week': r'이번주|이번 주|이번 주간|이번 주의',
            'last_week': r'지난주|지난 주|지난 주간|지난 주의',
            'next_week': r'다음주|다음 주|다음 주간|다음 주의',
            
            # 월
            'this_month': r'이번달|이번 달|이번 월|이번 월의',
            'last_month': r'지난달|지난 달|지난 월|지난 월의',
            'next_month': r'다음달|다음 달|다음 월|다음 월의',
            
            # 년
            'this_year': r'올해|이번년|이번 년|이번 년도|이번 년의',
            'last_year': r'작년|지난해|지난 년|지난 년도|지난 년의',
            'next_year': r'내년|다음해|다음 년|다음 년도|다음 년의',
            
            # 구체적인 시간 표현
            'hours_ago': r'(\d+)시간\s*전',
            'days_ago': r'(\d+)일\s*전',
            'weeks_ago': r'(\d+)주\s*전',
            'months_ago': r'(\d+)개월\s*전|(\d+)달\s*전',
            'years_ago': r'(\d+)년\s*전',
            
            'hours_later': r'(\d+)시간\s*후',
            'days_later': r'(\d+)일\s*후',
            'weeks_later': r'(\d+)주\s*후',
            'months_later': r'(\d+)개월\s*후|(\d+)달\s*후',
            'years_later': r'(\d+)년\s*후',
            
            # 특정 날짜
            'specific_date': r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
            'month_day': r'(\d{1,2})월\s*(\d{1,2})일',
            
            # 영어 표현도 포함
            'today_en': r'today|current|now',
            'yesterday_en': r'yesterday',
            'tomorrow_en': r'tomorrow',
            'this_week_en': r'this week|current week',
            'last_week_en': r'last week|previous week',
            'next_week_en': r'next week',
            'this_month_en': r'this month|current month',
            'last_month_en': r'last month|previous month',
            'next_month_en': r'next month',
            'this_year_en': r'this year|current year',
            'last_year_en': r'last year|previous year',
            'next_year_en': r'next year',
        }
    
    def parse_time_expressions(self, text: str) -> Dict[str, any]:
        """
        텍스트에서 시간 표현을 파싱하고 현재 시간을 기준으로 계산
        """
        current_time = datetime.now()
        parsed_info = {
            'original_text': text,
            'current_time': current_time,
            'time_expressions': [],
            'calculated_dates': {},
            'enhanced_query': text
        }
        
        # 각 패턴에 대해 검사
        for pattern_name, pattern in self.time_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                expression = match.group(0)
                parsed_info['time_expressions'].append({
                    'type': pattern_name,
                    'expression': expression,
                    'start': match.start(),
                    'end': match.end()
                })
                
                # 시간 계산
                calculated_date = self._calculate_date(pattern_name, match, current_time)
                if calculated_date:
                    parsed_info['calculated_dates'][pattern_name] = calculated_date
        
        # 쿼리 개선
        enhanced_query = self._enhance_query(text, parsed_info)
        parsed_info['enhanced_query'] = enhanced_query
        
        return parsed_info
    
    def _calculate_date(self, pattern_name: str, match, current_time: datetime) -> Optional[datetime]:
        """패턴에 따라 날짜 계산"""
        try:
            if pattern_name == 'today' or pattern_name == 'today_en':
                return current_time
            
            elif pattern_name == 'yesterday' or pattern_name == 'yesterday_en':
                return current_time - timedelta(days=1)
            
            elif pattern_name == 'tomorrow' or pattern_name == 'tomorrow_en':
                return current_time + timedelta(days=1)
            
            elif pattern_name == 'this_week' or pattern_name == 'this_week_en':
                # 이번 주 월요일
                days_since_monday = current_time.weekday()
                return current_time - timedelta(days=days_since_monday)
            
            elif pattern_name == 'last_week' or pattern_name == 'last_week_en':
                # 지난 주 월요일
                days_since_monday = current_time.weekday()
                return current_time - timedelta(days=days_since_monday + 7)
            
            elif pattern_name == 'next_week' or pattern_name == 'next_week_en':
                # 다음 주 월요일
                days_since_monday = current_time.weekday()
                return current_time + timedelta(days=7 - days_since_monday)
            
            elif pattern_name == 'this_month' or pattern_name == 'this_month_en':
                return current_time.replace(day=1)
            
            elif pattern_name == 'last_month' or pattern_name == 'last_month_en':
                if current_time.month == 1:
                    return current_time.replace(year=current_time.year-1, month=12, day=1)
                else:
                    return current_time.replace(month=current_time.month-1, day=1)
            
            elif pattern_name == 'next_month' or pattern_name == 'next_month_en':
                if current_time.month == 12:
                    return current_time.replace(year=current_time.year+1, month=1, day=1)
                else:
                    return current_time.replace(month=current_time.month+1, day=1)
            
            elif pattern_name == 'this_year' or pattern_name == 'this_year_en':
                return current_time.replace(month=1, day=1)
            
            elif pattern_name == 'last_year' or pattern_name == 'last_year_en':
                return current_time.replace(year=current_time.year-1, month=1, day=1)
            
            elif pattern_name == 'next_year' or pattern_name == 'next_year_en':
                return current_time.replace(year=current_time.year+1, month=1, day=1)
            
            elif pattern_name == 'hours_ago':
                hours = int(match.group(1))
                return current_time - timedelta(hours=hours)
            
            elif pattern_name == 'days_ago':
                days = int(match.group(1))
                return current_time - timedelta(days=days)
            
            elif pattern_name == 'weeks_ago':
                weeks = int(match.group(1))
                return current_time - timedelta(weeks=weeks)
            
            elif pattern_name == 'months_ago':
                months = int(match.group(1)) if match.group(1) else int(match.group(2))
                # 간단한 월 계산 (정확하지 않을 수 있음)
                return current_time - timedelta(days=months * 30)
            
            elif pattern_name == 'years_ago':
                years = int(match.group(1))
                return current_time.replace(year=current_time.year - years)
            
            elif pattern_name == 'hours_later':
                hours = int(match.group(1))
                return current_time + timedelta(hours=hours)
            
            elif pattern_name == 'days_later':
                days = int(match.group(1))
                return current_time + timedelta(days=days)
            
            elif pattern_name == 'weeks_later':
                weeks = int(match.group(1))
                return current_time + timedelta(weeks=weeks)
            
            elif pattern_name == 'months_later':
                months = int(match.group(1)) if match.group(1) else int(match.group(2))
                return current_time + timedelta(days=months * 30)
            
            elif pattern_name == 'years_later':
                years = int(match.group(1))
                return current_time.replace(year=current_time.year + years)
            
            elif pattern_name == 'specific_date':
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day)
            
            elif pattern_name == 'month_day':
                month = int(match.group(1))
                day = int(match.group(2))
                year = current_time.year
                # 과거 날짜인지 확인
                date = datetime(year, month, day)
                if date > current_time:
                    year -= 1
                    date = datetime(year, month, day)
                return date
        
        except Exception as e:
            logger.warning(f"날짜 계산 중 오류 발생: {e}")
            return None
        
        return None
    
    def _enhance_query(self, original_text: str, parsed_info: Dict) -> str:
        """파싱된 시간 정보를 바탕으로 쿼리를 개선"""
        enhanced_text = original_text
        
        # 현재 시간 정보 추가
        current_time = parsed_info['current_time']
        time_info = f"현재 시간: {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}"
        
        # 계산된 날짜 정보 추가
        date_info = []
        for pattern_name, calculated_date in parsed_info['calculated_dates'].items():
            if calculated_date:
                date_str = calculated_date.strftime('%Y년 %m월 %d일')
                date_info.append(f"{pattern_name}: {date_str}")
        
        if date_info:
            enhanced_text += f" (시간 정보: {', '.join(date_info)})"
        
        return enhanced_text
    
    def get_time_context(self, text: str) -> str:
        """시간 컨텍스트 정보를 반환"""
        parsed_info = self.parse_time_expressions(text)
        
        context_parts = []
        current_time = parsed_info['current_time']
        context_parts.append(f"현재 시간: {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}")
        
        if parsed_info['calculated_dates']:
            date_info = []
            for pattern_name, calculated_date in parsed_info['calculated_dates'].items():
                if calculated_date:
                    date_str = calculated_date.strftime('%Y년 %m월 %d일')
                    date_info.append(f"{pattern_name}: {date_str}")
            context_parts.append(f"참조 시간: {', '.join(date_info)}")
        
        return " | ".join(context_parts)

# 전역 인스턴스
time_parser = TimeParser() 