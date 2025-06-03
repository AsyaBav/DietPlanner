"""
📘 dairy.py — модуль для взаимодействия с дневником питания в Telegram-боте

Этот модуль реализует основную логику ведения дневника питания пользователя:
- Просмотр дневника за выбранную дату с подсчетом калорий и нутриентов.
- Добавление продуктов по приему пищи (завтрак, обед и т.п.) с использованием поиска по API (FatSecret).
- Работа с недавно добавленными продуктами.
- Подтверждение или отмена ввода данных.
- Очистка дневника за конкретную дату.
- Навигация по датам с помощью inline-кнопок.
- Поддержка состояний FSM (Finite State Machine) для управления диалогом пользователя.

Модуль использует:
- aiogram для Telegram-бота,
- собственные утилиты (`utils.py`, `keyboards.py`, `food_api.py`, `database.py`) для работы с БД, клавиатурами и API,
- систему логирования для отладки.

Функции организованы по сценариям: отображение дневника, добавление продуктов, выбор даты/приема пищи, обработка ввода и подтверждений.
"""


import logging
import json

from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter

from database import (
    get_user, get_daily_entries, add_food_entry,
    get_daily_totals, clear_daily_entries, get_entries_by_meal,
    get_recent_foods
)

from keyboards import create_date_selection_keyboard, create_meal_types_keyboard, create_food_entry_keyboard,  create_recent_foods_keyboard
from food_api import search_food, get_food_nutrients, get_branded_food_info
from utils import format_date, get_progress_percentage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


'''Состояния для ведения дневника'''
class DiaryStates(StatesGroup):
    selecting_date = State()        # Выбор даты
    selecting_meal_type = State()   # Выбор приёма пищи
    entering_food = State()         # Ввод названия продукта
    selecting_food = State()        # Выбор продукта из списка
    entering_amount = State()       # Ввод веса продукта
    confirming_entry = State()      # Подтверждение добавления


# Состояния для трекера воды
class WaterStates(StatesGroup):
    entering_amount = State()
    setting_goal = State()


async def show_diary(message: types.Message, state: FSMContext):
    """Показывает дневник питания."""
    # Проверяем, зарегистрирован ли пользователь
    user = get_user(message.from_user.id)
    if not user or not user.get('registration_complete'):  # Измененная проверка:
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Поехали!")
        return

    # Получаем текущую дату
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Сохраняем дату в состоянии
    await state.update_data(selected_date=current_date)

    # Показываем дневник на текущую дату
    await show_diary_for_date(message, current_date, user, state)


async def show_diary_for_date(message, date, user, state):
    """Показывает дневник питания на указанную дату."""
    user_id = user['id'] if isinstance(user, dict) else user

    # Получаем записи за день
    entries = get_daily_entries(user_id, date)

    # Получаем общие показатели за день
    totals = get_daily_totals(user_id, date)

    # Получаем цели пользователя
    user_data = get_user(user_id)
    goal_calories = user_data.get('goal_calories', 0)
    goal_protein = user_data.get('protein', 0)
    goal_fat = user_data.get('fat', 0)
    goal_carbs = user_data.get('carbs', 0)

    # Форматируем дату
    formatted_date = format_date(date)

    # Составляем сообщение
    message_text = f"📝 <b>Дневник питания за {formatted_date}</b>\n\n"

    if entries:
        # Группируем записи по приемам пищи
        meal_entries = {}
        for entry in entries:
            meal_type = entry['meal_type']
            if meal_type not in meal_entries:
                meal_entries[meal_type] = []
            meal_entries[meal_type].append(entry)

        # Выводим записи по каждому приему пищи
        for meal_type, meal_list in meal_entries.items():
            message_text += f"<b>{meal_type}:</b>\n"

            meal_calories = 0
            for entry in meal_list:
                message_text += f"  • {entry['food_name']} – {entry['calories']:.0f} ккал\n"
                meal_calories += entry['calories']

            message_text += f"  Всего: {meal_calories:.0f} ккал\n\n"

        # Выводим итоги за день
        message_text += "<b>Итого за день:</b>\n"
        message_text += f"Калории: {totals['total_calories']:.0f} / {goal_calories:.0f} ккал "

        # Добавляем процент от цели
        calories_percent = get_progress_percentage(totals['total_calories'], goal_calories)
        message_text += f"({calories_percent}%)\n"

        # Добавляем БЖУ
        message_text += f"Белки: {totals['total_protein']:.1f} / {goal_protein:.1f} г "
        protein_percent = get_progress_percentage(totals['total_protein'], goal_protein)
        message_text += f"({protein_percent}%)\n"

        message_text += f"Жиры: {totals['total_fat']:.1f} / {goal_fat:.1f} г "
        fat_percent = get_progress_percentage(totals['total_fat'], goal_fat)
        message_text += f"({fat_percent}%)\n"

        message_text += f"Углеводы: {totals['total_carbs']:.1f} / {goal_carbs:.1f} г "
        carbs_percent = get_progress_percentage(totals['total_carbs'], goal_carbs)
        message_text += f"({carbs_percent}%)\n"
    else:
        message_text += "В дневнике пока нет записей на этот день. Нажмите 'Добавить продукт', чтобы начать вести дневник."

    # Создаем клавиатуру для навигации по датам
    keyboard = create_date_selection_keyboard(date)

    # Отправляем сообщение
    await message.answer(message_text, reply_markup=keyboard, parse_mode="HTML")


