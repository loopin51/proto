## 목차

1. 소개
2. 이론적 배경
3. 프로젝트의 디렉토리 구조
4. 함수 설명
5. 에이전트 간의 대화 과정 및 방법
6. 향후 개선 방안
7. 참고

---

## 1. 소개

본 프로젝트는 **에이전트 기반 시스템**에서의 메모리 관리와 대형 언어 모델(**Large Language Model**, 이하 LLM)을 활용한 AI의 감정 구현 방안을 연구하는 것을 목적으로 한다. 특히, 에이전트는 상황별 **메모리 스트림**을 기반으로 대화에 참여하며, 단기 기억(**Short-Term Memory**, 이하 STM)과 장기 기억(**Long-Term Memory**, 이하 LTM)을 효율적으로 관리하여 적절한 회상과 응답을 제공한다. 또한 선행 연구에 적극적인 감정 시스템을 개발 및 적용하는 것이 주 목표이다.
 
현재 구현한 주요 기능은 다음과 같다:

- 에이전트 간 자동 대화 및 사용자 입력 기반 대화 지원
- 메모리 스트림(단기 기억 및 장기 기억) 관리
- 기억 중요도 평가 및 승격
- Flask 기반 웹 인터페이스를 통한 상호작용 지원

본 연구는 멀티 에이전트 협업 시나리오를 가정하여 개발되었으며, 실시간 대화 품질 향상을 위한 중요도 평가와 메모리 관리 로직을 포함한다.

---

## 2. 이론적 배경

### 에이전트

에이전트는 **독립적인 개체**로서 특정한 역할과 성격을 지닌다. 각 에이전트는 상황에 맞게 기억을 활용하여 응답을 생성하며, 시간이 지남에 따라 경험을 축적한다. 에이전트의 주요 특징은 다음과 같다:

- **개별 성격**: 각 에이전트는 고유한 목표와 성격을 가진다.
- **기억 관리**: 단기 기억(STM)과 장기 기억(LTM)을 활용한다.
- **회상 생성**: 기억에서 교훈, 전략, 요약 등의 회상을 추출한다.

### LLM (Large Language Model)

LLM은 에이전트가 생성하는 대화, 요약, 회상 작업에서 중요한 역할을 담당한다. 본 프로젝트에서는 **SentenceTransformer**와 같은 임베딩 모델을 활용하여 다음의 작업을 수행한다:

- 대화에 사용되는 **프롬프트 생성**
- 기억 요약 및 중요도 평가
- 메모리 간 **유사도 계산** 및 회상 생성

LLM은 문맥 이해 능력을 바탕으로 단순한 대화에서 벗어나, 기억과 성격을 반영한 정교한 응답을 생성한다.

### 메모리 스트림의 구조와 작동 원리

**Memory DB**는 에이전트의 기억을 관리하기 위해 SQLite로 구현되며, 다음과 같은 테이블로 구성된다:

1. **short\_term\_memory (STM)**

   - **목적**: 최근 대화 맥락과 이벤트를 저장하여 즉각적인 상황에 대응한다.
   - **구성**:
     - `id`: 고유 식별자
     - `agent_name`: 에이전트 이름
     - `timestamp`: 저장된 시간
     - `content`: 기억 내용
     - `importance`: 중요도 점수
     - `reference_count`: 참조 횟수

2. **long\_term\_memory (LTM)**

   - **목적**: 장기적으로 유지해야 할 중요한 기억과 회상을 저장한다.
   - **구성**:
     - `id`: 고유 식별자
     - `agent_name`: 에이전트 이름
     - `content`: 기억 내용
     - `importance`: 중요도 점수
     - `last_accessed`: 마지막 접근 시간
     - `reflection_type`: 회상 유형 (전략, 교훈 등)
     - `reference_count`: 참조 횟수

3. **conversations**

   - **목적**: 대화 기록을 저장하여 에이전트 간 상호작용을 추적한다.
   - **구성**:
     - `id`: 고유 식별자
     - `turn`: 대화 차례
     - `speaker`: 발화자
     - `message`: 메시지 내용

4. **thought\_processes**

   - **목적**: 에이전트의 사고 과정과 추론 내용을 저장한다.
   - **구성**:
     - `id`: 고유 식별자
     - `agent_name`: 에이전트 이름
     - `thought_process`: 사고 과정 내용

**중요도 평가 방법**

중요도는 다음 네 가지 요소를 기반으로 계산된다:

