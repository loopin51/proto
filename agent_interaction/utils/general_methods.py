import sqlite3
from datetime import datetime
import re
from .llm_connector import query_llm
import os
from sentence_transformers import SentenceTransformer, util
from .prompt_templates import *
from .importance_scoring import *
from .memory_management import *

model = SentenceTransformer('all-MiniLM-L6-v2') #model used for context similarity calculation

# 데이터베이스 파일 경로 생성 함수
def get_database_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("database", f"memory_system_{timestamp}.db")

# 전역 데이터베이스 경로
database_path = None

def set_database_path(path):
    global database_path
    database_path = path

# 데이터베이스 초기화
def init_memory_db():
    if not os.path.exists(os.path.dirname(database_path)):
        os.makedirs(os.path.dirname(database_path))
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # LTM 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            content TEXT,
            importance INTEGER,
            last_accessed TEXT,
            reflection_type TEXT,
            reference_count INTEGER DEFAULT 0
        )
    ''')

    # STM 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            timestamp TEXT,
            content TEXT,
            importance INTEGER,
            reference_count INTEGER DEFAULT 0
        )
    ''')

    # 대화 기록 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        )
    ''')

    # Thought Process 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thought_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            thought_process TEXT
        )
    ''')

    conn.commit()
    conn.close()

#프리셋 DB 데이터를 복사하는 함수
def copy_preset_to_new_db(preset_db_path, database_path):
    """
    Copies data from the preset database to the new database.
    Ensures table structures match before copying data.

    Args:
        preset_db_path (str): Path to the preset database.
        database_path (str): Path to the new database.
    """
    preset_conn = sqlite3.connect(preset_db_path)
    new_conn = sqlite3.connect(database_path)

    preset_cursor = preset_conn.cursor()
    new_cursor = new_conn.cursor()

    # Tables to copy
    tables = ["long_term_memory", "short_term_memory", "conversations", "thought_processes"]

    for table in tables:
        # Fetch the schema from the preset database
        preset_cursor.execute(f"PRAGMA table_info({table})")
        preset_columns = [info[1] for info in preset_cursor.fetchall()]

        # Fetch data from the preset database
        preset_cursor.execute(f"SELECT * FROM {table}")
        rows = preset_cursor.fetchall()

        # Adjust data to match the target table's schema
        new_cursor.execute(f"PRAGMA table_info({table})")
        new_columns = [info[1] for info in new_cursor.fetchall()]

        # Map only matching columns
        matching_columns = [col for col in preset_columns if col in new_columns]
        placeholders = ", ".join("?" for _ in matching_columns)
        columns_to_copy = ", ".join(matching_columns)

        # Insert data into the new database
        for row in rows:
            # Match values to the target table columns
            mapped_row = tuple(row[preset_columns.index(col)] for col in matching_columns)
            new_cursor.execute(f"INSERT INTO {table} ({columns_to_copy}) VALUES ({placeholders})", mapped_row)

    preset_conn.close()
    new_conn.commit()
    new_conn.close()
    print(f"Data from {preset_db_path} has been copied to {database_path}")

# Initialize memory database with preset data
def init_db_with_preset(database_path):
    # Preset database path
    preset_db_path = os.path.join(os.path.dirname(__file__), "../preset_memory.db")
    # Create a new database and copy preset data
    init_memory_db()
    copy_preset_to_new_db(preset_db_path, database_path)

    return database_path


# LLM 응답 파싱 함수
def parse_llm_response(content):
    """
    Parse the LLM's response content into Thought Process and Speech.
    """
    thought_process = "No thought process provided."
    speech = "No speech provided."

    try:
        content = re.sub(r"^(Response:|.*?responds:\n)", "", content, flags=re.IGNORECASE).strip()

        # Extract Thought Process
        thought_match = re.search(r"Thought process:\s*(.*?)\n\n", content, re.DOTALL)
        if thought_match:
            thought_process = thought_match.group(1).strip()

        # Extract Speech
        speech_match = re.search(r"Speech:\s*(.+)", content, re.DOTALL)
        if speech_match:
            speech = speech_match.group(1).strip()

    except Exception as e:
        print(f"Error parsing LLM response content: {e}")

    return speech, thought_process

# 에이전트 대화 처리 (수정됨)
def agent_conversation(database_path, agent1, agent2, message, conversation_turn, context=None):
    """
    Handle agent conversation and manage memories, incorporating all reflection types.

    Args:
        database_path (str): Path to the SQLite database.
        agent1 (Agent): The agent initiating the conversation.
        agent2 (Agent): The agent responding to the conversation.
        message (str): The message from agent1 to agent2.
        conversation_turn (int): The current turn in the conversation.
        context (dict): Context containing short-term and long-term memories for the conversation.

    Returns:
        str: The response speech from agent2.
        int: Updated conversation turn.
    """
    debug_log(f"{agent1.name} is talking to {agent2.name} with message: {message}. Conversation turn: {conversation_turn}")

    if context is None:
        # Retrieve context if not provided
        context = generate_context(database_path, agent2.name)

    memory_context = agent2.get_memory_context(database_path)

    reflections = retrieve_reflections_from_db(database_path, agent2.name)

    # Construct the prompt with all reflection types
    prompt = conversation_prompt(
        agent1.name, agent1.persona, agent2.name, message, memory_context, reflections
    )    

    try:
        # Send the prompt to the LLM
        llm_response = query_llm(prompt)

        if not isinstance(llm_response, dict) or "choices" not in llm_response:
            raise ValueError("Invalid LLM response format.")

        # Extract content from the LLM response
        content = llm_response["choices"][0]["message"]["content"]
        speech, thought_process = parse_llm_response(content) #thought_process는 사용하지 않음?

        debug_log(f"{agent2.name} answered : {speech}")

        add_to_short_term_memory(database_path, {"content": speech, "agent_name": agent2.name}, context) #agent2.name을 전달하는게 맞나?
        promote_to_long_term_memory(database_path, agent2.name)

        # Save the messages in the database
        save_message_to_db(database_path, conversation_turn, agent1.name, message)
        conversation_turn += 1
        save_message_to_db(database_path, conversation_turn, agent2.name, speech)
        conversation_turn += 1

        # Save the thought process associated with agent2's response
        save_thought_process_to_db(database_path, agent2.name, thought_process)

        return speech, conversation_turn

    except Exception as e:
        print(f"Error in agent_conversation: {e}")
        save_message_to_db(database_path, conversation_turn, "Error", str(e))
        conversation_turn += 1
        raise

