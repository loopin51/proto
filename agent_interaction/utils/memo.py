# agent_methods.py

import sqlite3
from .memory_management import (
    add_to_short_term_memory,
    promote_to_long_term_memory,
    # 기타 필요한 함수들...
)
from .memory_management import (
    save_message_to_db,
    save_thought_process_to_db,
    debug_log,
    retrieve_reflections_from_db
)
from .llm_connector import query_llm  # LLM API 호출 함수
from .prompt_templates import c_onversation_prompt
from .general_methods import parse_llm_response
# 감정 관련 함수들 import
from .emotion_methods import (
    retrieve_current_emotions,
    update_emotion,
    adjust_emotions,
    analyze_sentiment
)
from .context_methods import g_enerate_context

def agent_conversation(database_path, agent1, agent2, message, conversation_turn, context=None):
    """
    Handle agent conversation and manage memories, incorporating all reflection types and emotion logic.
    Also includes conversation history as context.

    Args:
        database_path (str): Path to the SQLite database.
        agent1 (Agent): The agent initiating the conversation.
        agent2 (Agent): The agent responding to the conversation.
        message (str): The message from agent1 to agent2.
        conversation_turn (int): The current turn in the conversation.
        context (str, optional): Context string containing memories and conversation history. Defaults to None.

    Returns:
        tuple: (response speech from agent2, updated conversation turn)
    """
    debug_log(f"{agent1.name} is talking to {agent2.name} with message: {message}. Conversation turn: {conversation_turn}")

    try:
        # 1) Context가 없으면 생성 (이미 대화 기록이 포함됨)
        if context is None:
            context = g_enerate_context(database_path, agent2, max_stm=5, max_ltm=5, history_limit=10)

        # 2) 상대방(Agent1)의 말에 대한 감정 분석 (agent2가 이를 듣고 기분이 변함)
        sentiment_score = analyze_sentiment(message)
        if sentiment_score > 0:
            event_type = 'positive_interaction'
        elif sentiment_score < 0:
            event_type = 'negative_interaction'
        else:
            event_type = 'neutral_interaction'

        # 감정 업데이트
        update_emotion(database_path, agent2.name, event_type, sentiment_score)
        # 필요하다면 감정 조정
        adjust_emotions(database_path, agent2.name)

        # 3) agent2의 현재 감정 상태 조회
        current_emotions = retrieve_current_emotions(database_path, agent2.name)
        # 감정 상태를 문자열로 변환
        emotion_text = f"Emotional State of {agent2.name}: " + ", ".join(
            f"{k}={v:.2f}" for k, v in current_emotions.items()
        )

        # 4) 메모리 컨텍스트와 리플렉션 가져오기 (이미 generate_context에서 포함됨)
        memory_context = context  # generate_context에서 이미 대화 기록 포함
        reflections = retrieve_reflections_from_db(database_path, agent2.name)

        # 5) 대화 프롬프트에 감정 상태 및 대화 기록 추가
        prompt = c_onversation_prompt(
            agent1.name,
            agent1.persona,
            agent2.name,
            message,
            memory_context,
            reflections,
            emotion_text=emotion_text  # 추가된 파라미터로 감정 상태 전달
            # history_text는 generate_context에서 이미 포함되어 있음
        )

        # 6) LLM에 프롬프트 전송
        llm_response = query_llm(prompt)

        if not isinstance(llm_response, dict) or "choices" not in llm_response:
            raise ValueError("Invalid LLM response format.")

        # 7) LLM 응답 파싱
        content = llm_response["choices"][0]["message"]["content"]
        speech, thought_process = parse_llm_response(content)

        debug_log(f"{agent2.name} answered : {speech}")

        # 8) 에이전트(Agent2)의 응답에 대한 감정 분석 (자신의 발화가 자기 감정에도 영향 줄 수 있음)
        response_sentiment_score = analyze_sentiment(speech)
        if response_sentiment_score > 0:
            resp_event = 'positive_interaction'
        elif response_sentiment_score < 0:
            resp_event = 'negative_interaction'
        else:
            resp_event = 'neutral_interaction'

        # 응답에 대한 감정 업데이트 및 조정
        update_emotion(database_path, agent2.name, resp_event, response_sentiment_score)
        adjust_emotions(database_path, agent2.name)

        # 9) agent2가 말한 내용을 STM에 추가
        add_to_short_term_memory(
            database_path,
            {"content": speech, "agent_name": agent2.name},
            context
        )
        promote_to_long_term_memory(database_path, agent2.name)

        # 10) 대화 로그 DB 저장
        save_message_to_db(database_path, conversation_turn, agent1.name, message)
        #conversation_turn += 1 #이거 안해야함 나중에 고치셈
        save_message_to_db(database_path, conversation_turn, agent2.name, speech)
        conversation_turn += 1

        # 11) thought_process 저장
        save_thought_process_to_db(database_path, agent2.name, thought_process)

        return speech, conversation_turn

    except Exception as e:
        print(f"Error in agent_conversation: {e}")
        save_message_to_db(database_path, conversation_turn, "Error", str(e))
        #conversation_turn += 1
        raise