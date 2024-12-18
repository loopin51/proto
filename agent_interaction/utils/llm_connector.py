import requests
import threading
import time
import json

# 최대 동시 요청 제한 설정
llm_request_lock = threading.Semaphore(5)

def query_llm(prompt, max_retries=10,retry_delay=2):
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
