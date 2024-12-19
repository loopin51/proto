import sqlite3

def generate_context_dict(database_path, agent_name, max_stm=5, max_ltm=5):
    """
    Generate context by retrieving the agent's short-term and long-term memories.
    
    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose context to generate.
        max_stm (int): Maximum number of short-term memories to include.
        max_ltm (int): Maximum number of long-term memories to include.

    Returns:
        dict: A dictionary containing 'short_term_memory' and 'long_term_memory' lists.
    """
    context = {
        "short_term_memory": [],
        "long_term_memory": []
    }

    try:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()

        # Retrieve short-term memories
        cursor.execute('''
            SELECT content FROM short_term_memory 
            WHERE agent_name = ? 
            ORDER BY timestamp DESC LIMIT ?
        ''', (agent_name, max_stm))
        context["short_term_memory"] = [row[0] for row in cursor.fetchall()]

        # Retrieve long-term memories
        cursor.execute('''
            SELECT content FROM long_term_memory 
            WHERE agent_name = ? 
            ORDER BY importance DESC, last_accessed DESC LIMIT ?
        ''', (agent_name, max_ltm))
        context["long_term_memory"] = [row[0] for row in cursor.fetchall()]

        conn.close()
    except Exception as e:
        print(f"Error generating context for agent '{agent_name}': {e}")

    return context

def generate_context(database_path, agent_name, max_stm=5, max_ltm=5):
    """
    Generate context as a string by retrieving the agent's short-term and long-term memories.
    
    Args:
        database_path (str): Path to the SQLite database.
        agent_name (str): Name of the agent whose context to generate.
        max_stm (int): Maximum number of short-term memories to include.
        max_ltm (int): Maximum number of long-term memories to include.

    Returns:
        str: A string combining short-term and long-term memories.
    """
    short_term_memories = []
    long_term_memories = []

    try:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        cursor = conn.cursor()

        # Retrieve short-term memories
        cursor.execute('''
            SELECT content FROM short_term_memory 
            WHERE agent_name = ? 
            ORDER BY timestamp DESC LIMIT ?
        ''', (agent_name, max_stm))
        short_term_memories = [row[0] for row in cursor.fetchall()]

        # Retrieve long-term memories
        cursor.execute('''
            SELECT content FROM long_term_memory 
            WHERE agent_name = ? 
            ORDER BY importance DESC, last_accessed DESC LIMIT ?
        ''', (agent_name, max_ltm))
        long_term_memories = [row[0] for row in cursor.fetchall()]

        conn.close()
    except Exception as e:
        print(f"Error generating context for agent '{agent_name}': {e}")

    # Combine memories into a single string
    context_string = (
        "Short-term memories:\n" +
        "\n".join(short_term_memories) +
        "\n\n" +
        "Long-term memories:\n" +
        "\n".join(long_term_memories)
    ).strip()

    return context_string
