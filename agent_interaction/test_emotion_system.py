from agents.agent import Agent 
import sqlite3
from utils.emotion_methods import init_emotion_db, retrieve_current_emotions, update_emotion, adjust_emotions, analyze_sentiment
from utils.prompt_templates import c_onversation_prompt
from utils.context_methods import g_enerate_context
# Define the database path
database_path = "test_database.db"

def setup_database(database_path):
    """
    Sets up the necessary tables for testing.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        );
    ''')
    
    # Create short_term_memory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # Create long_term_memory table with reflection_type
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL NOT NULL,
            last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
            reflection_type TEXT
        );
    ''')
    
    # Create emotion_states table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotion_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            joy REAL NOT NULL,
            trust REAL NOT NULL,
            fear REAL NOT NULL,
            surprise REAL NOT NULL,
            sadness REAL NOT NULL,
            disgust REAL NOT NULL,
            anger REAL NOT NULL,
            anticipation REAL NOT NULL
        );
    ''')
    
    conn.commit()
    conn.close()

def populate_initial_data(database_path):
    """
    Populates the database with initial data for testing.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Initialize emotion database
    init_emotion_db(database_path)
    
    # Insert initial emotion states for agents
    agents = ['agent_1', 'agent_2']
    for agent in agents:
        # Insert initial emotion state (all emotions set to 0.0)
        cursor.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    
    # Insert some short-term memories
    cursor.execute("""
        INSERT INTO short_term_memory (agent_name, content)
        VALUES (?, ?)
    """, ("agent_1", "Remember to check the weather forecast tomorrow."))
    
    cursor.execute("""
        INSERT INTO short_term_memory (agent_name, content)
        VALUES (?, ?)
    """, ("agent_2", "Prepare a summary of today's meeting notes."))
    
    # Insert some long-term memories (including reflections)
    cursor.execute("""
        INSERT INTO long_term_memory (agent_name, content, importance, reflection_type)
        VALUES (?, ?, ?, ?)
    """, ("agent_1", "Past experience with similar conversations was successful.", 0.9, None))
    
    cursor.execute("""
        INSERT INTO long_term_memory (agent_name, content, importance, reflection_type)
        VALUES (?, ?, ?, ?)
    """, ("agent_1", "Reflection on improving communication strategies.", 0.8, "strategy"))
    
    cursor.execute("""
        INSERT INTO long_term_memory (agent_name, content, importance, reflection_type)
        VALUES (?, ?, ?, ?)
    """, ("agent_2", "Understanding the importance of emotional intelligence.", 0.95, None))
    
    # Insert some conversation logs
    cursor.execute("""
        INSERT INTO conversations (turn, speaker, message)
        VALUES (?, ?, ?)
    """, (1, "agent_1", "Hello, how are you today?"))
    
    cursor.execute("""
        INSERT INTO conversations (turn, speaker, message)
        VALUES (?, ?, ?)
    """, (2, "agent_2", "I'm doing well, thank you! How can I assist you today?"))
    
    conn.commit()
    conn.close()

def test_emotion_system(database_path):
    """
    Tests the emotion system using the existing functions.
    """
    # Initialize agents
    agent1 = Agent(name="agent_1", persona="Friendly and helpful.", partner_name="agent_2")
    agent2 = Agent(name="agent_2", persona="Calm and wise.", partner_name="agent_1")
    
    # Simulate a message from agent1 to agent2
    message = "I'm feeling fantastic today! The weather is great and I'm very happy."
    conversation_turn = 3
    
    print("=== Analyzing Sentiment ===")
    sentiment_score = analyze_sentiment(message)
    print(f"Message: {message}")
    print(f"Sentiment Score: {sentiment_score}")
    
    print("\n=== Updating Emotions ===")
    update_emotion(database_path, agent2.name, 'positive_interaction', sentiment_score)
    
    # Retrieve and print current emotions for agent2
    current_emotions = retrieve_current_emotions(database_path, agent2.name)
    print(f"Current Emotions for {agent2.name}: {current_emotions}")
    
    print("\n=== Adjusting Emotions ===")
    adjust_emotions(database_path, agent2.name)
    
    # Retrieve and print adjusted emotions for agent2
    adjusted_emotions = retrieve_current_emotions(database_path, agent2.name)
    print(f"Adjusted Emotions for {agent2.name}: {adjusted_emotions}")
    
    print("\n=== Generating Context ===")
    context = g_enerate_context(database_path, agent2, max_stm=5, max_ltm=5, history_limit=10)
    print("Generated Context:\n")
    print(context)
    
    print("\n=== Creating Conversation Prompt ===")
    # Retrieve reflections for agent2
    reflections = {
        'summary': "Today, I focused on understanding the importance of emotional intelligence.",
        'strategy': "Improve communication by actively listening and responding empathetically.",
        'lesson': "Emotional intelligence enhances interpersonal relationships.",
        'prediction': "With better emotional management, interactions will become more positive."
    }
    
    # Format emotion_text based on current emotions
    emotion_text = ", ".join([f"{emotion.capitalize()}={value:.2f}" for emotion, value in current_emotions.items()])
    
    prompt = c_onversation_prompt(
        agent1.name,
        agent1.persona,
        agent2.name,
        message,
        context,
        reflections,
        emotion_text
    )
    
    print("Conversation Prompt:\n")
    print(prompt)
    
    # Optionally, simulate a response from agent2 using the prompt
    # For this test, we can just print the prompt
    # In real use, this prompt would be sent to an LLM to generate the response

if __name__ == "__main__":
    # Setup
    setup_database(database_path)
    populate_initial_data(database_path)
    
    # Test
    test_emotion_system(database_path)
