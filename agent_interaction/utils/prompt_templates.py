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
    if reflection_type == "strategy": #응답 포맷 정형화 필요
        return (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            f"Short-term memories:\n" + "\n".join(short_term_memories) + "\n\n"
            f"Long-term memories:\n" + "\n".join(long_term_memories) + "\n\n"
            f"What is the best course of action for the current situation? Provide a detailed reasoning and action plan."
        )
    elif reflection_type == "lesson":
        return (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            f"Short-term memories:\n" + "\n".join(short_term_memories) + "\n\n"
            f"Long-term memories:\n" + "\n".join(long_term_memories) + "\n\n"
            f"Summarize the key lessons learned from these experiences."
        )
    elif reflection_type == "summary":
        return (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            f"Short-term memories:\n" + "\n".join(short_term_memories) + "\n\n"
            f"Long-term memories:\n" + "\n".join(long_term_memories) + "\n\n"
            f"Summarize these memories into a concise overview."
        )
    elif reflection_type == "prediction":
        return (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            f"Short-term memories:\n" + "\n".join(short_term_memories) + "\n\n"
            f"Long-term memories:\n" + "\n".join(long_term_memories) + "\n\n"
            f"Predict the likely outcomes of taking the current proposed action."
        )
    else:  # Default to general reflection
        return (
            f"Based on the following memories of agent '{agent_name}':\n\n"
            f"Short-term memories:\n" + "\n".join(short_term_memories) + "\n\n"
            f"Long-term memories:\n" + "\n".join(long_term_memories) + "\n\n"
            f"Reflect on these memories and generate a summary or insight."
        )

def summarize_memory_prompt(content, context):
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