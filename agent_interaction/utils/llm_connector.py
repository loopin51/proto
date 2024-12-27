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
from .prompt_templates import system_prompt
from langchain_core.output_parsers import StrOutputParser

# LangChain ChatOpenAI 설정
llm = ChatOpenAI(
    base_url="http://10.12.121.81:11434/v1",
    api_key="ollama",
    model="llama3.1",
    temperature=0.7,
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
        chat_prompt  = ChatPromptTemplate.from_messages([
                        ("system", system_prompt()),
                        ("user", "{input}")
                    ])
        chain = chat_prompt | llm | StrOutputParser()  # 체인 구성
        for attempt in range(max_retries):
            try:
                # 체인을 통해 invoke 호출
                response = await chain.ainvoke({"input": prompt})
                return {"choices": [{"message": {"content": response}}]}  # JSON 형식으로 응답 포맷팅
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise RuntimeError(f"Error querying LLM after {max_retries} attempts: {e}")

    # 비동기 실행
    return asyncio.run(_query_async())

def query_llm_dict(messages, max_retries=5, retry_delay=2):
    """
    LangChain 기반 LLM 요청 함수. OpenAI 스타일의 messages (list[dict])를 입력받아 처리.
    Args:
        messages (list[dict]): 예) [
          {"role": "system", "content": "..."},
          {"role": "user", "content": "..."}
        ]
        max_retries (int): 최대 재시도 횟수.
        retry_delay (int): 재시도 간격(초).
    Returns:
        dict: LLM의 응답을 OpenAI 호환 JSON 형태로 반환. {"choices": [{"message": {"content": ...}}]}
    """

    async def _query_async_dict():
        # 1) messages 리스트를 LangChain에서 요구하는 (role, content) 튜플 형태로 변환
        prompt_list = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt_list.append((role, content))

        # 2) ChatPromptTemplate.from_messages(...)로 PromptTemplate 구성
        chat_prompt = ChatPromptTemplate.from_messages(prompt_list)

        # 3) 체인 구성 (StrOutputParser는 단순 문자열로 결과를 파싱)
        chain = chat_prompt | llm | StrOutputParser()

        # 4) 비동기 실행
        for attempt in range(max_retries):
            try:
                # chain.ainvoke에 빈 딕셔너리(또는 필요한 입력) 전달
                response = await chain.ainvoke({})
                # OpenAI 호환 JSON 형태로 반환
                return {
                    "choices": [
                        {"message": {"content": response}}
                    ]
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise RuntimeError(f"Error querying LLM after {max_retries} attempts: {e}")

    # 5) asyncio.run(...)으로 비동기 함수 실행
    return asyncio.run(_query_async_dict())