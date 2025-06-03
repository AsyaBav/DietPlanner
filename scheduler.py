'''from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import execute_query

from aiogram import Bot
from config import TOKEN
import logging

# Глобальный объект бота для отправки уведомлений
bot = Bot(token=TOKEN)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_notification(user_id: int, message: str):
    """Отправка уведомления пользователю через бота."""
    try:
        await bot.send_message(user_id, message)
        logger.info(f"Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")


async def schedule_user_notifications(user_id: int):
    """Планирует уведомления для конкретного пользователя."""
    notifications = execute_query(
        "SELECT type, time FROM notifications WHERE user_id = ? AND is_active = 1",
        (user_id,),
        fetch_all=True
    )

    for notif in notifications:
        notif_type = notif['type']
        time_str = notif['time']

        try:
            hour, minute = map(int, time_str.split(':'))
            scheduler.add_job(
                send_notification,
                trigger='cron',
                hour=hour,
                minute=minute,
                args=[user_id, f"⏰ Напоминание: {notif_type}!"]
            )
            logger.info(f"Запланировано уведомление для {user_id} на {time_str}")
        except Exception as e:
            logger.error(f"Ошибка планирования уведомления: {e}")


async def start_scheduler():
    """Запуск планировщика уведомлений для всех пользователей."""
    global scheduler
    scheduler = AsyncIOScheduler()

    # Получаем всех пользователей, завершивших регистрацию
    users = execute_query(
        "SELECT id FROM users WHERE registration_complete = 1",
        fetch_all=True
    )

    if users:
        for user in users:
            await schedule_user_notifications(user['id'])

    scheduler.start()
    logger.info("Планировщик уведомлений запущен")