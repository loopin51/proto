
from agent_interaction.agents.agent import Agent


# Agent1: 감정 변화가 잦고 잘 당황, 잘 화냄. 경험 풍부.
# - 추가 특성: 단기 폭발 후 책임감 발휘, 직접적 감정 표현, 오래 일해 리더십 있지만 순간 감정에 휩쓸림
agent1_persona = (
    "Often experiences rapid emotional changes, easily startled and quick to anger, "
    "but has a wealth of experience from past major crises. "
    "Expresses sadness, anger, or anxiety very directly, sometimes surprising teammates. "
    "Short meltdown episodes happen, but eventually takes responsibility and tries to fix issues. "
    "Has led projects successfully despite emotional fluctuations."
)

# Agent2: 이성적, 주관 확실, 침착. 스스로 원칙 지킴.
# - 추가 특성: 철저한 원칙주의, 감정보다 데이터/논리를 중시, 단호한 커뮤니케이션
agent2_persona = (
    "Highly rational and calm under pressure. Holds firm personal principles and "
    "prefers logic and data over emotional pleas. Known for methodically analyzing problems "
    "before proposing solutions, and rarely raises their voice. Believes a stable set of rules "
    "is crucial in a chaotic world."
)

# Agent3: 친절하고 밝고 도덕감이 높음, 남 돕길 좋아함
# - 추가 특성: 이타주의, 낙천적, 감정 공감 능력 높음, 정의감
agent3_persona = (
    "Kind, bright, and morally driven. Strong sense of altruism, always willing to lend a hand. "
    "Believes helping others is one of the greatest joys. Stays optimistic even in tough times, "
    "and naturally empathizes with people's feelings, often acting as a mediator."
)


agent1 = Agent(name="Catarina", persona=agent1_persona, partner_name="Garen")
agent2 = Agent(name="Garen", persona=agent2_persona, partner_name="Catarina")
agent3 = Agent(name="agent_3", persona=agent3_persona, partner_name=None)
conversation_turn = 3


scenarios = {
    1: {
        "description": f"{agent1.name} is behind on a school assignment, {agent2.name} already submitted.",
        "stm": [
            (f"{agent1.name}", "I have so much to do for the assignment, I'm freaking out!", 8),
            (f"{agent2.name}", f"I already finished and submitted mine. Let me help {agent1.name}.", 6),
        ],
        "ltm": [
            (f"{agent1.name}", "Had a last-minute success before, but also faced near-failure times.", 9, None),
            (f"{agent2.name}", "Knows effective study strategies under pressure.", 8, "strategy"),
        ],
        "conversations": [
            (1, f"{agent1.name}", "Hey, the assignment is due tomorrow. I'm still behind. Can you help me?"),
            (2, f"{agent2.name}", "Sure, what's your biggest struggle? I've already submitted mine."),
        ],
        "emotions": {
            f"{agent1.name}": {"joy": 0.2, "trust": 0.3, "fear": 0.5, "surprise": 0.1, "sadness": 0.6, "disgust": 0.1, "anger": 0.4, "anticipation": 0.2},
            f"{agent2.name}": {"joy": 0.8, "trust": 0.7, "fear": 0.1, "surprise": 0.2, "sadness": 0.1, "disgust": 0.0, "anger": 0.0, "anticipation": 0.5},
        },
    },
    2: {
        "description": f"{agent1.name} is dealing with an angry client, {agent2.name} helps calm them down.",
        "stm": [
            (f"{agent1.name}", "The client is furious about the delay in our project!", 7),
            (f"{agent2.name}", "We need to address their concerns calmly and quickly.", 5),
        ],
        "ltm": [
            (f"{agent1.name}", "Had experiences of losing a major client once, feels guilt and fear.", 8, "lesson"),
            (f"{agent2.name}", "Previously overcame angry stakeholders by rational explanation.", 8, None),
        ],
        "conversations": [
            (1, f"{agent1.name}", "I just got an angry call from the client. I'm panicking."),
            (2, f"{agent2.name}", "Take a deep breath. Let's figure out a calm approach."),
        ],
        "emotions": {
            f"{agent1.name}": {"joy": 0.1, "trust": 0.2, "fear": 0.6, "surprise": 0.3, "sadness": 0.7, "disgust": 0.2, "anger": 0.5, "anticipation": 0.3},
            f"{agent2.name}": {"joy": 0.6, "trust": 0.8, "fear": 0.2, "surprise": 0.1, "sadness": 0.1, "disgust": 0.0, "anger": 0.1, "anticipation": 0.6},
        },
    },
    3: {
        "description": f"{agent1.name} and {agent2.name} are working on a group project presentation tomorrow.",
        "stm": [
            (f"{agent1.name}", "I haven't finished my slides, I'm worried about speaking in public.", 6),
            (f"{agent2.name}", "I can help you design better slides. Public speaking tips are also crucial.", 7),
        ],
        "ltm": [
            (f"{agent1.name}", "Always had stage fright but overcame it once with practice.", 8, "lesson"),
            (f"{agent2.name}", "Confident in public speaking, loves structured outlines.", 9, None),
        ],
        "conversations": [
            (1, f"{agent1.name}", "Our presentation is tomorrow, and I'm still not ready."),
            (2, f"{agent2.name}", "Let me see your slides. We'll polish them together."),
        ],
        "emotions": {
            f"{agent1.name}": {"joy": 0.3, "trust": 0.4, "fear": 0.7, "surprise": 0.5, "sadness": 0.6, "disgust": 0.2, "anger": 0.3, "anticipation": 0.4},
            f"{agent2.name}": {"joy": 0.9, "trust": 0.8, "fear": 0.1, "surprise": 0.2, "sadness": 0.0, "disgust": 0.0, "anger": 0.0, "anticipation": 0.8},
        },
    },
}

