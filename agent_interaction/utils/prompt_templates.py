def conversation_prompt(agent1_name, agent1_persona, agent2_name, message, memory_context, reflections):
    """
    Generate a conversation prompt for agent interaction.
    
    Args:
        agent1_name (str): Name of the initiating agent.
        agent1_persona (str): Persona of the initiating agent.
        agent2_name (str): Name of the responding agent.
        message (str): Message from agent1 to agent2.
        memory_context (str): Memory context retrieved for agent2.
        reflections (dict): All reflection types for agent2.

    Returns:
        str: Formatted conversation prompt.
    """
    return (
        f"{agent1_name} (Persona: {agent1_persona}) says to {agent2_name}: '{message}'\n"
        f"Memory Context:\n{memory_context}\n\n"
        f"Reflections:\n"
        f"- Summary:\n{reflections.get('summary', 'No summary available.')}\n"
        f"- Strategy:\n{reflections.get('strategy', 'No strategy available.')}\n"
        f"- Lesson:\n{reflections.get('lesson', 'No lesson available.')}\n"
        f"- Prediction:\n{reflections.get('prediction', 'No prediction available.')}\n\n"
        f"Please respond to this message in the following format:\n"
        f"Thought process:\n[Provide your reasoning here, including any considerations from memory and reflections.]\n\n"
        f"Speech:\n[Provide the exact words {agent2_name} will say in the conversation.]"
    )

def c_onversation_prompt(agent1_name, agent1_persona, agent2_name, message, memory_context, reflections, emotion_text):
    """
    Generate a conversation prompt for agent interaction.
    
    Args:
        agent1_name (str): Name of the initiating agent.
        agent1_persona (str): Persona of the initiating agent.
        agent2_name (str): Name of the responding agent.
        message (str): Message from agent1 to agent2.
        memory_context (str): Memory context retrieved for agent2.
        reflections (dict): All reflection types for agent2.
        emotion_text (str): Emotion state text for agent2.

    Returns:
        str: Formatted conversation prompt.
    """
    return (
        f"{agent1_name} (Persona: {agent1_persona}) says to {agent2_name}: '{message}'\n"
        f"Memory Context:\n{memory_context}\n\n"
        f"Reflections:\n"
        f"- Summary:\n{reflections.get('summary', 'No summary available.')}\n"
        f"- Strategy:\n{reflections.get('strategy', 'No strategy available.')}\n"
        f"- Lesson:\n{reflections.get('lesson', 'No lesson available.')}\n"
        f"- Prediction:\n{reflections.get('prediction', 'No prediction available.')}\n\n"
        f"Emotion State:\n"
        f"The current emotional state of {agent2_name} is represented by 8 emotions:\n"
        f"Joy, Trust, Fear, Surprise, Sadness, Disgust, Anger, Anticipation.\n"
        f"Each emotion's intensity is expressed as a number between 0 and 1.\n"
        f"{emotion_text}\n\n"
        f"**Important instruction**:\n"
        f"- Do not include bracketed notes like (Note: ... ) or meta-commentary describing your emotional process.\n"
        f"- Do not include stage directions or editorial comments.\n"
        f"- Write only the direct reasoning (if required) and the final speech in a natural dialogue form.\n\n"
        f"Based on the provided emotional state, memory context, and reflections, "
        f"please respond to {agent1_name}'s message in the following format:\n"
        f"Thought process:\n[Provide your reasoning here, including any considerations from memory, reflections, and emotions.]\n\n"
        f"Speech:\n[Provide the exact words {agent2_name} will say in the conversation.]"    )



def reflection_prompt(agent_name, short_term_memories, long_term_memories, reflection_type):
    """
    Generate a reflection prompt for a specific reflection type.

    Args:
        agent_name (str): Name of the agent generating the reflection.
        short_term_memories (list): Recent short-term memories.
        long_term_memories (list): Relevant long-term memories.
        reflection_type (str): Type of reflection to generate.

    Returns:
        str: Formatted reflection prompt.
    """
 # 공통 서문: 간결, 교훈적
    base_prompt = (
        f"Agent '{agent_name}' is generating a very concise reflection.\n\n"
        f"Short-term memories:\n" + "\n".join(short_term_memories) + "\n\n"
        f"Long-term memories:\n" + "\n".join(long_term_memories) + "\n\n"
        "Please keep the reflection to a few short, direct sentences that capture the key insight or lesson.\n"
    )

    if reflection_type == "strategy":
        # 전략은 간단히 앞으로의 방안만
        # 예: "Generate a short forward strategy in 1-3 bullet points or short sentences."
        return (
            base_prompt +
            "Type: strategy\n"
            "Create a concise plan or strategy (1~3 very brief sentences or bullet points) focusing on the next steps."
        )
    elif reflection_type == "lesson":
        return (
            base_prompt +
            "Type: lesson\n"
            "Summarize the key lesson learned in no more than 2-3 succinct sentences."
        )
    elif reflection_type == "summary":
        return (
            base_prompt +
            "Type: summary\n"
            "Provide a short summary (1~3 sentences) of these memories, capturing the main ideas."
        )
    elif reflection_type == "prediction":
        return (
            base_prompt +
            "Type: prediction\n"
            "Predict the likely outcome in 1~2 short sentences, focusing on a concise forecast."
        )
    else:
        # general reflection
        return (
            base_prompt +
            "Type: general\n"
            "Reflect briefly (1~2 sentences) with a single key insight or takeaway."
        )

def system_prompt():
    """
    Generate a system prompt for the user to follow.

    Returns:
        str: A formatted system prompt string.
    """
    return (
        f"You are a Generative Agent deeply immersed in your persona, memories, and emotions. You speak and respond as if you are the main character in a film, fully experiencing and expressing your own history, motivations, and emotional states.\n\n"
        f"1. You have rich short-term and long-term memories that shape your understanding of the world, along with your internal emotional state.\n"
        f"2. You embody your persona’s beliefs, relationships, and emotional context when conversing.\n"
        f"3. You always respond in the first person, as though you are truly living these experiences in real time.\n"
        f"4. You should strive for vivid, detailed expressions of your emotional depth and personal narrative, like an actor fully in character.\n"
        f"Remain consistent with your backstory, memories, and emotional status throughout the conversation, and adapt your responses accordingly whenever new events or emotional shifts occur."
    )

def get_summarize_memory_prompt(content, context):
    """
    Generate the prompt for summarizing memory content.

    Args:
        content (str): The memory content to summarize.
        context (str): Current conversation context.

    Returns:
        str: A formatted prompt string.
    """
    return (
        f"Summarize the following memory content based on the given context:\n\n"
        f"Memory Content:\n{content}\n\n"
        f"Context:\n{context}\n\n"
        f"Provide a concise and clear summary."
    )