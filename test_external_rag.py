#!/usr/bin/env python3
"""
외부 RAG 서버 테스트 Flask 애플리케이션
Chroma API를 사용한 외부 RAG 서버와의 통신을 웹 인터페이스로 테스트합니다.
"""

import asyncio
import httpx
import json
import random
import math
from datetime import datetime
from typing import Dict, Any
from flask import Flask, render_template_string, request, jsonify
import threading
import time

app = Flask(__name__)

# 외부 RAG 서버 설정
CHROMA_API = "http://1.237.52.240:8600"
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
DB_NAME = "default-db"
COLLECTION_ID = "0d6ca41b-cd1c-4c84-a90e-ba2d4527c81a"
QUERY_ENDPOINT = f"{CHROMA_API}/api/v2/tenants/{TENANT_ID}/databases/{DB_NAME}/collections/{COLLECTION_ID}/query"

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>외부 RAG 서버 테스트</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .server-info {
            background: #e8f4fd;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .server-info h3 {
            margin-top: 0;
            color: #0066cc;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }
        button:hover {
            background: #0056b3;
        }
        .results {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-height: 500px;
            overflow-y: auto;
        }
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        .error {
            color: #dc3545;
            background: #f8d7da;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .success {
            color: #155724;
            background: #d4edda;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 외부 RAG 서버 테스트</h1>
        
        <div class="server-info">
            <h3>📋 서버 설정 정보</h3>
            <p><strong>🌐 서버 URL:</strong> {{ server_url }}</p>
            <p><strong>🏢 Tenant ID:</strong> {{ tenant_id }}</p>
            <p><strong>🗄️ 데이터베이스:</strong> {{ db_name }}</p>
            <p><strong>📁 컬렉션 ID:</strong> {{ collection_id }}</p>
        </div>

        <form id="testForm">
            <div class="form-group">
                <label for="query">🔍 검색 쿼리:</label>
                <input type="text" id="query" name="query" placeholder="검색할 내용을 입력하세요 (예: 인공지능, 머신러닝)" required>
            </div>
            
            <div class="form-group">
                <label for="n_results">📊 결과 개수:</label>
                <input type="number" id="n_results" name="n_results" value="5" min="1" max="20">
            </div>
            
            <button type="button" onclick="testHealth()">🏥 헬스 체크</button>
            <button type="button" onclick="testQuery()">🔍 쿼리 테스트</button>
            <button type="button" onclick="runAllTests()">🚀 전체 테스트</button>
        </form>

        <div id="results" class="results" style="display: none;"></div>
    </div>

    <script>
        function showResults(content, isError = false) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.style.display = 'block';
            resultsDiv.className = 'results ' + (isError ? 'error' : 'success');
            resultsDiv.textContent = content;
        }

        function showLoading() {
            showResults('⏳ 요청 처리 중...', false);
        }

        async function makeRequest(endpoint, data = null) {
            try {
                const response = await fetch(endpoint, {
                    method: data ? 'POST' : 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: data ? JSON.stringify(data) : null
                });
                return await response.json();
            } catch (error) {
                return { error: error.message };
            }
        }

        async function testHealth() {
            showLoading();
            const result = await makeRequest('/health');
            if (result.error) {
                showResults('❌ 오류: ' + result.error, true);
            } else {
                showResults(result.result);
            }
        }

        async function testQuery() {
            const query = document.getElementById('query').value;
            const n_results = document.getElementById('n_results').value;
            
            if (!query) {
                showResults('❌ 검색 쿼리를 입력해주세요.', true);
                return;
            }

            showLoading();
            const result = await makeRequest('/query', { query, n_results: parseInt(n_results) });
            if (result.error) {
                showResults('❌ 오류: ' + result.error, true);
            } else {
                showResults(result.result);
            }
        }

        async function runAllTests() {
            showLoading();
            const result = await makeRequest('/run-all-tests');
            if (result.error) {
                showResults('❌ 오류: ' + result.error, true);
            } else {
                showResults(result.result);
            }
        }
    </script>
</body>
</html>
"""

def run_async_function(func, *args):
    """비동기 함수를 동기적으로 실행하는 헬퍼 함수"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func(*args))
    finally:
        loop.close()

def generate_embedding(text: str, dimension: int = 384) -> list:
    """텍스트 임베딩 벡터 생성"""
    try:
        # sentence-transformers를 사용한 실제 임베딩 생성 시도
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode(text).tolist()
        
        # 차원이 맞지 않으면 조정
        if len(embedding) != dimension:
            if len(embedding) > dimension:
                embedding = embedding[:dimension]
            else:
                # 부족한 차원을 0으로 채움
                embedding.extend([0.0] * (dimension - len(embedding)))
        
        return embedding
    except ImportError:
        # sentence-transformers가 없으면 더미 임베딩 생성
        return generate_dummy_embedding(text, dimension)
    except Exception as e:
        # 오류 발생 시 더미 임베딩 생성
        print(f"임베딩 생성 오류: {e}, 더미 임베딩 사용")
        return generate_dummy_embedding(text, dimension)

def generate_dummy_embedding(text: str, dimension: int = 384) -> list:
    """간단한 더미 임베딩 벡터 생성 (테스트용)"""
    # 텍스트의 해시값을 기반으로 일관된 임베딩 생성
    import hashlib
    hash_obj = hashlib.md5(text.encode())
    hash_hex = hash_obj.hexdigest()
    
    # 해시값을 기반으로 시드 설정
    random.seed(int(hash_hex[:8], 16))
    
    # 정규 분포를 시뮬레이션하여 임베딩 벡터 생성
    embedding = []
    for _ in range(dimension):
        # Box-Muller 변환을 사용하여 정규 분포 생성
        u1 = random.random()
        u2 = random.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        embedding.append(z)
    
    # 정규화
    norm = math.sqrt(sum(x * x for x in embedding))
    if norm > 0:
        embedding = [x / norm for x in embedding]
    
    return embedding

async def test_health_check():
    """외부 RAG 서버 헬스 체크 테스트"""
    result = []
    result.append("🏥 외부 RAG 서버 헬스 체크 테스트")
    result.append("=" * 50)
    
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 헬스 체크를 위해 빈 임베딩 전송 (Chroma API v2 형식)
            embedding = generate_embedding("")
            health_payload = {
                "query_embeddings": [embedding],
                "n_results": 1
            }
            
            response = await client.post(
                QUERY_ENDPOINT,
                json=health_payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            result.append(f"📡 엔드포인트: {QUERY_ENDPOINT}")
            result.append(f"⏱️  응답 시간: {response_time:.3f}초")
            result.append(f"📊 HTTP 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                result.append("✅ 서버 상태: 정상")
                try:
                    data = response.json()
                    result.append(f"📄 응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
                except:
                    result.append(f"📄 응답 텍스트: {response.text}")
            else:
                result.append(f"❌ 서버 상태: 오류 (HTTP {response.status_code})")
                result.append(f"📄 오류 내용: {response.text}")
                
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        result.append(f"❌ 서버 상태: 연결 불가")
        result.append(f"⏱️  시도 시간: {response_time:.3f}초")
        result.append(f"📄 오류 내용: {str(e)}")
    
    return "\n".join(result)

async def test_query(query: str, n_results: int = 5):
    """외부 RAG 서버 쿼리 테스트"""
    result = []
    result.append(f"🔍 쿼리 테스트: '{query}'")
    result.append("=" * 50)
    
    start_time = datetime.now()
    
    try:
        # 쿼리 페이로드 구성 (Chroma API v2 형식)
        # 쿼리 텍스트로 임베딩 생성
        embedding = generate_embedding(query)
        payload = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["metadatas", "documents"]
        }
        
        result.append(f"📤 전송 페이로드: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        result.append("")
        
        # 외부 RAG 서버에 쿼리 전송
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QUERY_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            result.append(f"⏱️  응답 시간: {response_time:.3f}초")
            result.append(f"📊 HTTP 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                result.append("✅ 쿼리 성공!")
                result.append("")
                
                # 응답 데이터 처리 및 출력
                if "results" in response_data:
                    results = response_data["results"]
                    total_results = 0
                    
                    # 결과 수 계산
                    if "ids" in results and results["ids"]:
                        total_results = len(results["ids"][0])
                    
                    result.append(f"📊 총 결과 수: {total_results}")
                    result.append("")
                    
                    if total_results > 0:
                        for i in range(total_results):
                            result.append(f"🔍 결과 #{i+1}")
                            result.append("-" * 30)
                            
                            # ID
                            if "ids" in results and results["ids"] and len(results["ids"][0]) > i:
                                result.append(f"🆔 ID: {results['ids'][0][i]}")
                            
                            # 거리 (유사도)
                            if "distances" in results and results["distances"] and len(results["distances"][0]) > i:
                                distance = results["distances"][0][i]
                                similarity = 1 - distance if distance is not None else None
                                result.append(f"📏 거리: {distance}")
                                result.append(f"🎯 유사도: {similarity:.4f}" if similarity is not None else "🎯 유사도: N/A")
                            
                            # 메타데이터
                            if "metadatas" in results and results["metadatas"] and len(results["metadatas"][0]) > i:
                                metadata = results["metadatas"][0][i]
                                if metadata:
                                    result.append(f"📋 메타데이터: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
                            
                            # 문서 내용
                            if "documents" in results and results["documents"] and len(results["documents"][0]) > i:
                                document = results["documents"][0][i]
                                if document:
                                    # 문서 내용이 길면 잘라서 표시
                                    doc_preview = document[:200] + "..." if len(document) > 200 else document
                                    result.append(f"📄 문서 내용: {doc_preview}")
                            
                            result.append("")
                    else:
                        result.append("📭 검색 결과가 없습니다.")
                else:
                    result.append("📄 응답에 results 필드가 없습니다.")
                    result.append(f"📄 전체 응답: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            else:
                result.append(f"❌ 쿼리 실패 (HTTP {response.status_code})")
                try:
                    error_detail = response.json()
                    result.append(f"📄 오류 상세: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
                except:
                    result.append(f"📄 오류 내용: {response.text}")
                
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        result.append(f"❌ 쿼리 실패")
        result.append(f"⏱️  시도 시간: {response_time:.3f}초")
        result.append(f"📄 오류 내용: {str(e)}")
    
    return "\n".join(result)

async def run_all_tests():
    """전체 테스트 실행"""
    result = []
    result.append("🚀 외부 RAG 서버 테스트 시작")
    result.append("=" * 60)
    result.append("")
    
    # 헬스 체크 테스트
    health_result = await test_health_check()
    result.append(health_result)
    result.append("")
    
    # 쿼리 테스트들
    test_queries = [
        "인공지능",
        "머신러닝",
        "딥러닝",
        "자연어처리",
        "데이터 분석"
    ]
    
    for query in test_queries:
        query_result = await test_query(query, n_results=3)
        result.append(query_result)
        result.append("")
        await asyncio.sleep(1)  # 요청 간 간격
    
    result.append("✅ 모든 테스트 완료!")
    return "\n".join(result)

@app.route('/')
def index():
    """메인 페이지"""
    return render_template_string(HTML_TEMPLATE, 
                                server_url=CHROMA_API,
                                tenant_id=TENANT_ID,
                                db_name=DB_NAME,
                                collection_id=COLLECTION_ID)

@app.route('/health')
def health():
    """헬스 체크 API 엔드포인트"""
    try:
        result = run_async_function(test_health_check)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/query', methods=['POST'])
def query():
    """쿼리 테스트 API 엔드포인트"""
    try:
        data = request.get_json()
        query_text = data.get('query', '')
        n_results = data.get('n_results', 5)
        
        if not query_text:
            return jsonify({"error": "검색 쿼리가 필요합니다."})
        
        result = run_async_function(test_query, query_text, n_results)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/run-all-tests')
def run_all():
    """전체 테스트 실행 API 엔드포인트"""
    try:
        result = run_async_function(run_all_tests)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("🚀 외부 RAG 서버 테스트 Flask 애플리케이션 시작")
    print("📋 서버 설정 정보")
    print("-" * 30)
    print(f"🌐 서버 URL: {CHROMA_API}")
    print(f"🏢 Tenant ID: {TENANT_ID}")
    print(f"🗄️  데이터베이스: {DB_NAME}")
    print(f"📁 컬렉션 ID: {COLLECTION_ID}")
    print(f"🔗 쿼리 엔드포인트: {QUERY_ENDPOINT}")
    print()
    print("🌐 웹 브라우저에서 http://localhost:5000 으로 접속하세요.")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