import pandas as pd

def export_scenarios_to_excel(scenarios, excel_path="scenarios.xlsx"):
    """
    scenarios 딕셔너리를 엑셀 파일(.xlsx)로 저장한다.
    
    scenarios: {
      scenario_id(int): {
        "description": str,
        "stm": [(agent_name, content, importance), ...],
        "ltm": [(agent_name, content, importance, reflection_type), ...],
        "conversations": [(turn, speaker, message), ...],
        "emotions": { agent_name: { joy, trust, fear, ... }, ... }
      },
      ...
    }
    """
    # 시나리오 리스트 (scenario_id, description)
    scenario_rows = []
    # STM (scenario_id, agent_name, content, importance)
    stm_rows = []
    # LTM (scenario_id, agent_name, content, importance, reflection_type)
    ltm_rows = []
    # Conversations (scenario_id, turn, speaker, message)
    conv_rows = []
    # Emotions (scenario_id, agent_name, joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
    emo_rows = []

    for scenario_id, scenario_data in scenarios.items():
        # (A) 시나리오 리스트
        scenario_rows.append({
            "scenario_id": scenario_id,
            "description": scenario_data["description"]
        })

        # (B) STM
        for (agent_name, content, importance) in scenario_data.get("stm", []):
            stm_rows.append({
                "scenario_id": scenario_id,
                "agent_name": agent_name,
                "content": content,
                "importance": importance
            })

        # (C) LTM
        for (agent_name, content, importance, reflection_type) in scenario_data.get("ltm", []):
            ltm_rows.append({
                "scenario_id": scenario_id,
                "agent_name": agent_name,
                "content": content,
                "importance": importance,
                "reflection_type": reflection_type
            })

        # (D) Conversations
        for (turn, speaker, message) in scenario_data.get("conversations", []):
            conv_rows.append({
                "scenario_id": scenario_id,
                "turn": turn,
                "speaker": speaker,
                "message": message
            })

        # (E) Emotions
        # "emotions": { agent_name: {joy, trust, ...}, ...}
        for agent_name, emo_dict in scenario_data.get("emotions", {}).items():
            row_data = {
                "scenario_id": scenario_id,
                "agent_name": agent_name,
                "joy": emo_dict.get("joy", 0.0),
                "trust": emo_dict.get("trust", 0.0),
                "fear": emo_dict.get("fear", 0.0),
                "surprise": emo_dict.get("surprise", 0.0),
                "sadness": emo_dict.get("sadness", 0.0),
                "disgust": emo_dict.get("disgust", 0.0),
                "anger": emo_dict.get("anger", 0.0),
                "anticipation": emo_dict.get("anticipation", 0.0)
            }
            emo_rows.append(row_data)

    # 각 시트에 저장할 pandas DataFrame 생성
    df_scenario = pd.DataFrame(scenario_rows, columns=["scenario_id", "description"])
    df_stm = pd.DataFrame(stm_rows, columns=["scenario_id", "agent_name", "content", "importance"])
    df_ltm = pd.DataFrame(ltm_rows, columns=["scenario_id", "agent_name", "content", "importance", "reflection_type"])
    df_conv = pd.DataFrame(conv_rows, columns=["scenario_id", "turn", "speaker", "message"])
    df_emo = pd.DataFrame(emo_rows, columns=[
        "scenario_id", "agent_name", "joy", "trust", "fear", "surprise",
        "sadness", "disgust", "anger", "anticipation"
    ])

    # 엑셀 파일로 저장 (pandas ExcelWriter)
    with pd.ExcelWriter(excel_path) as writer:
        df_scenario.to_excel(writer, sheet_name="scenario_list", index=False)
        df_stm.to_excel(writer, sheet_name="stm", index=False)
        df_ltm.to_excel(writer, sheet_name="ltm", index=False)
        df_conv.to_excel(writer, sheet_name="conversations", index=False)
        df_emo.to_excel(writer, sheet_name="emotions", index=False)

    print(f"Scenarios exported to Excel: {excel_path}")


export_scenarios_to_excel(scenarios, excel_path="scenarios.xlsx")
