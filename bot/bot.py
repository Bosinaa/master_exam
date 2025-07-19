# Основной код бота
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import mysql.connector
from dotenv import load_dotenv
import os
load_dotenv("config.env")  # Загружает переменные из config.env

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Код подключения к RAG
from bot_llm_task import llm_tasks
# Старт
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.chat.id

    # Сначала создаём клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да")
    markup.add(btn1)

    # Затем отправляем сообщение с этой клавиатурой
    bot.send_message(user_id, "Привет! Помочь с выбором программы или плана обучения?", reply_markup=markup)

llm_tasks(bot)
bot.polling()