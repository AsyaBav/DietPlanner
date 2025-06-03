import logging
import io
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib
from aiogram.types import Message

matplotlib.use('Agg')  # Использование Agg бэкенда (не требует GUI)
import os
from database import get_user
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram import Dispatcher

from database import (
    get_user, get_daily_totals, get_daily_water,
    get_weekly_water, get_water_goal
)
from utils import format_date


# Локальное определение функции для избежания проблем импорта
def get_progress_percentage(current, goal):
    """Вычисляет процент прогресса."""
    if goal <= 0:
        return 0
    return min(round(current / goal * 100), 100)


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Состояния для визуализации
class VisualizationStates(StatesGroup):
    selecting_period = State()
    selecting_chart_type = State()


async def show_statistics(message: types.Message, state: FSMContext):
    """Показывает меню выбора статистики пользователя."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Погнали!")
        return

    # Создаем клавиатуру для выбора статистики
    keyboard = [
        [
            types.InlineKeyboardButton(text="📊 Калории и БЖУ", callback_data="stats:nutrition"),
            types.InlineKeyboardButton(text="💧 Вода", callback_data="stats:water")
        ],
        [
            types.InlineKeyboardButton(text="◀️ Главное меню", callback_data="stats:back")
        ]
    ]

    await message.answer(
        "📈 <b>Статистика и аналитика</b>\n\n"
        "Выберите, какую статистику вы хотите посмотреть:",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


'''async def handle_statistics_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа статистики."""
    action = callback_query.data.split(':')[1]
    data = callback_query.data

    if action == "nutrition":
        await show_nutrition_statistics(callback_query, state)
    elif action == "water":
        await show_water_statistics(callback_query, state)
    if data == "stats:water":
        await show_water_statistics(callback_query.message)
    elif data == "stats:nutrition":
        await show_nutrition_statistics(callback_query.message)
    elif action == "back":
        from keyboards import after_calories_keyboard
        await callback_query.message.answer(
            "Вы вернулись в главное меню",
            reply_markup=after_calories_keyboard
        )

    await callback_query.answer()'''

async def handle_statistics_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обработка нажатий кнопок статистики"""
    data = callback_query.data
    logger.info(f"Получен callback: {data}")

    if data == "stats:water":
        await show_water_statistics(callback_query.message, state)
    elif data == "stats:nutrition":
        await show_nutrition_statistics(callback_query.message, state)
    else:
        logger.warning(f"Неизвестная команда: {data}")
        await callback_query.answer("Неизвестная команда.")


async def show_nutrition_statistics(message: types.Message, state: FSMContext):
    logging.info("Вызвана функция show_nutrition_statistics")
    logging.info(f"User ID: {message.from_user.id}")
    user_id = message.from_user.id
    logging.info(f"Получение данных для пользователя {user_id}")

    user = get_user(user_id)

    today = datetime.now().strftime("%Y-%m-%d")

    # Получаем данные из базы
    daily_totals = get_daily_totals(user_id, today)
    logging.info(f"Запрос пользователя с ID: {user_id}")
    user_data = get_user(user_id)
    logging.info(f"Данные пользователя из базы: {user_data}")

    # Проверяем, есть ли данные
    if not daily_totals or user:
        logging.warning(f"Пользователь {user_id} не найден")
        await message.answer("Сегодня вы еще не добавляли продукты.")
        return

    logging.info(f"Данные пользователя: {user}")


    # Формируем сообщение
    text = (
        f"📊 <b>Статистика по калориям и БЖУ за сегодня:</b>\n\n"
        f"Калории: {daily_totals['total_calories']} / {user_data['goal_calories']} ккал\n"
        f"Белки: {daily_totals['total_protein']} г\n"
        f"Жиры: {daily_totals['total_fat']} г\n"
        f"Углеводы: {daily_totals['total_carbs']} г\n"
    )

    await message.answer(text, parse_mode="HTML")

'''async def show_nutrition_statistics(callback_query: CallbackQuery, state: FSMContext):
    """Показывает статистику питания за день."""
    user_id = callback_query.from_user.id

    # Получаем данные о пользователе
    user = get_user(user_id)

    if not user:
        await callback_query.message.answer("Сначала нужно зарегистрироваться.")
        return

    # Получаем данные за текущий день
    today = datetime.now().strftime("%Y-%m-%d")
    daily_totals = get_daily_totals(user_id, today)

    # Получаем цели пользователя
    goal_calories = user['goal_calories']
    goal_protein = user['protein']
    goal_fat = user['fat']
    goal_carbs = user['carbs']

    # Проверяем, есть ли данные
    if daily_totals['total_calories'] == 0:
        # Если данных нет, предлагаем перейти в дневник
        keyboard = [
            [types.InlineKeyboardButton(text="📝 Перейти в дневник", callback_data="goto:diary")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="stats:back")]
        ]

        await callback_query.message.answer(
            "У вас пока нет данных о питании за сегодня. "
            "Добавьте приемы пищи в дневник, чтобы увидеть статистику.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return

    # Создаем график для сравнения текущих значений с целями
    image_path = await create_nutrition_chart(
        daily_totals,
        goal_calories,
        goal_protein,
        goal_fat,
        goal_carbs,
        user_id
    )

    # Формируем текст с аналитикой
    text = "📊 <b>Статистика питания за сегодня</b>\n\n"

    # Калории
    calories_percent = get_progress_percentage(daily_totals['total_calories'], goal_calories)
    text += f"Калории: {daily_totals['total_calories']:.0f} / {goal_calories:.0f} ккал ({calories_percent}%)\n"

    # БЖУ
    protein_percent = get_progress_percentage(daily_totals['total_protein'], goal_protein)
    fat_percent = get_progress_percentage(daily_totals['total_fat'], goal_fat)
    carbs_percent = get_progress_percentage(daily_totals['total_carbs'], goal_carbs)

    text += f"Белки: {daily_totals['total_protein']:.1f} / {goal_protein:.1f} г ({protein_percent}%)\n"
    text += f"Жиры: {daily_totals['total_fat']:.1f} / {goal_fat:.1f} г ({fat_percent}%)\n"
    text += f"Углеводы: {daily_totals['total_carbs']:.1f} / {goal_carbs:.1f} г ({carbs_percent}%)\n\n"

    # Общая оценка и рекомендации
    text += "<b>Анализ:</b>\n"

    if abs(calories_percent - 100) <= 10:
        text += "✅ Вы соблюдаете дневную норму калорий.\n"
    elif calories_percent < 90:
        text += "⚠️ Вы потребляете меньше калорий, чем нужно для вашей цели.\n"
    else:  # calories_percent > 110
        text += "⚠️ Вы превышаете дневную норму калорий.\n"

    # Анализ БЖУ
    if protein_percent < 90:
        text += "📌 Рекомендуем увеличить потребление белка.\n"

    if fat_percent > 110:
        text += "📌 Рекомендуем уменьшить потребление жиров.\n"

    if carbs_percent > 110 and user['goal'] == "🔻 Похудение":
        text += "📌 Для похудения стоит уменьшить потребление углеводов.\n"

    # Отправляем изображение с графиком
    with open(image_path, 'rb') as photo:
        await callback_query.message.answer_photo(
            photo=types.BufferedInputFile(
                file=photo.read(),
                filename="nutrition_chart.png"
            ),
            caption=text,
            parse_mode="HTML"
        )

    # Удаляем временный файл
    try:
        os.remove(image_path)
    except:
        pass'''


async def create_nutrition_chart(data, goal_calories, goal_protein, goal_fat, goal_carbs, user_id):
    """Создает график сравнения текущих значений питания с целями."""
    # Подготавливаем данные для графика
    categories = ['Калории/10', 'Белки', 'Жиры', 'Углеводы']

    # Нормализуем калории для лучшего отображения на графике
    current_values = [
        data['total_calories'] / 10,  # Делим на 10 для визуализации
        data['total_protein'],
        data['total_fat'],
        data['total_carbs']
    ]

    goal_values = [
        goal_calories / 10,  # Делим на 10 для визуализации
        goal_protein,
        goal_fat,
        goal_carbs
    ]

    # Создаем график
    plt.figure(figsize=(10, 6))

    # Задаем ширину столбцов
    width = 0.35

    # Позиции для текущих значений и целей
    x = range(len(categories))

    # Строим столбчатую диаграмму
    plt.bar([i - width / 2 for i in x], current_values, width, label='Текущее', color='#4682b8')
    plt.bar([i + width / 2 for i in x], goal_values, width, label='Цель', color='#2ca02c', alpha=0.7)

    # Добавляем подписи значений над столбцами
    for i, v in enumerate(current_values):
        if categories[i] == 'Калории/10':
            # Для калорий умножаем обратно на 10
            plt.text(i - width / 2, v + 2, f'{int(v * 10)}', ha='center')
        else:
            plt.text(i - width / 2, v + 2, f'{v:.1f}', ha='center')

    for i, v in enumerate(goal_values):
        if categories[i] == 'Калории/10':
            # Для калорий умножаем обратно на 10
            plt.text(i + width / 2, v + 2, f'{int(v * 10)}', ha='center')
        else:
            plt.text(i + width / 2, v + 2, f'{v:.1f}', ha='center')

    # Настраиваем график
    plt.title('Сравнение текущих значений с целями', fontsize=16)
    plt.ylabel('Значение', fontsize=12)
    plt.xticks(x, categories)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    # Сохраняем график во временный файл
    filename = f"nutrition_chart_{user_id}.png"
    plt.savefig(filename)
    plt.close()

    return filename


async def show_water_statistics(callback_query: CallbackQuery, state: FSMContext):
    """Показывает статистику потребления воды за неделю."""
    logging.info("Вызвана функция show_water_statistics")

    user_id = callback_query.from_user.id
    logging.info(f"Получение данных по воде для пользователя {user_id}")

    # Получаем данные о пользователе
    user = get_user(user_id)

    if not user:
        logging.warning(f"Пользователь {user_id} не найден")

        await callback_query.message.answer("Сначала нужно зарегистрироваться.")
        return

    # Получаем данные за неделю
    weekly_data = get_weekly_water(user_id)

    # Проверяем, есть ли данные
    if not any(day['amount'] > 0 for day in weekly_data):
        # Если данных нет, предлагаем перейти в трекер воды
        keyboard = [
            [types.InlineKeyboardButton(text="💧 Перейти в трекер воды", callback_data="goto:water")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="stats:back")]
        ]

        await callback_query.message.answer(
            "У вас пока нет данных о потреблении воды за последнюю неделю. "
            "Добавьте записи в трекер воды, чтобы увидеть статистику.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return

    # Получаем цель по воде
    water_goal = get_water_goal(user_id)

    # Создаем график
    image_path = await create_water_chart(weekly_data, water_goal, user_id)

    # Форматируем текст с аналитикой
    text = "📊 <b>Статистика потребления воды за неделю</b>\n\n"

    # Вычисляем общее потребление за неделю
    total_week = sum(day['amount'] for day in weekly_data)
    avg_daily = total_week / 7

    text += f"Всего за неделю: {total_week} мл\n"
    text += f"В среднем за день: {avg_daily:.0f} мл\n"
    text += f"Целевое потребление: {water_goal} мл в день\n\n"

    # Находим день с максимальным и минимальным потреблением
    non_zero_days = [day for day in weekly_data if day['amount'] > 0]
    if non_zero_days:
        max_day = max(non_zero_days, key=lambda x: x['amount'])
        min_day = min(non_zero_days, key=lambda x: x['amount'])

        text += f"Лучший день: {format_date(max_day['date'])} — {max_day['amount']} мл\n"
        text += f"Худший день: {format_date(min_day['date'])} — {min_day['amount']} мл\n\n"

    # Общая оценка
    if avg_daily >= water_goal:
        text += "🎉 Отлично! Вы достигаете своей цели по потреблению воды!"
    elif avg_daily >= water_goal * 0.8:
        text += "👍 Хорошо! Вы близки к достижению своей цели по воде."
    else:
        text += "💡 Старайтесь пить больше воды каждый день для достижения цели."

    # Отправляем изображение с графиком
    with open(image_path, 'rb') as photo:
        await callback_query.message.answer_photo(
            photo=types.BufferedInputFile(
                file=photo.read(),
                filename="water_chart.png"
            ),
            caption=text,
            parse_mode="HTML"
        )

    # Удаляем временный файл
    try:
        os.remove(image_path)
    except:
        pass


async def create_water_chart(data, water_goal, user_id):
    """Создает график потребления воды за неделю."""
    # Подготавливаем данные для графика
    dates = [format_date(day['date']) for day in data]
    amounts = [day['amount'] for day in data]

    # Создаем график
    plt.figure(figsize=(10, 6))

    # Строим столбчатую диаграмму
    bars = plt.bar(dates, amounts, color='#4682b8', width=0.6)

    # Добавляем горизонтальную линию с целью
    plt.axhline(y=water_goal, color='red', linestyle='--', alpha=0.7)
    plt.text(0, water_goal + 100, f'Цель: {water_goal} мл', color='red')

    # Добавляем подписи значений над столбцами
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(bar.get_x() + bar.get_width() / 2., height + 50,
                     f'{int(height)}',
                     ha='center', va='bottom', rotation=0)

    # Настраиваем график
    plt.title('Потребление воды за неделю', fontsize=16)
    plt.xlabel('Дата', fontsize=12)
    plt.ylabel('Количество (мл)', fontsize=12)
    plt.ylim(0, max(max(amounts) + 500 if amounts else water_goal, water_goal + 500))
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    # Сохраняем график во временный файл
    filename = f"water_chart_{user_id}.png"
    plt.savefig(filename)
    plt.close()

    return filename


async def goto_tracker(callback_query: CallbackQuery, state: FSMContext):
    """Перенаправляет пользователя в другой трекер."""
    action = callback_query.data.split(':')[1]

    if action == "diary":
        from diary import show_diary
        await show_diary(callback_query.message, state)
    elif action == "water":
        from water_tracker import water_tracker
        await water_tracker(callback_query.message, state)

    await callback_query.answer()


def register_visualization_handlers(dp: Dispatcher):
    """Регистрирует обработчики для модуля визуализации."""
    # Обработка кнопок в меню статистики
    dp.callback_query.register(handle_statistics_callback, lambda c: c.data.startswith("stats:"))
    dp.callback_query.register(goto_tracker, lambda c: c.data.startswith("goto:"))