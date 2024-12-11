class Agent:
    def __init__(self, name, persona):
        self.name = name
        self.persona = persona
        self.short_term_memory = []
        self.long_term_memory = []

    def add_memory(self, memory):
        self.short_term_memory.append(memory)
        if memory['importance'] > 7:
            self.long_term_memory.append(memory)
        if len(self.short_term_memory) > 10:
            self.short_term_memory.pop(0)

    def get_memory_context(self):
        short_term_context = " ".join(
            [mem['content'] for mem in self.short_term_memory]
        )
        long_term_context = " ".join(
            [mem['content'] for mem in self.long_term_memory]
        )
        return f"Short-term Memory: {short_term_context}\nLong-term Memory: {long_term_context}"

    def reflect(self):
        reflections = [
            f"Reflection on memory: {mem['content']}"
            for mem in self.long_term_memory if mem['importance'] > 5
        ]
        return "\n".join(reflections)
