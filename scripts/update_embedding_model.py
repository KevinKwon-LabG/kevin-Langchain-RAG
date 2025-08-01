#!/usr/bin/env python3
"""
임베딩 모델을 KURE로 변경하고 벡터 저장소를 재구성하는 스크립트
"""

import os
import shutil
import logging
from pathlib import Path
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.services.document_service import document_service

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_existing_vectorstore():
    """기존 벡터 저장소를 백업합니다."""
    vectorstore_path = Path(settings.chroma_persist_directory)
    backup_path = vectorstore_path.parent / f"{vectorstore_path.name}_backup"
    
    if vectorstore_path.exists():
        logger.info(f"기존 벡터 저장소를 백업합니다: {backup_path}")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(vectorstore_path, backup_path)
        return True
    else:
        logger.info("기존 벡터 저장소가 없습니다.")
        return False

def remove_existing_vectorstore():
    """기존 벡터 저장소를 제거합니다."""
    vectorstore_path = Path(settings.chroma_persist_directory)
    if vectorstore_path.exists():
        logger.info(f"기존 벡터 저장소를 제거합니다: {vectorstore_path}")
        shutil.rmtree(vectorstore_path)
        return True
    return False

def reinitialize_document_service():
    """문서 서비스를 재초기화하여 KURE 모델을 사용하도록 합니다."""
    try:
        logger.info("문서 서비스를 KURE 모델로 재초기화합니다...")
        
        # 기존 서비스 정리
        if hasattr(document_service, 'vectorstore') and document_service.vectorstore:
            del document_service.vectorstore
        
        # 새로운 임베딩 모델로 재초기화
        document_service._initialize_vectorstore()
        
        # RAG 디렉토리의 문서들을 다시 로드
        rag_directory = Path("static/RAG")
        if rag_directory.exists():
            logger.info("RAG 디렉토리의 문서들을 다시 로드합니다...")
            for file_path in rag_directory.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.txt', '.docx', '.md', '.xlsx', '.xls']:
                    logger.info(f"문서 로드: {file_path}")
                    try:
                        # 문서 내용 로드
                        content = document_service.load_document(str(file_path))
                        # 문서 처리 및 벡터 저장소에 저장
                        document_service.process_document(content, file_path.name)
                    except Exception as e:
                        logger.error(f"문서 로드 실패 {file_path}: {e}")
        
        logger.info("✅ KURE 모델로 벡터 저장소 재구성이 완료되었습니다.")
        return True
        
    except Exception as e:
        logger.error(f"벡터 저장소 재구성 중 오류 발생: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🔄 KURE 임베딩 모델로 변경 및 벡터 저장소 재구성을 시작합니다...")
    
    # 1. 기존 벡터 저장소 백업
    backup_created = backup_existing_vectorstore()
    
    # 2. 기존 벡터 저장소 제거
    remove_existing_vectorstore()
    
    # 3. KURE 모델로 재초기화
    success = reinitialize_document_service()
    
    if success:
        print("✅ KURE 모델 변경이 성공적으로 완료되었습니다!")
        if backup_created:
            print("📁 기존 벡터 저장소는 백업되었습니다.")
        print("\n🔧 변경 사항:")
        print("- 임베딩 모델: BM-K/KURE (한국어 특화)")
        print("- 벡터 저장소: 새로 생성됨")
        print("- RAG 문서: 재로드됨")
    else:
        print("❌ KURE 모델 변경 중 오류가 발생했습니다.")
        if backup_created:
            print("📁 백업된 벡터 저장소에서 복원할 수 있습니다.")

if __name__ == "__main__":
    main() 