"""
주식 키워드 추출 서비스
사용자 프롬프트에서 주식 관련 키워드를 추출합니다.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class StockKeywordExtractor:
    """주식 키워드 추출 서비스"""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434", model_name: Optional[str] = None):
        """
        StockKeywordExtractor 초기화
        
        Args:
            ollama_base_url: Ollama 서버 URL
            model_name: 사용할 AI 모델 이름 (None이면 설정에서 가져옴)
        """
        self.ollama_base_url = ollama_base_url
        
        # 설정에서 모델 정보 가져오기
        try:
            from src.config.settings import Settings
            settings = Settings()
            self.model = model_name or settings.keyword_extractor_model
            self.timeout = settings.keyword_extractor_timeout
            self.temperature = settings.keyword_extractor_temperature
            self.top_p = settings.keyword_extractor_top_p
            self.max_tokens = settings.keyword_extractor_max_tokens
        except Exception as e:
            logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
            self.model = model_name or "gemma3b-it"
            self.timeout = 30
            self.temperature = 0.1
            self.top_p = 0.9
            self.max_tokens = 200
    
    def update_model(self, model_name: str):
        """
        사용할 AI 모델을 동적으로 변경합니다.
        
        Args:
            model_name: 새로운 모델 이름
        """
        self.model = model_name
        logger.info(f"StockKeywordExtractor 모델이 {model_name}으로 변경되었습니다.")
    
    async def extract_stock_keyword(self, user_prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        사용자 프롬프트에서 주식 키워드를 추출합니다.
        
        Args:
            user_prompt: 사용자 입력 프롬프트 (예: "Naver 주가 정보를 알려줘")
            model_name: 사용할 모델 이름 (None이면 기존 모델 사용)
        
        Returns:
            추출 결과 (keyword, confidence, extraction_type)
        """
        # 모델이 지정된 경우 업데이트
        if model_name and model_name != self.model:
            self.update_model(model_name)
        
        try:
            # 1단계: 주식 코드 추출 (6자리 숫자)
            stock_codes = self._extract_stock_codes(user_prompt)
            if stock_codes:
                return {
                    "success": True,
                    "keyword": stock_codes[0],  # 첫 번째 주식 코드 반환
                    "extraction_type": "stock_code",
                    "confidence": 0.95,
                    "original_prompt": user_prompt,
                    "extracted_at": datetime.now().isoformat()
                }
            
            # 2단계: AI 모델을 사용한 키워드 추출
            return await self._extract_with_ai_model(user_prompt)
            
        except Exception as e:
            logger.error(f"주식 키워드 추출 중 오류: {e}")
            return {
                "success": False,
                "error": f"키워드 추출 실패: {str(e)}",
                "original_prompt": user_prompt,
                "extracted_at": datetime.now().isoformat()
            }
    
    def _extract_stock_codes(self, text: str) -> List[str]:
        """텍스트에서 6자리 주식 코드를 추출합니다."""
        pattern = r'\b\d{6}\b'
        return re.findall(pattern, text)
    
    async def _extract_with_ai_model(self, user_prompt: str) -> Dict[str, Any]:
        """
        AI 모델을 사용하여 주식 키워드를 추출합니다.
        
        Args:
            user_prompt: 사용자 입력 프롬프트
        
        Returns:
            추출 결과
        """
        try:
            import aiohttp
            
            # AI 모델에 전달할 프롬프트 구성
            system_prompt = """당신은 사용자의 주식 관련 질문에서 주식 종목명이나 회사명을 추출하는 전문가입니다.

추출 규칙:
1. 주식 종목명이나 회사명만 추출 (예: "삼성전자", "SK하이닉스", "Naver", "카카오")
2. "주가", "시세", "정보", "알려줘" 등의 부가적인 단어는 제외
3. 영어 회사명은 원래 형태로 유지 (예: "Naver", "Kakao")
4. 한글 회사명은 정확한 명칭으로 추출 (예: "삼성전자", "SK하이닉스")
5. 추출할 수 없는 경우 빈 문자열 반환

응답 형식:
{
    "keyword": "추출된_키워드",
    "confidence": 0.0-1.0,
    "reason": "추출 이유"
}

예시:
- 입력: "Naver 주가 정보를 알려줘" → 출력: {"keyword": "Naver", "confidence": 0.9, "reason": "Naver는 명확한 회사명"}
- 입력: "삼성전자 시세 보여줘" → 출력: {"keyword": "삼성전자", "confidence": 0.95, "reason": "삼성전자는 명확한 종목명"}
- 입력: "오늘 날씨 어때?" → 출력: {"keyword": "", "confidence": 0.0, "reason": "주식 관련 키워드가 없음"}

반드시 JSON 형식으로만 응답하세요."""

            # Ollama API 호출
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n사용자 질문: {user_prompt}",
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                        "num_predict": self.max_tokens
                    }
                }
                
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama API 호출 실패: {response.status}")
                    
                    result = await response.json()
                    ai_response = result.get("response", "").strip()
                    
                    # JSON 응답 파싱
                    try:
                        import json
                        extracted_data = json.loads(ai_response)
                        
                        return {
                            "success": True,
                            "keyword": extracted_data.get("keyword", ""),
                            "extraction_type": "ai_model",
                            "confidence": extracted_data.get("confidence", 0.0),
                            "reason": extracted_data.get("reason", ""),
                            "original_prompt": user_prompt,
                            "ai_response": ai_response,
                            "extracted_at": datetime.now().isoformat()
                        }
                        
                    except json.JSONDecodeError:
                        # JSON 파싱 실패 시 텍스트에서 키워드 추출 시도
                        keyword = self._extract_keyword_from_text(ai_response)
                        return {
                            "success": True,
                            "keyword": keyword,
                            "extraction_type": "ai_model_fallback",
                            "confidence": 0.7,
                            "reason": "AI 응답에서 키워드 추출",
                            "original_prompt": user_prompt,
                            "ai_response": ai_response,
                            "extracted_at": datetime.now().isoformat()
                        }
                        
        except Exception as e:
            logger.error(f"AI 모델 키워드 추출 실패: {e}")
            # AI 모델 실패 시 기본 추출 방법 사용
            return self._extract_keyword_fallback(user_prompt)
    
    def _extract_keyword_from_text(self, text: str) -> str:
        """AI 응답 텍스트에서 키워드를 추출합니다."""
        # 일반적인 주식 종목명 패턴
        stock_patterns = [
            r'["\']([^"\']*?주식[^"\']*?)["\']',
            r'["\']([^"\']*?전자[^"\']*?)["\']',
            r'["\']([^"\']*?하이닉스[^"\']*?)["\']',
            r'["\']([^"\']*?Naver[^"\']*?)["\']',
            r'["\']([^"\']*?Kakao[^"\']*?)["\']',
            r'["\']([^"\']*?삼성[^"\']*?)["\']',
            r'["\']([^"\']*?SK[^"\']*?)["\']',
            r'["\']([^"\']*?LG[^"\']*?)["\']',
            r'["\']([^"\']*?현대[^"\']*?)["\']',
            r'["\']([^"\']*?기아[^"\']*?)["\']',
        ]
        
        for pattern in stock_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_keyword_fallback(self, user_prompt: str) -> Dict[str, Any]:
        """AI 모델 실패 시 기본 추출 방법을 사용합니다."""
        # 일반적인 주식 종목명 패턴
        stock_keywords = [
            "삼성전자", "SK하이닉스", "Naver", "카카오", "Kakao", "LG전자", "현대차", "기아",
            "삼성바이오로직스", "셀트리온", "POSCO홀딩스", "삼성SDI", "LG화학", "현대모비스",
            "KB금융", "신한지주", "하나금융지주", "우리금융지주", "NH투자증권", "미래에셋증권"
        ]
        
        user_prompt_lower = user_prompt.lower()
        
        for keyword in stock_keywords:
            if keyword.lower() in user_prompt_lower:
                return {
                    "success": True,
                    "keyword": keyword,
                    "extraction_type": "fallback",
                    "confidence": 0.6,
                    "reason": f"기본 패턴 매칭으로 '{keyword}' 추출",
                    "original_prompt": user_prompt,
                    "extracted_at": datetime.now().isoformat()
                }
        
        return {
            "success": False,
            "keyword": "",
            "extraction_type": "fallback",
            "confidence": 0.0,
            "reason": "키워드를 찾을 수 없음",
            "original_prompt": user_prompt,
            "extracted_at": datetime.now().isoformat()
        }
    
    async def extract_multiple_keywords(self, user_prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        사용자 프롬프트에서 여러 주식 키워드를 추출합니다.
        
        Args:
            user_prompt: 사용자 입력 프롬프트
            model_name: 사용할 모델 이름 (None이면 기존 모델 사용)
        
        Returns:
            추출된 키워드 목록
        """
        try:
            # 주식 코드 추출
            stock_codes = self._extract_stock_codes(user_prompt)
            
            # AI 모델로 키워드 추출 (모델이 지정된 경우 업데이트)
            if model_name and model_name != self.model:
                self.update_model(model_name)
            ai_result = await self._extract_with_ai_model(user_prompt)
            
            keywords = []
            
            # 주식 코드 추가
            for code in stock_codes:
                keywords.append({
                    "keyword": code,
                    "type": "stock_code",
                    "confidence": 0.95
                })
            
            # AI 추출 결과 추가
            if ai_result.get("success") and ai_result.get("keyword"):
                keywords.append({
                    "keyword": ai_result["keyword"],
                    "type": ai_result["extraction_type"],
                    "confidence": ai_result["confidence"]
                })
            
            # 중복 제거
            unique_keywords = []
            seen_keywords = set()
            
            for kw in keywords:
                if kw["keyword"] not in seen_keywords:
                    unique_keywords.append(kw)
                    seen_keywords.add(kw["keyword"])
            
            return {
                "success": True,
                "keywords": unique_keywords,
                "total_count": len(unique_keywords),
                "original_prompt": user_prompt,
                "extracted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"다중 키워드 추출 중 오류: {e}")
            return {
                "success": False,
                "error": f"다중 키워드 추출 실패: {str(e)}",
                "original_prompt": user_prompt,
                "extracted_at": datetime.now().isoformat()
            }
    
    async def extract_and_get_stock_info(self, user_prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        키워드 추출 후 주식 검색 및 상세 정보를 조회합니다.
        
        Args:
            user_prompt: 사용자 입력 프롬프트
            model_name: 사용할 모델 이름 (None이면 기존 모델 사용)
        
        Returns:
            주식 정보 (키워드 추출 → 검색 → 상세 정보 조회)
        """
        try:
            from src.services.integrated_mcp_client import safe_mcp_call, OptimizedIntegratedMCPClient
            
            # 1단계: 키워드 추출 (모델이 지정된 경우 업데이트)
            if model_name and model_name != self.model:
                self.update_model(model_name)
            extraction_result = await self.extract_stock_keyword(user_prompt, model_name)
            
            if not extraction_result.get('success', False):
                return {
                    "success": False,
                    "error": f"키워드 추출 실패: {extraction_result.get('error', '알 수 없는 오류')}",
                    "original_prompt": user_prompt,
                    "extracted_at": datetime.now().isoformat()
                }
            
            extracted_keyword = extraction_result.get('keyword', '')
            if not extracted_keyword:
                return {
                    "success": False,
                    "error": f"'{user_prompt}'에서 주식 관련 키워드를 찾을 수 없습니다.",
                    "original_prompt": user_prompt,
                    "extracted_at": datetime.now().isoformat()
                }
            
            async with OptimizedIntegratedMCPClient() as client:
                # 주식 코드인지 확인
                import re
                if re.match(r'^\d{6}$', extracted_keyword):
                    # 주식 코드로 직접 상세 정보 조회
                    try:
                        stock_info = await safe_mcp_call(client, client.get_stock_info, extracted_keyword)
                        return {
                            "success": True,
                            "extraction_result": extraction_result,
                            "stock_info": stock_info,
                            "search_results": None,
                            "processing_type": "direct_stock_code",
                            "processed_at": datetime.now().isoformat()
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"주식 정보 조회 실패: {str(e)}",
                            "extraction_result": extraction_result,
                            "original_prompt": user_prompt,
                            "processed_at": datetime.now().isoformat()
                        }
                else:
                    # 2단계: 키워드로 주식 검색
                    try:
                        search_results = await safe_mcp_call(client, client.search_stock, extracted_keyword)
                        
                        if not search_results or not search_results.get('success', True) or "results" not in search_results:
                            return {
                                "success": False,
                                "error": "주식 검색 결과가 없습니다.",
                                "extraction_result": extraction_result,
                                "search_results": search_results,
                                "original_prompt": user_prompt,
                                "processed_at": datetime.now().isoformat()
                            }
                        
                        # 3단계: 첫 번째 검색 결과의 stock_code로 상세 정보 조회
                        if search_results["results"]:
                            first_stock = search_results["results"][0]
                            stock_code = first_stock.get('stock_code', '')
                            
                            if stock_code:
                                try:
                                    stock_info = await safe_mcp_call(client, client.get_stock_info, stock_code)
                                    return {
                                        "success": True,
                                        "extraction_result": extraction_result,
                                        "search_results": search_results,
                                        "stock_info": stock_info,
                                        "selected_stock_code": stock_code,
                                        "selected_stock_name": first_stock.get('company_name', ''),
                                        "processing_type": "keyword_search_then_detail",
                                        "processed_at": datetime.now().isoformat()
                                    }
                                except Exception as e:
                                    return {
                                        "success": False,
                                        "error": f"상세 정보 조회 실패: {str(e)}",
                                        "extraction_result": extraction_result,
                                        "search_results": search_results,
                                        "original_prompt": user_prompt,
                                        "processed_at": datetime.now().isoformat()
                                    }
                            else:
                                return {
                                    "success": False,
                                    "error": "검색 결과에서 stock_code를 찾을 수 없습니다.",
                                    "extraction_result": extraction_result,
                                    "search_results": search_results,
                                    "original_prompt": user_prompt,
                                    "processed_at": datetime.now().isoformat()
                                }
                        else:
                            return {
                                "success": False,
                                "error": "검색 결과가 없습니다.",
                                "extraction_result": extraction_result,
                                "search_results": search_results,
                                "original_prompt": user_prompt,
                                "processed_at": datetime.now().isoformat()
                            }
                            
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"주식 검색 실패: {str(e)}",
                            "extraction_result": extraction_result,
                            "original_prompt": user_prompt,
                            "processed_at": datetime.now().isoformat()
                        }
                        
        except Exception as e:
            logger.error(f"키워드 추출 및 주식 정보 조회 중 오류: {e}")
            return {
                "success": False,
                "error": f"처리 중 오류가 발생했습니다: {str(e)}",
                "original_prompt": user_prompt,
                "processed_at": datetime.now().isoformat()
            }

# 전역 인스턴스
stock_keyword_extractor = StockKeywordExtractor() 