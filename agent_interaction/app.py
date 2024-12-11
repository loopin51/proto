import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from threading import Thread
from agents.agent import Agent
from utils.llm_connector import query_llm
import re

app = Flask(__name__)

# 에이전트 초기화
agent1 = Agent("John", "Friendly pharmacist who likes helping others.")
agent2 = Agent("Maria", "Artist who enjoys painting and nature.")

# 대화 기록 저장 리스트
conversation_history = []
conversation_turn = 1

# 현재 대화 시작 시각 기반 데이터베이스 파일 경로 생성
def get_database_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_path = os.path.join('database', f'conversations_{timestamp}.db')
    return db_path

database_path = get_database_path()

# 데이터베이스 초기화
def init_db():
    if not os.path.exists(os.path.dirname(database_path)):
        os.makedirs(os.path.dirname(database_path))
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html', conversation_history=conversation_history)

@app.route('/conversation', methods=['POST'])
def conversation():
    user_message = request.form['message']
    try:
        response = agent_conversation(agent1, agent2, user_message)
        return jsonify({"success": True, "response": response})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/reflect', methods=['GET'])
def reflect():
    reflection = agent1.reflect()
    return render_template('reflection.html', reflection=reflection)

@app.route('/memory', methods=['GET'])
def memory():
    memory_context = agent1.get_memory_context()
    return render_template('memory.html', memory_context=memory_context)

@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('SELECT turn, speaker, message FROM conversations ORDER BY turn ASC')
    rows = cursor.fetchall()
    conn.close()
    conversation = [{"turn": row[0], "speaker": row[1], "message": row[2]} for row in rows]
    return jsonify(conversation)

@app.route('/get_reflection', methods=['GET'])
def get_reflection():
    reflection = agent1.reflect()
    return jsonify({"reflection": reflection})

def save_message_to_db(turn, speaker, message):
    conn = sqlite3.connect(database_path,check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (turn, speaker, message) VALUES (?, ?, ?)
    ''', (turn, speaker, message))
    conn.commit()
    conn.close()

def parse_llm_response(content):
    """
    Parse the LLM's response to extract thought process and speech.
    """
    # Extract thought process
    thought_process_match = re.search(r"Thought process:\s*(.+?)\n\n", content, re.DOTALL)
    thought_process = thought_process_match.group(1).strip() if thought_process_match else "No thought process provided."

    # Extract speech
    speech_match = re.search(r"Speech:\s*(.+)", content, re.DOTALL)
    speech = speech_match.group(1).strip() if speech_match else "No speech provided."

    return speech, thought_process

def save_thought_process_to_db(agent_name, thought_process):
    """
    Save the agent's thought process to a separate database table.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # 추론 내용을 저장하는 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thought_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            thought_process TEXT
        )
    ''')
    conn.commit()

    # 데이터 저장
    cursor.execute('''
        INSERT INTO thought_processes (agent_name, thought_process) VALUES (?, ?)
    ''', (agent_name, thought_process))
    conn.commit()
    conn.close()


def agent_conversation(agent1, agent2, message):
    global conversation_turn  # 전역 변수 사용
    memory_context = agent2.get_memory_context()
    reflection = agent2.reflect()
    prompt = (
        f"{agent1.name} (Persona: {agent1.persona}) says to {agent2.name}: '{message}'\n"
        f"Memory Context:\n{memory_context}\n"
        f"Reflection:\n{reflection}\n\n"
        f"Please respond to this message in the following format:\n"
        f"Thought process:\n[Provide your reasoning here, including any considerations from memory and reflection.]\n\n"
        f"Speech:\n[Provide the exact words the agent will say in the conversation.]"
    )
    try:
        # LLM에게 프롬프트 전송 및 응답 수신
        llm_response = query_llm(prompt)
        content = llm_response["choices"][0]["message"]["content"]

        # Parse the response to extract speech and thought process
        speech, thought_process = parse_llm_response(content)

        # 대화 기록에 에이전트가 실제로 말한 내용만 저장
        save_message_to_db(conversation_turn, agent1.name, message)
        conversation_turn += 1
        save_message_to_db(conversation_turn, agent2.name, speech)
        conversation_turn += 1

        # 에이전트의 추론 과정은 별도로 저장
        save_thought_process_to_db(agent2.name, thought_process)

        return speech
    except RuntimeError as e:
        save_message_to_db(conversation_turn, "Error", str(e))
        conversation_turn += 1
        raise e


def automated_conversation(agent1, agent2, num_turns=10):
    current_message = "Hello!"
    for _ in range(num_turns):
        try:
            response = agent_conversation(agent1, agent2, current_message)
            current_message = response
        except RuntimeError as e:
            print(f"Error during automated conversation: {e}")
            break

# 비동기로 자동 대화 실행
def run_automated_conversation():
    automated_conversation(agent1, agent2, num_turns=10)

if __name__ == '__main__':
    # 데이터베이스 초기화
    init_db()

    # 비동기 스레드에서 자동 대화 실행
    conversation_thread = Thread(target=run_automated_conversation)
    conversation_thread.start()

    # Flask 앱 실행
    app.run(debug=True)
