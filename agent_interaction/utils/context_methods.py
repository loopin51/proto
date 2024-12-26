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

def g_enerate_context(database_path, agent, max_stm=5, max_ltm=5, history_limit=10):
    """
    Generate context as a string by retrieving the agent's short-term and long-term memories,
    as well as recent conversation history.

    Args:
        database_path (str): Path to the SQLite database.
        agent (Agent): The agent object whose context to generate.
        max_stm (int): Maximum number of short-term memories to include.
        max_ltm (int): Maximum number of long-term memories to include.
        history_limit (int): Maximum number of conversation turns to include.

    Returns:
        str: A string combining short-term memories, long-term memories, and conversation history.
    """
    short_term_memories = []
    long_term_memories = []
    conversation_history = []

    from .memory_management import (
    retrieve_conversation_history,
    format_conversation_history,
    db_connection
)
    try:
        with db_connection(database_path) as conn:
            cursor = conn.cursor()

            # Retrieve short-term memories
            cursor.execute('''
                SELECT content FROM short_term_memory 
                WHERE agent_name = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (agent.name, max_stm))
            short_term_memories = [row[0] for row in cursor.fetchall()]

            # Retrieve long-term memories
            cursor.execute('''
                SELECT content FROM long_term_memory 
                WHERE agent_name = ?
                  AND reflection_type IS NULL
                ORDER BY importance DESC, last_accessed DESC LIMIT ?
            ''', (agent.name, max_ltm))
            long_term_memories = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error generating context for agent '{agent.name}': {e}")

    # Retrieve conversation history
    try:
        conversation_history = retrieve_conversation_history(database_path, agent.name, agent.partner_name, limit=history_limit)
    except Exception as e:
        print(f"Error retrieving conversation history for agent '{agent.name}': {e}")

    # Format memories
    stm_text = "=== Short-Term Memories ===\n" + "\n".join(short_term_memories) if short_term_memories else "=== Short-Term Memories ===\n(No short-term memories)"
    ltm_text = "\n\n=== Long-Term Memories ===\n" + "\n".join(long_term_memories) if long_term_memories else "\n\n=== Long-Term Memories ===\n(No long-term memories)"
    
    # Format conversation history
    history_text = "\n\n" + format_conversation_history(conversation_history) if conversation_history else "\n\n(No conversation history)"
    
    # Combine all into context string
    context_string = stm_text + ltm_text + history_text

    return context_string.strip()

###################################
# Example Usage
###################################

if __name__ == "__main__":
    # Example database path and agent names
    database_path = "path/to/your/database.db"
    agent_name = "agent_1"
    agent_partner_name = "agent_2"

    # Example Agent class usage
    class Agent:
        def __init__(self, name, persona, partner_name=None):
            self.name = name
            self.persona = persona
            self.partner_name = partner_name  # 대화 상대 에이전트의 이름

    agent = Agent(name=agent_name, persona="Friendly and helpful.", partner_name=agent_partner_name)
    
    # Generate context
    context = generate_context(database_path, agent, max_stm=5, max_ltm=5, history_limit=10)
    print("Generated Context:\n")
    print(context)

