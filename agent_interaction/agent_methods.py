import sqlite3
from datetime import datetime
import re
from utils.llm_connector import query_llm

# 데이터베이스에 메시지를 저장하는 함수
def save_message_to_db(database_path, turn, speaker, message):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (turn, speaker, message) VALUES (?, ?, ?)
    ''', (turn, speaker, message))
    conn.commit()
    conn.close()

# LLM 응답 파싱 함수
def parse_llm_response(content):
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

# 단기 기억에 추가
def add_to_short_term_memory(database_path, event):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO short_term_memory (timestamp, content, importance)
        VALUES (datetime('now'), ?, ?)
    ''', (event['content'], event['importance']))
    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM short_term_memory')
    count = cursor.fetchone()[0]

    MAX_SHORT_TERM_MEMORY = 10
    if count > MAX_SHORT_TERM_MEMORY:
        cursor.execute('''
            DELETE FROM short_term_memory WHERE id = (
                SELECT id FROM short_term_memory ORDER BY timestamp ASC LIMIT 1
            )
        ''')
        conn.commit()
    conn.close()

# 장기 기억으로 승격
def promote_to_long_term_memory(database_path):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, content, importance FROM short_term_memory WHERE importance > 7
    ''')
    important_memories = cursor.fetchall()

    for memory in important_memories:
        memory_id, content, importance = memory
        cursor.execute('''
            INSERT INTO long_term_memory (content, importance, last_accessed)
            VALUES (?, ?, datetime('now'))
        ''', (content, importance))
        cursor.execute('DELETE FROM short_term_memory WHERE id = ?', (memory_id,))
    conn.commit()
    conn.close()

# 에이전트 대화 처리
def agent_conversation(database_path, agent1, agent2, message, conversation_turn):
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
        llm_response = query_llm(prompt)
        print("DEBUG: llm_response in agent_conversation:", llm_response)

        if not isinstance(llm_response, dict) or "choices" not in llm_response:
            raise ValueError("Invalid LLM response format.")

        content = llm_response["choices"][0]["message"]["content"]

        speech, thought_process = parse_llm_response(content)

        add_to_short_term_memory(database_path, {"content": speech, "importance": 5})
        promote_to_long_term_memory(database_path)

        save_message_to_db(database_path, conversation_turn, agent1.name, message)
        conversation_turn += 1
        save_message_to_db(database_path, conversation_turn, agent2.name, speech)
        conversation_turn += 1

        return speech, conversation_turn

    except Exception as e:
        print(f"Error in agent_conversation: {e}")
        save_message_to_db(database_path, conversation_turn, "Error", str(e))
        conversation_turn += 1
        raise
