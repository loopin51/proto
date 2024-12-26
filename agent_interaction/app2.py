from flask import Flask, render_template, jsonify, request
from utils.memo import agent_conversation
from utils.memory_management import manage_memories
from utils.emotion_methods import retrieve_current_emotions
from agents.agent import Agent

import threading
import os
import sqlite3
import time

app = Flask(__name__)
from test_agent_interaction import setup_database, populate_initial_data  # (파일/함수 위치에 맞게 변경)

# Database path
DATABASE_PATH = "test_system.db"

# Agent1: 감정 변화가 잦고 잘 당황, 잘 화냄. 경험 풍부.
# - 추가 특성: 단기 폭발 후 책임감 발휘, 직접적 감정 표현, 오래 일해 리더십 있지만 순간 감정에 휩쓸림
agent1_persona = (
    "Often experiences rapid emotional changes, easily startled and quick to anger, "
    "but has a wealth of experience from past major crises. "
    "Expresses sadness, anger, or anxiety very directly, sometimes surprising teammates. "
    "Short meltdown episodes happen, but eventually takes responsibility and tries to fix issues. "
    "Has led projects successfully despite emotional fluctuations."
)

# Agent2: 이성적, 주관 확실, 침착. 스스로 원칙 지킴.
# - 추가 특성: 철저한 원칙주의, 감정보다 데이터/논리를 중시, 단호한 커뮤니케이션
agent2_persona = (
    "Highly rational and calm under pressure. Holds firm personal principles and "
    "prefers logic and data over emotional pleas. Known for methodically analyzing problems "
    "before proposing solutions, and rarely raises their voice. Believes a stable set of rules "
    "is crucial in a chaotic world."
)

# Agent3: 친절하고 밝고 도덕감이 높음, 남 돕길 좋아함
# - 추가 특성: 이타주의, 낙천적, 감정 공감 능력 높음, 정의감
agent3_persona = (
    "Kind, bright, and morally driven. Strong sense of altruism, always willing to lend a hand. "
    "Believes helping others is one of the greatest joys. Stays optimistic even in tough times, "
    "and naturally empathizes with people's feelings, often acting as a mediator."
)

agent1 = Agent(name="agent_1", persona=agent1_persona, partner_name="agent_2")
agent2 = Agent(name="agent_2", persona=agent2_persona, partner_name="agent_1")
agent3 = Agent(name="agent_3", persona=agent3_persona, partner_name=None)
conversation_turn = 1

# Background thread for memory management
def manage_agent_memories():
    while True:
        # Adjust memories and promote to long-term for agent1 and agent2
        manage_memories(DATABASE_PATH, agent1.name)
        manage_memories(DATABASE_PATH, agent2.name)
        time.sleep(10)  # Run every 60 seconds

#threading.Thread(target=manage_agent_memories, daemon=True).start()

# Route: Home
@app.route('/')
def home():
    return render_template('home.html')

# Route: Auto conversation
@app.route('/auto_conversation', methods=['GET'])
def auto_conversation():
    global conversation_turn

    message = "Let's start discussing the project's current status."
    auto_conversation_log = []

    for i in range(5):  # Simulate 5 turns of conversation
        sender, receiver = (agent1, agent2) if i % 2 == 0 else (agent2, agent1)
        print(f"=== Turn {conversation_turn}: {sender.name} to {receiver.name} ===")
        print(f"Message: {message}\n")
        response, conversation_turn = agent_conversation(
            DATABASE_PATH,
            agent1=sender,
            agent2=receiver,
            message=message,
            conversation_turn=conversation_turn
        )
        auto_conversation_log.append({
            "turn": conversation_turn,
            "sender": sender.name,
            "receiver": receiver.name,
            "message": message,
            "response": response
        })
        message = response  # Set the response as the next message
        print(f"{receiver.name}'s Response:\n{response}\n")
        print(f"Updated conversation turn: {conversation_turn}\n")
        
        # Retrieve and print current emotions of the receiver as a demonstration of dramatic change
        receiver_emotions = retrieve_current_emotions(DATABASE_PATH, receiver.name)
        print(f"Current Emotions for {receiver.name}: {receiver_emotions}\n")
        print("-"*50)
    #return jsonify(auto_conversation_log)
    # JSON 대신 render_template를 사용하여, logs를 템플릿에 전달
    return render_template('auto_conversation.html', logs=auto_conversation_log)

# Route: Manual chat - placeholder
@app.route('/manual_chat', methods=['GET'])
def manual_chat():
    return render_template('manual_chat.html')

# Route: Memory viewer
@app.route('/memory_view/<agent_name>', methods=['GET'])
def memory_view(agent_name):
    try:
        # Fetch short-term and long-term memories for the given agent
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, importance FROM short_term_memory
            WHERE agent_name = ?
            ORDER BY timestamp DESC
        """, (agent_name,))
        short_term_memories = cursor.fetchall()

        cursor.execute("""
            SELECT content, importance FROM long_term_memory
            WHERE agent_name = ?
            ORDER BY importance DESC
        """, (agent_name,))
        long_term_memories = cursor.fetchall()

        conn.close()

        emotions = retrieve_current_emotions(DATABASE_PATH, agent_name)

        return render_template(
            'memory_view.html',
            agent_name=agent_name,
            short_term_memories=short_term_memories,
            long_term_memories=long_term_memories,
            emotions=emotions
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # DB가 이미 있으면 삭제
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"Existing database '{DATABASE_PATH}' has been removed.")

    setup_database(DATABASE_PATH)
    populate_initial_data(DATABASE_PATH) 
    app.run(debug=True)
