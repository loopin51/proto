import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from threading import Thread
from agents.agent import Agent
from agent_methods import *
import time

app = Flask(__name__)

# 에이전트 초기화
agent1 = Agent("John", "Friendly pharmacist who likes helping others.")
agent2 = Agent("Maria", "Artist who enjoys painting and nature.")

# 대화 기록 저장 리스트 및 초기화
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

    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        )
    ''')

    # Create short-term memory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            content TEXT,
            importance INTEGER
        )
    ''')

    # Create long-term memory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            importance INTEGER,
            last_accessed TEXT
        )
    ''')

    conn.commit()
    conn.close()

# 라우팅
@app.route('/')
def index():
    return render_template('index.html', conversation_history=conversation_history)

@app.route('/conversation', methods=['POST'])
def conversation():
    global conversation_turn
    user_message = request.form['message']

    # 새로운 컨텍스트 생성
    context = {
        "short_term_memory": retrieve_from_short_term_memory(database_path),
        "long_term_memory": retrieve_from_long_term_memory(database_path)
    }

    try:
        response, conversation_turn = agent_conversation(
            database_path, agent1, agent2, user_message, conversation_turn, context
        )
        return jsonify({"success": True, "response": response})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory', methods=['GET'])
def memory():
    short_term = retrieve_from_short_term_memory(database_path)
    long_term = retrieve_from_long_term_memory(database_path)
    return render_template('memory.html', short_term=short_term, long_term=long_term)

@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT turn, speaker, message FROM conversations ORDER BY turn ASC')
    rows = cursor.fetchall()
    conn.close()
    conversation = [{"turn": row[0], "speaker": row[1], "message": row[2]} for row in rows]
    return jsonify(conversation)

# 자동 대화
def automated_conversation(agent1, agent2, num_turns=10):
    current_message = "Hello!"
    global conversation_turn

    for _ in range(num_turns):
        # 새로운 컨텍스트 생성
        context = {
            "short_term_memory": retrieve_from_short_term_memory(database_path),
            "long_term_memory": retrieve_from_long_term_memory(database_path)
        }

        try:
            response, conversation_turn = agent_conversation(
                database_path, agent1, agent2, current_message, conversation_turn, context
            )
            current_message = response
        except RuntimeError as e:
            print(f"Error during automated conversation: {e}")
            break

# 메모리 관리 자동화 주기적 실행
def run_memory_management():
    """
    메모리 관리 자동화: 장기 기억 승격 및 회상 생성.
    """
    while True:
        try:
            manage_memories(database_path, agent2.name)
        except Exception as e:
            print(f"Error in memory management thread: {e}")
        time.sleep(10)  # 10초 간격으로 실행


# 비동기로 자동 대화 실행
def run_automated_conversation():
    automated_conversation(agent1, agent2, num_turns=10)

if __name__ == '__main__':
    # 데이터베이스 초기화
    init_db()

    # 비동기 스레드에서 자동 대화 실행
    conversation_thread = Thread(target=run_automated_conversation)
    conversation_thread.start()

    # 비동기 스레드에서 메모리 관리 실행
    memory_management_thread = Thread(target=run_memory_management)
    memory_management_thread.start()

    # Flask 앱 실행
    app.run(debug=True)
