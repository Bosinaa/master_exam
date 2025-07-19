# Ответы на вопросы
from telebot import types
import mysql.connector
import re
import random
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import os
# Импорт кода RAG
from RAG  import rag_answer, DialogueContext

dialogue_contexts = {}

# Список стикеров для эмоций
emotion_stickers = [
        "CAACAgIAAxkBAAIHBGg0cCcWwGYHcX8nhUR0hZyq8RFAAAKLbQACQi-hSWQrPNDRDfaONgQ",
        "CAACAgIAAxkBAAIGbGg0TuSO0aNPWvKm60Bwiw9NULOEAAJtdgACpr6hSXy4hRKdMQ4ONgQ", 
        "CAACAgIAAxkBAAIGdmg0T_QpKJfgNbI67_hG7XIPF2zfAALYYgACBZOhSaeRjMJjeOnWNgQ", 
        "CAACAgIAAxkBAAIGd2g0UAlhs6-X2CkeENBzbtrvVT2zAAI-agACZYegSTzfQYpWNee7NgQ",
        "CAACAgIAAxkBAAMMaF1g1GKEmN50VFnfRc2o5B0NCg0AAiF1AALzzehKhRRzAl8s9WY2BA"] 
# Список стикеров для вопросов про зарплату
salary_stickers = ["CAACAgIAAxkBAAIGcmg0T7xvPtwwcRKi9cPmV7bSyg-_AAJmagACpsWhSVyqtTQYD5elNgQ"]

def llm_tasks(bot):
    user_state = {}
    @bot.message_handler(func=lambda message: message.text == "Да")
    def ask_no_program(message):
        user_id = message.chat.id
        user_state[user_id] = {
            'step': 'waiting_for_question',
            'message_count': 0 
        }
        bot.send_message(user_id, "Отлично! Я готов рассказать тебе всё о программах <b>Искусственный интеллект</b> и <b>Управление ИИ-продуктами</b> 💙",
        parse_mode="HTML")
    def convert_bold_markdown_to_html(text: str) -> str:
        return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    def format_list_markers(text: str) -> str:
        return re.sub(r"(?m)^(\s*)\*\s+", r"\1• ", text)
    def prepare_html_answer(text: str) -> str:
        html = convert_bold_markdown_to_html(text)
        html = format_list_markers(html)
        return html

    @bot.message_handler(func=lambda message: (user_state.get(message.chat.id, {}).get("step") == "waiting_for_question"))
    def handle_question_for_program(message):
        user_id = message.chat.id
        state = user_state.get(user_id)
        question = message.text
    
        # Инициализация диалогового контекста
        dialogue_context = dialogue_contexts.setdefault(user_id, DialogueContext())
        thinking_msg = bot.send_message(user_id, "⏳ Думаю над ответом...")
    
        try:
            answer = prepare_html_answer(rag_answer(question, dialogue_context=dialogue_context))
            bot.delete_message(chat_id=user_id, message_id=thinking_msg.message_id)
    
            if is_salary_question(question):
                sticker_id = random.choice(salary_stickers)
                bot.send_sticker(user_id, sticker_id)
            elif should_send_sticker(user_id):
                send_random_emotion_sticker(user_id)
                user_state[user_id]["message_count"] = 0
            bot.send_message(user_id, answer, parse_mode="HTML")
    
        except Exception as e:
            bot.delete_message(chat_id=user_id, message_id=thinking_msg.message_id)
            bot.send_message(user_id, f"Произошла ошибка при получении ответа: {str(e)}")


# Создание более яркого диалога с помощью стикеров    
    def is_salary_question(question: str) -> bool:
        keywords = ["зарплат", "оплат", "доход", "заработ", "сколько платят", "сколько получают"]
        return any(kw in question.lower() for kw in keywords)
    def should_send_sticker(user_id):
        state = user_state.setdefault(user_id, {})
        count = state.get("message_count", 0) + 1
        state["message_count"] = count
        return count >= random.choice([4, 5, 6])
    def send_random_emotion_sticker(chat_id):
        sticker_id = random.choice(emotion_stickers)
        bot.send_sticker(chat_id, sticker_id)