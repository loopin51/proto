import requests

BASE_URL = "http://127.0.0.1:5000"

def test_index():
    response = requests.get(BASE_URL + "/")
    assert response.status_code == 200, "Index page should return 200 OK"

def test_conversation():
    payload = {"message": "Hello!"}
    response = requests.post(BASE_URL + "/conversation", data=payload)
    assert response.status_code == 200, "Conversation endpoint should return 200 OK"
    response_data = response.json()
    assert response_data.get("success") is True, "Conversation endpoint should indicate success"

def test_get_conversation():
    response = requests.get(BASE_URL + "/get_conversation")
    assert response.status_code == 200, "Get Conversation endpoint should return 200 OK"
    conversations = response.json()
    assert isinstance(conversations, list), "Get Conversation endpoint should return a list"

def test_reflection():
    response = requests.get(BASE_URL + "/reflect")
    assert response.status_code == 200, "Reflection endpoint should return 200 OK"

def test_memory():
    response = requests.get(BASE_URL + "/memory")
    assert response.status_code == 200, "Memory endpoint should return 200 OK"

if __name__ == "__main__":
    test_index()
    test_conversation()
    test_get_conversation()
    test_reflection()
    test_memory()
    print("All endpoint tests passed.")
