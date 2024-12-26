from flask import Flask, render_template, jsonify, request
from utils.memo import agent_conversation
from utils.memory_management import manage_memories
from utils.emotion_methods import retrieve_current_emotions
from agents.agent import Agent

import threading
import os
import sqlite3
import time
from datetime import datetime

app = Flask(__name__)

DATABASE_PATH = "test_agents.db"

# 시나리오별로 DB에 삽입할 초기 데이터 정의
# (시나리오 번호 => dict 형태)
scenarios = {
    1: {
        "description": "Scenario 1: Agent1 is behind on a school assignment, Agent2 already submitted.",
        "stm": [
            # (agent_name, content, importance)
            ("agent_1", "I have so much to do for the assignment, I'm freaking out!", 0.8),
            ("agent_2", "I already finished and submitted mine. Let me help agent1.", 0.6),
        ],
        "ltm": [
            # (agent_name, content, importance, reflection_type)
            ("agent_1", "Had a last-minute success before, but also faced near-failure times.", 0.9, None),
            ("agent_2", "Knows effective study strategies under pressure.", 0.8, "strategy"),
        ],
        "conversations": [
            # (turn, speaker, message)
            (1, "agent_1", "Hey, the assignment is due tomorrow. I'm still behind. Can you help me?"),
            (2, "agent_2", "Sure, what's your biggest struggle? I've already submitted mine."),
        ],
    },
    2: {
        "description": "Scenario 2: Agent1 is dealing with an angry client, Agent2 helps calm them down.",
        "stm": [
            ("agent_1", "The client is furious about the delay in our project!", 0.7),
            ("agent_2", "We need to address their concerns calmly and quickly.", 0.5),
        ],
        "ltm": [
            ("agent_1", "Had experiences of losing a major client once, feels guilt and fear.", 0.85, "lesson"),
            ("agent_2", "Previously overcame angry stakeholders by rational explanation.", 0.8, None),
        ],
        "conversations": [
            (1, "agent_1", "I just got an angry call from the client. I'm panicking."),
            (2, "agent_2", "Take a deep breath. Let's figure out a calm approach."),
        ],
    },
    # 원하는 만큼 추가 시나리오...
    3: {
        "description": "Scenario 3: Agent1 and Agent2 are working on a group project presentation tomorrow.",
        "stm": [
            ("agent_1", "I haven't finished my slides, I'm worried about speaking in public.", 0.6),
            ("agent_2", "I can help you design better slides. Public speaking tips are also crucial.", 0.7),
        ],
        "ltm": [
            ("agent_1", "Always had stage fright but overcame it once with practice.", 0.8, "lesson"),
            ("agent_2", "Confident in public speaking, loves structured outlines.", 0.9, None),
        ],
        "conversations": [
            (1, "agent_1", "Our presentation is tomorrow, and I'm still not ready."),
            (2, "agent_2", "Let me see your slides. We'll polish them together."),
        ]
    },
}

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

agent1 = Agent(name="Catarina", persona=agent1_persona, partner_name="agent_2")
agent2 = Agent(name="Garen", persona=agent2_persona, partner_name="agent_1")
agent3 = Agent(name="agent_3", persona=agent3_persona, partner_name=None)
conversation_turn = 1

# 폴더명은 현재 시간
CURRENT_TIME_STR = datetime.now().strftime("%Y-%m-%d_%H%M%S")
SCENARIO_FOLDER = f"./runs_{CURRENT_TIME_STR}"

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

def populate_scenario(db_path, scenario_id):
    """
    DB에 scenario_id에 대응하는 시나리오를 삽입
    """
    scenario = scenarios[scenario_id]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1) 감정 상태 (0.0)
    for agent_n in [agent1.name, agent2.name]:
        cursor.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_n, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # 2) short_term_memory
    for (agent_name, content, importance) in scenario["stm"]:
        cursor.execute("""
            INSERT INTO short_term_memory (agent_name, content, importance)
            VALUES (?, ?, ?)
        """, (agent_name, content, importance))

    # 3) long_term_memory
    for (agent_name, content, importance, reflection_type) in scenario["ltm"]:
        cursor.execute("""
            INSERT INTO long_term_memory (agent_name, content, importance, reflection_type)
            VALUES (?, ?, ?, ?)
        """, (agent_name, content, importance, reflection_type))

    # 4) conversations
    for (turn, speaker, message) in scenario["conversations"]:
        cursor.execute("""
            INSERT INTO conversations (turn, speaker, message)
            VALUES (?, ?, ?)
        """, (turn, speaker, message))

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

