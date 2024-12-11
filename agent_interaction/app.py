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

    # Create thought processes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thought_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            thought_process TEXT
        )
    ''')

    conn.commit()
    conn.close()

def add_to_short_term_memory(event):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Insert new memory into short-term memory
    cursor.execute('''
        INSERT INTO short_term_memory (timestamp, content, importance)
        VALUES (datetime('now'), ?, ?)
    ''', (event['content'], event['importance']))
    conn.commit()

    # Check the number of entries in short-term memory
    cursor.execute('SELECT COUNT(*) FROM short_term_memory')
    count = cursor.fetchone()[0]

    # Remove oldest memory if capacity exceeded
    MAX_SHORT_TERM_MEMORY = 10
    if count > MAX_SHORT_TERM_MEMORY:
        cursor.execute('''
            DELETE FROM short_term_memory WHERE id = (
                SELECT id FROM short_term_memory ORDER BY timestamp ASC LIMIT 1
            )
        ''')
        conn.commit()
    conn.close()

def promote_to_long_term_memory():
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Find important memories in short-term memory
    cursor.execute('''
        SELECT id, content, importance FROM short_term_memory WHERE importance > 7
    ''')
    important_memories = cursor.fetchall()

    # Move each important memory to long-term memory
    for memory in important_memories:
        memory_id, content, importance = memory
        cursor.execute('''
            INSERT INTO long_term_memory (content, importance, last_accessed)
            VALUES (?, ?, datetime('now'))
        ''', (content, importance))
        cursor.execute('DELETE FROM short_term_memory WHERE id = ?', (memory_id,))
    conn.commit()
    conn.close()

def retrieve_from_short_term_memory():
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Retrieve recent memories
    cursor.execute('''
        SELECT content FROM short_term_memory ORDER BY timestamp DESC LIMIT 5
    ''')
    memories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return memories

def retrieve_from_long_term_memory():
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Retrieve important memories
    cursor.execute('''
        SELECT content FROM long_term_memory ORDER BY importance DESC, last_accessed DESC LIMIT 5
    ''')
    memories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return memories

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
    short_term = retrieve_from_short_term_memory()
    long_term = retrieve_from_long_term_memory()
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

def save_message_to_db(turn, speaker, message):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (turn, speaker, message) VALUES (?, ?, ?)
    ''', (turn, speaker, message))
    conn.commit()
    conn.close()

def parse_llm_response(content):
    """
    Parse the LLM's response content into Thought Process and Speech.
    """
    thought_process = "No thought process provided."
    speech = "No speech provided."

    # Extract Thought Process
    thought_match = re.search(r"Thought process:\s*(.*?)\n\n", content, re.DOTALL)
    if thought_match:
        thought_process = thought_match.group(1).strip()

    # Extract Speech
    speech_match = re.search(r"Speech:\s*(.+)", content, re.DOTALL)
    if speech_match:
        speech = speech_match.group(1).strip()

    return speech, thought_process


def save_thought_process_to_db(agent_name, thought_process):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Save thought process
    cursor.execute('''
        INSERT INTO thought_processes (agent_name, thought_process) VALUES (?, ?)
    ''', (agent_name, thought_process))
    conn.commit()
    conn.close()

def agent_conversation(agent1, agent2, message):
    global conversation_turn

    # Prepare memory and reflection context
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
        # Send prompt to LLM and get response
        llm_response = query_llm(prompt)
        print("DEBUG: Parsed JSON response:", llm_response)

        # Validate response structure
        if not isinstance(llm_response, dict) or "choices" not in llm_response or not llm_response["choices"]:
            raise ValueError("Unexpected LLM response format.")

        # Extract content field
        content = llm_response["choices"][0]["message"]["content"]

        # Parse Thought Process and Speech
        speech, thought_process = parse_llm_response(content)

        # Save to short-term memory and thought processes
        add_to_short_term_memory({"content": speech, "importance": 5})
        save_thought_process_to_db(agent2.name, thought_process)

        # Promote important memories to long-term memory
        promote_to_long_term_memory()

        # Save conversation to database
        save_message_to_db(conversation_turn, agent1.name, message)
        conversation_turn += 1
        save_message_to_db(conversation_turn, agent2.name, speech)
        conversation_turn += 1

        return speech

    except Exception as e:
        print(f"Error in agent_conversation: {e}")
        print(f"DEBUG: Raw LLM Response Content: {llm_response}")
        save_message_to_db(conversation_turn, "Error", str(e))
        conversation_turn += 1
        raise



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
