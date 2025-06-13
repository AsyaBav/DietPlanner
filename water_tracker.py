from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import logging
import os

from database import get_user, get_daily_water, add_water_entry, get_water_goal, set_water_goal, get_weekly_water
from diary import WaterStates

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def water_tracker(message: types.Message, state: FSMContext):
    """Показывает трекер воды и кнопки для добавления."""
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("Сначала нужно зарегистрироваться!")
        return

    # Получаем текущую дату
    today = datetime.now().strftime("%Y-%m-%d")

    # Получаем данные о потреблении воды
    daily_water = get_daily_water(user_id, today)
    water_goal = get_water_goal(user_id)

    # Рассчитываем процент выполнения цели
    percentage = min(daily_water / water_goal * 100 if water_goal > 0 else 0, 100)

    # Определяем эмодзи в зависимости от прогресса
    emoji = "🌊" if percentage >= 100 else "💧"

    # Создаем прогресс-бар
    progress_bar = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))

    # Формируем сообщение
    message_text = f"<b>{emoji} Водный баланс на сегодня</b>\n\n"
    message_text += f"📏 <b>Прогресс:</b> {progress_bar} ({percentage:.0f}%)\n\n"
    message_text += f"🥛 <b>Выпито:</b> {daily_water} мл\n"
    message_text += f"🎯 <b>Цель:</b> {water_goal} мл\n"
    message_text += f"🔆 <b>Осталось выпить:</b> {max(0, water_goal - daily_water)} мл\n\n"
    message_text += "Нажмите на кнопку, чтобы добавить воду:"

    # Создаем клавиатуру
    keyboard = create_water_keyboard()

    await message.answer(message_text, reply_markup=keyboard, parse_mode="HTML")

def create_water_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="+200 мл", callback_data="water_add:200"),
            InlineKeyboardButton(text="+300 мл", callback_data="water_add:300"),
            InlineKeyboardButton(text="+500 мл", callback_data="water_add:500")
        ],
        [
            InlineKeyboardButton(text="Свое количество", callback_data="water_custom"),
            InlineKeyboardButton(text="Изменить цель", callback_data="water_goal")
        ],
        [
            InlineKeyboardButton(text="Статистика", callback_data="water_stats"),
            InlineKeyboardButton(text="Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def add_water_amount(callback_query: types.CallbackQuery, state: FSMContext):
    """Добавляет указанное количество воды."""
    try:
        # Логируем нажатие кнопки
        logger.info(f"User {callback_query.from_user.id} pressed water_add: {callback_query.data}")
        logger.info(f"Получен callback: {callback_query.data}")

        # Получаем количество воды из callback_data
        amount = int(callback_query.data.split(":")[1])

        # Добавляем запись в БД
        user_id = callback_query.from_user.id
        add_water_entry(user_id, amount)

        # Обновляем исходное сообщение
        await update_water_tracker_message(callback_query.message, user_id)
        await callback_query.answer(f"✅ Добавлено {amount} мл воды!")

    except Exception as e:
        logger.error(f"Ошибка в add_water_amount: {e}")
        await callback_query.answer("❌ Ошибка добавления воды")

async def update_water_tracker_message(message: types.Message, user_id: int):
    """Обновляет сообщение с трекером воды."""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_water = get_daily_water(user_id, today)
    water_goal = get_water_goal(user_id)
    percentage = min(daily_water / water_goal * 100 if water_goal > 0 else 0, 100)
    progress_bar = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))

    # Формируем текст
    message_text = (
        f"<b>💧 Водный баланс на сегодня</b>\n\n"
        f"📏 <b>Прогресс:</b> {progress_bar} ({percentage:.0f}%)\n\n"
        f"🥛 <b>Выпито:</b> {daily_water} мл\n"
        f"🎯 <b>Цель:</b> {water_goal} мл\n"
        f"🔆 <b>Осталось:</b> {max(0, water_goal - daily_water)} мл"
    )

    # Обновляем сообщение
    await message.edit_text(
        message_text,
        reply_markup=create_water_keyboard(),
        parse_mode="HTML"
    )

async def custom_water_amount(callback_query: types.CallbackQuery, state: FSMContext):
    """Запрашивает у пользователя произвольное количество воды."""
    await callback_query.answer()

    await callback_query.message.answer("Введите количество выпитой воды в миллилитрах (мл):")
    await state.set_state(WaterStates.entering_amount)


async def process_water_amount(message: types.Message, state: FSMContext):
    """Обрабатывает ввод произвольного количества воды."""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError

        # Проверяем разумные пределы (не более 3 литров за один раз)
        if amount > 3000:
            await message.answer(
                "Слишком большое количество для одного раза. Пожалуйста, введите значение не более 3000 мл.")
            return
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число для количества воды.")
        return

    # Добавляем запись в БД
    user_id = message.from_user.id
    add_water_entry(user_id, amount)

    # Очищаем состояние и показываем обновленный трекер
    await state.clear()
    await message.answer(f"✅ Добавлено {amount} мл воды!")
    await water_tracker(message, state)


