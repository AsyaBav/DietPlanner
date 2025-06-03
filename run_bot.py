import asyncio
import logging
import threading
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN
from handlers import register_handlers
from database import close_db


# Создаем бота и диспетчер
bot = None
dp = None

# Отключаем обработку сигналов, которая вызывает проблему set_wakeup_fd
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Функция запуска бота
async def start_bot():
    global bot, dp
    # Проверяем токен
    if not TOKEN or TOKEN == "your_bot_token_here":
        logger.error("Токен бота не указан! Укажите действительный токен в .env файле.")
        logger.info("Для тестирования используем эмуляцию бота без подключения к Telegram API")
        return
    try:
        bot = Bot(token=TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        register_handlers(dp)        # Регистрируем обработчики

        logger.info("Бот запущен!")
        await dp.start_polling(
            bot,
            skip_updates=True,
            timeout=60,
            relax=0.1,
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        if bot:
            await bot.session.close()
        close_db()
        logger.info("Бот остановлен, соединение с БД закрыто.")


# Функция для запуска бота в отдельном потоке
def run_bot_forever():
    asyncio.run(start_bot())


# Запускает бота в отдельном потоке
def start_bot_thread():
    bot_thread = threading.Thread(target=run_bot_forever)
    bot_thread.daemon = True
    bot_thread.start()
    return bot_thread


# Если скрипт запущен напрямую
if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")