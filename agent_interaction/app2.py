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
        "description": "Scenario 1: Catarina is behind on a school assignment, Garen already submitted.",
        "stm": [
            # (agent_name, content, importance)
            ("agent_1", "I have so much to do for the assignment, I'm freaking out!", 8),
            ("agent_2", "I already finished and submitted mine. Let me help agent1.", 6),
        ],
        "ltm": [
            # (agent_name, content, importance, reflection_type)
            ("agent_1", "Had a last-minute success before, but also faced near-failure times.", 9, None),
            ("agent_2", "Knows effective study strategies under pressure.", 8, "strategy"),
        ],
        "conversations": [
            # (turn, speaker, message)
            (1, "agent_1", "Hey, the assignment is due tomorrow. I'm still behind. Can you help me?"),
            (2, "agent_2", "Sure, what's your biggest struggle? I've already submitted mine."),
        ],
    },
    2: {
        "description": "Scenario 2: Catarina is dealing with an angry client, Garen helps calm them down.",
        "stm": [
            ("agent_1", "The client is furious about the delay in our project!", 7),
            ("agent_2", "We need to address their concerns calmly and quickly.", 5),
        ],
        "ltm": [
            ("agent_1", "Had experiences of losing a major client once, feels guilt and fear.", 8, "lesson"),
            ("agent_2", "Previously overcame angry stakeholders by rational explanation.", 8, None),
        ],
        "conversations": [
            (1, "agent_1", "I just got an angry call from the client. I'm panicking."),
            (2, "agent_2", "Take a deep breath. Let's figure out a calm approach."),
        ],
    },
    # 원하는 만큼 추가 시나리오...
    3: {
        "description": "Scenario 3: Catarina and Garen are working on a group project presentation tomorrow.",
        "stm": [
            ("agent_1", "I haven't finished my slides, I'm worried about speaking in public.", 6),
            ("agent_2", "I can help you design better slides. Public speaking tips are also crucial.", 7),
        ],
        "ltm": [
            ("agent_1", "Always had stage fright but overcame it once with practice.", 8, "lesson"),
            ("agent_2", "Confident in public speaking, loves structured outlines.", 9, None),
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

agent1 = Agent(name="Catarina", persona=agent1_persona, partner_name="Garen")
agent2 = Agent(name="Garen", persona=agent2_persona, partner_name="Catarina")
agent3 = Agent(name="agent_3", persona=agent3_persona, partner_name=None)
conversation_turn = 3

# 폴더명은 현재 시간
CURRENT_TIME_STR = datetime.now().strftime("%Y-%m-%d_%H%M%S")
#SCENARIO_FOLDER = f"./results/runs_{CURRENT_TIME_STR}"
SCENARIO_FOLDER = f"./results/runs_2024-12-26_231056"

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

def populate_scenario(db_path, scenario_id,agent1_name, agent2_name):
    """
    DB에 scenario_id에 대응하는 시나리오를 삽입
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
    
    # Emotion States 삽입 (초기값 0.0으로 설정)
    for agent_name in [agent1_name, agent2_name]:
        c.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    
    # Thought Processes 삽입 (초기 데이터가 있다면 삽입)
    for ltm in scenario["ltm"]:
        agent_name, content, importance, reflection_type = ltm
        if reflection_type:
            thought = f"{reflection_type.capitalize()} Reflection: {content}"
            c.execute("""
                INSERT INTO thought_processes (agent_name, thought_process)
                VALUES (?, ?)
            """, (agent_name, thought))
    
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
    GET: 시나리오 선택 폼만 표시 (아직 대화 없음)
    POST: 
      1) 사용자가 시나리오 ID 선택
      2) scenario_{id}.db 파일 존재 여부 확인
      3) 없으면 => setup_database + populate_scenario + 5턴 자동대화 => conversations 테이블 생성
      4) 있으면 => 이미 대화가 생성되었다고 가정 => conversations 테이블 로드
      5) chat 형식으로 로그 보여주기
    """
    if request.method == 'GET':
        # 시나리오 목록 보여주기 (대화 로그 없음)
        return render_template('auto_conversation.html', scenarios=scenarios, scenario_logs=None, chosen_scenario=None, db_filename=None)
    
    else:
        # POST: 시나리오 선택 후 대화 생성 또는 로드
        try:
            scenario_id = int(request.form.get('scenario_id'))
            scenario_data = scenarios.get(scenario_id)
            if not scenario_data:
                return "Unvalid Scenario ID", 400
            
            db_path = os.path.join(SCENARIO_FOLDER, f"scenario_{scenario_id}.db")
            db_filename = f"scenario_{scenario_id}.db"
            
            # scenario_logs 초기화
            scenario_logs = []
            chosen_scenario = scenario_id
            
            if not os.path.exists(db_path):
                # DB가 없으면 초기화 및 대화 생성
                setup_database(db_path)  # 테이블 생성 함수 호출
                populate_scenario(db_path, scenario_id, agent1.name, agent2.name)
                
                conversation_turn = 3
                message = f"시나리오 {scenario_id} 시작. {scenario_data['description']}"
                
                # 20턴 자동 대화
                for i in range(20):
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
                    receiver_emotions = retrieve_current_emotions(DATABASE_PATH, receiver.name)
                    print(f"Current Emotions for {receiver.name}: {receiver_emotions}\n")
                    print("-"*50)
                    message = response

            # 4) DB에서 대화 기록 조회 (좌/우 표시)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
            WITH ranked_conversations AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY turn ORDER BY id ASC) AS row_num
                FROM conversations
            )
            SELECT turn, speaker, message
            FROM ranked_conversations
            WHERE row_num = 2
            ORDER BY turn ASC;
            """)
            rows = c.fetchall()
            conn.close()

            # 한 턴당 2행(메시지, 응답)이라고 가정
            # DM 채팅 스타일로, speaker=agent_1 => 왼쪽, speaker=agent_2 => 오른쪽
            for (turn_num, spk, msg) in rows:
                scenario_logs.append({
                    "turn": turn_num,
                    "speaker": spk,
                    "message": msg
                })

            # 렌더링
            return render_template('auto_conversation.html',
                                scenarios=scenarios,
                                scenario_logs=scenario_logs,
                                chosen_scenario=chosen_scenario,
                                agent1_name=agent1.name,  # 추가
                                agent2_name=agent2.name 
                                )
        except Exception as e:
            return f"오류가 발생했습니다: {str(e)}", 500

@app.route('/memory_view', methods=['GET','POST'])
def memory_view_page():
    """
    메모리 뷰 페이지에서 agent1, agent2의 모든 STM, LTM, Emotion, 그리고 Thought Process를
    시나리오를 기준으로 한 번에 2등분하여 각각 표시.
    감정 히스토리를 포함한 시각화 데이터 생성
    """
    if request.method == 'GET':
        return render_template(
            'memory_view.html',
            scenarios=scenarios,
            data_agent1=None,
            data_agent2=None,
            chosen_scenario=None,
            agent1_name=agent1.name,
            agent2_name=agent2.name,
            agent1_emotion_history=None,
            agent2_emotion_history=None
        )
    else:
        try:
            # 시나리오 선택 및 DB 경로 설정
            scenario_id = int(request.form.get('scenario_id'))
            scenario_data = scenarios.get(scenario_id)
            if not scenario_data:
                return "유효하지 않은 시나리오 ID입니다.", 400

            db_path = os.path.join(SCENARIO_FOLDER, f"scenario_{scenario_id}.db")
            chosen_scenario = scenario_id

            # 데이터 저장용 딕셔너리
            data_agent1 = {
                "short_term_memories": [],
                "long_term_memories": [],
                "emotions": {},
                "thought_processes": []
            }
            data_agent2 = {
                "short_term_memories": [],
                "long_term_memories": [],
                "emotions": {},
                "thought_processes": []
            }
            agent1_emotion_history = []
            agent2_emotion_history = []

            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    c = conn.cursor()

                    # Agent1 데이터
                    c.execute("""
                        SELECT content, importance
                        FROM short_term_memory
                        WHERE agent_name=?
                        ORDER BY timestamp DESC
                    """, (agent1.name,))
                    data_agent1["short_term_memories"] = c.fetchall()

                    c.execute("""
                        SELECT content, importance, reflection_type
                        FROM long_term_memory
                        WHERE agent_name=?
                        ORDER BY importance DESC
                    """, (agent1.name,))
                    data_agent1["long_term_memories"] = c.fetchall()

                    data_agent1["emotions"] = retrieve_current_emotions(db_path, agent1.name)

                    c.execute("""
                        SELECT thought_process
                        FROM thought_processes
                        WHERE agent_name=?
                        ORDER BY id ASC
                    """, (agent1.name,))
                    thoughts1 = c.fetchall()
                    data_agent1["thought_processes"] = [t[0] for t in thoughts1]

                    c.execute("""
                        SELECT timestamp, joy, trust, fear, surprise, sadness, disgust, anger, anticipation
                        FROM emotion_states
                        WHERE agent_name=?
                        ORDER BY timestamp ASC
                    """, (agent1.name,))
                    agent1_emotion_history = c.fetchall()

                    # Agent2 데이터
                    c.execute("""
                        SELECT content, importance
                        FROM short_term_memory
                        WHERE agent_name=?
                        ORDER BY timestamp DESC
                    """, (agent2.name,))
                    data_agent2["short_term_memories"] = c.fetchall()

                    c.execute("""
                        SELECT content, importance, reflection_type
                        FROM long_term_memory
                        WHERE agent_name=?
                        ORDER BY importance DESC
                    """, (agent2.name,))
                    data_agent2["long_term_memories"] = c.fetchall()

                    data_agent2["emotions"] = retrieve_current_emotions(db_path, agent2.name)

                    c.execute("""
                        SELECT thought_process
                        FROM thought_processes
                        WHERE agent_name=?
                        ORDER BY id ASC
                    """, (agent2.name,))
                    thoughts2 = c.fetchall()
                    data_agent2["thought_processes"] = [t[0] for t in thoughts2]

                    c.execute("""
                        SELECT timestamp, joy, trust, fear, surprise, sadness, disgust, anger, anticipation
                        FROM emotion_states
                        WHERE agent_name=?
                        ORDER BY timestamp ASC
                    """, (agent2.name,))
                    agent2_emotion_history = c.fetchall()

            return render_template(
                'memory_view.html',
                scenarios=scenarios,
                data_agent1=data_agent1,
                data_agent2=data_agent2,
                chosen_scenario=chosen_scenario,
                agent1_name=agent1.name,
                agent2_name=agent2.name,
                agent1_emotion_history=agent1_emotion_history,
                agent2_emotion_history=agent2_emotion_history
            )
        except Exception as e:
            return f"오류가 발생했습니다: {str(e)}", 500


@app.route('/manual_chat', methods=['GET'])
def manual_chat():
    return render_template('manual_chat.html')

@app.route('/memory_view/<agent_name>', methods=['GET'])
def memory_view(agent_name):
    try:
        # 모든 시나리오 DB에서 해당 에이전트의 메모리와 감정 상태를 가져옴
        all_short_term_memories = []
        all_long_term_memories = []
        all_emotions = {}
        
        for scenario_id in scenarios.keys():
            db_path = os.path.join(SCENARIO_FOLDER, f"scenario_{scenario_id}.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                
                # Short-term memories
                c.execute("""
                    SELECT content, importance
                    FROM short_term_memory
                    WHERE agent_name = ?
                    ORDER BY timestamp DESC
                """, (agent_name,))
                short_term = c.fetchall()
                all_short_term_memories.extend(short_term)
                
                # Long-term memories
                c.execute("""
                    SELECT content, importance
                    FROM long_term_memory
                    WHERE agent_name = ?
                    ORDER BY importance DESC
                """, (agent_name,))
                long_term = c.fetchall()
                all_long_term_memories.extend(long_term)
                
                # Emotions
                emotions = retrieve_current_emotions(db_path, agent_name)
                all_emotions[scenario_id] = emotions
                
                conn.close()
        
        return render_template(
            'memory_view.html',
            agent_name=agent_name,
            short_term_memories=all_short_term_memories,
            long_term_memories=all_long_term_memories,
            emotions=all_emotions
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