async def set_water_goal_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Запрашивает у пользователя новую цель по воде."""
    await callback_query.answer()

    # Показываем текущую цель и запрашиваем новую
    user_id = callback_query.from_user.id
    current_goal = get_water_goal(user_id)

    await callback_query.message.answer(
        f"Ваша текущая цель: {current_goal} мл.\n\nВведите новую цель по потреблению воды в миллилитрах (мл):"
    )

    # Создаем инлайн-клавиатуру с распространенными значениями
    keyboard = [
        [
            types.InlineKeyboardButton(text="1500 мл", callback_data="water_goal_set:1500"),
            types.InlineKeyboardButton(text="2000 мл", callback_data="water_goal_set:2000"),
            types.InlineKeyboardButton(text="2500 мл", callback_data="water_goal_set:2500")
        ],
        [
            types.InlineKeyboardButton(text="3000 мл", callback_data="water_goal_set:3000"),
            types.InlineKeyboardButton(text="3500 мл", callback_data="water_goal_set:3500"),
            types.InlineKeyboardButton(text="4000 мл", callback_data="water_goal_set:4000")
        ],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="water_tracker")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback_query.message.answer("Или выберите из распространенных значений:", reply_markup=markup)


async def process_water_goal(message: types.Message, state: FSMContext):
    """Обрабатывает ввод новой цели по воде."""
    try:
        goal = int(message.text.strip())
        if goal < 500 or goal > 10000:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение от 500 до 10000 мл.")
        return

    # Устанавливаем новую цель
    user_id = message.from_user.id
    set_water_goal(user_id, goal)

    # Очищаем состояние и показываем обновленный трекер
    await state.clear()
    await message.answer(f"✅ Новая цель по потреблению воды установлена: {goal} мл!")
    await water_tracker(message, state)


async def show_water_statistics(callback_query: types.CallbackQuery, state: FSMContext):
    """Показывает статистику потребления воды за неделю."""
    await callback_query.answer()

    user_id = callback_query.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")

    # Получаем данные за неделю
    weekly_data = get_weekly_water(user_id, today)

    # Создаем директорию для графиков, если не существует
    os.makedirs("temp", exist_ok=True)

    # Подготавливаем данные для графика
    dates = [item['date'] for item in weekly_data]
    amounts = [item['amount'] for item in weekly_data]

    # Преобразуем даты в более читаемый формат
    readable_dates = []
    for date_str in dates:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        readable_dates.append(date_obj.strftime("%d.%m"))

    # Получаем цель пользователя
    water_goal = get_water_goal(user_id)

    # Создаем график
    plt.figure(figsize=(10, 6))
    plt.bar(readable_dates, amounts, color='skyblue')

    # Добавляем линию цели
    plt.axhline(y=water_goal, color='r', linestyle='-', label=f'Цель: {water_goal} мл')

    plt.title('Потребление воды за неделю')
    plt.xlabel('Дата')
    plt.ylabel('Количество (мл)')
    plt.legend()

    # Сохраняем график в байтовый поток
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Отправляем график пользователю
    await callback_query.message.answer_photo(
        types.BufferedInputFile(
            buf.getvalue(),
            filename="water_stats.png"
        ),
        caption="📊 Статистика потребления воды за последнюю неделю"
    )

    # Очищаем ресурсы matplotlib
    plt.close()

    # Отправляем текстовую статистику
    weekly_total = sum(amounts)
    daily_avg = weekly_total / 7
    days_achieved = sum(1 for amount in amounts if amount >= water_goal)

    stats_text = f"<b>📈 Статистика за неделю:</b>\n\n"
    stats_text += f"• Всего выпито: {weekly_total} мл\n"
    stats_text += f"• Среднее в день: {daily_avg:.0f} мл\n"
    stats_text += f"• Достигнута цель: {days_achieved} из 7 дней\n"
    stats_text += f"• Выполнение цели: {(daily_avg / water_goal * 100):.0f}%"

    # Создаем клавиатуру для возврата
    keyboard = [
        [types.InlineKeyboardButton(text="◀️ Назад к трекеру воды", callback_data="water_tracker")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback_query.message.answer(stats_text, reply_markup=markup, parse_mode="HTML")


async def return_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Возвращает пользователя в трекер воды."""
    from handlers import after_calories_keyboard

    user_id = callback_query.from_user.id
    user = get_user(user_id)  # Проверяем, есть ли пользователь в БД

    logger.info(f"Пользователь {user_id} существует: {user is not None}")

    if not user:
        await callback_query.answer("❌ Пользователь не найден. Нажмите /start")
        return

    # Если пользователь есть, показываем трекер воды
    await callback_query.message.answer(
        "Вы вернулись в главное меню",
        reply_markup=after_calories_keyboard
    )
    await callback_query.answer()