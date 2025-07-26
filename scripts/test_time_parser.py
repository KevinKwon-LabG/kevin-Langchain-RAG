import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.time_parser import time_parser

def test_time_parser():
    test_queries = [
        "오늘자 트럼프 관련 기사 5개를 출처와 함께 알려주세요.",
        "어제 발생한 주요 뉴스",
        "이번 주 AI 기술 동향",
        "지난달 경제 지표",
        "3일 전 발생한 사고",
        "2주 후 예정된 이벤트",
        "2024년 12월 25일 크리스마스",
        "5월 15일 생일",
        "1시간 전 업데이트된 정보",
        "내일 날씨 예보",
        "다음 주 주식 시장 전망",
        "작년 이맘때 상황",
        "올해 상반기 실적",
        "3개월 후 프로젝트 완료",
        "현재 시간 기준 최신 정보"
    ]
    
    print("🕐 시간 파서 테스트")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] 원본 쿼리: {query}")
        print("-" * 40)
        
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
                    print(f"   - {pattern_name}: {calculated_date.strftime('%Y년 %m월 %d일 %H시 %M분')}")
            
            print(f"🔍 개선된 쿼리: {time_info['enhanced_query']}")
        else:
            print("❌ 시간 표현이 발견되지 않음")
        
        print(f"📋 시간 컨텍스트: {time_parser.get_time_context(query)}")

if __name__ == "__main__":
    test_time_parser() 