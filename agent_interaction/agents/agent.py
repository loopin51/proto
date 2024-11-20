class Agent:
    def __init__(self, name, persona):
        self.name = name
        self.persona = persona
        self.memory_stream = []

    def add_memory(self, event):
        self.memory_stream.append(event)

    def reflect(self):
        important_events = [mem for mem in self.memory_stream if mem['importance'] > 5]
        return f"{self.name} reflects on: {important_events}"

    def respond_to(self, agent, message):
        return f"{self.name} received a message from {agent.name}: '{message}'"