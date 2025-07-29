#!/usr/bin/env python3
"""
환경 변수 설정 스크립트
.env 파일을 생성하고 기본 설정을 적용합니다.
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """env.settings 파일 생성"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / "env.settings"
    
    if env_file.exists():
        print("⚠️  env.settings 파일이 이미 존재합니다.")
        response = input("덮어쓰시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("취소되었습니다.")
            return False
    
    try:
        # 기본 env.settings 내용 생성
        content = """# =============================================================================
# 서버 설정
# =============================================================================
HOST=0.0.0.0
PORT=11040
DEBUG=true
LOG_LEVEL=INFO

# =============================================================================
# Ollama 설정
# =============================================================================
OLLAMA_BASE_URL=http://1.237.52.240:11434
OLLAMA_TIMEOUT=120
OLLAMA_MAX_RETRIES=3

# =============================================================================
# 벡터 데이터베이스 설정
# =============================================================================
CHROMA_PERSIST_DIRECTORY=data/vectorstore
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu

# =============================================================================
# 문서 처리 설정
# =============================================================================
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_TOKENS=4000
UPLOAD_FOLDER=data/documents
MAX_FILE_SIZE=16777216
ALLOWED_EXTENSIONS=.pdf,.txt,.docx,.md

# =============================================================================
# LLM 모델 설정 (기본값)
# =============================================================================
DEFAULT_MODEL=gemma3:12b-it-qat
DEFAULT_TEMPERATURE=0.7
DEFAULT_TOP_P=0.9
DEFAULT_TOP_K=40
DEFAULT_REPEAT_PENALTY=1.1
DEFAULT_SEED=-1

# =============================================================================
# RAG 설정
# =============================================================================
DEFAULT_USE_RAG=true
DEFAULT_TOP_K_DOCUMENTS=5
DEFAULT_SIMILARITY_THRESHOLD=0.7

# =============================================================================
# 시스템 프롬프트 설정
# =============================================================================
DEFAULT_SYSTEM_PROMPT=You are a helpful assistant. Answer questions based on the provided context. If you cannot find relevant information in the context, say so clearly.
RAG_SYSTEM_PROMPT=You are a helpful assistant. Use the provided context to answer questions accurately. If the context doesn't contain relevant information, say "컨텍스트에서 해당 정보를 찾을 수 없습니다."

# =============================================================================
# 세션 관리 설정
# =============================================================================
MAX_SESSION_AGE_HOURS=24
MAX_MESSAGES_PER_SESSION=100
SESSION_CLEANUP_INTERVAL_HOURS=6

# =============================================================================
# 고급 설정 - Temperature 범위
# =============================================================================
TEMPERATURE_MIN=0.0
TEMPERATURE_MAX=2.0
TEMPERATURE_STEP=0.1
TEMPERATURE_PRESETS=0.1,0.3,0.5,0.7,0.9,1.0,1.2

# =============================================================================
# 고급 설정 - Top P 범위
# =============================================================================
TOP_P_MIN=0.1
TOP_P_MAX=1.0
TOP_P_STEP=0.05
TOP_P_PRESETS=0.1,0.3,0.5,0.7,0.9,1.0

# =============================================================================
# 고급 설정 - Top K 범위
# =============================================================================
TOP_K_MIN=1
TOP_K_MAX=100
TOP_K_STEP=1
TOP_K_PRESETS=10,20,40,60,80,100

# =============================================================================
# 고급 설정 - 최대 토큰 수 범위
# =============================================================================
MAX_TOKENS_MIN=100
MAX_TOKENS_MAX=8192
MAX_TOKENS_STEP=100
MAX_TOKENS_PRESETS=1024,2048,4096,6144,8192

# =============================================================================
# 고급 설정 - Repeat Penalty 범위
# =============================================================================
REPEAT_PENALTY_MIN=1.0
REPEAT_PENALTY_MAX=2.0
REPEAT_PENALTY_STEP=0.1
REPEAT_PENALTY_PRESETS=1.0,1.1,1.2,1.3,1.5,1.8

# =============================================================================
# 고급 설정 - RAG 관련 범위
# =============================================================================
RAG_TOP_K_MIN=1
RAG_TOP_K_MAX=20
RAG_TOP_K_STEP=1
RAG_TOP_K_PRESETS=3,5,7,10,15,20

# =============================================================================
# 사용 가능한 모델 목록 (JSON 형식)
# =============================================================================
AVAILABLE_MODELS=[
  {"name": "gemma3:12b-it-qat", "size": "8.9 GB", "id": "5d4fa005e7bb", "description": "Google의 Gemma 3 12B 모델 (양자화됨)"},
  {"name": "llama3.1:8b", "size": "4.9 GB", "id": "46e0c10c039e", "description": "Meta의 Llama 3.1 8B 모델"},
  {"name": "llama3.2-vision:11b-instruct-q4_K_M", "size": "7.8 GB", "id": "6f2f9757ae97", "description": "Meta의 Llama 3.2 Vision 11B 모델"},
  {"name": "qwen3:14b-q8_0", "size": "15 GB", "id": "304bf7349c71", "description": "Alibaba의 Qwen 3 14B 모델"},
  {"name": "deepseek-r1:14b", "size": "9.0 GB", "id": "c333b7232bdb", "description": "DeepSeek의 R1 14B 모델"},
  {"name": "deepseek-v2:16b-lite-chat-q8_0", "size": "16 GB", "id": "1d62ef756269", "description": "DeepSeek의 V2 16B Lite 모델"}
]

# =============================================================================
# 시스템 프롬프트 템플릿 (JSON 형식)
# =============================================================================
SYSTEM_PROMPT_TEMPLATES=[
  {"name": "기본", "prompt": "You are a helpful assistant. Answer questions based on the provided context. If you cannot find relevant information in the context, say so clearly."},
  {"name": "한국어", "prompt": "당신은 도움이 되는 한국어 어시스턴트입니다. 제공된 컨텍스트를 기반으로 질문에 답변하세요. 컨텍스트에서 관련 정보를 찾을 수 없는 경우 명확히 말씀해 주세요."},
  {"name": "코딩", "prompt": "You are a helpful programming assistant. Provide clear, well-documented code examples and explanations. Always consider best practices and security."},
  {"name": "번역", "prompt": "You are a professional translator. Provide accurate and natural translations while preserving the original meaning and context."},
  {"name": "요약", "prompt": "You are a summarization expert. Provide concise, accurate summaries that capture the key points and main ideas."},
  {"name": "분석", "prompt": "You are an analytical assistant. Provide detailed analysis with supporting evidence and logical reasoning."}
]

# =============================================================================
# 보안 설정
# =============================================================================
CORS_ALLOW_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

# =============================================================================
# 로깅 설정
# =============================================================================
LOG_FILE=logs/app.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ env.settings 파일이 성공적으로 생성되었습니다.")
        return True
        
    except Exception as e:
        print(f"❌ .env 파일 생성 실패: {e}")
        return False

def customize_env_file():
    """사용자 입력을 받아 env.settings 파일을 커스터마이즈"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / "env.settings"
    
    if not env_file.exists():
        print("❌ env.settings 파일이 존재하지 않습니다. 먼저 생성해주세요.")
        return False
    
    print("\n🔧 환경 변수 커스터마이즈")
    print("=" * 50)
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 서버 설정
        print("\n📡 서버 설정")
        host = input(f"호스트 (기본값: 0.0.0.0): ").strip() or "0.0.0.0"
        port = input(f"포트 (기본값: 11040): ").strip() or "11040"
        
        # Ollama 설정
        print("\n🤖 Ollama 설정")
        ollama_url = input(f"Ollama 서버 URL (기본값: http://1.237.52.240:11434): ").strip() or "http://1.237.52.240:11434"
        
        # 기본 모델 설정
        print("\n🎯 기본 모델 설정")
        default_model = input(f"기본 모델 (기본값: gemma3:12b-it-qat): ").strip() or "gemma3:12b-it-qat"
        
        # RAG 설정
        print("\n📚 RAG 설정")
        use_rag = input(f"기본적으로 RAG 사용 (기본값: true): ").strip() or "true"
        top_k_docs = input(f"기본 문서 검색 수 (기본값: 5): ").strip() or "5"
        
        # 고급 설정
        print("\n⚙️  고급 설정")
        temperature = input(f"기본 Temperature (기본값: 0.7): ").strip() or "0.7"
        top_p = input(f"기본 Top P (기본값: 0.9): ").strip() or "0.9"
        max_tokens = input(f"기본 최대 토큰 수 (기본값: 4000): ").strip() or "4000"
        
        # 설정 적용
        content = content.replace("HOST=0.0.0.0", f"HOST={host}")
        content = content.replace("PORT=11040", f"PORT={port}")
        content = content.replace("OLLAMA_BASE_URL=http://1.237.52.240:11434", f"OLLAMA_BASE_URL={ollama_url}")
        content = content.replace("DEFAULT_MODEL=gemma3:12b-it-qat", f"DEFAULT_MODEL={default_model}")
        content = content.replace("DEFAULT_USE_RAG=true", f"DEFAULT_USE_RAG={use_rag}")
        content = content.replace("DEFAULT_TOP_K_DOCUMENTS=5", f"DEFAULT_TOP_K_DOCUMENTS={top_k_docs}")
        content = content.replace("DEFAULT_TEMPERATURE=0.7", f"DEFAULT_TEMPERATURE={temperature}")
        content = content.replace("DEFAULT_TOP_P=0.9", f"DEFAULT_TOP_P={top_p}")
        content = content.replace("MAX_TOKENS=4000", f"MAX_TOKENS={max_tokens}")
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n✅ env.settings 파일이 성공적으로 커스터마이즈되었습니다.")
        return True
        
    except Exception as e:
        print(f"❌ 환경 변수 커스터마이즈 실패: {e}")
        return False

def validate_env_file():
    """환경 변수 파일 검증"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / "env.settings"
    
    if not env_file.exists():
        print("❌ env.settings 파일이 존재하지 않습니다.")
        return False
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 필수 설정 확인
        required_vars = [
            "HOST", "PORT", "OLLAMA_BASE_URL", "DEFAULT_MODEL",
            "DEFAULT_TEMPERATURE", "DEFAULT_TOP_P", "MAX_TOKENS"
        ]
        
        missing_vars = []
        for var in required_vars:
            if f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 필수 환경 변수가 누락되었습니다: {', '.join(missing_vars)}")
            return False
        
        print("✅ 환경 변수 파일이 유효합니다.")
        return True
        
    except Exception as e:
        print(f"❌ 환경 변수 파일 검증 실패: {e}")
        return False

def show_current_config():
    """현재 설정 표시"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / "env.settings"
    
    if not env_file.exists():
        print("❌ env.settings 파일이 존재하지 않습니다.")
        return
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n📋 현재 env.settings 설정")
        print("=" * 50)
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                print(f"{key}: {value}")
        
    except Exception as e:
        print(f"❌ 설정 표시 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 Ollama RAG Interface 환경 변수 설정")
    print("=" * 50)
    
    while True:
        print("\n📋 메뉴:")
        print("1. env.settings 파일 생성")
        print("2. 환경 변수 커스터마이즈")
        print("3. 설정 검증")
        print("4. 현재 설정 표시")
        print("5. 종료")
        
        choice = input("\n선택하세요 (1-5): ").strip()
        
        if choice == '1':
            create_env_file()
        elif choice == '2':
            customize_env_file()
        elif choice == '3':
            validate_env_file()
        elif choice == '4':
            show_current_config()
        elif choice == '5':
            print("👋 종료합니다.")
            break
        else:
            print("❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.")

if __name__ == "__main__":
    main() 