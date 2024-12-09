class Agent:
    def __init__(self, name, persona):
        self.name = name
        self.persona = persona
        self.short_term_memory = []
        self.long_term_memory = []

    def add_memory(self, event):
        # 단기 기억에 추가
        self.short_term_memory.append(event)
        # 중요도가 높은 경우 장기 기억에 추가
        if event['importance'] > 7:
            self.long_term_memory.append(event)
        # 단기 기억이 일정 길이를 초과하면 오래된 기억 삭제
        if len(self.short_term_memory) > 20:
            self.short_term_memory.pop(0)

    def reflect(self):
        important_events = [mem['event'] for mem in self.short_term_memory if mem['importance'] > 5]
        return f"{self.name} reflects on: {'; '.join(important_events)}"

    def get_memory_context(self):
        # 단기 기억과 장기 기억을 결합하여 컨텍스트 생성
        short_term = " ".join([mem['event'] for mem in self.short_term_memory])
        long_term = " ".join([mem['event'] for mem in self.long_term_memory])
        return f"Long-term Memory: {long_term}\nShort-term Memory: {short_term}"

    def summarize_memory(self):
        # 중요 기억을 요약하고 장기 기억에 추가
        important_events = self.reflect()  # 중요 기억 필터링
        summary = query_llm(f"Summarize these important events: {important_events}")
        self.long_term_memory.append({"event": summary, "importance": 10})
        self.short_term_memory = []