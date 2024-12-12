import sqlite3
from datetime import datetime
import re
from utils.llm_connector import query_llm
import os
from textblob import TextBlob

# 데이터베이스 파일 경로
database_path = os.path.join("database", "memory_system.db")

# 데이터베이스 초기화
def init_memory_db():
    if not os.path.exists(os.path.dirname(database_path)):
        os.makedirs(os.path.dirname(database_path))
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Short-term memory 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            content TEXT,
            importance INTEGER
        )
    ''')

    # Long-term memory 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            importance INTEGER,
            last_accessed TEXT
        )
    ''')

    conn.commit()
    conn.close()


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

# 중요도 계산 함수
def calculate_importance(content, context, recency, frequency, sentiment):
    """
    Calculate importance based on multiple factors.
    Args:
        content (str): The memory content.
        context (str): Current conversation or context.
        recency (int): Time elapsed since the memory was created.
        frequency (int): How often the memory has been accessed or mentioned.
        sentiment (float): Sentiment analysis score (-1 to 1).

    Returns:
        int: Importance score (0 to 10).
    """
    w1, w2, w3, w4 = 0.4, 0.3, 0.2, 0.1  # Weights for each factor
    relevance = context_score(content, context)
    recency_score = max(0, 10 - recency // 10)  # Example: scale recency to 0-10
    frequency_score = min(10, frequency * 2)  # Example: scale frequency to 0-10
    sentiment_score = max(0, min(10, (sentiment + 1) * 5))  # Scale sentiment to 0-10

    return int(w1 * relevance + w2 * recency_score + w3 * frequency_score + w4 * sentiment_score)

def context_score(content, context):
    """
    Placeholder for context relevance scoring.
    """
    return 10 if content in context else 5

def analyze_sentiment(content):
    """
    Perform sentiment analysis on the memory content.
    Args:
        content (str): Text to analyze.

    Returns:
        float: Sentiment polarity (-1 to 1).
    """
    analysis = TextBlob(content)
    return analysis.sentiment.polarity

def add_to_short_term_memory(database_path, event, context):
    """
    Add a new memory to short-term memory, and calculate its importance.
    Args:
        database_path (str): Path to the SQLite database.
        event (dict): Memory content and metadata.
        context (str): Current conversation context.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Extract recency and frequency from database
    cursor.execute('SELECT COUNT(*) FROM short_term_memory WHERE content = ?', (event['content'],))
    frequency = cursor.fetchone()[0]

    recency = 0  # Placeholder: Add logic to calculate recency based on timestamp.

    sentiment = analyze_sentiment(event['content'])  # Example: Sentiment analysis
    importance = calculate_importance(event['content'], context, recency, frequency, sentiment)

    # Insert new memory into short-term memory
    cursor.execute('''
        INSERT INTO short_term_memory (timestamp, content, importance)
        VALUES (datetime('now'), ?, ?)
    ''', (event['content'], importance))
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

# 단기 기억 검색
def retrieve_from_short_term_memory():
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT content FROM short_term_memory ORDER BY timestamp DESC LIMIT 5
    ''')
    memories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return memories

# 단기 기억을 장기 기억으로 승격
def promote_to_long_term_memory(database_path):
    """
    Promote important memories from short-term to long-term memory.
    Args:
        database_path (str): Path to the SQLite database.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Find important memories in short-term memory
    cursor.execute('''
        SELECT id, content, importance FROM short_term_memory WHERE importance >= 7
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

# 장기 기억 검색
def retrieve_from_long_term_memory():
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT content FROM long_term_memory
        ORDER BY importance DESC, last_accessed DESC LIMIT 5
    ''')
    memories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return memories

from utils.llm_connector import query_llm

# 회상 생성
def generate_reflection():
    short_term = retrieve_from_short_term_memory()
    long_term = retrieve_from_long_term_memory()

    # LLM 프롬프트 생성
    prompt = (
        "Based on the following memories:\n\n"
        "Short-term memories:\n" + "\n".join(short_term) + "\n\n"
        "Long-term memories:\n" + "\n".join(long_term) + "\n\n"
        "Reflect on these memories and generate a summary or insight."
    )

    # LLM 호출
    try:
        reflection = query_llm(prompt)
        return reflection
    except RuntimeError as e:
        print(f"Reflection generation failed: {e}")
        return None

# 회상 저장
def store_reflection(reflection):
    if reflection:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO long_term_memory (content, importance, last_accessed)
            VALUES (?, ?, datetime('now'))
        ''', (reflection, 10))  # 회상의 중요도를 기본값 10으로 설정
        conn.commit()
        conn.close()


# 에이전트 대화 처리 (수정됨)
def agent_conversation(database_path, agent1, agent2, message, conversation_turn, context):
    """
    Handle agent conversation and manage memories.
    """
    memory_context = agent2.get_memory_context()
    reflection = agent2.reflect()
    prompt = (
        f"{agent1.name} (Persona: {agent1.persona}) says to {agent2.name}: '{message}'\n"
        f"Memory Context:\n{memory_context}\n"
        f"Reflection:\n{reflection}\n\n"
        f"Please respond to this message in the following format:\n"
        f"Thought process:\n[Provide your reasoning here.]\n\n"
        f"Speech:\n[Provide the exact words the agent will say in the conversation.]"
    )

    try:
        llm_response = query_llm(prompt)
        content = llm_response["choices"][0]["message"]["content"]
        speech, thought_process = parse_llm_response(content)

        add_to_short_term_memory(database_path, {"content": speech, "importance": 5}, context)
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

# 기억 자동 관리 함수
def manage_memories(database_path, new_event):
    """
    단기 기억 추가, 장기 기억 승격, 회상 저장을 자동으로 처리합니다.
    """
    try:
        # 단기 기억 추가
        add_to_short_term_memory(database_path, new_event)

        # 중요도가 높은 단기 기억을 장기 기억으로 승격
        promote_to_long_term_memory(database_path)

        # 현재 기억을 기반으로 회상 생성 및 저장
        reflection = generate_reflection(database_path)
        store_reflection(database_path, new_event.get("agent_name", "Unknown"), reflection)

    except Exception as e:
        print(f"Error in manage_memories: {e}")
        raise
