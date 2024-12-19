import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from threading import Thread, Lock
from agents.agent import Agent
from utils.agent_methods import *
import time
import signal
import sys
from utils.context_methods import *
app = Flask(__name__)

# 에이전트 초기화
agent1 = Agent("John", "Friendly pharmacist who likes helping others.")
agent2 = Agent("Maria", "Artist who enjoys painting and nature.")

# 대화 기록 저장 리스트 및 초기화
conversation_history = []
conversation_turn = 1
conversation_lock = Lock()  # Protect conversation_turn

# 데이터베이스 초기화
#init_memory_db()

# DB 경로를 한 번만 설정
database_path = get_database_path()
set_database_path(database_path)

# 프리셋 데이터베이스 초기화
init_db_with_preset(database_path)

# Routing
@app.route('/')
def index():
    return render_template('index.html', conversation_history=conversation_history)

@app.route('/conversation', methods=['POST'])
def conversation():
    global conversation_turn
    user_message = request.form['message']
    """
    Purpose: 
        This function handles user messages sent via the Flask web interface.
        It interacts with the agent_conversation function to generate responses 
        and manages conversation flow for user-agent interaction.

    Use Case:
        Primarily used when a web-based client (e.g., browser) is required to 
        interact with the agents in real-time.

    Current Status:
        Not actively used in the current project as the automated_conversation 
        function fulfills the primary use case of simulating agent interactions. 
        Retained for potential future use or manual testing purposes.
    """
    global conversation_turn
    user_message = request.form['message']

    # Generate context based on agent memories
    # This retrieves both short-term and long-term memory for the responding agent.
    context = generate_context(database_path, agent2.name)

    try:
        # Perform agent conversation
        response, turn = agent_conversation(
            database_path, agent1, agent2, user_message, conversation_turn, context
        )

        with conversation_lock:
            conversation_turn = turn  # Update safely

        # Call manage_memories to process new memory
        manage_memories(
            database_path,
            agent_name=agent2.name,
            new_event=None   #{"content": response, "importance": 5}  # Adjust importance as needed
        )

        return jsonify({"success": True, "response": response})

    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory', methods=['GET'])
def memory():
    short_term = retrieve_from_short_term_memory(database_path, agent2.name)
    long_term = retrieve_from_long_term_memory(database_path, agent2.name)
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
        context = generate_context(database_path, agent2.name)


        try:
            response, turn = agent_conversation(
                database_path, agent1, agent2, current_message, conversation_turn, context
            )

            with conversation_lock:
                conversation_turn = turn  # Update safely
            current_message = response

            # Call manage_memories to process new memory
            manage_memories(
                database_path,
                agent_name=agent2.name,
                new_event= None # Not needed
            )

        except RuntimeError as e:
            print(f"Error during automated conversation: {e}")
            break

# 메모리 관리 자동화 주기적 실행
def run_memory_management(conversation_turn, num_turns):
    """
    Periodically manage memory: promote important short-term memories and create reflections.
    """
    while conversation_turn < num_turns:
        try:
            print(f"DEBUG: Running memory management at conversation_turn={conversation_turn}")
            manage_memories(database_path, agent2.name)
        except Exception as e:
            print(f"Error in memory management thread: {e}")
        time.sleep(10)  # 10초 간격으로 실행
    print("Memory management thread terminated as conversation_turn reached num_turns.")

# 비동기로 자동 대화 실행
def run_automated_conversation():
    automated_conversation(agent1, agent2, num_turns=10)

# Graceful shutdown handler
def shutdown_handler(signal, frame):
    print("\nShutting down gracefully...")
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown_handler)

    conversation_thread = Thread(target=run_automated_conversation, daemon=True)
    conversation_thread.start()

    memory_management_thread = Thread(
        target=run_memory_management, args=(conversation_turn, 10), daemon=True
    )
    memory_management_thread.start()

    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        print("Server interrupted and shutting down...")

# 메인 실행
if __name__ == '__main__':
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)

    # Set threads as daemon to ensure they stop with the main process
    conversation_thread = Thread(target=run_automated_conversation, daemon=True)
    conversation_thread.start()

    #memory_management_thread = Thread(target=run_memory_management, args=(conversation_turn, 10), daemon=True)
    #memory_management_thread.start()

    # Run Flask app
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        print("Server interrupted and shutting down...")
