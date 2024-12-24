from datetime import datetime
from textblob import TextBlob
from sentence_transformers import SentenceTransformer, util
from utils.prompt_templates import *
from utils.context_methods import *

model = SentenceTransformer('all-MiniLM-L6-v2') #model used for context similarity calculation

# 중요도 계산 함수
def calculate_importance(content, context, recency, frequency, sentiment):
    """
    Calculate importance based on multiple factors.
    Args:
        content (str): The memory content.
        context (str): Current conversation or context.
        recency (int): Time elapsed since the memory was created.
        frequency (int): How often the memory has been accessed or mentioned.
        sentiment (float): Sentiment analysis score (-1 to 1).

    Returns:
        int: Importance score (0 to 10).
    """
    w1, w2, w3, w4 = 0.4, 0.3, 0.2, 0.1  # Weights for each factor
    relevance = context_score(content, context)
    recency_score = max(0, 10 - recency // 10)  # Example: scale recency to 0-10
    frequency_score = min(10, frequency * 2)  # Example: scale frequency to 0-10
    sentiment_score = max(0, min(10, (sentiment + 1) * 5))  # Scale sentiment to 0-10

    return int(w1 * relevance + w2 * recency_score + w3 * frequency_score + w4 * sentiment_score)

def calculate_recency(timestamp):
    """
    Calculate recency score based on the timestamp.

    Args:
        timestamp (str): Timestamp of the memory (YYYY-MM-DD HH:MM:SS).

    Returns:
        int: Recency score.
    """
    try:
        memory_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        elapsed_time = (datetime.now() - memory_time).total_seconds() // 60  # Elapsed time in minutes
        return max(0, 10 - int(elapsed_time // 10))  # Scale to 0-10
    except Exception as e:
        print(f"Error calculating recency: {e}")
        return 0

def get_frequency(conn, table_name, content):
    """
    Calculate frequency of a memory in the database.

    Args:
        conn (sqlite3.Connection): SQLite database connection.
        table_name (str): Table name to query.
        content (str): Memory content.

    Returns:
        int: Frequency count.
    """
    cursor = conn.cursor()
    cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE content = ?', (content,))
    frequency = cursor.fetchone()[0]
    return frequency

def context_score(memory_content, current_context):
    """
    Calculate similarity score between a memory content and the current context.

    Args:
        memory_content (str): Memory content to evaluate.
        current_context (str): Current context as a single string.

    Returns:
        float: Similarity score scaled to 0-10.
    """
    # Ensure current_context is processed as a list of individual memory lines
    if isinstance(current_context, str):
        context_lines = current_context.split("\n")
        # Filter out metadata lines like 'Short-term memories:' or 'Long-term memories:'
        context_lines = [line.strip() for line in context_lines if line.strip() and ":" not in line]
    else:
        raise ValueError("current_context must be a string.")

    try:
        memory_embedding = model.encode(memory_content, convert_to_tensor=True)
        context_embeddings = model.encode(context_lines, convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(memory_embedding, context_embeddings)

        # Return the highest similarity score scaled to 0-10
        return float(similarity.max().item()) * 10
    except Exception as e:
        print(f"Error calculating context score: {e}")
        return 0.0


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
