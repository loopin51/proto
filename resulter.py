from flask import Flask, render_template, jsonify, request, make_response
from agent_interaction.utils.memo import agent_conversation
from agent_interaction.utils.memory_management import manage_memories, debug_log
from agent_interaction.utils.emotion_methods import retrieve_current_emotions
from agent_interaction.agents.agent import Agent

import threading
import os
import sqlite3
import time
from datetime import datetime

app = Flask(__name__)

DATABASE_PATH = "test_agents.db"

# 시나리오별로 DB에 삽입할 초기 데이터 정의
# (시나리오 번호 => dict 형태)

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

agent1 = Agent(name="Catarina", persona=agent1_persona, partner_name="Garen")
agent2 = Agent(name="Garen", persona=agent2_persona, partner_name="Catarina")
agent3 = Agent(name="agent_3", persona=agent3_persona, partner_name=None)
conversation_turn = 3
goal_turn = 10

scenarios = {
    1: {
        "description": f"{agent1.name} is behind on a school assignment, {agent2.name} already submitted.",
        "stm": [
            (f"{agent1.name}", "I have so much to do for the assignment, I'm freaking out!", 8),
            (f"{agent2.name}", f"I already finished and submitted mine. Let me help {agent1.name}.", 6),
        ],
        "ltm": [
            (f"{agent1.name}", "Had a last-minute success before, but also faced near-failure times.", 9, None),
            (f"{agent2.name}", "Knows effective study strategies under pressure.", 8, "strategy"),
        ],
        "conversations": [
            (1, f"{agent1.name}", "Hey, the assignment is due tomorrow. I'm still behind. Can you help me?"),
            (2, f"{agent2.name}", "Sure, what's your biggest struggle? I've already submitted mine."),
        ],
        "emotions": {
            f"{agent1.name}": {"joy": 1.0, "trust": 0.3, "fear": 0.5, "surprise": 0.1, "sadness": 0.2, "disgust": 0.1, "anger": 0.4, "anticipation": 0.2},
            f"{agent2.name}": {"joy": 1.0, "trust": 0.7, "fear": 0.1, "surprise": 0.2, "sadness": 0.2, "disgust": 0.0, "anger": 0.0, "anticipation": 0.5},
        },
    },
    2: {
        "description": f"{agent1.name} is dealing with an angry client, {agent2.name} helps calm them down.",
        "stm": [
            (f"{agent1.name}", "The client is furious about the delay in our project!", 7),
            (f"{agent2.name}", "We need to address their concerns calmly and quickly.", 5),
        ],
        "ltm": [
            (f"{agent1.name}", "Had experiences of losing a major client once, feels guilt and fear.", 8, "lesson"),
            (f"{agent2.name}", "Previously overcame angry stakeholders by rational explanation.", 8, None),
        ],
        "conversations": [
            (1, f"{agent1.name}", "I just got an angry call from the client. I'm panicking."),
            (2, f"{agent2.name}", "Take a deep breath. Let's figure out a calm approach."),
        ],
        "emotions": {
            f"{agent1.name}": {"joy": 1.0, "trust": 0.2, "fear": 0.6, "surprise": 0.3, "sadness": 0.2, "disgust": 0.2, "anger": 0.5, "anticipation": 0.3},
            f"{agent2.name}": {"joy": 1.0, "trust": 0.8, "fear": 0.2, "surprise": 0.1, "sadness": 0.2, "disgust": 0.0, "anger": 0.1, "anticipation": 0.6},
        },
    },
    3: {
        "description": f"{agent1.name} and {agent2.name} are working on a group project presentation tomorrow.",
        "stm": [
            (f"{agent1.name}", "I haven't finished my slides, I'm worried about speaking in public.", 6),
            (f"{agent2.name}", "I can help you design better slides. Public speaking tips are also crucial.", 7),
        ],
        "ltm": [
            (f"{agent1.name}", "Always had stage fright but overcame it once with practice.", 8, "lesson"),
            (f"{agent2.name}", "Confident in public speaking, loves structured outlines.", 9, None),
        ],
        "conversations": [
            (1, f"{agent1.name}", "Our presentation is tomorrow, and I'm still not ready."),
            (2, f"{agent2.name}", "Let me see your slides. We'll polish them together."),
        ],
        "emotions": {
            f"{agent1.name}": {"joy": 1.0, "trust": 0.4, "fear": 0.7, "surprise": 0.5, "sadness": 0.2, "disgust": 0.2, "anger": 0.3, "anticipation": 0.4},
            f"{agent2.name}": {"joy": 1.0, "trust": 0.8, "fear": 0.1, "surprise": 0.2, "sadness": 0.2, "disgust": 0.0, "anger": 0.0, "anticipation": 0.8},
        },
    },
}

#시나리오에 감정 지정 구현할 것


# 폴더명은 현재 시간
CURRENT_TIME_STR = datetime.now().strftime("%Y-%m-%d_%H%M%S")
SCENARIO_FOLDER = f"./results/manual_joy10_{CURRENT_TIME_STR}"
#SCENARIO_FOLDER = f"./results/manual_2024-12-27_053932"

