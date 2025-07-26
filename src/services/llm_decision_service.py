from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import Ollama

from src.config.settings import settings

# Llama3-18B 또는 선택된 모델을 사용할 수 있도록 설정

def get_llm(model_name=None):
    return Ollama(model=model_name or "deepseek-r1:14b")

class LLMDecisionService:
    def __init__(self):
        self.prompt = PromptTemplate(
            input_variables=["question"],
            template=(
                """
                아래 사용자의 질문에 대해 인터넷 검색(구글 등)이 필요한지 판단하세요. 
                반드시 '네' 또는 '아니오'로만 답변하세요.
                
                질문: {question}
                답변:
                """
            )
        )

    def needs_web_search(self, question: str, model_name=None) -> bool:
        llm = get_llm(model_name)
        chain = LLMChain(llm=llm, prompt=self.prompt)
        result = chain.run(question=question).strip()
        return result.startswith("네")

llm_decision_service = LLMDecisionService() 