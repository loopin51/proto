import requests
import threading
import json
import time

# 최대 동시 요청 제한 설정
llm_request_lock = threading.Semaphore(5)

def query_llm(prompt, max_retries=3, retry_delay=2):
    """
    Query the LLM API with a prompt and return the response content.
    Includes error handling and retry logic.
    """
    with llm_request_lock:
        url = "http://127.0.0.1:1234/v1/chat/completions"  # LLM API 주소 예시
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(max_retries):
            try:
                # POST 요청 전송
                response = requests.post(url, json=data, timeout=10)
                response.raise_for_status()  # HTTP 상태 코드 검사

                # 응답 JSON 파싱
                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Error parsing JSON response: {e}")

                # 'choices' 필드가 예상대로 있는지 확인
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    return response_data['choices'][0]['message']['content']
                else:
                    # 응답 형식이 예상과 다를 경우 디버깅용 출력
                    print("Unexpected response format:", response_data)
                    raise ValueError("LLM response does not contain 'choices' or is empty")

            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)  # 재시도 전 대기
                else:
                    raise RuntimeError(f"Error: Unable to connect to LLM after {max_retries} attempts - {e}")

            except ValueError as ve:
                print(f"Attempt {attempt + 1} failed: {ve}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)  # 재시도 전 대기
                else:
                    raise RuntimeError(f"Error: LLM returned invalid response - {ve}")

