from flask import Flask, render_template, request
from agents.agent import Agent
from utils.llm_connector import query_llm

app = Flask(__name__)

# 에이전트 초기화
agent1 = Agent("John", "Friendly pharmacist who likes helping others.")
agent2 = Agent("Maria", "Artist who enjoys painting and nature.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conversation', methods=['POST'])
def conversation():
    user_message = request.form['message']
    response = agent_conversation(agent1, agent2, user_message)
    return render_template('index.html', user_message=user_message, agent_response=response)

def agent_conversation(agent1, agent2, message):
    prompt = (
        f"{agent1.name} (Persona: {agent1.persona}) says to {agent2.name}: '{message}'\n"
        f"{agent2.name}'s memory: {agent2.memory_stream}\n"
        f"How should {agent2.name} respond?"
    )
    return query_llm(prompt)

if __name__ == '__main__':
    app.run(debug=True)