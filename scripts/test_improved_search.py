import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.websearch_service import websearch_service
from src.utils.time_parser import time_parser

def test_improved_search():
    test_queries = [
        "오늘자 트럼프 관련 기사",
        "어제 발생한 주요 뉴스",
        "이번 주 AI 기술 동향"
    ]
    
    print("🔍 개선된 날짜 필터링 검색 테스트")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] 검색 쿼리: {query}")
        print("-" * 60)
        
        try:
            # 시간 정보 파싱
            time_info = time_parser.parse_time_expressions(query)
            print(f"📅 현재 시간: {time_info['current_time'].strftime('%Y년 %m월 %d일 %H시 %M분')}")
            
            if time_info['time_expressions']:
                print(f"⏰ 발견된 시간 표현:")
                for expr in time_info['time_expressions']:
                    print(f"   - {expr['expression']} (타입: {expr['type']})")
                
                print(f"📊 계산된 날짜:")
                for pattern_name, calculated_date in time_info['calculated_dates'].items():
                    if calculated_date:
                        print(f"   - {pattern_name}: {calculated_date.strftime('%Y년 %m월 %d일')}")
            
            # 개선된 검색 쿼리 구성
            search_query = websearch_service._build_time_aware_query(query, time_info)
            print(f"🔍 개선된 검색 쿼리: {search_query}")
            
            # 구글 검색 실행
            print(f"\n🔍 구글 검색 실행 중...")
            search_result = websearch_service.search_web(query)
            print(f"📋 검색 결과:")
            print(search_result)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    test_improved_search() 