# emotions_methods.py
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from textblob import TextBlob

# 데이터베이스 파일 경로 생성 함수
def get_emo_database_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("database", f"memory_system_{timestamp}.db")

# 전역 데이터베이스 경로
emo_database_path = None

def set_emo_database_path(path):
    global emo_database_path
    emo_database_path = path

###################################
# Database Connection Utility
###################################

@contextmanager
def db_connection(database_path):
    """
    Context manager for SQLite database connection.
    
    Args:
        database_path (str): Path to the SQLite database file.
    
    Yields:
        sqlite3.Connection: SQLite connection object.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

###################################
# Database Initialization
###################################

def init_emotion_db(database_path):
    """
    Initialize the emotion_states table in the SQLite database if it doesn't exist.
    
    Args:
        database_path (str): Path to the SQLite database file.
    """
    with db_connection(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
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
        """)
        conn.commit()

###################################
# Emotion Vector Utilities
###################################

def empty_emotion_vector():
    """
    Returns an empty emotion vector with all emotions set to 0.0.
    
    Returns:
        dict: Dictionary with emotions as keys and 0.0 as values.
    """
    return {
        'joy': 0.0,
        'trust': 0.0,
        'fear': 0.0,
        'surprise': 0.0,
        'sadness': 0.0,
        'disgust': 0.0,
        'anger': 0.0,
        'anticipation': 0.0
    }

def clamp_emotion_value(val):
    """
    Clamps the emotion value between 0.0 and 1.0.
    
    Args:
        val (float): Emotion value to clamp.
    
    Returns:
        float: Clamped emotion value.
    """
    return max(0.0, min(1.0, val))

###################################
# Emotion Retrieval Functions
###################################

def retrieve_current_emotions(database_path, agent_name, recent_n=10):
    """
    Retrieve the average of the most recent N emotion states for the specified agent.
    
    Args:
        database_path (str): Path to the SQLite database file.
        agent_name (str): Name of the agent.
        recent_n (int): Number of recent emotion states to average.
    
    Returns:
        dict: Dictionary with averaged emotions.
    """
    with db_connection(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT joy, trust, fear, surprise, sadness, disgust, anger, anticipation
            FROM emotion_states
            WHERE agent_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_name, recent_n))
        rows = cursor.fetchall()
    
    if not rows:
        return empty_emotion_vector()
    
    avg_emotions = empty_emotion_vector()
    for row in rows:
        for i, emotion in enumerate(avg_emotions.keys()):
            avg_emotions[emotion] += row[i]
    
    for emotion in avg_emotions:
        avg_emotions[emotion] /= len(rows)
    
    return avg_emotions

###################################
# Emotion Update Functions
###################################

def update_emotion(database_path, agent_name, event, sentiment_score):
    """
    Update the emotion state based on an event and its sentiment score.
    
    Args:
        database_path (str): Path to the SQLite database file.
        agent_name (str): Name of the agent.
        event (str): Type of event ('positive_interaction', 'negative_interaction', 'neutral_interaction').
        sentiment_score (float): Sentiment score between -1 and +1.
    """
    emotion_map = {
        'positive_interaction': 'joy',
        'negative_interaction': 'sadness',
        'neutral_interaction': 'trust'
    }
    
    # Map event to emotion
    emotion = emotion_map.get(event, 'anticipation')  # Default to 'anticipation' if event not found
    intensity = clamp_emotion_value((sentiment_score + 1) / 2)  # Scale from -1~1 to 0~1
    
    # Retrieve current emotions
    current_emotions = retrieve_current_emotions(database_path, agent_name)
    updated_emotions = current_emotions.copy()
    updated_emotions[emotion] = intensity  # Update the specific emotion
    
    # Insert the new emotion state into the database
    with db_connection(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            updated_emotions['joy'],
            updated_emotions['trust'],
            updated_emotions['fear'],
            updated_emotions['surprise'],
            updated_emotions['sadness'],
            updated_emotions['disgust'],
            updated_emotions['anger'],
            updated_emotions['anticipation']
        ))
        conn.commit()

def adjust_emotions(database_path, agent_name):
    """
    Adjust emotions so that very high or very low values move slightly toward 0.5,
    making strong emotions 'cool down' a bit.

    로직 요약:
      - 감정값이 0.7보다 크면 0.5 쪽으로 조금 감소 (겹치는 부분 만큼 줄임)
      - 0.0 ~ 0.7 사이면 조정하지 않음 (자연스럽게 유지)

    Args:
        database_path (str): Path to the SQLite database file.
        agent_name (str): Name of the agent.
    """
    # alpha: 감정이 중간값(0.5)에 접근하는 정도 (0~1)
    alpha = 0.2

    # 1) 현재 감정 상태 조회
    emotions = retrieve_current_emotions(database_path, agent_name)
    new_emotions = emotions.copy()

    for emotion_name, val in emotions.items():
        if val > 0.7:
            # 너무 큰 감정 => 0.5 쪽으로 조금씩 수렴
            # new_val = val - (val-0.5)*alpha
            #   = val*(1-alpha) + 0.5*alpha
            new_val = val - (val - 0.5) * alpha
        else:
            # 0.3 ~ 0.7 사이라면 그대로 둠
            new_val = val

        new_val = clamp_emotion_value(new_val)
        new_emotions[emotion_name] = new_val

    # 2) DB에 새 감정 상태를 반영
    with db_connection(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emotion_states
            (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            new_emotions['joy'],
            new_emotions['trust'],
            new_emotions['fear'],
            new_emotions['surprise'],
            new_emotions['sadness'],
            new_emotions['disgust'],
            new_emotions['anger'],
            new_emotions['anticipation']
        ))
        conn.commit()

def analyze_sentiment(content):
        """
        Perform sentiment analysis on the memory content.
        Args:
            content (str): Text to analyze.

        Returns:
            float: Sentiment polarity (-1 to 1).
        """
        analysis = TextBlob(content)
        return analysis.sentiment.polarity
###################################
# Testing and Example Usage
###################################

if __name__ == "__main__":
    # Example database path and agent name
    database_path = "example_emotion_states.db"
    agent_name = "agent_1"
    
    # Initialize the emotion database
    init_emotion_db(database_path)
    
    # Insert initial emotion state (all emotions set to 0.0)
    with db_connection(database_path) as conn:
        cursor = conn.cursor()
        zero = 0.0
        cursor.execute("""
            INSERT INTO emotion_states (agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_name, zero, zero, zero, zero, zero, zero, zero, zero))
        conn.commit()
    
    # Example: Update emotion based on a positive interaction with sentiment_score=0.8
    update_emotion(database_path, agent_name, 'positive_interaction', 0.8)
    current = retrieve_current_emotions(database_path, agent_name)
    print("Current emotions after positive interaction:", current)
    
    # Example: Adjust emotions if necessary
    adjust_emotions(database_path, agent_name)
    current = retrieve_current_emotions(database_path, agent_name)
    print("Current emotions after adjustment:", current)
    
    # Example: Update emotion based on a negative interaction with sentiment_score=-0.6
    update_emotion(database_path, agent_name, 'negative_interaction', -0.6)
    current = retrieve_current_emotions(database_path, agent_name)
    print("Current emotions after negative interaction:", current)
    
    # Adjust emotions again if necessary
    adjust_emotions(database_path, agent_name)
    current = retrieve_current_emotions(database_path, agent_name)
    print("Current emotions after second adjustment:", current)
