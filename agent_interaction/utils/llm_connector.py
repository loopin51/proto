import requests
import threading
import time
import json

# 최대 동시 요청 제한 설정
llm_request_lock = threading.Semaphore(5)

def query_llm_old(prompt, max_retries=5,retry_delay=2):
    with llm_request_lock:
        url = "http://127.0.0.1:1234/v1/chat/completions"
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=data, timeout=10)
                response.raise_for_status()

                # Debug raw response
                #print("DEBUG: Raw response text:", response.text)

                # Parse JSON response
                try:
                    clean_response_text = response.text.strip()
                    response_data = json.loads(clean_response_text)
                    #print("DEBUG: Parsed JSON response:", response_data)
                    return response_data
                except ValueError as e:
                    #print("DEBUG: JSON parsing failed. Raw response:", response.text)
                    raise RuntimeError(f"Error parsing JSON response: {e}")

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError(f"Error: Unable to connect to LLM after {max_retries} attempts - {e}")
            except ValueError as ve:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError(f"Error: LLM returned invalid response - {ve}")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import asyncio

# LangChain ChatOpenAI 설정
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
    model="lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
    temperature=0.1,
    streaming=False,  # 스트리밍 비활성화
)

# query_llm 함수 구현
def query_llm(prompt, max_retries=5, retry_delay=2):
    """
    LangChain 기반 LLM 요청 함수. JSON 응답을 그대로 반환.
    Args:
        prompt (str): LLM에 보낼 프롬프트.
        max_retries (int): 최대 재시도 횟수.
        retry_delay (int): 재시도 간격(초).
    Returns:
        dict: LLM의 응답 JSON.
    """
    async def _query_async():
        chat_prompt = ChatPromptTemplate.from_template("{input} 한국어로 답변해줘.")
        for attempt in range(max_retries):
            try:
                # LangChain API 호출
                response = await llm.acomplete(prompt={"messages": [{"role": "user", "content": chat_prompt.format(input=prompt)}]})
                return response  # JSON 응답 반환
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise RuntimeError(f"Error querying LLM after {max_retries} attempts: {e}")

    # 비동기 실행
    return asyncio.run(_query_async())
