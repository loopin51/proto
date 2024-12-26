from flask import Flask, render_template, jsonify, request
from utils.general_methods import agent_conversation, generate_context
from utils.memory_management import promote_to_long_term_memory, adjust_memories
from utils.emotion_methods import retrieve_current_emotions
from agents.agent import Agent

import threading
import sqlite3
import time

app = Flask(__name__)

# Database path
DATABASE_PATH = "test_agents.db"

# Initialize agents
agent1 = Agent(name="agent_1", persona="Stressed and anxious, but determined.", partner_name="agent_2")
agent2 = Agent(name="agent_2", persona="Calm and experienced under pressure.", partner_name="agent_1")
agent3 = Agent(name="agent_3", persona="Interactive and friendly, ready to help users.", partner_name=None)

conversation_turn = 1

# Background thread for memory management
def manage_agent_memories():
    while True:
        # Adjust memories and promote to long-term for agent1 and agent2
        adjust_memories(DATABASE_PATH, agent1.name)
        adjust_memories(DATABASE_PATH, agent2.name)
        promote_to_long_term_memory(DATABASE_PATH, agent1.name)
        promote_to_long_term_memory(DATABASE_PATH, agent2.name)
        time.sleep(60)  # Run every 60 seconds

threading.Thread(target=manage_agent_memories, daemon=True).start()

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

    return jsonify(auto_conversation_log)

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
    app.run(debug=True)
