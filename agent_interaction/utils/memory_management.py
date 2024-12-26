import sqlite3
from .llm_connector import query_llm
from .prompt_templates import *
from .context_methods import *
from .importance_scoring import *
from contextlib import contextmanager 

@contextmanager
def db_connection(database_path):
    """
    Context manager for SQLite database connection.
    
    Args:
        database_path (str): Path to the SQLite database file.
    
    Yields:
        sqlite3.Connection: SQLite connection object.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def debug_log(message):
    """
    Print debug messages with the current timestamp.
    Args:
        message (str): The message to print.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DEBUG {timestamp}] {message}")

def update_reference_count(database_path, agent_name, memory_content, memory_type="short_term"):
    """
    Update the reference count of a memory.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose memory is being updated.
        memory_content (str): The content of the memory being referenced.
        memory_type (str): Type of memory ('short_term' or 'long_term').
    """
    table = "short_term_memory" if memory_type == "short_term" else "long_term_memory"

    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Update reference count
    cursor.execute(f'''
        UPDATE {table}
        SET reference_count = reference_count + 1
        WHERE agent_name = ? AND content = ?
    ''', (agent_name, memory_content))

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


def summarize_memory(content, context):
    """
    Summarize the given memory content based on context.

    Args:
        content (str): The memory content to summarize.
        context (str): Current conversation context.

    Returns:
        str: Summarized memory content.
    """
    try:
        # Generate the prompt using the centralized template
        prompt = get_summarize_memory_prompt(content, context)
        
        # Query the LLM
        response = query_llm(prompt)
        
        # Extract the summarized content from the response
        summarized_content = response.get("choices", [{}])[0].get("message", {}).get("content", content).strip()
        return summarized_content

    except Exception as e:
        print(f"Error summarizing memory: {e}")
        return content  # Fallback to original content if summarization fails