1. **Relevance (관련성)**
   - `context_score`를 통해 현재 대화 맥락과 기억 간의 **코사인 유사도**를 측정한다.
   - SentenceTransformer 모델을 활용해 기억과 맥락을 임베딩한 후 계산한다.

2. **Recency (최신성)**
   - 기억이 생성된 시간 기준으로 최근일수록 높은 점수를 부여한다.
   - 예시: `10 - (경과 시간(분) // 10)`

3. **Frequency (참조 빈도)**
   - 기억이 얼마나 자주 참조되었는지를 기준으로 점수를 부여한다.
   - 예시: `min(10, 참조 횟수 * 2)`

4. **Sentiment (감정 분석)**
   - 기억의 감정적 긍정성을 분석하여 점수를 부여한다.
   - TextBlob 라이브러리를 사용하여 -1~1 값을 0~10으로 변환한다.

**중요도 계산 수식**:

```
importance = (0.4 * relevance) + (0.3 * recency_score) + (0.2 * frequency_score) + (0.1 * sentiment_score)
```

이 계산을 통해 중요도가 높은 기억은 장기 기억으로 승격되며, 상대적으로 덜 중요한 기억은 단기 기억에서 삭제된다.

---

## 3. 프로젝트의 디렉토리 구조

```plaintext
PROTO
├── agent_interaction
│   ├── agents
│   │   ├── agent.py
│   ├── database
│   │   ├── conversations.db
│   ├── memory
│   │   ├── agent_memory.json
│   ├── static
│   │   ├── style.css
│   ├── templates
│   │   ├── index.html
│   │   ├── memory.html
│   │   ├── reflection.html
│   ├── tests
│   │   ├── test_conversation.py
│   │   ├── test_endpoints.py
│   │   ├── test_memory.py
│   ├── utils
│       ├── agent_methods.py
│       ├── context_methods.py
│       ├── llm_connector.py
│       ├── prompt_templates.py
├── app.py
├── preset_db.py
├── requirements.txt
```

---

## 4. 구현한 함수들에 대한 대략적 설명

### 주요 함수

- **`agent_conversation`**: 에이전트 간 대화를 관리하고 메모리를 업데이트한다.
- **`manage_memories`**: 메모리의 중요도를 재평가하고 중요한 기억을 승격한다.
- **`generate_reflection`**: 기억을 요약하고 교훈을 추출하는 회상을 생성한다.
- **`calculate_importance`**: 네 가지 기준을 사용하여 기억의 중요도를 계산한다.
- **`add_to_short_term_memory`**: 새로운 기억을 요약 후 STM에 추가한다.
- **`promote_to_long_term_memory`**: 중요도가 높은 기억을 STM에서 LTM으로 승격한다.
- **`generate_context`**: 현재 대화 맥락을 생성하고 반환한다.
- **`reflection_tree`**: 기억의 구조를 시각화하고 에이전트의 자기 개념을 생성한다【10†source】.

---

## 5. 에이전트 간의 대화 과정 및 방법

에이전트 간 대화는 다음과 같은 과정을 따른다:

1. **대화 시작**:
   - 한 에이전트가 메시지를 전송하며 대화가 시작된다. 메시지와 대화 턴(turn) 정보는 데이터베이스에 저장된다.

2. **컨텍스트 생성**:
   - 대상 에이전트는 `generate_context` 함수를 사용해 STM과 LTM 데이터를 기반으로 컨텍스트를 생성한다.
   - 생성된 컨텍스트는 대화의 흐름과 기억 참조를 돕는 역할을 한다.

3. **회상 참조**:
   - 에이전트는 `retrieve_reflections_from_db`를 통해 이전에 생성된 회상을 참조하여 대화의 맥락을 이해한다.

4. **LLM을 통한 응답 생성**:
   - 생성된 컨텍스트와 회상을 기반으로 대화 프롬프트가 생성된다.
   - 프롬프트는 LLM에 전달되어 적절한 응답과 사고 과정을 반환받는다.

5. **기억 업데이트**:
   - 대화 응답은 `add_to_short_term_memory` 함수를 통해 STM에 저장된다.
   - 중요도 평가를 통해 STM 데이터를 정리하고, 필요 시 LTM으로 승격된다.

6. **데이터 저장**:
  화

---

## 7. 참고

- OpenAI API 문서
- SentenceTransformer: [https://www.sbert.net/](https://www.sbert.net/)
- TextBlob: [https://textblob.readthedocs.io/](https://textblob.readthedocs.io/)
- Generative Agents: Interactive Simulacra of Human Behavior【10†source】.

