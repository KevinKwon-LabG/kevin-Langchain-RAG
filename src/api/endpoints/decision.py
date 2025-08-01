from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from src.services.langchain_decision_service import LangchainDecisionService

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("decision_debug")
debug_logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/api/decision", tags=["decision"])

# 의사결정 서비스 인스턴스
decision_service = LangchainDecisionService()


class PromptRequest(BaseModel):
    """사용자 prompt 요청 모델"""
    prompt: str
    use_async: bool = True


class DecisionResponse(BaseModel):
    """의사결정 응답 모델"""
    user_prompt: str
    decision_result: str
    success: bool
    error_message: Optional[str] = None


@router.post("/classify", response_model=DecisionResponse)
async def classify_prompt(request: PromptRequest):
    """
    사용자의 prompt를 분석하여 4가지 카테고리 중 하나로 분류
    
    분류 결과:
    - 날씨 정보를 요청하셨습니다.
    - 한국 주식 시장에 상장되어 있는 종목의 주가 관련 정보를 요청하셨습니다.
    - 정확한 답변을 위해서는 웹 검색이 필요합니다.
    - 바로 답변드리겠습니다
    """
    try:
        debug_logger.debug(f"🔍 의사결정 요청 시작 - 프롬프트: {request.prompt[:100]}{'...' if len(request.prompt) > 100 else ''}")
        
        if not request.prompt.strip():
            debug_logger.warning("⚠️ 빈 프롬프트 요청")
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        # 비동기 또는 동기 방식으로 분류 수행
        if request.use_async:
            debug_logger.debug("🔄 비동기 분류 수행")
            decision_result = await decision_service.classify_prompt(request.prompt)
        else:
            debug_logger.debug("⚡ 동기 분류 수행")
            decision_result = decision_service.classify_prompt_sync(request.prompt)
        
        debug_logger.debug(f"✅ 분류 완료 - 결과: {decision_result}")
        
        return DecisionResponse(
            user_prompt=request.prompt,
            decision_result=decision_result,
            success=True
        )
        
    except HTTPException:
        debug_logger.error("❌ HTTP 예외 발생")
        raise
    except Exception as e:
        debug_logger.error(f"❌ 예외 발생: {e}")
        logger.error(f"의사결정 분류 중 오류: {e}")
        return DecisionResponse(
            user_prompt=request.prompt,
            decision_result="정확한 답변을 위해서는 웹 검색이 필요합니다.",
            success=False,
            error_message=str(e)
        )


@router.get("/health")
async def health_check():
    """서비스 상태 확인"""
    debug_logger.debug("🏥 헬스 체크 요청")
    return {"status": "healthy", "service": "langchain_decision_service"} 