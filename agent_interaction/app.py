import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request
from agents.agent import Agent
from utils.llm_connector import query_llm
from flask import jsonify


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
        # 웹페이지에 최신 대화 상태를 동적으로 반영
        return render_template('index.html', conversation_history=conversation_history)
    except RuntimeError as e:
        # 오류 메시지 출력
        return render_template('index.html', conversation_history=conversation_history, error=str(e))

@app.route('/reflect', methods=['GET'])
def reflect():
    reflection = agent1.reflect()  # 에이전트 1의 회상
    return render_template('reflection.html', reflection=reflection)

@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    """
    Fetch conversation history from the database.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('SELECT turn, speaker, message FROM conversations ORDER BY turn ASC')
    rows = cursor.fetchall()
    conn.close()

    # Format data as JSON
    conversation = [{"turn": row[0], "speaker": row[1], "message": row[2]} for row in rows]
    return jsonify(conversation)

@app.route('/get_reflection', methods=['GET'])
def get_reflection():
    """
    Fetch the agent's reflection based on their memory.
    """
    reflection = agent1.reflect()  # Example: Agent 1's reflection
    return jsonify({"reflection": reflection})

def save_message_to_db(turn, speaker, message):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (turn, speaker, message) VALUES (?, ?, ?)
    ''', (turn, speaker, message))
    conn.commit()
    conn.close()


def agent_conversation(agent1, agent2, message):
    global conversation_turn  # 전역 변수 사용
    memory_context = agent2.get_memory_context()
    reflection = agent2.reflect()
    prompt = (
        f"{agent1.name} (Persona: {agent1.persona}) says to {agent2.name}: '{message}'\n"
        f"{memory_context}\n"
        f"{reflection}\n"
        f"How should {agent2.name} respond?"
    )
    try:
        response = query_llm(prompt)
        # 메시지를 DB에 저장
        save_message_to_db(conversation_turn, agent1.name, message)
        conversation_turn += 1
        save_message_to_db(conversation_turn, agent2.name, response)
        conversation_turn += 1
        return response
    except RuntimeError as e:
        # 오류 발생 시 메시지와 대화 순서를 저장
        save_message_to_db(conversation_turn, "Error", str(e))
        conversation_turn += 1
        raise e

# 자동 대화 함수
def automated_conversation(agent1, agent2, num_turns=10):
    current_message = "Hello!" # Starting message
    for _ in range(num_turns):
        try:
            # Agent 1 -> Agent 2
            response = agent_conversation(agent1, agent2, current_message)
            # Update the current message for the next turn
            current_message = response

        except RuntimeError as e:
            print(f"Error during automated conversation: {e}")
            break


if __name__ == '__main__':
    # 데이터베이스 초기화
    init_db()

    # 자동 대화 실행 (플라스크 앱 실행 전에 실행)
    automated_conversation(agent1, agent2, num_turns=10)
    
    # Flask 앱 실행
    app.run(debug=True)