import pandas as pd

def load_scenarios_from_excel(excel_path):
    """
    엑셀 파일에서 여러 시트를 읽어와, 시나리오 딕셔너리를 구성해 반환.

    시트 예:
      - scenario_list: columns=[scenario_id, description]
      - stm: columns=[scenario_id, agent_name, content, importance]
      - ltm: columns=[scenario_id, agent_name, content, importance, reflection_type]
      - conversations: columns=[scenario_id, turn, speaker, message]
      - emotions: columns=[scenario_id, agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation]

    Returns:
        dict: {
            scenario_id: {
                "description": str,
                "stm": [(agent_name, content, importance), ...],
                "ltm": [(agent_name, content, importance, reflection_type), ...],
                "conversations": [(turn, speaker, message), ...],
                "emotions": {
                    agent_name: {
                        "joy": float, "trust": float, ...
                    }, ...
                }
            },
            ...
        }
    """

    # 1) 각 시트를 DataFrame으로 읽어옴
    df_scenario_list = pd.read_excel(excel_path, sheet_name="scenario_list")
    df_stm = pd.read_excel(excel_path, sheet_name="stm")
    df_ltm = pd.read_excel(excel_path, sheet_name="ltm")
    df_conv = pd.read_excel(excel_path, sheet_name="conversations")
    df_emo = pd.read_excel(excel_path, sheet_name="emotions")

    # 2) 시나리오 딕셔너리 골격
    scenarios_dict = {}

    # 2-A) 시나리오 리스트
    for _, row in df_scenario_list.iterrows():
        sid = int(row["scenario_id"])
        desc = row["description"]
        scenarios_dict[sid] = {
            "description": desc,
            "stm": [],
            "ltm": [],
            "conversations": [],
            "emotions": {}
        }

    # 2-B) STM
    for _, row in df_stm.iterrows():
        sid = int(row["scenario_id"])
        agent_name = row["agent_name"]
        content = row["content"]
        importance = float(row["importance"])
        if sid not in scenarios_dict:
            # 시나리오가 scenario_list에 없을 수도 있으니
            scenarios_dict[sid] = {
                "description": "",
                "stm": [],
                "ltm": [],
                "conversations": [],
                "emotions": {}
            }
        scenarios_dict[sid]["stm"].append((agent_name, content, importance))

    # 2-C) LTM
    for _, row in df_ltm.iterrows():
        sid = int(row["scenario_id"])
        agent_name = row["agent_name"]
        content = row["content"]
        importance = float(row["importance"])
        reflection_type = row.get("reflection_type", None)
        if sid not in scenarios_dict:
            scenarios_dict[sid] = {
                "description": "",
                "stm": [],
                "ltm": [],
                "conversations": [],
                "emotions": {}
            }
        scenarios_dict[sid]["ltm"].append(
            (agent_name, content, importance, reflection_type)
        )

    # 2-D) Conversations
    for _, row in df_conv.iterrows():
        sid = int(row["scenario_id"])
        turn = int(row["turn"])
        speaker = row["speaker"]
        message = row["message"]
        if sid not in scenarios_dict:
            scenarios_dict[sid] = {
                "description": "",
                "stm": [],
                "ltm": [],
                "conversations": [],
                "emotions": {}
            }
        scenarios_dict[sid]["conversations"].append(
            (turn, speaker, message)
        )

    # 2-E) Emotions
    # agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation
    for _, row in df_emo.iterrows():
        sid = int(row["scenario_id"])
        agent_name = row["agent_name"]
        joy = float(row["joy"])
        trust = float(row["trust"])
        fear = float(row["fear"])
        surprise = float(row["surprise"])
        sadness = float(row["sadness"])
        disgust = float(row["disgust"])
        anger = float(row["anger"])
        anticipation = float(row["anticipation"])

        if sid not in scenarios_dict:
            scenarios_dict[sid] = {
                "description": "",
                "stm": [],
                "ltm": [],
                "conversations": [],
                "emotions": {}
            }
        if agent_name not in scenarios_dict[sid]["emotions"]:
            scenarios_dict[sid]["emotions"][agent_name] = {}

        scenarios_dict[sid]["emotions"][agent_name] = {
            "joy": joy,
            "trust": trust,
            "fear": fear,
            "surprise": surprise,
            "sadness": sadness,
            "disgust": disgust,
            "anger": anger,
            "anticipation": anticipation
        }

    return scenarios_dict