def setup_database(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turn INTEGER,
        speaker TEXT,
        message TEXT
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS short_term_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        content TEXT NOT NULL,
        importance REAL NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS long_term_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        content TEXT NOT NULL,
        importance REAL NOT NULL,
        last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
        reflection_type TEXT
    );
    """)

    c.execute("""
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
    # Thought Process 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS thought_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            thought_process TEXT
        )
    ''')

    conn.commit()
    conn.close()

def populate_scenario(db_path, scenario_id, agent1, agent2):
    """
    DB에 scenario_id에 대응하는 시나리오를 삽입.
    agent1과 agent2의 이름을 동적으로 적용하고, 초기 감정 상태를 저장.
    """
    scenario = scenarios[scenario_id]
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Short-term Memory 삽입
    for stm in scenario["stm"]:
        agent_name, content, importance = stm
        c.execute("""
            INSERT INTO short_term_memory (agent_name, content, importance)
            VALUES (?, ?, ?)
        """, (agent_name, content, importance))

    # Long-term Memory 삽입
    for ltm in scenario["ltm"]:
        agent_name, content, importance, reflection_type = ltm
        c.execute("""
            INSERT INTO long_term_memory (agent_name, content, importance, reflection_type)
            VALUES (?, ?, ?, ?)
        """, (agent_name, content, importance, reflection_type))

    # Conversations 삽입
    for conv in scenario["conversations"]:
        turn, speaker, message = conv
        c.execute("""
            INSERT INTO conversations (turn, speaker, message)
            VALUES (?, ?, ?)
        """, (turn, speaker, message))

    # Emotion States 삽입
    for agent_name, emotions in scenario.get("emotions", {}).items():
        c.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            emotions.get("joy", 0.0),
            emotions.get("trust", 0.0),
            emotions.get("fear", 0.0),
            emotions.get("surprise", 0.0),
            emotions.get("sadness", 0.0),
            emotions.get("disgust", 0.0),
            emotions.get("anger", 0.0),
            emotions.get("anticipation", 0.0),
        ))

    conn.commit()
    conn.close()

##############################
# 백그라운드 스레드
##############################
# Background thread for memory management
def manage_agent_memories():
    while True:
        # Adjust memories and promote to long-term for agent1 and agent2
        manage_memories(DATABASE_PATH, agent1.name)
        manage_memories(DATABASE_PATH, agent2.name)
        time.sleep(10)  # Run every 60 seconds

#threading.Thread(target=manage_agent_memories, daemon=True).start()
#이거 각 시나리오 바뀔때마다 어떻게 처리할지 생각해보기

def generator():
    """
    GET: 시나리오 선택 폼만 표시 (아직 대화 없음)
    POST: 
      1) 사용자가 시나리오 ID 선택
      2) scenario_{id}.db 파일 존재 여부 확인
      3) 없으면 => setup_database + populate_scenario + 5턴 자동대화 => conversations 테이블 생성
      4) 있으면 => 이미 대화가 생성되었다고 가정 => conversations 테이블 로드
      5) chat 형식으로 로그 보여주기
    """
    for scenario_id in scenarios:
            scenario_data = scenarios.get(scenario_id)

            db_path = os.path.join(SCENARIO_FOLDER, f"scenario_{scenario_id}.db")
            if os.path.exists(db_path):
                continue
            # scenario_logs 초기화
            scenario_logs = []
            chosen_scenario = scenario_id

                # DB가 없으면 초기화 및 대화 생성
            setup_database(db_path)  # 테이블 생성 함수 호출
            populate_scenario(db_path, scenario_id, agent1.name, agent2.name)
            
            conversation_turn = 3
            message = f"Let's talk together.{scenario_data['description']}"
            
            #자동 대화
            for i in range(goal_turn):
                sender, receiver = (agent1, agent2) if i % 2 == 0 else (agent2, agent1)
                print(f"=== Turn {conversation_turn}: {sender.name} to {receiver.name} ===")
                print(f"Message: {message}\n")
                response, conversation_turn = agent_conversation(
                    db_path,
                    agent1=sender,
                    agent2=receiver,
                    message=message,
                    conversation_turn=conversation_turn
                )

                print(f"{receiver.name}'s Response:\n{response}\n")
                print(f"Updated conversation turn: {conversation_turn}\n")
                # Retrieve and print current emotions of the receiver as a demonstration of dramatic change
                receiver_emotions = retrieve_current_emotions(db_path, receiver.name)
                print(f"Current Emotions for {receiver.name}: {receiver_emotions}\n")
                print("-"*50)
                message = response


#################################
# 앱 실행: DB는 처음엔 안 건드림
#################################
if __name__ == '__main__':
    # 폴더 생성
    if not os.path.exists(SCENARIO_FOLDER):
        os.makedirs(SCENARIO_FOLDER)    
    generator()
    debug_log("생성 완료.")
    exit()
