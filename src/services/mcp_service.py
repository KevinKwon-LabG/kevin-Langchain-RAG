import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.config.settings import settings

logger = logging.getLogger(__name__)

class MCPService:
    """MCP (Model Context Protocol) 서버와 통신하는 서비스"""
    
    def __init__(self):
        self.base_url = settings.mcp_server_url
        self.timeout = settings.mcp_timeout
        self.max_retries = settings.mcp_max_retries
        self.enabled = settings.mcp_enabled
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션 생성 또는 반환"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """MCP 서버에 요청을 보내는 공통 메서드"""
        if not self.enabled:
            raise Exception("MCP 서비스가 비활성화되어 있습니다.")
        
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers) as response:
                        return await response.json()
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        return await response.json()
                elif method.upper() == "PUT":
                    async with session.put(url, headers=headers, json=data) as response:
                        return await response.json()
                elif method.upper() == "DELETE":
                    async with session.delete(url, headers=headers) as response:
                        return await response.json()
                else:
                    raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
                    
            except aiohttp.ClientError as e:
                logger.warning(f"MCP 서버 요청 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"MCP 서버 연결 실패: {e}")
                await asyncio.sleep(1)  # 재시도 전 대기
            except Exception as e:
                logger.error(f"MCP 서버 요청 중 예외 발생: {e}")
                raise
    
    async def health_check(self) -> Dict[str, Any]:
        """MCP 서버 상태 확인"""
        try:
            response = await self._make_request("GET", "/")
            return {"status": "healthy", "message": "MCP 서버 연결 성공", "info": response}
        except Exception as e:
            logger.error(f"MCP 서버 상태 확인 실패: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """사용 가능한 도구 목록 조회"""
        try:
            response = await self._make_request("GET", "/tools")
            return response.get("tools", [])
        except Exception as e:
            logger.error(f"도구 목록 조회 실패: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """도구 호출"""
        try:
            response = await self._make_request("POST", f"/tools/{tool_name}", arguments)
            return response
        except Exception as e:
            logger.error(f"도구 호출 실패: {e}")
            raise
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 조회 (하위 호환성을 위해 유지)"""
        try:
            # MCP 서버는 모델 기반이 아닌 도구 기반이므로 빈 리스트 반환
            return []
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {e}")
            return []
    
    async def chat_completion(self, 
                            model: str, 
                            messages: List[Dict[str, str]], 
                            temperature: float = 0.7,
                            max_tokens: int = 1000,
                            **kwargs) -> Dict[str, Any]:
        """채팅 완성 요청"""
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            response = await self._make_request("POST", "/chat/completions", data)
            return response
        except Exception as e:
            logger.error(f"채팅 완성 요청 실패: {e}")
            raise
    
    async def text_completion(self, 
                            model: str, 
                            prompt: str, 
                            temperature: float = 0.7,
                            max_tokens: int = 1000,
                            **kwargs) -> Dict[str, Any]:
        """텍스트 완성 요청"""
        try:
            data = {
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            response = await self._make_request("POST", "/completions", data)
            return response
        except Exception as e:
            logger.error(f"텍스트 완성 요청 실패: {e}")
            raise
    
    async def embeddings(self, 
                        model: str, 
                        input_texts: List[str]) -> Dict[str, Any]:
        """임베딩 생성 요청"""
        try:
            data = {
                "model": model,
                "input": input_texts
            }
            
            response = await self._make_request("POST", "/embeddings", data)
            return response
        except Exception as e:
            logger.error(f"임베딩 생성 요청 실패: {e}")
            raise
    
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """특정 모델 정보 조회"""
        try:
            response = await self._make_request("GET", f"/models/{model}")
            return response
        except Exception as e:
            logger.error(f"모델 정보 조회 실패: {e}")
            return {}
    
    async def close(self):
        """세션 정리"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """소멸자에서 세션 정리"""
        try:
            if hasattr(self, 'session') and self.session and not self.session.closed:
                # 이벤트 루프가 실행 중인 경우에만 태스크 생성
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.session.close())
                except RuntimeError:
                    # 이벤트 루프가 실행 중이지 않은 경우 무시
                    pass
        except Exception:
            # 소멸자에서 발생하는 예외는 무시
            pass

# 싱글톤 인스턴스
mcp_service = MCPService() 