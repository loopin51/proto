import sqlite3
import os

def create_preset_db():
 # Preset database path (in the same directory as this script)
    preset_db_path = os.path.join(os.path.dirname(__file__), "preset_memory.db")
    if not os.path.exists(os.path.dirname(preset_db_path)):
        os.makedirs(os.path.dirname(preset_db_path))

    # 데이터베이스 연결 및 테이블 생성
    conn = sqlite3.connect(preset_db_path)
    cursor = conn.cursor()

    # LTM 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            content TEXT,
            importance INTEGER,
            last_accessed TEXT,
            reflection_type TEXT
        )
    ''')

    # STM 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            timestamp TEXT,
            content TEXT,
            importance INTEGER
        )
    ''')

    # 대화 기록 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn INTEGER,
            speaker TEXT,
            message TEXT
        )
    ''')

    # Thought Process 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thought_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            thought_process TEXT
        )
    ''')


    # Data insertion
    # Long-Term Memory (LTM)
    ltm_data = [
        ("John", "Maria tries to capture warmth and healing through observing nature.", 8, "Experience Summary", "2024-12-14"),
        ("John", "Small actions can create big changes. Recommending lavender tea reminds me of this.", 9, "Lesson", "2024-12-14"),
        ("John", "The health booth should focus on herbal remedies connected to nature.", 10, "Strategy", "2024-12-14"),
        ("Maria", "John helps patients by using herbal remedies in his consultations.", 8, "Experience Summary", "2024-12-14"),
        ("Maria", "Even small help can have a big impact on others.", 9, "Lesson", "2024-12-14"),
        ("Maria", "I should express more vitality and healing from nature in my artwork.", 10, "Strategy", "2024-12-14")
    ]
    cursor.executemany('''
        INSERT INTO long_term_memory (agent_name, content, importance, reflection_type, last_accessed)
        VALUES (?, ?, ?, ?, ?)
    ''', ltm_data)

    # Short-Term Memory (STM)
    stm_data = [
        ("John", "2024-12-14 19:00:00", "Maria decided on 'Dialogue with Nature' as the theme for her exhibition.", 7),
        ("John", "2024-12-14 19:01:00", "Maria was inspired by an elderly couple at the park to create her artwork.", 8),
        ("John", "2024-12-14 19:02:00", "Maria mentioned she might consider creating an artwork themed around herbs.", 6),
        ("Maria", "2024-12-14 19:00:00", "John said he would introduce herbal remedies at the health booth.", 7),
        ("Maria", "2024-12-14 19:01:00", "John explained lavender and chamomile are good for stress relief.", 8),
        ("Maria", "2024-12-14 19:02:00", "John wants to connect elements from nature to health consultations.", 6)
    ]
    cursor.executemany('''
        INSERT INTO short_term_memory (agent_name, timestamp, content, importance)
        VALUES (?, ?, ?, ?)
    ''', stm_data)

    # Conversations
    conversations_data = [
        (1, "John", "Hi Maria! I remember you sketching at the park. Those sketches are for your exhibition, right? How's the preparation going?"),
        (2, "Maria", "Hi John! Yes, I prepared my artworks inspired by the park. Actually, the theme of this exhibition is 'Dialogue with Nature'. I'm really excited!"),
        (3, "John", "That sounds amazing! 'Dialogue with Nature' is such a great theme. I've also been preparing a health booth to introduce herbal remedies inspired by nature."),
        (4, "Maria", "Oh, herbal remedies sound fascinating. Connecting health and nature must be very beneficial for people. What kinds of herbs will you showcase?")
    ]
    cursor.executemany('''
        INSERT INTO conversations (turn, speaker, message)
        VALUES (?, ?, ?)
    ''', conversations_data)

    conn.commit()
    conn.close()
    print("Preset database created at:", preset_db_path)

create_preset_db()
