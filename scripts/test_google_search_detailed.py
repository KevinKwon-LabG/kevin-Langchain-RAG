from langchain_community.utilities import GoogleSearchAPIWrapper
import json

GOOGLE_API_KEY = "AIzaSyCku3y4jh9dOG5Y12AZ5Z8TmOkWM4wrcRk"
GOOGLE_CSE_ID = "929c878b1943943e0"

def test_search(query: str, num_results: int = 5):
    search = GoogleSearchAPIWrapper(
        google_api_key=GOOGLE_API_KEY,
        google_cse_id=GOOGLE_CSE_ID,
        k=num_results
    )
    
    try:
        results = search.results(query, num_results=num_results)
        print(f"\n[검색 쿼리: {query}]")
        print(f"[결과 수: {len(results)}]")
        
        for i, r in enumerate(results):
            print(f"\n[{i+1}] 제목: {r['title']}")
            print(f"    요약: {r['snippet']}")
            print(f"    링크: {r['link']}")
            if 'date' in r:
                print(f"    날짜: {r['date']}")
        
        # 전체 결과를 JSON으로도 출력
        print(f"\n[전체 결과 JSON]")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    # 다양한 쿼리로 테스트
    test_queries = [
        "LangChain이란?",
        "최신 AI 기술 2025",
        "Python FastAPI 최신 버전"
    ]
    
    for query in test_queries:
        test_search(query, 3)
        print("\n" + "="*50) 