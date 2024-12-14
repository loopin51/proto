import sqlite3
from datetime import datetime
import re
from utils.llm_connector import query_llm
import os
from textblob import TextBlob

# 데이터베이스 파일 경로 생성 함수
def get_database_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_path = os.path.join("database", f"memory_system_{timestamp}.db")
    return db_path

# 전역 데이터베이스 경로
database_path = get_database_path()

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
            agent_name TEXT,
            timestamp TEXT,
            content TEXT,
            importance INTEGER
        )
    ''')

    # Long-term memory 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            content TEXT,
            importance INTEGER,
            last_accessed TEXT
        )
    ''')

    # Conversations 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        )
    ''')

    # Thought processes 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thought_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            thought_process TEXT
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

def retrieve_from_short_term_memory(database_path, agent_name):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT content FROM short_term_memory 
        WHERE agent_name = ? 
        ORDER BY timestamp DESC LIMIT 5
    ''', (agent_name,))
    memories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return memories

# 단기 기억을 장기 기억으로 승격
def promote_to_long_term_memory(database_path, agent_name):
    """
    Promote important memories from short-term to long-term memory for a specific agent.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): The name of the agent whose memories are being managed.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    try:
        # Find important memories in short-term memory for the specified agent
        cursor.execute('''
            SELECT id, content, importance FROM short_term_memory
            WHERE importance >= 7 AND agent_name = ?
        ''', (agent_name,))
        important_memories = cursor.fetchall()

        # Move each important memory to long-term memory
        for memory in important_memories:
            memory_id, content, importance = memory
            cursor.execute('''
                INSERT INTO long_term_memory (agent_name, content, importance, last_accessed)
                VALUES (?, ?, ?, datetime('now'))
            ''', (agent_name, content, importance))
            cursor.execute('DELETE FROM short_term_memory WHERE id = ?', (memory_id,))

        conn.commit()

    except Exception as e:
        print(f"Error in promote_to_long_term_memory for agent '{agent_name}': {e}")

    finally:
        conn.close()


# 장기 기억 검색
def retrieve_from_long_term_memory(database_path, agent_name):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT content FROM long_term_memory 
        WHERE agent_name = ? 
        ORDER BY importance DESC, last_accessed DESC LIMIT 5
    ''', (agent_name,))
    memories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return memories

# Retrieve context for reflection
def retrieve_context_for_reflection(database_path, agent_name):
    """
    Retrieve short-term and long-term memories for a specific agent to create a reflection context.
    
    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose memories are to be retrieved.
    
    Returns:
        dict: A dictionary containing short-term and long-term memories.
    """
    if not isinstance(database_path, str):
        raise TypeError(f"Expected database_path to be a string, got {type(database_path).__name__}")

    try:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()

        # Retrieve short-term memories
        cursor.execute('''
            SELECT content FROM short_term_memory 
            WHERE agent_name = ? 
            ORDER BY timestamp DESC LIMIT 5
        ''', (agent_name,))
        short_term_memories = [row[0] for row in cursor.fetchall()]

        # Retrieve long-term memories
        cursor.execute('''
            SELECT content FROM long_term_memory 
            WHERE agent_name = ? 
            ORDER BY importance DESC, last_accessed DESC LIMIT 5
        ''', (agent_name,))
        long_term_memories = [row[0] for row in cursor.fetchall()]

        conn.close()

        return {
            "short_term_memories": short_term_memories,
            "long_term_memories": long_term_memories,
        }

    except Exception as e:
        print(f"Error retrieving context for reflection: {e}")
        return {
            "short_term_memories": [],
            "long_term_memories": [],
        }



# 회상 생성
def generate_reflection(database_path, agent_name):
    """
    Generate a reflection based on the agent's memories.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose memories will be used.

    Returns:
        str: Generated reflection or None if an error occurs.
    """
    # Retrieve memory context
    context = retrieve_context_for_reflection(database_path, agent_name)

    # Generate the prompt using the retrieved context
    prompt = (
        f"Based on the following memories of agent '{agent_name}':\n\n"
        "Short-term memories:\n" + "\n".join(context["short_term_memories"]) + "\n\n"
        "Long-term memories:\n" + "\n".join(context["long_term_memories"]) + "\n\n"
        "Reflect on these memories and generate a summary or insight."
    )

    # LLM 호출
    try:
        reflection = query_llm(prompt)
        if isinstance(reflection, dict):  # LLM 반환값이 dict인 경우
            reflection = reflection.get("choices", [{}])[0].get("message", {}).get("content", "")
        return reflection.strip() if isinstance(reflection, str) else str(reflection)
    except RuntimeError as e:
        print(f"Reflection generation failed: {e}")
        return None
    
# 회상 저장
def store_reflection(database_path, agent_name, reflection):
    """
    Store a reflection in the long-term memory of a specific agent.
    
    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose reflection is being stored.
        reflection (str): The reflection content to be stored.
    """
    if reflection:
        if not isinstance(reflection, str):
            raise ValueError(f"Invalid reflection type: {type(reflection)}. Expected a string.")

        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()

        # Insert the reflection into the long-term memory table with a high importance score
        cursor.execute('''
            INSERT INTO long_term_memory (agent_name, content, importance, last_accessed)
            VALUES (?, ?, ?, datetime('now'))
        ''', (agent_name, reflection, 10))  # Importance is set to 10 as a default for reflections
        
        conn.commit()
        conn.close()

# 에이전트 대화 처리 (수정됨)
def agent_conversation(database_path, agent1, agent2, message, conversation_turn, context=None):
    """
    Handle agent conversation and manage memories.

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
    if context is None:
        # Retrieve context if not provided
        context = {
            "short_term_memory": retrieve_from_short_term_memory(database_path, agent2.name),
            "long_term_memory": retrieve_from_long_term_memory(database_path, agent2.name)
        }

    memory_context = agent2.get_memory_context(database_path)
    reflection = agent2.reflect(database_path)
    prompt = (
        f"{agent1.name} (Persona: {agent1.persona}) says to {agent2.name}: '{message}'\n"
        f"Memory Context:\n{memory_context}\n"
        f"Reflection:\n{reflection}\n\n"
        f"Please respond to this message in the following format:\n"
        f"Thought process:\n[Provide your reasoning here, including any considerations from memory and reflection.]\n\n"
        f"Speech:\n[Provide the exact words the agent will say in the conversation.]"
    )

    try:
        # Query the LLM with the prompt
        llm_response = query_llm(prompt)
        if not isinstance(llm_response, dict) or "choices" not in llm_response:
            raise ValueError("Invalid LLM response format.")

        # Parse the response content
        content = llm_response["choices"][0]["message"]["content"]
        speech, thought_process = parse_llm_response(content)

        # Add to short-term memory with context
        add_to_short_term_memory(database_path, {"content": speech, "importance": 5}, agent2.name)

        # Promote important memories to long-term memory for the responding agent
        promote_to_long_term_memory(database_path, agent2.name)

        # Save messages to the conversation log
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
def manage_memories(database_path, agent_name, new_event=None):
    """
    Automatically manages memories:
    - Adds new events to short-term memory (if provided).
    - Promotes important short-term memories to long-term memory.
    - Generates reflections and stores them in long-term memory.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent managing the memories.
        new_event (dict, optional): A new memory event to add to short-term memory.
            Example format: {"content": "Sample memory", "importance": 5}.
    """
    try:
        # Add new event to short-term memory, if provided
        if new_event:
            add_to_short_term_memory(database_path, new_event, context={})  # Provide appropriate context if available

        # Generate a reflection based on recent memories
        reflection = generate_reflection(database_path, agent_name)
        
        if reflection:
            store_reflection(database_path, agent_name, reflection)

        # Promote important short-term memories to long-term memory
        promote_to_long_term_memory(database_path, agent_name)

    except Exception as e:
        print(f"Error in manage_memories: {e}")
        raise