##############################
# Flask Routes
##############################

@app.route('/')
def home():
    return render_template('home.html')

##############################################
# GET /auto_conversation -> 시나리오 목록 + Generate 버튼
# POST /auto_conversation -> 시나리오 자동대화 실행 + 결과 표시
##############################################
@app.route('/auto_conversation', methods=['GET', 'POST'])
def auto_conversation_page():
    """
    - GET: 시나리오 목록을 보여주고, 'Generate' 버튼
    - POST: 시나리오ID 받아서 DB 초기화 + populate + 자동 대화 => 결과 로그
    """
    if request.method == 'GET':
        # 시나리오 목록만 보여주고, 아직 대화 생성 안 함
        return render_template('auto_conversation.html', scenario_results=None, scenarios=scenarios)

    else:  # POST
        scenario_id = int(request.form['scenario_id'])
        scenario_data = scenarios[scenario_id]

        
        db_path = os.path.join(SCENARIO_FOLDER, f"scenario_{scenario_id}.db")
        
        # DB 초기화
        if os.path.exists(db_path):
            os.remove(db_path)
        setup_database(db_path)
        populate_scenario(db_path, scenario_id)

        conversation_turn = 1
        scenario_log = []
        message = f"(Scenario {scenario_id}) Start conversation. {scenario_data['description']}"

        for i in range(10):
            sender, receiver = (agent1, agent2) if i % 2 == 0 else (agent2, agent1)
            print(f"=== Turn {conversation_turn}: {sender.name} to {receiver.name} ===")
            print(f"Message: {message}\n")
            response, conversation_turn = agent_conversation(
                db_path,  # 이 시나리오의 DB
                agent1=sender,
                agent2=receiver,
                message=message,
                conversation_turn=conversation_turn
            )
            scenario_log.append({
                "turn": conversation_turn,
                "sender": sender.name,
                "receiver": receiver.name,
                "message": message,
                "response": response
            })
            message = response
            print(f"{receiver.name}'s Response:\n{response}\n")
            print(f"Updated conversation turn: {conversation_turn}\n")
        
            # Retrieve and print current emotions of the receiver as a demonstration of dramatic change
            receiver_emotions = retrieve_current_emotions(DATABASE_PATH, receiver.name)
            print(f"Current Emotions for {receiver.name}: {receiver_emotions}\n")
            print("-"*50)

        # scenario_results에 한 개의 시나리오 대화 로그만 담음
        scenario_results = [{
            "scenario_id": scenario_id,
            "description": scenario_data['description'],
            "db_path": db_path,
            "logs": scenario_log
        }]

        # 렌더링
        return render_template('auto_conversation.html', scenario_results=scenario_results, scenarios=scenarios)

        #return jsonify(results)

@app.route('/manual_chat', methods=['GET'])
def manual_chat():
    return render_template('manual_chat.html')

@app.route('/memory_view/<agent_name>', methods=['GET'])
def memory_view(agent_name):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, importance
            FROM short_term_memory
            WHERE agent_name = ?
            ORDER BY timestamp DESC
        """, (agent_name,))
        short_term_memories = cursor.fetchall()

        cursor.execute("""
            SELECT content, importance
            FROM long_term_memory
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

#################################
# 앱 실행: DB는 처음엔 안 건드림
#################################
if __name__ == '__main__':
    # 폴더 생성
    if not os.path.exists(SCENARIO_FOLDER):
        os.makedirs(SCENARIO_FOLDER)    
    app.run(debug=True)
