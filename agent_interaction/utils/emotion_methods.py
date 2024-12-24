# emotions_methods.py

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

###################################
# DB 연결 관리 함수 (SQLite용)
###################################
@contextmanager
def db_connection():
    # 로컬 파일 기반 SQLite DB 사용 (emotion_states.db)
    conn = sqlite3.connect('emotion_states.db')
    try:
        yield conn
    finally:
        conn.close()

###################################
# 테이블 생성 함수
###################################
def init_emotion_db():
    """
    SQLite에서 감정 상태 저장용 테이블 생성
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        # SQLite에서는 REAL 타입 사용, timestamp는 DATETIME
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS emotion_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
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
# 감정 벡터 유틸리티
###################################
def empty_emotion_vector():
    """
    모든 감정을 0으로 초기화한 벡터 반환
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
    감정 강도 값을 0~1 범위로 제한
    """
    return max(0.0, min(1.0, val))

def create_event_emotion_vector(joy=0.0, trust=0.0, fear=0.0, surprise=0.0,
                                sadness=0.0, disgust=0.0, anger=0.0, anticipation=0.0):
    """
    이벤트로 인한 감정 변화나 목표 감정 상태를 쉽게 정의하기 위한 헬퍼.
    """
    vec = {
        'joy': clamp_emotion_value(joy),
        'trust': clamp_emotion_value(trust),
        'fear': clamp_emotion_value(fear),
        'surprise': clamp_emotion_value(surprise),
        'sadness': clamp_emotion_value(sadness),
        'disgust': clamp_emotion_value(disgust),
        'anger': clamp_emotion_value(anger),
        'anticipation': clamp_emotion_value(anticipation)
    }
    return vec

###################################
# 감정 상태 저장 함수
###################################
def store_emotion_state(agent_id, emotion_vector):
    """
    현재 감정 상태(8차원 벡터)를 DB에 저장
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emotion_states (agent_id, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            emotion_vector['joy'],
            emotion_vector['trust'],
            emotion_vector['fear'],
            emotion_vector['surprise'],
            emotion_vector['sadness'],
            emotion_vector['disgust'],
            emotion_vector['anger'],
            emotion_vector['anticipation']
        ))
        conn.commit()

###################################
# 감정 조회 함수
###################################
def retrieve_current_emotion(agent_id, recent_n=10):
    """
    최근 N개의 감정 상태를 평균내어 현재 감정 상태 반환.
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT joy, trust, fear, surprise, sadness, disgust, anger, anticipation
            FROM emotion_states
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_id, recent_n))
        rows = cursor.fetchall()

    if not rows:
        return empty_emotion_vector()

    avg_emotion = empty_emotion_vector()
    count = len(rows)
    for row in rows:
        for i, emotion_name in enumerate(avg_emotion.keys()):
            avg_emotion[emotion_name] += row[i]
    for e in avg_emotion:
        avg_emotion[e] /= count
        avg_emotion[e] = clamp_emotion_value(avg_emotion[e])

    return avg_emotion

def recall_past_emotions(agent_id, timeframe_hours=1):
    """
    특정 시간(timeframe_hours) 동안의 감정 상태 평균 조회
    예: 지난 1시간 동안의 감정 평균
    """
    cutoff = datetime.now() - timedelta(hours=timeframe_hours)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT joy, trust, fear, surprise, sadness, disgust, anger, anticipation
            FROM emotion_states
            WHERE agent_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (agent_id, cutoff_str))
        rows = cursor.fetchall()

    if not rows:
        return empty_emotion_vector()

    avg_emotion = empty_emotion_vector()
    count = len(rows)
    for row in rows:
        for i, emotion_name in enumerate(avg_emotion.keys()):
            avg_emotion[emotion_name] += row[i]
    for e in avg_emotion:
        avg_emotion[e] /= count
        avg_emotion[e] = clamp_emotion_value(avg_emotion[e])

    return avg_emotion

###################################
# 감정 업데이트 로직
###################################
def update_emotion_state(agent_id, event_emotion_vector):
    """
    현재 감정을 조회한 후, 이벤트 감정 벡터를 반영하여 새로운 감정 상태 생성
    여기서는 단순히 현재 평균 감정과 이벤트 벡터를 평균하는 방식으로 예시
    """
    current = retrieve_current_emotion(agent_id)
    new_emotion = empty_emotion_vector()

    for e in new_emotion:
        val = (current[e] + event_emotion_vector[e]) / 2.0
        new_emotion[e] = clamp_emotion_value(val)

    store_emotion_state(agent_id, new_emotion)

###################################
# 감정 조정 함수
###################################
def adjust_emotions(agent_id):
    """
    현재 감정을 조회하고 특정 조건에 따라 조정.
    예: sadness가 0.8 이상이면 joy를 0.1 증가, sadness를 0.1 감소
    """
    current = retrieve_current_emotion(agent_id)
    sadness = current['sadness']

    if sadness > 0.8:
        current['joy'] = clamp_emotion_value(current['joy'] + 0.1)
        current['sadness'] = clamp_emotion_value(current['sadness'] - 0.1)
        # 변경 사항 DB 반영
        store_emotion_state(agent_id, current)

###################################
# 테스트용 감정 분석 함수 예제 (간단)
###################################
def analyze_sentiment(text):
    """
    매우 단순한 감정 분석:
    긍정 단어 -> 점수 상승, 부정 단어 -> 점수 하락
    최종 -1~1 범위 클램핑
    """
    positive_words = ["good", "great", "happy", "excellent", "joy", "love"]
    negative_words = ["bad", "sad", "terrible", "awful", "hate", "angry"]
    
    content_lower = text.lower()
    score = 0
    for w in positive_words:
        if w in content_lower:
            score += 0.5
    for w in negative_words:
        if w in content_lower:
            score -= 0.5
    return max(-1, min(1, score))

###################################
# 메인 테스트 예시
###################################
if __name__ == "__main__":
    init_emotion_db()
    agent_id = 1

    # 초기 감정 상태 (모두 0) 저장
    store_emotion_state(agent_id, empty_emotion_vector())

    # 사용자(상대 에이전트) 발화 예제
    user_input = "I am so happy to see you!"
    sentiment_score = analyze_sentiment(user_input)

    # 이벤트 벡터 생성: 긍정적 감정이므로 joy 증가
    if sentiment_score > 0:
        event_vector = create_event_emotion_vector(joy=0.8)
    elif sentiment_score < 0:
        event_vector = create_event_emotion_vector(sadness=0.5)
    else:
        event_vector = create_event_emotion_vector(trust=0.2)

    # 감정 업데이트
    update_emotion_state(agent_id, event_vector)
    print("Updated Emotion:", retrieve_current_emotion(agent_id))

    # 감정 조정 (예: 슬픔이 높다면 조정)
    adjust_emotions(agent_id)
    print("Adjusted Emotion:", retrieve_current_emotion(agent_id))

    # 과거 감정 회상
    past_emotion = recall_past_emotions(agent_id, timeframe_hours=1)
    print("Past 1-hour Emotion:", past_emotion)
