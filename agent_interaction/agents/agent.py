# agent.py

class Agent:
    """
    Agent class to define individual agents with their persona, name, and memory-related methods.
    """

    def __init__(self, name, persona):
        """
        Initialize an Agent with a name and persona.
        Args:
            name (str): The name of the agent.
            persona (str): A brief description of the agent's personality or role.
        """
        self.name = name
        self.persona = persona

    def get_memory_context(self, database_path):
        """
        Retrieve memory context from the agent's short-term and long-term memory.
        Args:
            database_path (str): Path to the SQLite database where memories are stored.
        Returns:
            dict: Combined short-term and long-term memory.
        """
        from agent_methods import retrieve_from_short_term_memory, retrieve_from_long_term_memory

        short_term_memories = retrieve_from_short_term_memory(database_path, self.name)
        long_term_memories = retrieve_from_long_term_memory(database_path, self.name)

        return {
            "short_term_memory": short_term_memories,
            "long_term_memory": long_term_memories
        }

    def reflect(self, database_path):
        """
        Generate a reflection based on the agent's memories.
        Args:
            database_path (str): Path to the SQLite database where memories are stored.
        Returns:
            str: Reflection generated from memory.
        """
        from agent_methods import retrieve_context_for_reflection, generate_reflection
        
        # Generate reflection
        reflection = generate_reflection(database_path, self.name)

        return reflection
