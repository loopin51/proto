# test_agent_interaction.py

import sqlite3

from agents.agent import Agent 
from utils.memo import agent_conversation
from utils.emotion_methods import analyze_sentiment,init_emotion_db, update_emotion, adjust_emotions
from utils.emotion_methods import init_emotion_db, retrieve_current_emotions, update_emotion, adjust_emotions
from utils.emotion_methods import retrieve_current_emotions

TEST_DB_PATH = "test_agents.db"

def setup_database(database_path=TEST_DB_PATH):
    """
    Create the required tables for testing agent conversation.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # conversations 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        );
    """)

    # short_term_memory 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # long_term_memory 테이블 (reflection_type 포함)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL NOT NULL,
            last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
            reflection_type TEXT,
            reference_count INTEGER DEFAULT 0
        );
    """)

    # emotion_states 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emotion_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            joy REAL NOT NULL,
            trust REAL NOT NULL,
            fear REAL NOT NULL,
            surprise REAL NOT NULL,
            sadness REAL NOT NULL,
            disgust REAL NOT NULL,
            anger REAL NOT NULL,
            anticipation REAL NOT NULL
        );
    """)

    conn.commit()
    conn.close()

def populate_initial_data(database_path=TEST_DB_PATH):
    """
    Populate the database with initial data for a more dramatic emotional scenario.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # 감정 DB 초기화
    init_emotion_db(database_path)

    # 에이전트 목록
    agents = ["agent_1", "agent_2"]

    # 1) 초기 감정 상태 (모두 0.0)
    for agent in agents:
        cursor.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # 2) Short-term memories
    #    감정 변화에 직접적으로 영향을 줄 만한 '불안', '스트레스' 등 내용
    stm_data = [
        ("agent_1", "Really worried about the client's reaction to our recent failure.", 0.7),
        ("agent_1", "Feeling pressured by upper management deadlines.", 0.6),
        ("agent_2", "Reminder to stay calm and logical in stressful situations.", 0.5),
        ("agent_2", "Has handled tough deadlines successfully before.", 0.8),
    ]
    for agent_name, content, importance in stm_data:
        cursor.execute("""
            INSERT INTO short_term_memory (agent_name, content, importance)
            VALUES (?, ?, ?)
        """, (agent_name, content, importance))

    # 3) Long-term memories
    #    일부 reflection_type이 NULL, 일부는 특정 값("strategy", "lesson" 등)
    ltm_data = [
        ("agent_1", "Previously overcame a massive crisis under time pressure.", 0.9, None),
        ("agent_1", "Reflection on losing a major deal - felt anger, disappointment.", 0.8, "lesson"),
        ("agent_2", "Deep experience in conflict resolution and stress management.", 0.95, None),
        ("agent_2", "Strategy reflection: calming down emotional colleagues.", 0.7, "strategy")
    ]
    for agent_name, content, importance, reflection_type in ltm_data:
        cursor.execute("""
            INSERT INTO long_term_memory (agent_name, content, importance, reflection_type)
            VALUES (?, ?, ?, ?)
        """, (agent_name, content, importance, reflection_type))

    # 4) Conversations (초기)
    #    이번에는 더욱 감정이 섞인 초기 대화
    initial_conversations = [
        (1, "agent_1", "Hello, are you free to discuss our recent project crisis?"),
        (2, "agent_2", "Yes, I'm here. Let's figure out a plan calmly.")
    ]
    for turn, speaker, message in initial_conversations:
        cursor.execute("""
            INSERT INTO conversations (turn, speaker, message) 
            VALUES (?, ?, ?)
        """, (turn, speaker, message))

    conn.commit()
    conn.close()

def test_agents_dialog():
    """
    Test 5-turn conversation scenario between agent1 and agent2,
    showcasing dramatic emotional changes.
    """
    # 에이전트 초기화
    agent1 = Agent(name="agent_1", persona="Stressed and anxious, but determined.", partner_name="agent_2")
    agent2 = Agent(name="agent_2", persona="Calm and experienced under pressure.", partner_name="agent_1")

    conversation_turn = 3

    # 대화 스크립트 총 5회
    # agent1 -> agent2, agent2 -> agent1를 번갈아 시뮬레이션
    # 메시지들이 점점 극단적으로 변해서 감정 변화를 드라마틱하게 보여줄 수 있도록 구성

    scripted_dialogs = [
        # Turn 1: agent1 -> agent2
        (
            agent1,  # sender
            agent2,  # receiver
            "I just got an angry call from our biggest client. They're furious about our failure! I'm really panicking here!"
        ),
        # Turn 2: agent2 -> agent1
        (
            agent2,
            agent1,
            "Take a deep breath. We've been through tough deadlines before. Let me help you figure this out logically."
        ),
        # Turn 3: agent1 -> agent2
        (
            agent1,
            agent2,
            "Logical? I'm sorry but I feel everything is collapsing! We might lose this client forever!"
        ),
        # Turn 4: agent2 -> agent1
        (
            agent2,
            agent1,
            "I understand your fear. Keep calm. We can propose a rapid solution and apologize sincerely. Let's plan this together."
        ),
        # Turn 5: agent1 -> agent2
        (
            agent1,
            agent2,
            "All right... Let me try to calm down. Maybe there's still hope if we act fast and show them a solid recovery plan."
        )
    ]

    for i, (sender, receiver, message) in enumerate(scripted_dialogs, start=1):
        print(f"=== Turn {conversation_turn}: {sender.name} to {receiver.name} ===")
        print(f"Message: {message}\n")
        
        response, conversation_turn = agent_conversation(
            database_path=TEST_DB_PATH,
            agent1=sender,
            agent2=receiver,
            message=message,
            conversation_turn=conversation_turn
        )

        print(f"{receiver.name}'s Response:\n{response}\n")
        print(f"Updated conversation turn: {conversation_turn}\n")
        
        # Retrieve and print current emotions of the receiver as a demonstration of dramatic change
        receiver_emotions = retrieve_current_emotions(TEST_DB_PATH, receiver.name)
        print(f"Current Emotions for {receiver.name}: {receiver_emotions}\n")
        print("-"*50)

def main():
    # 1) DB 생성 및 초기화
    setup_database()
    populate_initial_data()

    # 2) 5회 대화 시뮬레이션
    test_agents_dialog()

if __name__ == "__main__":
    main()
