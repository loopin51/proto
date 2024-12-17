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

    def reflect(self, database_path, reflection_type="general"): #not used yet
        """
        Generate a reflection based on the agent's memories and specified reflection type.

        Args:
            database_path (str): Path to the SQLite database where memories are stored.
            reflection_type (str): Type of reflection to generate. Options: "general", "strategy", "lesson", "summary", "prediction".

        Returns:
            str: Reflection generated from memory.
        """
        from agent_methods import generate_reflection

        try:
            # Generate reflection using the agent's name and the specified reflection type
            reflection = generate_reflection(database_path, self.name, reflection_type)
            print(f"DEBUG: Reflection generated for {self.name} - Type: {reflection_type}\n{reflection}")
            return reflection
        except Exception as e:
            print(f"Error generating reflection for {self.name}: {e}")
            return None
