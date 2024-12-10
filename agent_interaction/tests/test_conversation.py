import threading
import requests

BASE_URL = "http://127.0.0.1:5000"

def simulate_conversation(message):
    response = requests.post(f"{BASE_URL}/conversation", data={'message': message})
    print(response.json())

if __name__ == "__main__":
    # 테스트 메시지
    messages = [
        "Hello!",
        "How are you?",
        "Tell me about yourself.",
        "What do you think of art?",
        "Goodbye!"
    ]

    # 여러 스레드에서 병렬 요청 테스트
    threads = []
    for message in messages:
        thread = threading.Thread(target=simulate_conversation, args=(message,))
        threads.append(thread)
        thread.start()

    # 모든 스레드가 종료될 때까지 기다림
    for thread in threads:
        thread.join()

    print("All conversation tests completed.")
