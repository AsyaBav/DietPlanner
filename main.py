import logging
import os
from flask import Flask, render_template, jsonify
import time
import asyncio
import threading

# Импорт модулей бота
from run_bot import start_bot

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем Flask приложение
app = Flask(__name__)


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


def run_flask():
    """Запускает Flask в отдельном потоке"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


# Запуск приложения
if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    logger.info("Flask приложение запущено на порту 5000")

    # Запускаем бота в основном потоке
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено")
