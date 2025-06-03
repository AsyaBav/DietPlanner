import logging
import os
from flask import Flask, render_template, jsonify
import time
import asyncio


# Импорт модулей бота
from run_bot import start_bot_thread

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Создаем Flask приложение
app = Flask(__name__)

# Запуск бота в отдельном потоке
bot_thread = None



@app.route('/')
def index():
    return "Telegram Diet Planner Bot running! Check your Telegram client to interact with the bot."

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "bot_name": "Diet Planner Bot",
        "features": [
            "BMI calculation",
            "Daily food diary",
            "Water intake tracking",
            "Personalized meal planning",
            "Recipe suggestions",
            "Progress visualization"
        ]
    })


# Запуск приложения
if __name__ == "__main__":
    # Запускаем бота вместе с Flask приложением
    bot_thread = start_bot_thread()
    # Используем другой порт, чтобы избежать конфликта с Gunicorn
    app.run(host='0.0.0.0', port=8080, debug=False)
else:
    # В случае запуска через WSGI (gunicorn), инициализируем бот сразу
    # Небольшая задержка для уверенности, что Flask полностью инициализирован
    logger.info("Starting Telegram bot in a separate thread...")
    bot_thread = start_bot_thread()
    logger.info("Bot thread started")