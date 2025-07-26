import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.websearch_service import websearch_service
from src.services.llm_decision_service import llm_decision_service

def test_trump_search():
    query = "오늘자 트럼프 관련 기사 5개를 출처와 함께 알려주세요."
    
    print(f"테스트 쿼리: {query}")
    print("="*60)
    
    # 1. 검색 필요성 판단
    try:
        needs_search = llm_decision_service.needs_web_search(query, model_name="deepseek-r1:14b")
        print(f"🌐 구글 검색 필요: {needs_search}")
    except Exception as e:
        print(f"❌ 검색 필요성 판단 오류: {e}")
        needs_search = True  # 오류 시 기본적으로 검색 수행
    
    # 2. 구글 검색 실행
    if needs_search:
        try:
            search_result = websearch_service.search_web("트럼프 최신 뉴스 2025")
            print(f"\n📋 검색 결과:")
            print(search_result)
        except Exception as e:
            print(f"❌ 구글 검색 오류: {e}")
    else:
        print("🔍 구글 검색이 필요하지 않다고 판단됨")

if __name__ == "__main__":
    test_trump_search() 