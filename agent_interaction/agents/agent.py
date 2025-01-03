# agent.py

class Agent:
    """
    Agent class to define individual agents with their persona, name, and memory-related methods.
    """

    def __init__(self, name, persona, partner_name="Anonymous"):
        """
        Initialize an Agent with a name and persona.
        Args:
            name (str): The name of the agent.
            persona (str): A brief description of the agent's personality or role.
        """
        self.name = name
        self.persona = persona
        self.partner_name = partner_name

    def get_memory_context(self, database_path):
        """
        Retrieve memory context from the agent's short-term and long-term memory.
        Args:
            database_path (str): Path to the SQLite database where memories are stored.
        Returns:
            str: Combined short-term and long-term memory.
        """
        from utils.general_methods import retrieve_from_short_term_memory, retrieve_from_long_term_memory

        short_term_memories = retrieve_from_short_term_memory(database_path, self.name)
        long_term_memories = retrieve_from_long_term_memory(database_path, self.name)

         # Format the memories into a string
        short_term_section = "Short-term memories:\n" + "\n".join(short_term_memories) if short_term_memories else "Short-term memories: None"
        long_term_section = "Long-term memories:\n" + "\n".join(long_term_memories) if long_term_memories else "Long-term memories: None"

        # Combine sections into a single string
        memory_context = f"{short_term_section}\n\n{long_term_section}"
        
        return memory_context

    def reflect(self, database_path, reflection_type="general"): #not used yet
        """
        Generate a reflection based on the agent's memories and specified reflection type.

        Args:
            database_path (str): Path to the SQLite database where memories are stored.
            reflection_type (str): Type of reflection to generate. Options: "general", "strategy", "lesson", "summary", "prediction".

        Returns:
            str: Reflection generated from memory.
        """
        from agent_interaction.utils.general_methods import generate_reflection

        try:
            # Generate reflection using the agent's name and the specified reflection type
            reflection = generate_reflection(database_path, self.name, reflection_type)
            print(f"DEBUG: Reflection generated for {self.name} - Type: {reflection_type}\n{reflection}")
            return reflection
        except Exception as e:
            print(f"Error generating reflection for {self.name}: {e}")
            return None
