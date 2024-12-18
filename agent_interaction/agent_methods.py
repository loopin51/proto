import sqlite3
from datetime import datetime
import re
from utils.llm_connector import query_llm
import os
from textblob import TextBlob
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2') #model used for context similarity calculation

def debug_log(message):
    """
    Print debug messages with the current timestamp.
    Args:
        message (str): The message to print.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DEBUG {timestamp}] {message}")


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
            last_accessed TEXT,
            reflection_type TEXT
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
    preset_db_path = os.path.join(os.path.dirname(__file__), "preset_memory.db")
    # Create a new database and copy preset data
    init_memory_db()
    copy_preset_to_new_db(preset_db_path, database_path)

    return database_path

# 데이터베이스에 메시지를 저장하는 함수
def save_message_to_db(database_path, turn, speaker, message):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (turn, speaker, message) VALUES (?, ?, ?)
    ''', (turn, speaker, message))
    conn.commit()
    conn.close()
    debug_log(f" Message saved to db : {message}, turn : {turn}, speaker : {speaker}")


def save_thought_process_to_db(database_path, agent_name, thought_process):
    """
    Save the thought process to the thought_processes table in the database.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent.
        thought_process (str): The thought process to save.
    """
    if not thought_process:
        return  # Do not save empty thought processes

    try:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO thought_processes (agent_name, thought_process)
            VALUES (?, ?)
        ''', (agent_name, thought_process))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving thought process for agent '{agent_name}': {e}")


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

def context_score(memory_content, current_context):
    """
    Calculate similarity score between a memory content and the current context.

    Args:
        memory_content (str): Memory content to evaluate.
        current_context (list): List of strings representing the current context.

    Returns:
        float: Similarity score scaled to 0-10.
    """
    # Ensure current_context is a list of strings
    if not isinstance(current_context, list) or not all(isinstance(c, str) for c in current_context):
        print(f"DEBUG: Invalid current_context: {current_context}. Setting to empty list.")
        current_context = []

    try:
        memory_embedding = model.encode(memory_content, convert_to_tensor=True)
        context_embedding = model.encode(current_context, convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(memory_embedding, context_embedding)
        return float(similarity.item()) * 10  # Scale similarity to 0-10
    except Exception as e:
        print(f"Error calculating context score: {e}")
        return 0.0  # Default to 0 if any error occurs

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
def generate_reflection(database_path, agent_name, reflection_type="general"):
    """
    Generate a reflection based on the agent's memories and specified reflection type.

    Args:
        database_path (str): Path to the SQLite database where memories are stored.
        agent_name (str): Name of the agent generating the reflection.
        reflection_type (str): Type of reflection to generate. Options: "general", "strategy", "lesson", "summary", "prediction".

    Returns:
        str: Reflection generated from memory.
    """
    # Retrieve memory context
    context = retrieve_context_for_reflection(database_path, agent_name)

    # Log the context for debugging
    debug_log(f" Context retrieved for reflection - {context}")

    # Generate the prompt using the retrieved context
    if reflection_type == "strategy":
        prompt = (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            "Short-term memories:\n" + "\n".join(context["short_term_memories"]) + "\n\n"
            "Long-term memories:\n" + "\n".join(context["long_term_memories"]) + "\n\n"
            "What is the best course of action for the current situation? Provide a detailed reasoning and action plan."
        )
    elif reflection_type == "lesson":
        prompt = (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            "Short-term memories:\n" + "\n".join(context["short_term_memories"]) + "\n\n"
            "Long-term memories:\n" + "\n".join(context["long_term_memories"]) + "\n\n"
            "Summarize the key lessons learned from these experiences."
        )
    elif reflection_type == "summary":
        prompt = (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            "Short-term memories:\n" + "\n".join(context["short_term_memories"]) + "\n\n"
            "Long-term memories:\n" + "\n".join(context["long_term_memories"]) + "\n\n"
            "Summarize these memories into a concise overview."
        )
    elif reflection_type == "prediction":
        prompt = (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            "Short-term memories:\n" + "\n".join(context["short_term_memories"]) + "\n\n"
            "Long-term memories:\n" + "\n".join(context["long_term_memories"]) + "\n\n"
            "Predict the likely outcomes of taking the current proposed action."
        )
    else:  # Default to general reflection
        prompt = (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            "Short-term memories:\n" + "\n".join(context["short_term_memories"]) + "\n\n"
            "Long-term memories:\n" + "\n".join(context["long_term_memories"]) + "\n\n"
            "Reflect on these memories and generate a summary or insight."
        )

    # Call the LLM with the generated prompt
    try:
        reflection = query_llm(prompt)
        debug_log(f" Reflection generated: {reflection}")
        return reflection["choices"][0]["message"]["content"]
    except RuntimeError as e:
        print(f"Reflection generation failed: {e}")
        return None
    
# 회상 저장
def store_reflection(database_path, agent_name, reflection, reflection_type):
    """
    Store the reflection in the long-term memory.

    Args:
        database_path (str): Path to the SQLite database where memories are stored.
        agent_name (str): Name of the agent generating the reflection.
        reflection (str): The generated reflection text.
        reflection_type (str): Type of reflection.
    """
    if reflection:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO long_term_memory (content, importance, last_accessed, agent_name, reflection_type)
            VALUES (?, ?, datetime('now'), ?, ?)
        ''', (reflection, 10, agent_name, reflection_type))
        conn.commit()
        conn.close()
        debug_log(f" Reflection saved to db : {reflection} of {agent_name}")



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
        context = {
            "short_term_memory": retrieve_from_short_term_memory(database_path, agent2.name),
            "long_term_memory": retrieve_from_long_term_memory(database_path, agent2.name)
        }

    memory_context = agent2.get_memory_context(database_path)

    # Generate all types of reflections
    reflection_summary = agent2.reflect(database_path, reflection_type="summary")
    reflection_strategy = agent2.reflect(database_path, reflection_type="strategy")
    reflection_lesson = agent2.reflect(database_path, reflection_type="lesson")
    reflection_prediction = agent2.reflect(database_path, reflection_type="prediction")

    # Construct the prompt with all reflection types
    prompt = (
        f"{agent1.name} (Persona: {agent1.persona}) says to {agent2.name}: '{message}'\n"
        f"Memory Context:\n{memory_context}\n\n"
        f"Reflections:\n"
        f"- Summary:\n{reflection_summary}\n"
        f"- Strategy:\n{reflection_strategy}\n"
        f"- Lesson:\n{reflection_lesson}\n"
        f"- Prediction:\n{reflection_prediction}\n\n"
        f"Please respond to this message in the following format:\n"
        f"Thought process:\n[Provide your reasoning here, including any considerations from memory and reflections.]\n\n"
        f"Speech:\n[Provide the exact words {agent2.name} will say in the conversation.]"
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


        # Calculate importance and manage memories
        importance_score = calculate_importance(
            message,
            memory_context.get("short_term_memory", []) + memory_context.get("long_term_memory", []),  # Combine memories
            conversation_turn,
            0,  # Placeholder for frequency
            0   # Placeholder for sentiment
        )
        add_to_short_term_memory(database_path, {"content": speech, "importance": importance_score}, context)
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
        # Generate and store various reflections based on recent memories
        for reflection_type in ["strategy", "lesson", "summary", "prediction"]:
            reflection = generate_reflection(database_path, agent_name, reflection_type)
            if reflection:
                store_reflection(database_path, agent_name, reflection, reflection_type)
        # Promote important short-term memories to long-term memory
        promote_to_long_term_memory(database_path, agent_name)

    except Exception as e:
        print(f"Error in manage_memories: {e}")
        raise

