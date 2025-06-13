import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN
from handlers import register_handlers
from database import close_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем бота и диспетчер
bot = None
dp = None

# Функция запуска бота
async def start_bot():
    global bot, dp

    # Проверяем токен
    if not TOKEN or TOKEN == "your_bot_token_here":
        logger.error("Токен бота не указан! Укажите действительный токен в .env файле.")
        logger.info("Для тестирования используем эмуляцию бота без подключения к Telegram API")
        # Эмулируем работу без реального подключения к API Telegram
        while True:
            await asyncio.sleep(10)
            logger.info("Бот работает в режиме эмуляции...")

    try:
        bot = Bot(token=TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрируем обработчики
        register_handlers(dp)

        logger.info("Бот запущен!")
        await dp.start_polling(
            bot,
            skip_updates=True,
            timeout=60,
            relax=0.1
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        if bot:
            await bot.session.close()
        close_db()
        logger.info("Бот остановлен, соединение с БД закрыто.")

# Если скрипт запущен напрямую
if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")