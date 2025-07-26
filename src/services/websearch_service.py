from langchain_community.utilities import GoogleSearchAPIWrapper
import logging
import requests
from datetime import datetime, timedelta
from src.utils.time_parser import time_parser

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = "AIzaSyCku3y4jh9dOG5Y12AZ5Z8TmOkWM4wrcRk"
GOOGLE_CSE_ID = "929c878b1943943e0"

class WebSearchService:
    def __init__(self):
        self.search = GoogleSearchAPIWrapper(
            google_api_key=GOOGLE_API_KEY,
            google_cse_id=GOOGLE_CSE_ID,
            k=5
        )

    def search_web(self, query: str) -> str:
        """구글 검색 결과를 요약 텍스트로 반환"""
        try:
            # 시간 정보 파싱 및 쿼리 개선
            time_info = time_parser.parse_time_expressions(query)
            enhanced_query = time_info['enhanced_query']
            
            # 시간 정보에 따른 검색 전략 결정
            search_query = self._build_time_aware_query(query, time_info)
            
            # 기존 LangChain 검색 사용 (안정적)
            results = self.search.results(search_query, num_results=10)
            logger.info(f"구글 검색 완료: {len(results)}개 결과")
            
            # 시간 컨텍스트 정보 추가
            time_context = time_parser.get_time_context(query)
            
            # 결과를 더 자세히 포맷팅
            summary_parts = []
            
            # 시간 컨텍스트 정보를 맨 위에 추가
            if time_info['time_expressions']:
                summary_parts.append(f"⏰ 시간 컨텍스트: {time_context}")
                summary_parts.append("")
            
            # 날짜 필터링 적용
            filtered_results = self._filter_by_date(results, time_info)
            
            for i, r in enumerate(filtered_results[:5]):  # 상위 5개만 표시
                title = r.get('title', '제목 없음')
                snippet = r.get('snippet', '내용 없음')
                link = r.get('link', '링크 없음')
                
                # 날짜 정보 추출 (snippet에서)
                date_info = ""
                if '...' in snippet and any(month in snippet for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                    # snippet에서 날짜 정보 추출
                    date_start = snippet.find('...') + 3
                    if date_start < len(snippet):
                        date_part = snippet[date_start:].strip()
                        if any(month in date_part[:20] for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                            date_info = f" (날짜: {date_part.split('...')[0].strip()})"
                
                # 링크 유효성 검사 및 클릭 가능한 링크 생성
                if link and link != '링크 없음':
                    # 링크 텍스트를 간단하게 표시
                    link_text = link.replace('https://', '').replace('http://', '')
                    if len(link_text) > 50:
                        link_text = link_text[:47] + '...'
                    clickable_link = f"<a href=\"{link}\" target=\"_blank\" style=\"color: #3498db; text-decoration: underline; cursor: pointer;\">{link_text}</a>"
                else:
                    clickable_link = "링크 없음"
                
                summary_parts.append(f"[{i+1}] {title}{date_info}\n   {snippet}\n   링크: {clickable_link}")
            
            summary = "\n\n".join(summary_parts)
            return summary
            
        except Exception as e:
            logger.error(f"구글 검색 중 오류 발생: {e}")
            return f"검색 중 오류가 발생했습니다: {str(e)}"
    
    def _build_time_aware_query(self, original_query: str, time_info: dict) -> str:
        """시간 정보를 고려한 검색 쿼리 구성"""
        query_parts = [original_query]
        
        if time_info['calculated_dates']:
            # 시간 표현에 따른 검색 키워드 추가
            for pattern_name, calculated_date in time_info['calculated_dates'].items():
                if calculated_date:
                    if pattern_name in ['today', 'today_en']:
                        query_parts.extend(['오늘', '2025년', '최신', '실시간', '뉴스', '기사'])
                    elif pattern_name in ['yesterday', 'yesterday_en']:
                        query_parts.extend(['어제', '2025년', '최신', '뉴스', '기사'])
                    elif pattern_name in ['this_week', 'this_week_en']:
                        query_parts.extend(['이번주', '이번 주', '2025년', '최신', '뉴스', '기사'])
                    elif pattern_name in ['last_week', 'last_week_en']:
                        query_parts.extend(['지난주', '지난 주', '2025년', '뉴스', '기사'])
                    elif pattern_name in ['this_month', 'this_month_en']:
                        query_parts.extend(['이번달', '이번 달', '2025년', '최신', '뉴스', '기사'])
                    elif pattern_name in ['last_month', 'last_month_en']:
                        query_parts.extend(['지난달', '지난 달', '2025년', '뉴스', '기사'])
                    elif pattern_name in ['this_year', 'this_year_en']:
                        query_parts.extend(['2025년', '올해', '최신', '뉴스', '기사'])
                    elif pattern_name in ['last_year', 'last_year_en']:
                        query_parts.extend(['2024년', '작년', '지난 해', '뉴스', '기사'])
                    elif 'ago' in pattern_name:
                        query_parts.extend(['2025년', '최신', '뉴스', '기사'])
                    elif 'later' in pattern_name:
                        query_parts.extend(['2025년', '예정', '뉴스'])
        
        # 특정 키워드가 있으면 더 구체적인 검색
        if '트럼프' in original_query:
            query_parts.extend(['Donald Trump', '미국 대선', '공화당'])
        if '뉴스' in original_query or '기사' in original_query:
            query_parts.extend(['news', 'latest', 'breaking'])
        
        return ' '.join(query_parts)
    
    def _search_with_date_filter(self, query: str, time_info: dict) -> list:
        """날짜 필터링을 포함한 구글 검색"""
        try:
            # 구글 Custom Search API 직접 호출
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': GOOGLE_API_KEY,
                'cx': GOOGLE_CSE_ID,
                'q': query,
                'num': 20  # 더 많은 결과를 가져와서 필터링
            }
            
            # 시간 정보가 있으면 검색 쿼리에 날짜 정보 추가 (간단하게)
            if time_info['calculated_dates']:
                for pattern_name, calculated_date in time_info['calculated_dates'].items():
                    if calculated_date:
                        if pattern_name in ['today', 'today_en']:
                            # 오늘 날짜 정보를 쿼리에 추가
                            params['q'] = f"{query} 2025년 7월 27일 오늘"
                        elif pattern_name in ['yesterday', 'yesterday_en']:
                            # 어제 날짜 정보를 쿼리에 추가
                            params['q'] = f"{query} 2025년 7월 26일 어제"
                        elif pattern_name in ['this_week', 'this_week_en']:
                            # 이번 주 정보를 쿼리에 추가
                            params['q'] = f"{query} 2025년 7월 이번주"
                        elif pattern_name in ['this_month', 'this_month_en']:
                            # 이번 달 정보를 쿼리에 추가
                            params['q'] = f"{query} 2025년 7월 이번달"
                        break
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            # 강화된 날짜 필터링 및 정렬
            if items:
                filtered_items = self._filter_by_date(items, time_info)
                return filtered_items[:5]  # 상위 5개 결과만 반환
            
            return items[:5]
            
        except Exception as e:
            logger.error(f"날짜 필터링 검색 중 오류: {e}")
            # 폴백: 기존 LangChain 검색 사용
            return self.search.results(query, num_results=5)
    
    def _filter_by_date(self, items: list, time_info: dict) -> list:
        """날짜 정보를 기반으로 결과 필터링"""
        if not time_info['calculated_dates']:
            return items
        
        filtered_items = []
        current_year = datetime.now().year
        
        for item in items:
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            full_text = f"{title} {snippet}"
            
            # 시간 표현에 따른 필터링
            is_relevant = False
            
            for pattern_name, calculated_date in time_info['calculated_dates'].items():
                if calculated_date:
                    target_year = calculated_date.year
                    target_month = calculated_date.month
                    target_day = calculated_date.day
                    
                    if pattern_name in ['today', 'today_en']:
                        # 오늘 날짜가 포함된 결과만
                        if (str(target_year) in full_text and 
                            str(target_month).zfill(2) in full_text and 
                            str(target_day).zfill(2) in full_text):
                            is_relevant = True
                        elif '오늘' in full_text or 'today' in full_text.lower():
                            is_relevant = True
                    
                    elif pattern_name in ['yesterday', 'yesterday_en']:
                        # 어제 날짜가 포함된 결과만
                        if (str(target_year) in full_text and 
                            str(target_month).zfill(2) in full_text and 
                            str(target_day).zfill(2) in full_text):
                            is_relevant = True
                        elif '어제' in full_text or 'yesterday' in full_text.lower():
                            is_relevant = True
                    
                    elif pattern_name in ['this_week', 'this_week_en']:
                        # 이번 주 (2025년 7월 21일 이후)
                        if str(target_year) in full_text and '7월' in full_text:
                            is_relevant = True
                        elif '이번주' in full_text or 'this week' in full_text.lower():
                            is_relevant = True
                    
                    elif pattern_name in ['this_month', 'this_month_en']:
                        # 이번 달 (2025년 7월)
                        if str(target_year) in full_text and '7월' in full_text:
                            is_relevant = True
                        elif '이번달' in full_text or 'this month' in full_text.lower():
                            is_relevant = True
                    
                    elif pattern_name in ['this_year', 'this_year_en']:
                        # 올해 (2025년)
                        if str(target_year) in full_text:
                            is_relevant = True
                        elif '2025년' in full_text or '올해' in full_text:
                            is_relevant = True
                    
                    elif 'ago' in pattern_name:
                        # 과거 시간 표현
                        if str(target_year) in full_text:
                            is_relevant = True
                    
                    elif 'later' in pattern_name:
                        # 미래 시간 표현
                        if str(target_year) in full_text:
                            is_relevant = True
            
            if is_relevant:
                filtered_items.append(item)
        
        # 필터링된 결과가 없으면 원본 결과 반환
        if not filtered_items:
            logger.warning("날짜 필터링 결과가 없어 원본 결과를 반환합니다.")
            return items
        
        # 날짜순으로 정렬 (최신순)
        def extract_date_score(item):
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            full_text = f"{title} {snippet}"
            
            # 2025년이 있으면 높은 점수
            if '2025' in full_text:
                return 100
            elif '2024' in full_text:
                return 50
            else:
                return 0
        
        filtered_items.sort(key=extract_date_score, reverse=True)
        return filtered_items

websearch_service = WebSearchService() 