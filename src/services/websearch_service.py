from langchain_community.utilities import GoogleSearchAPIWrapper
import logging

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
            results = self.search.results(query, num_results=5)
            logger.info(f"구글 검색 완료: {len(results)}개 결과")
            
            # 결과를 더 자세히 포맷팅
            summary_parts = []
            for i, r in enumerate(results):
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
                
                summary_parts.append(f"[{i+1}] {title}{date_info}\n   {snippet}\n   링크: {link}")
            
            summary = "\n\n".join(summary_parts)
            return summary
            
        except Exception as e:
            logger.error(f"구글 검색 중 오류 발생: {e}")
            return f"검색 중 오류가 발생했습니다: {str(e)}"

websearch_service = WebSearchService() 