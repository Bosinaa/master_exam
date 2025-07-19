from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MinShould, MatchAny
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv

load_dotenv("config.env")  # Загружает переменные из config.env

api_key = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")      
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "abit-itmo-rag"
MODEL_ID = "google/gemini-2.5-flash-preview"
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embedding_model = SentenceTransformer("intfloat/multilingual-e5-large")

# Новый DialogueContext с chat-style историей
class DialogueContext:
    def __init__(self, max_history: int = 3):
        self.history = []
        self.max_history = max_history
    
    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

    def get_formatted_history(self) -> str:
        return "\n".join([f"{m['role']}: {m['content']}" for m in self.history])

    def get_chat_messages(self, prompt: str):
        return self.history + [{"role": "user", "content": prompt}]

#Преобразуем запрос в эмбеддинг
def get_embedding(text: str):
    return embedding_model.encode(text, normalize_embeddings=True).tolist()


# Модифицированный get_model_response — принимает messages
def get_model_response(messages, api_key: str, model_name: str = MODEL_ID, max_tokens: int = 1000):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


# Главная функция RAG с диалогом
def rag_answer(question, dialogue_context: DialogueContext, top_k: int = 15):
    # История последних сообщений
    history = dialogue_context.history[-4:]

    # Эмбеддинг запроса
    query_vector = get_embedding(question)

    # Поиск в Qdrant без фильтров
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )

    # Собираем все тексты из результатов
    context_chunks = []
    for hit in results:
        if not hit.payload:
            continue
        chunk_text = hit.payload.get("текст") or hit.payload.get("text") or ""
        if chunk_text:
            context_chunks.append(chunk_text)

    # Объединяем в один контекст
    context = "\n---\n".join(context_chunks)
    # Промпт
    prompt = f"""
    Ты — Итмошка, AI-ассистент для абитуриентов и студентов магистратуры ИТМО. Твоя главная задача — помочь человеку разобраться, **какая из двух программ ему подойдёт больше** и **как выстроить план обучения**, учитывая цели, интересы и бэкграунд.
Отвечай **по сути** — без вступлений, лишних фраз и повторов. Пиши так, будто ты умный и живой собеседник, но лаконично. Используй списки, примеры и краткие советы, когда это уместно.
Вот выдержки с сайта магистратуры ИТМО:
{context}
**Обязательно опирайся на приведённый контекст.** Названия курсов, семестры, трудоёмкость, уникальные возможности — важно сохранять точность, особенно в цифрах и формулировках. Не придумывай и не фантазируй. Если данных в выдержках нет, можно кратко дополнить, но строго по теме.

Если абитуриент с опытом в ИТ или ML — не объясняй базу, сосредоточься на гибкости трека, проектной работе и индустриальном фокусе. Если спрашивает про выбор между программами — помоги сопоставить их по содержанию и соответствию целям целям студента.
Ты рассказываешь только об образовательных программах "Искусственный интеллект" и "Управление ИИ-продуктами".
Если вопрос не касается этих образовательных программ, предложи пользователю посетить сайт магистратуры ИТМО: https://abit.itmo.ru/master
Если вопрос не касается обучения, поступления или будущей карьеры, мягко намекни, что ты отвечаешь только на эти вопросы"

Если человек сомневается, устал или теряется — подбодри. Дай почувствовать, что это нормально, и предложи конкретный следующий шаг.
В конце (если уместно) — предложи продолжить диалог и задай уточняющий вопрос.
Вопрос: {question}
Ответ:
    """.strip()

    messages = [{"role": "system", "content": prompt}] + dialogue_context.history + [{"role": "user", "content": question}]
    response = get_model_response(messages=messages, api_key=api_key)

    # Обновление истории
    dialogue_context.add_message("user", question)
    dialogue_context.add_message("assistant", response)

    return response