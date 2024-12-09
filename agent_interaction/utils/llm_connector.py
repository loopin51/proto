import requests

def query_llm(prompt):
    url = "http://127.0.0.1:1234/v1/chat/completions"  # LLM API 주소 예시
    data = {
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        # 올바른 데이터 형식을 사용하여 POST 요청 전송
        response = requests.post(url, json=data)
        response.raise_for_status()  # HTTP 상태 코드가 200이 아닌 경우 예외 발생

        # 응답에서 'choices' 필드 확인 후 내용 추출
        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            raise ValueError("Unexpected response format from LLM")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error: Unable to connect to LLM - {e}")
    except ValueError as ve:
        raise RuntimeError(f"Error: LLM returned invalid response - {ve}")