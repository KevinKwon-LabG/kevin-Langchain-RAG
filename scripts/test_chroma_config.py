#!/usr/bin/env python3
"""
Chroma DB 설정 테스트 스크립트
환경 변수를 통한 Chroma DB 연결을 테스트합니다.
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_chroma_config():
    """Chroma DB 설정을 테스트합니다."""
    print("=" * 60)
    print("Chroma DB 설정 테스트")
    print("=" * 60)
    
    # 현재 설정 출력
    print(f"Chroma DB 모드: {settings.chroma_mode}")
    print(f"Chroma DB URL: {settings.get_chroma_url()}")
    print(f"컬렉션 이름: {settings.chroma_collection_name}")
    
    if settings.chroma_mode == "local":
        print(f"로컬 저장 경로: {settings.chroma_persist_directory}")
    elif settings.chroma_mode == "http":
        print(f"호스트: {settings.chroma_host}")
        print(f"포트: {settings.chroma_port}")
        print(f"SSL 사용: {settings.chroma_ssl}")
        if settings.chroma_username:
            print(f"사용자명: {settings.chroma_username}")
        if settings.chroma_password:
            print(f"비밀번호: {'*' * len(settings.chroma_password)}")
    
    print()
    
    # 클라이언트 설정 테스트
    try:
        config = settings.get_chroma_client_config()
        print("✅ 클라이언트 설정 생성 성공")
        print(f"설정 모드: {config['mode']}")
    except Exception as e:
        print(f"❌ 클라이언트 설정 생성 실패: {e}")
        return False
    
    # 실제 연결 테스트
    try:
        import chromadb
        
        if config["mode"] == "local":
            # 로컬 모드 테스트
            os.makedirs(config["path"], exist_ok=True)
            client = chromadb.PersistentClient(
                path=config["path"],
                settings=chromadb.config.Settings(**config["settings"])
            )
            print("✅ 로컬 Chroma DB 연결 성공")
            
        elif config["mode"] == "http":
            # HTTP 모드 테스트
            client = chromadb.HttpClient(
                host=config["host"],
                port=config["port"],
                username=config["username"],
                password=config["password"],
                ssl=config["ssl"]
            )
            print("✅ HTTP Chroma DB 연결 성공")
        
        # 컬렉션 생성 테스트
        collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata=settings.chroma_collection_metadata
        )
        print("✅ 컬렉션 생성/접근 성공")
        
        # 간단한 임베딩 테스트
        test_embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        test_documents = ["테스트 문서"]
        test_metadatas = [{"test": True}]
        test_ids = ["test_id"]
        
        collection.add(
            embeddings=test_embeddings,
            documents=test_documents,
            metadatas=test_metadatas,
            ids=test_ids
        )
        print("✅ 임베딩 저장 테스트 성공")
        
        # 검색 테스트
        results = collection.query(
            query_embeddings=test_embeddings,
            n_results=1
        )
        print("✅ 검색 테스트 성공")
        
        # 테스트 데이터 정리
        collection.delete(ids=test_ids)
        print("✅ 테스트 데이터 정리 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ Chroma DB 연결/테스트 실패: {e}")
        return False

def show_environment_variables():
    """관련 환경 변수를 출력합니다."""
    print("\n" + "=" * 60)
    print("관련 환경 변수")
    print("=" * 60)
    
    chroma_vars = [
        "CHROMA_MODE",
        "CHROMA_PERSIST_DIRECTORY", 
        "CHROMA_HOST",
        "CHROMA_PORT",
        "CHROMA_USERNAME",
        "CHROMA_PASSWORD",
        "CHROMA_SSL",
        "CHROMA_ANONYMIZED_TELEMETRY",
        "CHROMA_COLLECTION_NAME",
        "CHROMA_COLLECTION_METADATA"
    ]
    
    for var in chroma_vars:
        value = os.getenv(var, "설정되지 않음")
        if "PASSWORD" in var and value != "설정되지 않음":
            value = "*" * len(value)
        print(f"{var}: {value}")

def show_usage_examples():
    """사용 예시를 출력합니다."""
    print("\n" + "=" * 60)
    print("사용 예시")
    print("=" * 60)
    
    print("1. 로컬 Chroma DB 사용:")
    print("   CHROMA_MODE=local")
    print("   CHROMA_PERSIST_DIRECTORY=data/vectorstore")
    print()
    
    print("2. 외부 HTTP Chroma DB 사용:")
    print("   CHROMA_MODE=http")
    print("   CHROMA_HOST=your-chroma-server.com")
    print("   CHROMA_PORT=8000")
    print("   CHROMA_USERNAME=your_username")
    print("   CHROMA_PASSWORD=your_password")
    print("   CHROMA_SSL=true")
    print()
    
    print("3. Docker로 Chroma DB 실행:")
    print("   docker run -p 8000:8000 chromadb/chroma")
    print()
    
    print("4. 환경 변수 설정 예시:")
    print("   export CHROMA_MODE=http")
    print("   export CHROMA_HOST=localhost")
    print("   export CHROMA_PORT=8000")

def main():
    """메인 함수"""
    print("Chroma DB 설정 테스트를 시작합니다...")
    
    # 환경 변수 출력
    show_environment_variables()
    
    # 설정 테스트
    success = test_chroma_config()
    
    # 사용 예시 출력
    show_usage_examples()
    
    if success:
        print("\n✅ 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("\n❌ 일부 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
