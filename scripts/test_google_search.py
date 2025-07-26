from langchain_community.utilities import GoogleSearchAPIWrapper

GOOGLE_API_KEY = "AIzaSyCku3y4jh9dOG5Y12AZ5Z8TmOkWM4wrcRk"
GOOGLE_CSE_ID = "929c878b1943943e0"

if __name__ == "__main__":
    search = GoogleSearchAPIWrapper(
        google_api_key=GOOGLE_API_KEY,
        google_cse_id=GOOGLE_CSE_ID,
        k=3
    )
    try:
        results = search.results("LangChain이란?", num_results=3)
        print("[구글 검색 결과]")
        for i, r in enumerate(results):
            print(f"[{i+1}] {r['title']}: {r['snippet']} ({r['link']})")
    except Exception as e:
        print(f"❌ 에러 발생: {e}") 