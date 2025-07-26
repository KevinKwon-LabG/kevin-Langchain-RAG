import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# app.py의 함수들을 직접 import
import importlib.util
spec = importlib.util.spec_from_file_location("app", os.path.join(os.path.dirname(__file__), "..", "app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

def test_time_parsing_in_app():
    test_queries = [
        "오늘자 트럼프 관련 기사 5개를 출처와 함께 알려주세요.",
        "어제 발생한 주요 뉴스",
        "이번 주 AI 기술 동향",
        "일반적인 질문입니다."
    ]
    
    print("🔍 app.py 시간 파싱 기능 테스트")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] 테스트 쿼리: {query}")
        print("-" * 60)
        
        try:
            # 세션 생성
            session_id = app.get_or_create_session()
            
            # 프롬프트 구성
            prompt = app.build_conversation_prompt(session_id, query)
            
            # 결과 출력
            print("📋 생성된 프롬프트:")
            print(prompt)
            
            # 시간 정보가 포함되었는지 확인
            if "[실시간 웹 검색 결과]" in prompt:
                print("✅ 시간 파싱 및 웹 검색이 성공적으로 적용되었습니다!")
            else:
                print("ℹ️  시간 정보가 없어 일반 프롬프트로 처리되었습니다.")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    test_time_parsing_in_app() 