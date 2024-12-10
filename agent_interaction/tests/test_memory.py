from agents.agent import Agent

def test_add_memory():
    agent = Agent("Test Agent", "A helpful test agent.")
    
    # Add short-term memory
    agent.add_memory({"event": "Met John at the pharmacy.", "importance": 5})
    assert len(agent.short_term_memory) == 1, "Short-term memory should have 1 event"
    
    # Add another memory and check size
    agent.add_memory({"event": "Helped Maria with her painting.", "importance": 8})
    assert len(agent.short_term_memory) == 2, "Short-term memory should have 2 events"
    
    # Check long-term memory (importance > 7)
    assert len(agent.long_term_memory) == 1, "Long-term memory should have 1 event"
    assert agent.long_term_memory[0]["event"] == "Helped Maria with her painting."

def test_memory_context():
    agent = Agent("Test Agent", "A helpful test agent.")
    
    # Add memories
    agent.add_memory({"event": "Met John at the pharmacy.", "importance": 5})
    agent.add_memory({"event": "Helped Maria with her painting.", "importance": 8})
    
    # Generate memory context
    context = agent.get_memory_context()
    assert "Short-term Memory" in context, "Short-term Memory section missing"
    assert "Long-term Memory" in context, "Long-term Memory section missing"

def test_reflection():
    agent = Agent("Test Agent", "A reflective test agent.")
    
    # Add memories
    agent.add_memory({"event": "Met John at the pharmacy.", "importance": 5})
    agent.add_memory({"event": "Helped Maria with her painting.", "importance": 8})
    
    # Reflect on important events
    reflection = agent.reflect()
    assert "Helped Maria with her painting." in reflection, "Reflection missing important memory"

if __name__ == "__main__":
    test_add_memory()
    test_memory_context()
    test_reflection()
    print("All memory tests passed.")