def add_to_short_term_memory(database_path, event, context):
    """
    Add a new memory to short-term memory with summarization, and calculate its importance.
    
    Args:
        database_path (str): Path to the SQLite database.
        event (dict): Memory content and metadata (e.g., {"content": "memory content", "agent_name"="Maria"}).
        context (str): Current conversation context.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    # Summarize memory content
    summarized_content = summarize_memory(event['content'], context)
    
    # Extract recency and frequency from database
    cursor.execute('SELECT COUNT(*) FROM short_term_memory WHERE content = ?', (summarized_content,))
    frequency = cursor.fetchone()[0]

    recency = 0  # Placeholder: Add logic to calculate recency based on timestamp.

    sentiment = analyze_sentiment(summarized_content)  # Example: Sentiment analysis
    importance = calculate_importance(summarized_content, context, recency, frequency, sentiment)

    # Insert summarized memory into short-term memory
    cursor.execute('''
        INSERT INTO short_term_memory (agent_name, timestamp, content, importance)
        VALUES (?, datetime('now'), ?, ?)
    ''', (event['agent_name'], summarized_content, importance))
    conn.commit()

    # Check the number of entries in short-term memory
    cursor.execute('SELECT COUNT(*) FROM short_term_memory WHERE agent_name = ?', (event['agent_name'],))
    count = cursor.fetchone()[0]

    # Remove oldest memory if capacity exceeded
    MAX_SHORT_TERM_MEMORY = 10
    if count > MAX_SHORT_TERM_MEMORY:
        cursor.execute('''
            DELETE FROM short_term_memory WHERE id = (
                SELECT id FROM short_term_memory WHERE agent_name = ? ORDER BY timestamp ASC LIMIT 1
            )
        ''', (event['agent_name'],))
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

    # Update reference count for each retrieved memory
    for memory in memories:
        update_reference_count(database_path, agent_name, memory, memory_type="long_term")
    
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

def retrieve_reflections_from_db(database_path, agent_name):
    """
    Retrieve existing reflections for a specific agent from the database.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose reflections to retrieve.

    Returns:
        dict: A dictionary containing different types of reflections.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    cursor = conn.cursor()

    reflections = {
        "summary": "No summary available.",
        "strategy": "No strategy available.",
        "lesson": "No lesson available.",
        "prediction": "No prediction available."
    }

    try:
        cursor.execute('''
            SELECT reflection_type, content 
            FROM long_term_memory 
            WHERE agent_name = ? AND reflection_type IN ('summary', 'strategy', 'lesson', 'prediction')
        ''', (agent_name,))

        rows = cursor.fetchall()
        for reflection_type, content in rows:
            if reflection_type in reflections:
                reflections[reflection_type] = content

    except Exception as e:
        print(f"Error retrieving reflections from database for agent '{agent_name}': {e}")
    finally:
        conn.close()

    return reflections



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
    prompt = reflection_prompt(
        agent_name, context["short_term_memories"], context["long_term_memories"], reflection_type
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

def update_memory_importance(database_path, context):
    """
    Update the importance scores for memories in the database.

    Args:
        database_path (str): Path to the SQLite database.
        context (str): The current context for relevance calculation.
    """
    try:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()

        # Fetch memories from both STM and LTM
        cursor.execute('SELECT id, content, importance, timestamp FROM short_term_memory')
        stm_memories = cursor.fetchall()

        cursor.execute('SELECT id, content, importance, last_accessed FROM long_term_memory')
        ltm_memories = cursor.fetchall()

        # Update STM memories
        for memory in stm_memories:
            memory_id, content, current_importance, timestamp = memory
            recency = calculate_recency(timestamp)
            frequency = get_frequency(conn, 'short_term_memory', content)
            sentiment = analyze_sentiment(content)
            new_importance = calculate_importance(content, context, recency, frequency, sentiment)

            cursor.execute('UPDATE short_term_memory SET importance = ? WHERE id = ?', (new_importance, memory_id))

        # Update LTM memories
        for memory in ltm_memories:
            memory_id, content, current_importance, last_accessed = memory
            recency = calculate_recency(last_accessed)
            frequency = get_frequency(conn, 'long_term_memory', content)
            sentiment = analyze_sentiment(content)
            new_importance = calculate_importance(content, context, recency, frequency, sentiment)

            cursor.execute('UPDATE long_term_memory SET importance = ? WHERE id = ?', (new_importance, memory_id))

        conn.commit()
        print("Memory importance scores have been updated.")

    except Exception as e:
        print(f"Error updating memory importance: {e}")

    finally:
        conn.close()



# 기억 자동 관리 함수
def manage_memories(database_path, agent_name, new_event=None):
    """
    Automatically manages memories:
    - Adds new events to short-term memory (if provided).
    - Promotes important short-term memories to long-term memory.
    - Recalculates importance for all memories in STM and LTM.
    - Generates reflections and stores them in long-term memory.

    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent managing the memories.
        new_event (dict, optional): A new memory event to add to short-term memory.
        Example format: {"content": "Sample memory", "agent_name": "Maria"}.
    """
    try:
        context = generate_context(database_path, agent_name)
        # Add new event to short-term memory, if provided. 쓸일 없음.
        if new_event:
            add_to_short_term_memory(database_path, new_event, context)

        # Recalculate importance scores for all memories
        update_memory_importance(database_path, context)

        # Promote important short-term memories to long-term memory
        promote_to_long_term_memory(database_path, agent_name)

        # Generate and store various reflections based on recent memories
        for reflection_type in ["strategy", "lesson", "summary", "prediction"]:
            reflection = generate_reflection(database_path, agent_name, reflection_type)
            if reflection:
                store_reflection(database_path, agent_name, reflection, reflection_type)

    except Exception as e:
        print(f"Error in manage_memories: {e}")
        raise

def retrieve_conversation_history(database_path, agent1_name, agent2_name, limit=10):
    """
    Retrieve the most recent conversation history between two agents.

    Args:
        database_path (str): Path to the SQLite database file.
        agent1_name (str): Name of the first agent.
        agent2_name (str): Name of the second agent.
        limit (int): Number of recent messages to retrieve.

    Returns:
        list of tuples: Each tuple contains (speaker, message).
    """
    with db_connection(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT speaker, message FROM conversations
            WHERE speaker IN (?, ?)
            ORDER BY turn DESC
            LIMIT ?
        """, (agent1_name, agent2_name, limit))
        rows = cursor.fetchall()
    
    # Reverse to have oldest first
    return rows[::-1]

def format_conversation_history(conversation_history):
    """
    Format the conversation history into a readable string.

    Args:
        conversation_history (list of tuples): Each tuple contains (speaker, message).

    Returns:
        str: Formatted conversation history.
    """
    if not conversation_history:
        return "(No previous conversation history)\n"
    
    history_text = "=== Conversation History ===\n"
    for speaker, message in conversation_history:
        history_text += f"{speaker}: {message}\n"
    return history_text.strip()

