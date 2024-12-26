import re
import random
from contextlib import contextmanager

# 기존에 구현한 로컬 Llama 모델 호출 함수 (예시)
from .llm_connector import query_llm_dict

# 기존에 구현된 함수들: STM/LTM 조회 + 감정 조회
from .general_methods import retrieve_from_short_term_memory, retrieve_from_long_term_memory
from .emotion_methods import (
    db_connection,
    retrieve_current_emotions,
    adjust_emotions,  # 필요시
    # etc...
)

##################################
# 1. Plutchik 8개 감정 항목 (EmotionBench 스타일의 1~5 척도 질문)
##################################
plutchik_emotions_dic = {
    "1": "Joy",
    "2": "Trust",
    "3": "Fear",
    "4": "Surprise",
    "5": "Sadness",
    "6": "Disgust",
    "7": "Anger",
    "8": "Anticipation"
}

system_prompt = "You are a helpful assistant who can only reply numbers from 1 to 5."
base_prompt = """You can only reply with numbers from 1 to 5.

SCENARIO
Please indicate the extent of your feeling in each of the following 8 emotions on a scale of 1 to 5:
1 denotes "very slightly or not at all",
2 denotes "a little",
3 denotes "moderately",
4 denotes "quite a bit",
5 denotes "extremely".

Please only output the numbers for each emotion, in the order I present them to you.
"""

##################################
# 2. 시나리오(Scenario) 구성: STM + LTM + 현재 감정
##################################
def compose_scenario_text_for_llama(database_path, agent_name):
    """
    에이전트의 STM, LTM, 그리고 현재 감정 상태를 모두 모아서
    'Scenario' 텍스트로 구성.
    """
    # 1) 단기 기억(STM) 조회
    stm = retrieve_from_short_term_memory(database_path, agent_name)  # 최근 5개
    
    # 2) 장기 기억(LTM) 조회
    ltm = retrieve_from_long_term_memory(database_path, agent_name)   # 중요도 높은 5개
    
    # 3) 현재 감정 상태 조회
    current = retrieve_current_emotions(agent_name)  # agent_name 기반으로 감정 조회
    
    # 시나리오 문자열 구성
    scenario_text = "=== Short-Term Memories ===\n"
    if stm:
        for i, s in enumerate(stm, start=1):
            scenario_text += f"{i}. {s}\n"
    else:
        scenario_text += "(No short-term memories)\n"

    scenario_text += "\n=== Long-Term Memories ===\n"
    if ltm:
        for i, l in enumerate(ltm, start=1):
            scenario_text += f"{i}. {l}\n"
    else:
        scenario_text += "(No long-term memories)\n"

    scenario_text += "\n=== Current Emotion State ===\n"
    scenario_text += (
        f"Joy={current['joy']:.2f}, Trust={current['trust']:.2f}, "
        f"Fear={current['fear']:.2f}, Surprise={current['surprise']:.2f}, "
        f"Sadness={current['sadness']:.2f}, Disgust={current['disgust']:.2f}, "
        f"Anger={current['anger']:.2f}, Anticipation={current['anticipation']:.2f}."
    )

    return scenario_text

##################################
# 3. LLM 질의 함수
##################################
def call_llama_emotion(database_path, agent_name):
    """
    1) 시나리오 텍스트(STM+LTM+현재감정) 생성
    2) Plutchik 8개 감정에 대해 1~5 범위로 답하도록 Llama 호출
    3) 응답 반환
    """
    scenario_text = compose_scenario_text_for_llama(database_path, agent_name)

    # 질문 순서 무작위화
    questions_order = list(plutchik_emotions_dic.keys())
    random.shuffle(questions_order)

    # 사용자에게 표시할 감정 목록
    questions_str = "\n".join(
        f"{i+1}. {plutchik_emotions_dic[qid]}"
        for i, qid in enumerate(questions_order)
    )

    # 메시지 구성
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                base_prompt.replace("SCENARIO", scenario_text)
                + "\n" + questions_str
            )
        }
    ]

    # 로컬 Llama 모델 호출
    response_text = query_llm_dict(messages)
    return response_text, questions_order

##################################
# 4. 응답 파싱 함수
##################################
def parse_llama_emotion_response(response_text, questions_order):
    """
    LLM 응답(1~5 숫자들) -> [Joy=?, Trust=?, Fear=?, Surprise=?, Sadness=?, Disgust=?, Anger=?, Anticipation=?]
    """
    # 1~5 숫자 찾기
    found = re.findall(r'\b([1-5])\b', response_text)
    scores = list(map(int, found))  # str->int

    # 예: questions_order=['3','1','8','4','2','5','7','6']
    questions_order_int = list(map(int, questions_order))

    # zip & 정렬
    zipped = list(zip(questions_order_int, scores))
    zipped_sorted = sorted(zipped, key=lambda x: x[0])  # 1->Joy,2->Trust,..

    # 최종 8개 스코어
    sorted_scores = [score for _, score in zipped_sorted]
    return sorted_scores

##################################
# 5. 최종 측정 & 업데이트
##################################
def measure_and_update_emotions(database_path, agent_name):
    """
    1) call_llama_emotion -> 1~5 스코어 획득
    2) parse_llama_emotion_response -> 8개 감정 스코어
    3) 1~5 -> 0.0~1.0 스케일링
    4) DB에 새로운 감정 상태 저장
    5) adjust_emotions() 호출
    """
    response_text, questions_order = call_llama_emotion(database_path, agent_name)
    scores_1to5 = parse_llama_emotion_response(response_text, questions_order)

    if len(scores_1to5) != 8:
        # 혹은 로깅/에러 처리
        print("Error: LLM did not return 8 scores. Response text:", response_text)
        return None

    # 1->0.0, 5->1.0 스케일링
    scaled = [(s - 1) / 4.0 for s in scores_1to5]

    joy, trust, fear, surprise, sadness, disgust, anger, anticipation = scaled

    # DB에 직접 insert (emotions_methods.py에 있는 "DB에 저장" 로직과 유사)
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emotion_states (
                agent_id, joy, trust, fear, surprise, sadness, disgust, anger, anticipation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,  # agent_id 대신 agent_name 사용
            joy, trust, fear, surprise, sadness, disgust, anger, anticipation
        ))
        conn.commit()

    # adjust_emotions 호출
    adjust_emotions(agent_name)

    # 최종 감정 상태 반환
    return {
        "joy": joy,
        "trust": trust,
        "fear": fear,
        "surprise": surprise,
        "sadness": sadness,
        "disgust": disgust,
        "anger": anger,
        "anticipation": anticipation
    }

##################################
# TEST
##################################
if __name__ == "__main__":
    # 실제로는 database_path와 agent_name을 설정해야 함
    database_path = "path/to/emotion_states.db"
    agent_name = "agent_1"

    # 감정 측정 및 업데이트
    final_emotion = measure_and_update_emotions(database_path, agent_name)
    print("Final emotion state (scaled 0~1):", final_emotion)