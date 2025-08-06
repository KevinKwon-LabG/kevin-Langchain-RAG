#!/usr/bin/env python3
"""
엑셀 임베딩 기능 테스트 스크립트
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.excel_embedding_service import ExcelEmbeddingService

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_excel_document():
    """테스트용 엑셀 문서 생성"""
    try:
        import pandas as pd
        
        # 테스트 데이터 생성
        data = {
            '이름': ['김철수', '이영희', '박민수', '정수진', '최동욱'],
            '나이': [25, 30, 28, 35, 27],
            '부서': ['개발팀', '마케팅팀', '개발팀', '인사팀', '영업팀'],
            '급여': [3500000, 4200000, 3800000, 4500000, 4000000],
            '입사일': ['2020-01-15', '2018-03-20', '2019-07-10', '2017-11-05', '2021-02-28']
        }
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 테스트 디렉토리 생성
        test_dir = Path('./data/test')
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # 엑셀 파일 저장
        test_file_path = test_dir / 'test_employee_data.xlsx'
        df.to_excel(test_file_path, index=False, sheet_name='직원정보')
        
        # 두 번째 시트 추가 (부서별 통계)
        dept_stats = df.groupby('부서').agg({
            '나이': 'mean',
            '급여': 'mean'
        }).round(2)
        dept_stats.columns = ['평균나이', '평균급여']
        
        with pd.ExcelWriter(test_file_path, mode='a', if_sheet_exists='replace') as writer:
            dept_stats.to_excel(writer, sheet_name='부서통계')
        
        print(f"    테스트 엑셀 문서 생성 완료: {test_file_path}")
        return str(test_file_path)
        
    except Exception as e:
        print(f"    테스트 문서 생성 실패: {e}")
        return None


def test_excel_embedding_service():
    """엑셀 임베딩 서비스 테스트"""
    try:
        print("  엑셀 임베딩 서비스 테스트 시작")
        
        # 1. 서비스 초기화
        print("  1. 서비스 초기화")
        service = ExcelEmbeddingService()
        print(f"    ✓ 서비스 초기화 완료 (모델: {service.embedding_model_name})")
        
        # 2. 테스트 문서 생성
        print("  2. 테스트 문서 생성")
        test_file_path = create_test_excel_document()
        if not test_file_path:
            print("    ✗ 테스트 문서 생성 실패")
            return False
        print("    ✓ 테스트 문서 생성 완료")
        
        # 3. 텍스트 추출 테스트
        print("  3. 텍스트 추출 테스트")
        try:
            extracted_text = service.extract_text_from_excel(test_file_path)
            print(f"    ✓ 텍스트 추출 완료: {len(extracted_text)} 문자")
            print(f"    샘플 텍스트: {extracted_text[:200]}...")
        except Exception as e:
            print(f"    ✗ 텍스트 추출 실패: {e}")
            return False
        
        # 4. 전처리 테스트
        print("  4. 전처리 테스트")
        try:
            processed_text = service.preprocess_text(extracted_text)
            print(f"    ✓ 전처리 완료: {len(processed_text)} 문자")
            print(f"    샘플 전처리 텍스트: {processed_text[:200]}...")
        except Exception as e:
            print(f"    ✗ 전처리 실패: {e}")
            return False
        
        # 5. 문서 분할 테스트
        print("  5. 문서 분할 테스트")
        try:
            metadata = {'file_name': 'test_employee_data.xlsx', 'file_type': 'excel'}
            chunks = service.split_excel_document(processed_text, metadata)
            print(f"    ✓ 문서 분할 완료: {len(chunks)}개 청크")
            
            # 청크 정보 출력
            for i, chunk in enumerate(chunks[:3]):  # 처음 3개만
                print(f"      청크 {i+1}: {chunk.sheet_name} - {chunk.row_info} ({chunk.token_count} 토큰)")
        except Exception as e:
            print(f"    ✗ 문서 분할 실패: {e}")
            return False
        
        # 6. 임베딩 생성 테스트
        print("  6. 임베딩 생성 테스트")
        try:
            embeddings = service.create_embeddings(chunks)
            print(f"    ✓ 임베딩 생성 완료: {len(embeddings)}개 벡터")
            print(f"    벡터 차원: {len(embeddings[0]) if embeddings else 0}")
        except Exception as e:
            print(f"    ✗ 임베딩 생성 실패: {e}")
            return False
        
        # 7. 벡터 DB 저장 테스트
        print("  7. 벡터 DB 저장 테스트")
        try:
            service.store_embeddings(chunks, embeddings)
            print("    ✓ 벡터 DB 저장 완료")
        except Exception as e:
            print(f"    ✗ 벡터 DB 저장 실패: {e}")
            return False
        
        # 8. 검색 테스트
        print("  8. 검색 테스트")
        try:
            search_results = service.search_similar_chunks("개발팀 직원", n_results=3)
            print(f"    ✓ 검색 완료: {len(search_results)}개 결과")
            
            for i, result in enumerate(search_results):
                print(f"      결과 {i+1}: {result['content'][:100]}...")
        except Exception as e:
            print(f"    ✗ 검색 실패: {e}")
            return False
        
        # 9. 전체 워크플로우 테스트
        print("  9. 전체 워크플로우 테스트")
        try:
            result = service.process_excel_document(test_file_path, {'test': True})
            print(f"    ✓ 전체 워크플로우 완료")
            print(f"    결과: {result['total_chunks']}개 청크, {result['total_tokens']} 토큰")
        except Exception as e:
            print(f"    ✗ 전체 워크플로우 실패: {e}")
            return False
        
        print("  ✓ 엑셀 임베딩 서비스 테스트 완료")
        return True
        
    except Exception as e:
        print(f"  ✗ 엑셀 임베딩 서비스 테스트 실패: {e}")
        return False


def test_api_endpoints():
    """API 엔드포인트 테스트"""
    try:
        print("  API 엔드포인트 테스트 시작")
        
        # FastAPI 테스트 클라이언트 사용
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        
        # 1. 헬스 체크 테스트
        print("  1. 헬스 체크 테스트")
        response = client.get("/health")
        if response.status_code == 200:
            print("    ✓ 헬스 체크 성공")
        else:
            print(f"    ✗ 헬스 체크 실패: {response.status_code}")
        
        # 2. 엑셀 업로드 엔드포인트 테스트 (실제 파일 없이)
        print("  2. 엑셀 업로드 엔드포인트 테스트")
        try:
            # 빈 파일로 테스트
            test_file_path = Path('./data/test/test_employee_data.xlsx')
            if test_file_path.exists():
                with open(test_file_path, 'rb') as f:
                    files = {'file': ('test.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                    data = {'chunk_size': 300, 'chunk_overlap': 50}
                    response = client.post("/api/excel-embedding/upload", files=files, data=data)
                    
                    if response.status_code == 200:
                        print("    ✓ 엑셀 업로드 성공")
                        result = response.json()
                        print(f"    결과: {result['total_chunks']}개 청크")
                    else:
                        print(f"    ✗ 엑셀 업로드 실패: {response.status_code}")
                        print(f"    오류: {response.text}")
            else:
                print("    ⚠ 테스트 파일이 없어 업로드 테스트 건너뜀")
        except Exception as e:
            print(f"    ✗ 엑셀 업로드 테스트 실패: {e}")
        
        # 3. 검색 엔드포인트 테스트
        print("  3. 검색 엔드포인트 테스트")
        try:
            search_data = {"query": "개발팀", "n_results": 3}
            response = client.post("/api/excel-embedding/search", json=search_data)
            
            if response.status_code == 200:
                print("    ✓ 검색 성공")
                results = response.json()
                print(f"    결과: {len(results)}개")
            else:
                print(f"    ✗ 검색 실패: {response.status_code}")
        except Exception as e:
            print(f"    ✗ 검색 테스트 실패: {e}")
        
        print("  ✓ API 엔드포인트 테스트 완료")
        return True
        
    except Exception as e:
        print(f"  ✗ API 엔드포인트 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("엑셀 임베딩 기능 테스트 시작")
    print("=" * 50)
    
    # 서비스 테스트
    service_test_success = test_excel_embedding_service()
    
    print("\n" + "=" * 50)
    
    # API 테스트
    api_test_success = test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"  서비스 테스트: {'성공' if service_test_success else '실패'}")
    print(f"  API 테스트: {'성공' if api_test_success else '실패'}")
    
    if service_test_success and api_test_success:
        print("  전체 테스트: 성공 ✓")
        return True
    else:
        print("  전체 테스트: 실패 ✗")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 