async def handle_diary_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатия на кнопки дневника."""
    action = callback_query.data

    if action.startswith("date:"):
        await handle_date_selection(callback_query, state)
    elif action == "add_food":
        await start_food_entry(callback_query, state)
    elif action == "clear_diary":
        await clear_diary(callback_query, state)
    elif action.startswith("meal_type:"):
        await handle_meal_type_selection(callback_query, state)
    elif action == "return_to_diary":
        await return_to_diary(callback_query, state)

    await callback_query.answer()


async def handle_date_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты в дневнике."""
    date_action = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    # Получаем текущую выбранную дату
    user_data = await state.get_data()
    current_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
    current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")

    if date_action == "prev":
        # Предыдущий день
        new_date = (current_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_action == "next":
        # Следующий день
        new_date = (current_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_action == "today":
        # Сегодня
        new_date = datetime.now().strftime("%Y-%m-%d")
    else:
        # Конкретная дата
        new_date = date_action

    # Обновляем состояние
    await state.update_data(selected_date=new_date)

    # Показываем дневник для новой даты
    await show_diary_for_date(callback_query.message, new_date, user, state)


async def start_food_entry(callback_query: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления продукта."""
    # Показываем клавиатуру с выбором приема пищи
    keyboard = create_meal_types_keyboard()

    await callback_query.message.answer(
        "Выберите прием пищи, в который хотите добавить продукт:",
        reply_markup=keyboard
    )

    # Устанавливаем состояние выбора приема пищи
    await state.set_state(DiaryStates.selecting_meal_type)


async def handle_meal_type_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа приема пищи."""
    meal_type = callback_query.data.split(':')[1]

    # Сохраняем выбранный тип приема пищи
    await state.update_data(meal_type=meal_type)

    # Показываем недавно добавленные продукты
    user_id = callback_query.from_user.id
    recent_foods = get_recent_foods(user_id)

    if recent_foods:
        keyboard = create_recent_foods_keyboard(recent_foods)

        await callback_query.message.answer(
            f"Выберите из недавно добавленных продуктов или введите название нового продукта для {meal_type}:",
            reply_markup=keyboard
        )
    else:
        keyboard = create_food_entry_keyboard()

        await callback_query.message.answer(
            f"Введите название продукта для {meal_type}:",
            reply_markup=keyboard
        )

    # Устанавливаем состояние ввода продукта
    await state.set_state(DiaryStates.entering_food)


async def process_food_entry(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия продукта."""
    logger.info(f"Initial message: {message.text}")
    logger.info(f"Current state: {await state.get_state()}")

    food_name = message.text.strip()

    if not food_name:
        await message.answer("Пожалуйста, введите название продукта.")
        return

    logger.info(f"Searching for: {food_name}")

    search_results = search_food(food_name)
    logger.info(f"Search results: {search_results}")

    if not search_results:
        await message.answer("Продукты не найдены. Попробуйте другое название.")
        return

    # Сохраняем только необходимые данные
    simplified_results = []
    for item in search_results:
        simplified_results.append({
            'food_name': item.get('food_name', 'Неизвестный продукт'),
            'food_type': item.get('food_type', 'common'),
            'tag_id': item.get('tag_id'),
            'nix_item_id': item.get('nix_item_id'),
            'serving_qty': item.get('serving_qty', 1),
            'serving_unit': item.get('serving_unit', 'г')
        })

    await state.update_data(search_results=simplified_results)

    # Создаем клавиатуру с продуктами (исправленная версия)
    buttons = []
    for i, item in enumerate(simplified_results):
        btn_text = item['food_name']
        if len(btn_text) > 30:
            btn_text = btn_text[:27] + "..."
        buttons.append([types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"select_food:{i}"
        )])

    # Добавляем кнопку "Назад"
    buttons.append([types.InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="return_to_meal_selection"
    )])

    # Создаем клавиатуру с явным указанием inline_keyboard
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("Выберите продукт:", reply_markup=keyboard)
    await state.set_state(DiaryStates.selecting_food)



async def process_food_amount(message: Message, state: FSMContext):
    """Обрабатывает введенный вес продукта."""
    try:
        weight = float(message.text)
        user_data = await state.get_data()

        # Получаем выбранный продукт из состояния
        selected_food = user_data.get('selected_food')
        if not selected_food:
            await message.answer("Ошибка: информация о продукте не найдена. Начните заново.")
            await state.clear()
            return

        logger.info(f"Processing amount for food: {selected_food}")

        # Рассчитываем КБЖУ для указанного веса
        if 'serving_weight_grams' in selected_food:
            # Если есть информация о весе порции
            ratio = weight / selected_food['serving_weight_grams']
        else:
            # Если нет информации о весе, считаем что 1 единица = 100г
            ratio = weight / 100

        nutrients = {
            'calories': selected_food.get('calories', 0) * ratio,
            'protein': selected_food.get('protein', 0) * ratio,
            'fat': selected_food.get('fat', 0) * ratio,
            'carbs': selected_food.get('carbs', 0) * ratio
        }

        # Получаем остальные данные из состояния
        meal_type = user_data.get('meal_type')
        selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
        food_name = selected_food.get('food_name', 'Неизвестный продукт')

        # Добавляем запись в базу данных
        entry_id = add_food_entry(
            user_id=message.from_user.id,
            date=selected_date,
            meal_type=meal_type,
            food_name=food_name,
            calories=nutrients['calories'],
            protein=nutrients['protein'],
            fat=nutrients['fat'],
            carbs=nutrients['carbs']
        )

        if entry_id:
            await message.answer(f"✅ Добавлено {weight}г продукта '{food_name}'")
            # Показываем обновленный дневник
            user = get_user(message.from_user.id)
            await show_diary_for_date(message, selected_date, user, state)
        else:
            await message.answer("❌ Ошибка при сохранении данных")

    except ValueError:
        await message.answer("Пожалуйста, введите число (например: 100)")
        return
    except Exception as e:
        logger.error(f"Error in process_food_amount: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка, попробуйте ещё раз")
    finally:
        await state.clear()


async def confirm_food_entry(callback_query: CallbackQuery, state: FSMContext):
    """Подтверждает добавление продукта в дневник."""
    # Получаем данные из состояния
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    selected_food = user_data.get('selected_food')
    meal_type = user_data.get('meal_type')
    selected_date = user_data.get('selected_date')
    calories = user_data.get('calories')
    protein = user_data.get('protein')
    fat = user_data.get('fat')
    carbs = user_data.get('carbs')

    # Добавляем запись в базу данных
    entry_id = add_food_entry(
        user_id,
        selected_date,
        meal_type,
        selected_food['food_name'],
        calories,
        protein,
        fat,
        carbs
    )

    if entry_id:
        await callback_query.message.answer("✅ Продукт успешно добавлен в дневник питания!")

        # Показываем обновленный дневник
        user = get_user(user_id)
        await show_diary_for_date(callback_query.message, selected_date, user, state)
    else:
        await callback_query.message.answer(
            "❌ Произошла ошибка при добавлении продукта. Пожалуйста, попробуйте еще раз.")

    # Очищаем состояние
    await state.clear()
    await callback_query.answer()


async def cancel_food_entry(callback_query: CallbackQuery, state: FSMContext):
    """Отменяет добавление продукта."""
    await callback_query.message.answer("Добавление продукта отменено.")

    # Возвращаемся к выбору приема пищи
    await start_food_entry(callback_query, state)
    await callback_query.answer()


async def clear_diary(callback_query: CallbackQuery, state: FSMContext):
    """Очищает все записи в дневнике за выбранный день."""
    # Запрашиваем подтверждение
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date')

    await callback_query.message.answer(
        f"Вы уверены, что хотите удалить все записи за {format_date(selected_date)}?",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Да", callback_data="confirm_clear"),
                types.InlineKeyboardButton(text="❌ Нет", callback_data="cancel_clear")
            ]
        ])
    )


async def confirm_clear_diary(callback_query: CallbackQuery, state: FSMContext):
    """Подтверждает очистку дневника."""
    user_id = callback_query.from_user.id
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date')

    # Очищаем записи
    success = clear_daily_entries(user_id, selected_date)

    if success:
        await callback_query.message.answer(f"✅ Дневник за {format_date(selected_date)} очищен.")

        # Показываем обновленный дневник
        user = get_user(user_id)
        await show_diary_for_date(callback_query.message, selected_date, user, state)
    else:
        await callback_query.message.answer("❌ Произошла ошибка при очистке дневника.")

    await callback_query.answer()


async def cancel_clear_diary(callback_query: CallbackQuery, state: FSMContext):
    """Отменяет очистку дневника."""
    await callback_query.message.answer("Очистка дневника отменена.")

    # Показываем дневник
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date')

    await show_diary_for_date(callback_query.message, selected_date, user, state)
    await callback_query.answer()


async def return_to_diary(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает к просмотру дневника."""
    # Очищаем состояние
    await state.clear()

    # Показываем дневник
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    # Получаем текущую дату
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Сохраняем дату в состоянии
    await state.update_data(selected_date=current_date)

    # Показываем дневник
    await show_diary_for_date(callback_query.message, current_date, user, state)

    await callback_query.answer()


async def handle_recent_food_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор недавно использованного продукта."""
    food_id = int(callback_query.data.split(':')[1])
    user_id = callback_query.from_user.id

    # Получаем список недавних продуктов
    recent_foods = get_recent_foods(user_id)

    # Находим выбранный продукт
    selected_food = None
    for food in recent_foods:
        if food['id'] == food_id:
            selected_food = food
            break

    if not selected_food:
        await callback_query.message.answer("Продукт не найден.")
        await callback_query.answer()
        return

    # Получаем данные из состояния
    user_data = await state.get_data()
    meal_type = user_data.get('meal_type')
    selected_date = user_data.get('selected_date')

    # Добавляем продукт в дневник
    entry_id = add_food_entry(
        user_id,
        selected_date,
        meal_type,
        selected_food['food_name'],
        selected_food['calories'],
        selected_food['protein'],
        selected_food['fat'],
        selected_food['carbs']
    )

    if entry_id:
        await callback_query.message.answer(
            f"✅ Продукт '{selected_food['food_name']}' успешно добавлен в {meal_type.lower()}!")

        # Показываем обновленный дневник
        user = get_user(user_id)
        await show_diary_for_date(callback_query.message, selected_date, user, state)
    else:
        await callback_query.message.answer(
            "❌ Произошла ошибка при добавлении продукта. Пожалуйста, попробуйте еще раз.")

    # Очищаем состояние
    await state.clear()
    await callback_query.answer()


async def handle_food_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор продукта из списка поиска."""
    try:
        index = int(callback_query.data.split(':')[1])
        user_data = await state.get_data()
        search_results = user_data.get('search_results', [])

        if index >= len(search_results):
            await callback_query.answer("Продукт не найден.")
            return

        selected_food = search_results[index]
        logger.info(f"Selected food: {selected_food}")

        # Получаем полную информацию о продукте
        if selected_food.get('food_type') == 'common':
            food_info = get_food_nutrients(selected_food['food_name'])  # Передаем русское название
        else:
            food_info = get_branded_food_info(selected_food.get('nix_item_id'))

        if not food_info:
            await callback_query.message.answer("Не удалось получить данные о продукте.")
            await callback_query.answer()
            return

        # Сохраняем выбранный продукт
        await state.update_data(selected_food=food_info)

        # Формируем сообщение
        message_text = (
            f"Выбран продукт: <b>{food_info['food_name']}</b>\n\n"
            f"Пищевая ценность (на {food_info.get('serving_qty', 1)} {food_info.get('serving_unit', 'г')}):\n"
            f"• Калории: {food_info.get('calories', 0):.0f} ккал\n"
            f"• Белки: {food_info.get('protein', 0):.1f} г\n"
            f"• Жиры: {food_info.get('fat', 0):.1f} г\n"
            f"• Углеводы: {food_info.get('carbs', 0):.1f} г\n\n"
            "Введите количество в граммах:"
        )

        await callback_query.message.answer(message_text, parse_mode="HTML")
        await state.set_state(DiaryStates.entering_amount)
        await callback_query.answer()

    except Exception as e:
        logger.error(f"Error in handle_food_selection: {str(e)}", exc_info=True)
        await callback_query.answer("Произошла ошибка, попробуйте ещё раз")

'''async def handle_food_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор продукта из списка поиска."""
    try:
        # Получаем индекс выбранного продукта
        index = int(callback_query.data.split(":")[1])

        # Получаем сохраненные результаты поиска
        user_data = await state.get_data()
        search_results = user_data.get('search_results', [])

        logger.info(f"Search results in handler: {search_results}")  # Логируем данные

        if index >= len(search_results):
            await callback_query.answer("Продукт не найден в списке.")
            return

        selected_food = search_results[index]
        logger.info(f"Selected food details: {selected_food}")  # Логируем выбранный продукт

        # Получаем полную информацию о продукте
        if selected_food.get('food_type') == 'common':
            # Для обычных продуктов используем food_name вместо tag_id
            food_info = get_food_nutrients(selected_food['food_name'])
        else:
            food_info = get_branded_food_info(selected_food.get('nix_item_id'))

        logger.info(f"Food info from API: {food_info}")  # Логируем ответ API

        if not food_info:
            await callback_query.message.answer("Не удалось получить данные о продукте.")
            await callback_query.answer()
            return

        # Сохраняем выбранный продукт
        await state.update_data(
            selected_food=food_info,
            selected_product_index=index
        )

        # Формируем сообщение
        message_text = (
            f"Выбран продукт: <b>{food_info.get('food_name', selected_food['food_name'])}</b>\n\n"
            f"Пищевая ценность (на {food_info.get('serving_qty', 100)} {food_info.get('serving_unit', 'г')}):\n"
            f"• Калории: {food_info.get('calories', 0):.0f} ккал\n"
            f"• Белки: {food_info.get('protein', 0):.1f} г\n"
            f"• Жиры: {food_info.get('fat', 0):.1f} г\n"
            f"• Углеводы: {food_info.get('carbs', 0):.1f} г\n\n"
            "Введите количество в граммах:"
        )

        await callback_query.message.answer(message_text, parse_mode="HTML")
        await state.set_state(DiaryStates.entering_amount)
        await callback_query.answer()

    except Exception as e:
        logger.error(f"Error in handle_food_selection: {str(e)}", exc_info=True)
        await callback_query.answer("Произошла ошибка, попробуйте ещё раз")'''

async def return_to_meal_selection(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает к выбору приема пищи."""
    await start_food_entry(callback_query, state)


async def add_product_handler(callback_query: CallbackQuery, state: FSMContext):
    """Добавляет продукт со стандартным весом (100г)"""
    index = int(callback_query.data.split(":")[1])
    user_data = await state.get_data()
    product = user_data['search_results'][index]

    # Добавляем в базу (пример для 100г)
    success = add_food_entry(
        user_id=callback_query.from_user.id,
        date=datetime.now().strftime("%Y-%m-%d"),
        meal_type=user_data['meal_type'],
        food_name=product['food_name'],
        calories=product['calories'],
        protein=product['protein'],
        fat=product['fat'],
        carbs=product['carbs']
    )

    if success:
        await callback_query.answer("✅ Продукт добавлен!")
    else:
        await callback_query.answer("❌ Ошибка добавления")


async def enter_weight_handler(callback_query: CallbackQuery, state: FSMContext):
    """Запрашивает вес продукта"""
    index = int(callback_query.data.split(":")[1])
    await state.update_data(selected_product_index=index)

    await callback_query.message.answer(
        "Введите вес продукта в граммах:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(DiaryStates.entering_amount)
    await callback_query.answer()


async def back_to_list_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад'"""
    await callback_query.message.delete()
    await process_food_entry(callback_query.message, state)



