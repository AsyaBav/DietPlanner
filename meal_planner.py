"""
meal_planner.py

Модуль реализует систему планирования питания для пользователей Telegram-бота.

Основной функционал:
- Просмотр и управление планом питания на выбранную дату.
- Добавление рецептов по типу приема пищи (завтрак, обед, ужин и т.д.).
- Переключение между датами (вчера, сегодня, завтра).
- Генерация плана питания (будущий функционал).
- Перенос блюд из плана питания в дневник потребления.
- Удаление отдельных блюд или очистка всего плана на день.

Модуль использует:
- `aiogram` для работы с Telegram Bot API.
- Локальную базу данных через функции из модуля `database`.
- Клавиатуры из модуля `keyboards`.
- Вспомогательные утилиты из `utils` и настройки из `config`.

Этот файл содержит только логику планировщика питания и его взаимодействие с пользователем через бота.
"""


import logging
import asyncio
import random
from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from database import (
    get_user, get_daily_meal_plan, get_saved_recipes,
    add_to_meal_plan, remove_from_meal_plan, clear_meal_plan,
    get_meal_plan_for_type, get_recipe_details, toggle_favorite_recipe,
    add_food_entry
)
from keyboards import create_date_selection_keyboard, create_meal_types_keyboard
from utils import format_date
from config import MEAL_TYPES

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Состояния для планировщика
class MealPlanStates(StatesGroup):
    selecting_date = State()
    selecting_meal_type = State()
    selecting_recipe = State()
    viewing_meal_plan = State()
    generating_plan = State()


async def show_meal_planner(message: types.Message, state: FSMContext):
    """Показывает меню рациона питания."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться.")
        return

    # Показываем приветствие раздела рациона согласно ТЗ
    keyboard = [
        [
            types.InlineKeyboardButton(text="🍽 На сегодня", callback_data="meal_plan:today"),
            types.InlineKeyboardButton(text="📅 На неделю", callback_data="meal_plan:week")
        ],
        [types.InlineKeyboardButton(text="◀️ Главное меню", callback_data="meal_plan:back")]
    ]

    await message.answer(
        "🍽 <b>Сформируйте идеальный рацион под ваши цели!</b>\n\n"
        "Я помогу составить персональный план питания, учитывающий ваши потребности в калориях и макронутриентах.\n\n"
        "Выберите период для генерации рациона:",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_daily_plan(message: types.Message, state: FSMContext, selected_date=None):
    """Показывает план питания на день."""
    user_id = message.from_user.id

    # Если дата не указана, используем текущую
    if selected_date is None:
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # Сохраняем выбранную дату в состояние
    if state:
        await state.update_data(selected_date=selected_date)

    # Получаем данные о плане питания за выбранный день
    daily_plan = get_daily_meal_plan(user_id, selected_date)

    # Группируем записи по типам приемов пищи
    meals = {}
    for meal_type in MEAL_TYPES:
        meals[meal_type] = []

    for entry in daily_plan:
        meal_type = entry['meal_type']
        meals[meal_type].append(entry)

    # Формируем сообщение с планом
    message_text = f"🍽 <b>План питания на {format_date(selected_date)}</b>\n\n"

    if not daily_plan:
        message_text += "План питания на этот день еще не составлен.\n"
    else:
        # Формируем записи по приемам пищи
        for meal_type in MEAL_TYPES:
            meal_entries = meals[meal_type]
            if meal_entries:
                message_text += f"<b>{meal_type}:</b>\n"

                # Считаем суммарные значения для приема пищи
                meal_calories = sum(entry['calories'] for entry in meal_entries)

                for entry in meal_entries:
                    message_text += f"  • {entry['name']} – {entry['calories']:.0f} ккал\n"

                message_text += f"  Всего: {meal_calories:.0f} ккал\n\n"

    # Создаем клавиатуру для действий с планом
    keyboard = [
        [
            types.InlineKeyboardButton(text="◀️ Вчера", callback_data="plan_date:prev"),
            types.InlineKeyboardButton(text="Сегодня", callback_data="plan_date:today"),
            types.InlineKeyboardButton(text="Завтра ▶️", callback_data="plan_date:next")
        ],
        [
            types.InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="plan:add"),
            types.InlineKeyboardButton(text="🔄 Сгенерировать", callback_data="plan:generate")
        ]
    ]

    # Добавляем дополнительные кнопки, если план не пустой
    if daily_plan:
        keyboard.append([
            types.InlineKeyboardButton(text="📝 Добавить в дневник", callback_data="plan:to_diary"),
            types.InlineKeyboardButton(text="🗑 Очистить", callback_data="plan:clear")
        ])

    # Добавляем кнопки для просмотра отдельных приемов пищи
    for meal_type in MEAL_TYPES:
        if meals[meal_type]:
            keyboard.append([
                types.InlineKeyboardButton(text=f"👁 {meal_type}", callback_data=f"plan:{meal_type}")
            ])

    # Добавляем кнопку возврата в главное меню
    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Главное меню", callback_data="plan:back")
    ])

    # Отправляем сообщение
    await message.answer(
        text=message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def handle_plan_date_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты для плана питания."""
    data = callback_query.data.split(':')

    if len(data) > 1:
        date_action = data[1]

        if date_action == "prev":
            # Получаем предыдущую дату
            user_data = await state.get_data()
            current_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            prev_date = (current_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")

            await show_daily_plan(callback_query.message, state, prev_date)
        elif date_action == "next":
            # Получаем следующую дату
            user_data = await state.get_data()
            current_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            next_date = (current_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

            await show_daily_plan(callback_query.message, state, next_date)
        elif date_action == "today":
            # Показываем текущую дату
            today = datetime.now().strftime("%Y-%m-%d")
            await show_daily_plan(callback_query.message, state, today)
        else:
            # Показываем выбранную дату
            await show_daily_plan(callback_query.message, state, date_action)

    await callback_query.answer()


async def start_add_to_plan(callback_query: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления блюда в план питания."""
    # Показываем список приемов пищи
    keyboard = create_meal_types_keyboard()

    await callback_query.message.answer(
        "Выберите прием пищи для добавления блюда:",
        reply_markup=keyboard
    )

    await state.set_state(MealPlanStates.selecting_meal_type)
    await callback_query.answer()


async def handle_meal_type_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа приема пищи для плана."""
    meal_type = callback_query.data.split(':')[1]

    # Сохраняем выбранный тип приема пищи
    await state.update_data(meal_type=meal_type)

    # Показываем список доступных рецептов
    user_id = callback_query.from_user.id
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов. "
            "Сначала добавьте рецепты в разделе 'Рецепты'."
        )
        await state.clear()
        await callback_query.answer()
        return

    # Создаем клавиатуру с рецептами
    keyboard = []
    for recipe in recipes:
        recipe_name = recipe['name']
        if len(recipe_name) > 30:
            recipe_name = recipe_name[:27] + "..."

        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{'★' if recipe['is_favorite'] else '☆'} {recipe_name} ({recipe['calories']} ккал)",
                callback_data=f"plan_recipe:{recipe['id']}"
            )
        ])

    # Добавляем кнопку отмены
    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Отмена", callback_data="return_to_plan_view")
    ])

    await callback_query.message.answer(
        f"Выберите блюдо для {meal_type}:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(MealPlanStates.selecting_recipe)
    await callback_query.answer()


async def handle_recipe_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор рецепта для плана питания."""
    recipe_id = int(callback_query.data.split(':')[1])

    # Получаем данные из состояния
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    meal_type = user_data.get('meal_type')
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Добавляем рецепт в план
    plan_id = add_to_meal_plan(user_id, recipe_id, meal_type, selected_date)

    if plan_id:
        await callback_query.message.answer(f"✅ Блюдо успешно добавлено в план на {meal_type.lower()}!")
    else:
        await callback_query.message.answer("❌ Не удалось добавить блюдо в план. Попробуйте еще раз.")

    # Очищаем состояние и возвращаемся к просмотру плана
    await state.clear()
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def view_meal_type_plan(callback_query: CallbackQuery, state: FSMContext):
    """Показывает план для конкретного приема пищи с возможностью удаления."""
    meal_type = callback_query.data.split(':')[1]

    # Получаем данные из состояния или устанавливаем текущую дату
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Получаем блюда для этого приема пищи
    meal_plan = get_meal_plan_for_type(user_id, meal_type, selected_date)

    if not meal_plan:
        await callback_query.message.answer(f"На {meal_type.lower()} пока нет запланированных блюд.")
        await callback_query.answer()
        return

    # Формируем сообщение
    message_text = f"🍽 <b>{meal_type} ({format_date(selected_date)})</b>\n\n"

    # Считаем общие значения
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    # Добавляем информацию о каждом блюде
    for i, entry in enumerate(meal_plan, 1):
        message_text += f"{i}. <b>{entry['name']}</b>\n"
        message_text += f"   Калории: {entry['calories']:.0f} ккал\n"
        message_text += f"   БЖУ: {entry['protein']:.1f}г / {entry['fat']:.1f}г / {entry['carbs']:.1f}г\n\n"

        # Суммируем значения
        total_calories += entry['calories']
        total_protein += entry['protein']
        total_fat += entry['fat']
        total_carbs += entry['carbs']

    # Добавляем общую информацию
    message_text += f"<b>Всего для {meal_type.lower()}:</b>\n"
    message_text += f"Калории: {total_calories:.0f} ккал\n"
    message_text += f"БЖУ: {total_protein:.1f}г / {total_fat:.1f}г / {total_carbs:.1f}г\n"

    # Создаем клавиатуру для действий
    keyboard = []

    # Добавляем кнопки для удаления каждого блюда
    for entry in meal_plan:
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"🗑 Удалить {entry['name'][:20] + '...' if len(entry['name']) > 20 else entry['name']}",
                callback_data=f"delete_plan_entry:{entry['id']}"
            )
        ])

    # Добавляем кнопку для возврата
    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Назад к плану", callback_data="return_to_plan_view")
    ])

    await callback_query.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await callback_query.answer()


async def delete_plan_entry(callback_query: CallbackQuery, state: FSMContext):
    """Удаляет блюдо из плана питания."""
    plan_id = int(callback_query.data.split(':')[1])

    # Удаляем запись
    success = remove_from_meal_plan(plan_id)

    if success:
        # Редактируем текущее сообщение вместо отправки нового
        await callback_query.message.edit_text("✅ Блюдо удалено из плана питания!")
        # Небольшая задержка перед показом обновленного плана
        await asyncio.sleep(1)
    else:
        await callback_query.message.edit_text("❌ Не удалось удалить блюдо. Попробуйте еще раз.")

    # Возвращаемся к просмотру плана
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def clear_plan(callback_query: CallbackQuery, state: FSMContext):
    """Очищает план питания на выбранный день."""
    # Запрашиваем подтверждение
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    keyboard = [
        [
            types.InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_clear_plan:{selected_date}"),
            types.InlineKeyboardButton(text="❌ Нет", callback_data="cancel_clear_plan")
        ]
    ]

    await callback_query.message.answer(
        f"Вы действительно хотите очистить план питания на {format_date(selected_date)}?",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback_query.answer()


async def confirm_clear_plan(callback_query: CallbackQuery, state: FSMContext):
    """Подтверждает очистку плана питания."""
    date = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id

    # Очищаем план
    success = clear_meal_plan(user_id, date)

    if success:
        await callback_query.message.answer(f"✅ План питания на {format_date(date)} очищен!")
    else:
        await callback_query.message.answer("❌ Не удалось очистить план. Попробуйте еще раз.")

    # Показываем обновленный план
    await show_daily_plan(callback_query.message, state, date)
    await callback_query.answer()


async def cancel_clear_plan(callback_query: CallbackQuery, state: FSMContext):
    """Отменяет очистку плана питания."""
    await callback_query.message.answer("Очистка плана отменена.")

    # Показываем план
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def transfer_plan_to_diary(callback_query: CallbackQuery, state: FSMContext):
    """Переносит блюда из плана питания в дневник."""
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Получаем план питания на выбранный день
    daily_plan = get_daily_meal_plan(user_id, selected_date)

    if not daily_plan:
        await callback_query.message.answer("План питания на этот день пуст.")
        await callback_query.answer()
        return

    # Переносим каждое блюдо в дневник
    for entry in daily_plan:
        # Получаем детали рецепта
        recipe = get_recipe_details(entry['recipe_id'])

        if recipe:
            # Добавляем запись в дневник питания
            add_food_entry(
                user_id,
                selected_date,
                entry['meal_type'],
                recipe['name'],
                recipe['calories'],
                recipe['protein'],
                recipe['fat'],
                recipe['carbs']
            )

    await callback_query.message.answer(
        f"✅ План питания на {format_date(selected_date)} добавлен в дневник!"
    )
    await callback_query.answer()


async def generate_meal_plan(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует план питания на основе целей пользователя."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user:
        await callback_query.message.answer("Сначала нужно зарегистрироваться.")
        await callback_query.answer()
        return

    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Сначала очищаем текущий план на выбранный день
    clear_meal_plan(user_id, selected_date)

    # Получаем цель по калориям
    goal_calories = user['goal_calories']

    # Получаем сохраненные рецепты
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов для генерации плана. "
            "Сначала добавьте рецепты в разделе 'Рецепты'."
        )
        await callback_query.answer()
        return

    # Пытаемся распределить калории по приемам пищи
    # Завтрак: 25%, Обед: 35%, Ужин: 30%, Перекус: 10%
    meal_calories = {
        "Завтрак": goal_calories * 0.25,
        "Обед": goal_calories * 0.35,
        "Ужин": goal_calories * 0.30,
        "Перекус": goal_calories * 0.10
    }

    # Для каждого приема пищи находим подходящие рецепты
    for meal_type, target_calories in meal_calories.items():
        await callback_query.message.answer(f"Подбираем блюда для {meal_type.lower()}...")

        # Сначала пытаемся найти рецепты с калориями в пределах ±15% от целевых
        suitable_recipes = [
            r for r in recipes
            if target_calories * 0.85 <= r['calories'] <= target_calories * 1.15
        ]

        # Если не нашли подходящих, расширяем диапазон до ±25%
        if not suitable_recipes:
            suitable_recipes = [
                r for r in recipes
                if target_calories * 0.75 <= r['calories'] <= target_calories * 1.25
            ]

        # Если все еще нет подходящих, берем ближайший по калориям
        if not suitable_recipes and recipes:
            # Сортируем по абсолютной разнице с целевыми калориями
            recipes_sorted = sorted(recipes, key=lambda r: abs(r['calories'] - target_calories))
            suitable_recipes = [recipes_sorted[0]]

        # Добавляем выбранный рецепт в план
        if suitable_recipes:
            selected_recipe = random.choice(suitable_recipes)
            add_to_meal_plan(user_id, selected_recipe['id'], meal_type, selected_date)

    await callback_query.message.answer("✅ План питания сгенерирован успешно!")

    # Показываем созданный план
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def return_to_plan_view(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает к просмотру плана питания."""
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


# Выносим эти функции на уровень модуля
async def handle_meal_plan_menu(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор в меню рациона."""
    action = callback_query.data.split(':')[1]

    if action == "today":
        await generate_daily_meal_plan(callback_query, state)
    elif action == "week":
        await generate_weekly_meal_plan(callback_query, state)
    elif action == "back":
        from keyboards import after_calories_keyboard
        await callback_query.message.delete()
        await callback_query.message.answer(
            "Вы вернулись в главное меню",
            reply_markup=after_calories_keyboard
        )
    await callback_query.answer()


async def generate_daily_meal_plan(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует рацион на сегодня."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user:
        await callback_query.message.answer("Сначала нужно зарегистрироваться.")
        await callback_query.answer()
        return

    await callback_query.message.answer("🔄 Генерирую рацион на сегодня...")

    # Получаем цель по калориям и макронутриентам
    goal_calories = user['goal_calories']
    goal_protein = user['protein']
    goal_fat = user['fat']
    goal_carbs = user['carbs']

    # Текущая дата
    today = datetime.now().strftime("%Y-%m-%d")

    # Очищаем текущий план на сегодня
    clear_meal_plan(user_id, today)

    # Получаем сохраненные рецепты пользователя
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов для генерации рациона. "
            "Сначала добавьте рецепты в разделе 'Рецепты'."
        )
        await callback_query.answer()
        return

    # Распределяем калории по приемам пищи
    meal_distribution = {
        "Завтрак": 0.25,
        "Обед": 0.35,
        "Ужин": 0.30,
        "Перекус": 0.10
    }

    generated_plan = []

    for meal_type, percentage in meal_distribution.items():
        target_calories = goal_calories * percentage

        # Находим подходящие рецепты
        suitable_recipes = [
            r for r in recipes
            if target_calories * 0.8 <= r['calories'] <= target_calories * 1.2
        ]

        if not suitable_recipes:
            # Если нет подходящих, берем ближайший по калориям
            suitable_recipes = sorted(recipes, key=lambda r: abs(r['calories'] - target_calories))[:1]

        if suitable_recipes:
            selected_recipe = random.choice(suitable_recipes)
            add_to_meal_plan(user_id, selected_recipe['id'], meal_type, today)
            generated_plan.append({
                'meal_type': meal_type,
                'recipe': selected_recipe
            })

    # Показываем сгенерированный план
    await show_generated_daily_plan(callback_query, state, generated_plan, today)


async def show_generated_daily_plan(callback_query: CallbackQuery, state: FSMContext, plan, date):
    """Показывает сгенерированный план на день."""

    message_text = f"🍽 <b>Рацион на {format_date(date)}</b>\n\n"

    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    for item in plan:
        recipe = item['recipe']
        meal_type = item['meal_type']

        message_text += f"<b>{meal_type}:</b>\n"
        message_text += f"  • {recipe['name']} – {recipe['calories']:.0f} ккал\n"
        message_text += f"    БЖУ: {recipe['protein']:.1f}г / {recipe['fat']:.1f}г / {recipe['carbs']:.1f}г\n\n"

        total_calories += recipe['calories']
        total_protein += recipe['protein']
        total_fat += recipe['fat']
        total_carbs += recipe['carbs']

    message_text += f"<b>Итого за день:</b>\n"
    message_text += f"Калории: {total_calories:.0f} ккал\n"
    message_text += f"БЖУ: {total_protein:.1f}г / {total_fat:.1f}г / {total_carbs:.1f}г"

    # Создаем клавиатуру с возможностью замены блюд и сохранения
    keyboard = []

    for item in plan:
        recipe = item['recipe']
        meal_type = item['meal_type']
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"🔄 Заменить {recipe['name'][:20]}...",
                callback_data=f"replace_dish:{recipe['id']}:{meal_type}:{date}"
            )
        ])

    keyboard.append([
        types.InlineKeyboardButton(
            text="💾 Сохранить рацион в дневник",
            callback_data=f"save_plan_to_diary:{date}"
        )
    ])

    keyboard.append([
        types.InlineKeyboardButton(text="🔄 Сгенерировать заново", callback_data="meal_plan:today"),
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="meal_plan:back")
    ])

    await callback_query.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def generate_weekly_meal_plan(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует рацион на неделю."""
    await callback_query.message.answer(
        "📅 <b>Генерация недельного рациона</b>\n\n"
        "🔧 Функция генерации рациона на неделю находится в разработке.\n"
        "Пока что вы можете генерировать рацион на каждый день отдельно.",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="meal_plan:back")]
        ])
    )
    await callback_query.answer()


async def handle_replace_dish(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает замену блюда в рационе."""
    data = callback_query.data.split(':')
    recipe_id = int(data[1])
    meal_type = data[2]
    date = data[3]

    user_id = callback_query.from_user.id

    # Получаем текущий рецепт для определения целевых калорий
    current_recipe = get_recipe_details(recipe_id)
    if not current_recipe:
        await callback_query.answer("Ошибка: рецепт не найден")
        return

    target_calories = current_recipe['calories']

    # Получаем все рецепты пользователя кроме текущего
    all_recipes = get_saved_recipes(user_id)
    available_recipes = [r for r in all_recipes if r['id'] != recipe_id]

    if not available_recipes:
        await callback_query.answer("Нет других рецептов для замены")
        return

    # Находим похожие по калориям рецепты
    similar_recipes = [
        r for r in available_recipes
        if target_calories * 0.8 <= r['calories'] <= target_calories * 1.2
    ]

    if not similar_recipes:
        # Если нет похожих, берем 3 ближайших по калориям
        similar_recipes = sorted(
            available_recipes, 
            key=lambda r: abs(r['calories'] - target_calories)
        )[:3]

    # Показываем варианты замены
    message_text = f"🔄 <b>Замена блюда для {meal_type}</b>\n\n"
    message_text += f"Текущее: {current_recipe['name']} ({current_recipe['calories']} ккал)\n\n"
    message_text += "Выберите замену:"

    keyboard = []
    for recipe in similar_recipes[:5]:  # Показываем максимум 5 вариантов
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{recipe['name']} ({recipe['calories']} ккал)",
                callback_data=f"confirm_replace:{recipe_id}:{recipe['id']}:{meal_type}:{date}"
            )
        ])

    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Отмена", callback_data=f"show_plan:{date}")
    ])

    await callback_query.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback_query.answer()


async def confirm_replace_dish(callback_query: CallbackQuery, state: FSMContext):
    """Подтверждает замену блюда."""
    data = callback_query.data.split(':')
    old_recipe_id = int(data[1])
    new_recipe_id = int(data[2])
    meal_type = data[3]
    date = data[4]

    user_id = callback_query.from_user.id

    # Получаем ID записи в плане питания для замены
    plan_entries = get_meal_plan_for_type(user_id, meal_type, date)
    plan_entry_to_replace = None

    for entry in plan_entries:
        if entry['recipe_id'] == old_recipe_id:
            plan_entry_to_replace = entry
            break

    if plan_entry_to_replace:
        # Удаляем старую запись
        remove_from_meal_plan(plan_entry_to_replace['id'])

        # Добавляем новую
        add_to_meal_plan(user_id, new_recipe_id, meal_type, date)

        new_recipe = get_recipe_details(new_recipe_id)
        await callback_query.message.answer(
            f"✅ Блюдо заменено на {new_recipe['name']}!"
        )

        # Показываем обновленный план
        await show_daily_plan(callback_query.message, state, date)
    else:
        await callback_query.message.answer("❌ Ошибка при замене блюда")

    await callback_query.answer()


async def save_plan_to_diary(callback_query: CallbackQuery, state: FSMContext):
    """Сохраняет весь рацион в дневник."""
    date = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id

    # Получаем план питания на выбранный день
    daily_plan = get_daily_meal_plan(user_id, date)

    if not daily_plan:
        await callback_query.message.answer("План питания на этот день пуст.")
        await callback_query.answer()
        return

    # Переносим каждое блюдо в дневник
    for entry in daily_plan:
        # Получаем детали рецепта
        recipe = get_recipe_details(entry['recipe_id'])

        if recipe:
            # Добавляем запись в дневник питания
            add_food_entry(
                user_id,
                date,
                entry['meal_type'],
                recipe['name'],
                recipe['calories'],
                recipe['protein'],
                recipe['fat'],
                recipe['carbs']
            )

    await callback_query.message.answer(
        f"✅ Рацион на {format_date(date)} сохранен в дневник питания!"
    )
    await callback_query.answer()

Модуль реализует систему планирования питания для пользователей Telegram-бота.

Основной функционал:
- Просмотр и управление планом питания на выбранную дату.
- Добавление рецептов по типу приема пищи (завтрак, обед, ужин и т.д.).
- Переключение между датами (вчера, сегодня, завтра).
- Генерация плана питания (будущий функционал).
- Перенос блюд из плана питания в дневник потребления.
- Удаление отдельных блюд или очистка всего плана на день.

Модуль использует:
- `aiogram` для работы с Telegram Bot API.
- Локальную базу данных через функции из модуля `database`.
- Клавиатуры из модуля `keyboards`.
- Вспомогательные утилиты из `utils` и настройки из `config`.

Этот файл содержит только логику планировщика питания и его взаимодействие с пользователем через бота.
"""


import logging
import asyncio
import random
from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from database import (
    get_user, get_daily_meal_plan, get_saved_recipes,
    add_to_meal_plan, remove_from_meal_plan, clear_meal_plan,
    get_meal_plan_for_type, get_recipe_details, toggle_favorite_recipe,
    add_food_entry
)
from keyboards import create_date_selection_keyboard, create_meal_types_keyboard
from utils import format_date
from config import MEAL_TYPES

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Состояния для планировщика
class MealPlanStates(StatesGroup):
    selecting_date = State()
    selecting_meal_type = State()
    selecting_recipe = State()
    viewing_meal_plan = State()
    generating_plan = State()


async def show_meal_planner(message: types.Message, state: FSMContext):
    """Показывает меню рациона питания."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться.")
        return

    # Показываем приветствие раздела рациона согласно ТЗ
    keyboard = [
        [
            types.InlineKeyboardButton(text="🍽 На сегодня", callback_data="meal_plan:today"),
            types.InlineKeyboardButton(text="📅 На неделю", callback_data="meal_plan:week")
        ],
        [types.InlineKeyboardButton(text="◀️ Главное меню", callback_data="meal_plan:back")]
    ]

    await message.answer(
        "🍽 <b>Сформируйте идеальный рацион под ваши цели!</b>\n\n"
        "Я помогу составить персональный план питания, учитывающий ваши потребности в калориях и макронутриентах.\n\n"
        "Выберите период для генерации рациона:",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_daily_plan(message: types.Message, state: FSMContext, selected_date=None):
    """Показывает план питания на день."""
    user_id = message.from_user.id

    # Если дата не указана, используем текущую
    if selected_date is None:
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # Сохраняем выбранную дату в состояние
    if state:
        await state.update_data(selected_date=selected_date)

    # Получаем данные о плане питания за выбранный день
    daily_plan = get_daily_meal_plan(user_id, selected_date)

    # Группируем записи по типам приемов пищи
    meals = {}
    for meal_type in MEAL_TYPES:
        meals[meal_type] = []

    for entry in daily_plan:
        meal_type = entry['meal_type']
        meals[meal_type].append(entry)

    # Формируем сообщение с планом
    message_text = f"🍽 <b>План питания на {format_date(selected_date)}</b>\n\n"

    if not daily_plan:
        message_text += "План питания на этот день еще не составлен.\n"
    else:
        # Формируем записи по приемам пищи
        for meal_type in MEAL_TYPES:
            meal_entries = meals[meal_type]
            if meal_entries:
                message_text += f"<b>{meal_type}:</b>\n"

                # Считаем суммарные значения для приема пищи
                meal_calories = sum(entry['calories'] for entry in meal_entries)

                for entry in meal_entries:
                    message_text += f"  • {entry['name']} – {entry['calories']:.0f} ккал\n"

                message_text += f"  Всего: {meal_calories:.0f} ккал\n\n"

    # Создаем клавиатуру для действий с планом
    keyboard = [
        [
            types.InlineKeyboardButton(text="◀️ Вчера", callback_data="plan_date:prev"),
            types.InlineKeyboardButton(text="Сегодня", callback_data="plan_date:today"),
            types.InlineKeyboardButton(text="Завтра ▶️", callback_data="plan_date:next")
        ],
        [
            types.InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="plan:add"),
            types.InlineKeyboardButton(text="🔄 Сгенерировать", callback_data="plan:generate")
        ]
    ]

    # Добавляем дополнительные кнопки, если план не пустой
    if daily_plan:
        keyboard.append([
            types.InlineKeyboardButton(text="📝 Добавить в дневник", callback_data="plan:to_diary"),
            types.InlineKeyboardButton(text="🗑 Очистить", callback_data="plan:clear")
        ])

    # Добавляем кнопки для просмотра отдельных приемов пищи
    for meal_type in MEAL_TYPES:
        if meals[meal_type]:
            keyboard.append([
                types.InlineKeyboardButton(text=f"👁 {meal_type}", callback_data=f"plan:{meal_type}")
            ])

    # Добавляем кнопку возврата в главное меню
    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Главное меню", callback_data="plan:back")
    ])

    # Отправляем сообщение
    await message.answer(
        text=message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def handle_plan_date_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты для плана питания."""
    data = callback_query.data.split(':')

    if len(data) > 1:
        date_action = data[1]

        if date_action == "prev":
            # Получаем предыдущую дату
            user_data = await state.get_data()
            current_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            prev_date = (current_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")

            await show_daily_plan(callback_query.message, state, prev_date)
        elif date_action == "next":
            # Получаем следующую дату
            user_data = await state.get_data()
            current_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            next_date = (current_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

            await show_daily_plan(callback_query.message, state, next_date)
        elif date_action == "today":
            # Показываем текущую дату
            today = datetime.now().strftime("%Y-%m-%d")
            await show_daily_plan(callback_query.message, state, today)
        else:
            # Показываем выбранную дату
            await show_daily_plan(callback_query.message, state, date_action)

    await callback_query.answer()


async def start_add_to_plan(callback_query: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления блюда в план питания."""
    # Показываем список приемов пищи
    keyboard = create_meal_types_keyboard()

    await callback_query.message.answer(
        "Выберите прием пищи для добавления блюда:",
        reply_markup=keyboard
    )

    await state.set_state(MealPlanStates.selecting_meal_type)
    await callback_query.answer()


async def handle_meal_type_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа приема пищи для плана."""
    meal_type = callback_query.data.split(':')[1]

    # Сохраняем выбранный тип приема пищи
    await state.update_data(meal_type=meal_type)

    # Показываем список доступных рецептов
    user_id = callback_query.from_user.id
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов. "
            "Сначала добавьте рецепты в разделе 'Рецепты'."
        )
        await state.clear()
        await callback_query.answer()
        return

    # Создаем клавиатуру с рецептами
    keyboard = []
    for recipe in recipes:
        recipe_name = recipe['name']
        if len(recipe_name) > 30:
            recipe_name = recipe_name[:27] + "..."

        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{'★' if recipe['is_favorite'] else '☆'} {recipe_name} ({recipe['calories']} ккал)",
                callback_data=f"plan_recipe:{recipe['id']}"
            )
        ])

    # Добавляем кнопку отмены
    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Отмена", callback_data="return_to_plan_view")
    ])

    await callback_query.message.answer(
        f"Выберите блюдо для {meal_type}:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(MealPlanStates.selecting_recipe)
    await callback_query.answer()


async def handle_recipe_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор рецепта для плана питания."""
    recipe_id = int(callback_query.data.split(':')[1])

    # Получаем данные из состояния
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    meal_type = user_data.get('meal_type')
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Добавляем рецепт в план
    plan_id = add_to_meal_plan(user_id, recipe_id, meal_type, selected_date)

    if plan_id:
        await callback_query.message.answer(f"✅ Блюдо успешно добавлено в план на {meal_type.lower()}!")
    else:
        await callback_query.message.answer("❌ Не удалось добавить блюдо в план. Попробуйте еще раз.")

    # Очищаем состояние и возвращаемся к просмотру плана
    await state.clear()
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def view_meal_type_plan(callback_query: CallbackQuery, state: FSMContext):
    """Показывает план для конкретного приема пищи с возможностью удаления."""
    meal_type = callback_query.data.split(':')[1]

    # Получаем данные из состояния или устанавливаем текущую дату
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Получаем блюда для этого приема пищи
    meal_plan = get_meal_plan_for_type(user_id, meal_type, selected_date)

    if not meal_plan:
        await callback_query.message.answer(f"На {meal_type.lower()} пока нет запланированных блюд.")
        await callback_query.answer()
        return

    # Формируем сообщение
    message_text = f"🍽 <b>{meal_type} ({format_date(selected_date)})</b>\n\n"

    # Считаем общие значения
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    # Добавляем информацию о каждом блюде
    for i, entry in enumerate(meal_plan, 1):
        message_text += f"{i}. <b>{entry['name']}</b>\n"
        message_text += f"   Калории: {entry['calories']:.0f} ккал\n"
        message_text += f"   БЖУ: {entry['protein']:.1f}г / {entry['fat']:.1f}г / {entry['carbs']:.1f}г\n\n"

        # Суммируем значения
        total_calories += entry['calories']
        total_protein += entry['protein']
        total_fat += entry['fat']
        total_carbs += entry['carbs']

    # Добавляем общую информацию
    message_text += f"<b>Всего для {meal_type.lower()}:</b>\n"
    message_text += f"Калории: {total_calories:.0f} ккал\n"
    message_text += f"БЖУ: {total_protein:.1f}г / {total_fat:.1f}г / {total_carbs:.1f}г\n"

    # Создаем клавиатуру для действий
    keyboard = []

    # Добавляем кнопки для удаления каждого блюда
    for entry in meal_plan:
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"🗑 Удалить {entry['name'][:20] + '...' if len(entry['name']) > 20 else entry['name']}",
                callback_data=f"delete_plan_entry:{entry['id']}"
            )
        ])

    # Добавляем кнопку для возврата
    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Назад к плану", callback_data="return_to_plan_view")
    ])

    await callback_query.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await callback_query.answer()


async def delete_plan_entry(callback_query: CallbackQuery, state: FSMContext):
    """Удаляет блюдо из плана питания."""
    plan_id = int(callback_query.data.split(':')[1])

    # Удаляем запись
    success = remove_from_meal_plan(plan_id)

    if success:
        # Редактируем текущее сообщение вместо отправки нового
        await callback_query.message.edit_text("✅ Блюдо удалено из плана питания!")
        # Небольшая задержка перед показом обновленного плана
        await asyncio.sleep(1)
    else:
        await callback_query.message.edit_text("❌ Не удалось удалить блюдо. Попробуйте еще раз.")

    # Возвращаемся к просмотру плана
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def clear_plan(callback_query: CallbackQuery, state: FSMContext):
    """Очищает план питания на выбранный день."""
    # Запрашиваем подтверждение
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    keyboard = [
        [
            types.InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_clear_plan:{selected_date}"),
            types.InlineKeyboardButton(text="❌ Нет", callback_data="cancel_clear_plan")
        ]
    ]

    await callback_query.message.answer(
        f"Вы действительно хотите очистить план питания на {format_date(selected_date)}?",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback_query.answer()


async def confirm_clear_plan(callback_query: CallbackQuery, state: FSMContext):
    """Подтверждает очистку плана питания."""
    date = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id

    # Очищаем план
    success = clear_meal_plan(user_id, date)

    if success:
        await callback_query.message.answer(f"✅ План питания на {format_date(date)} очищен!")
    else:
        await callback_query.message.answer("❌ Не удалось очистить план. Попробуйте еще раз.")

    # Показываем обновленный план
    await show_daily_plan(callback_query.message, state, date)
    await callback_query.answer()


async def cancel_clear_plan(callback_query: CallbackQuery, state: FSMContext):
    """Отменяет очистку плана питания."""
    await callback_query.message.answer("Очистка плана отменена.")

    # Показываем план
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def transfer_plan_to_diary(callback_query: CallbackQuery, state: FSMContext):
    """Переносит блюда из плана питания в дневник."""
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Получаем план питания на выбранный день
    daily_plan = get_daily_meal_plan(user_id, selected_date)

    if not daily_plan:
        await callback_query.message.answer("План питания на этот день пуст.")
        await callback_query.answer()
        return

    # Переносим каждое блюдо в дневник
    for entry in daily_plan:
        # Получаем детали рецепта
        recipe = get_recipe_details(entry['recipe_id'])

        if recipe:
            # Добавляем запись в дневник питания
            add_food_entry(
                user_id,
                selected_date,
                entry['meal_type'],
                recipe['name'],
                recipe['calories'],
                recipe['protein'],
                recipe['fat'],
                recipe['carbs']
            )

    await callback_query.message.answer(
        f"✅ План питания на {format_date(selected_date)} добавлен в дневник!"
    )
    await callback_query.answer()


async def generate_meal_plan(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует план питания на основе целей пользователя."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user:
        await callback_query.message.answer("Сначала нужно зарегистрироваться.")
        await callback_query.answer()
        return

    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    # Сначала очищаем текущий план на выбранный день
    clear_meal_plan(user_id, selected_date)

    # Получаем цель по калориям
    goal_calories = user['goal_calories']

    # Получаем сохраненные рецепты
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов для генерации плана. "
            "Сначала добавьте рецепты в разделе 'Рецепты'."
        )
        await callback_query.answer()
        return

    # Пытаемся распределить калории по приемам пищи
    # Завтрак: 25%, Обед: 35%, Ужин: 30%, Перекус: 10%
    meal_calories = {
        "Завтрак": goal_calories * 0.25,
        "Обед": goal_calories * 0.35,
        "Ужин": goal_calories * 0.30,
        "Перекус": goal_calories * 0.10
    }

    # Для каждого приема пищи находим подходящие рецепты
    for meal_type, target_calories in meal_calories.items():
        await callback_query.message.answer(f"Подбираем блюда для {meal_type.lower()}...")

        # Сначала пытаемся найти рецепты с калориями в пределах ±15% от целевых
        suitable_recipes = [
            r for r in recipes
            if target_calories * 0.85 <= r['calories'] <= target_calories * 1.15
        ]

        # Если не нашли подходящих, расширяем диапазон до ±25%
        if not suitable_recipes:
            suitable_recipes = [
                r for r in recipes
                if target_calories * 0.75 <= r['calories'] <= target_calories * 1.25
            ]

        # Если все еще нет подходящих, берем ближайший по калориям
        if not suitable_recipes and recipes:
            # Сортируем по абсолютной разнице с целевыми калориями
            recipes_sorted = sorted(recipes, key=lambda r: abs(r['calories'] - target_calories))
            suitable_recipes = [recipes_sorted[0]]

        # Добавляем выбранный рецепт в план
        if suitable_recipes:
            selected_recipe = random.choice(suitable_recipes)
            add_to_meal_plan(user_id, selected_recipe['id'], meal_type, selected_date)

    await callback_query.message.answer("✅ План питания сгенерирован успешно!")

    # Показываем созданный план
    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


async def return_to_plan_view(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает к просмотру плана питания."""
    user_data = await state.get_data()
    selected_date = user_data.get('selected_date', datetime.now().strftime("%Y-%m-%d"))

    await show_daily_plan(callback_query.message, state, selected_date)
    await callback_query.answer()


# Выносим эти функции на уровень модуля
async def handle_meal_plan_menu(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор в меню рациона."""
    action = callback_query.data.split(':')[1]

    if action == "today":
        await generate_daily_meal_plan(callback_query, state)
    elif action == "week":
        await generate_weekly_meal_plan(callback_query, state)
    elif action == "back":
        from keyboards import after_calories_keyboard
        await callback_query.message.delete()
        await callback_query.message.answer(
            "Вы вернулись в главное меню",
            reply_markup=after_calories_keyboard
        )
    await callback_query.answer()


async def generate_daily_meal_plan(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует рацион на сегодня."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user:
        await callback_query.message.answer("Сначала нужно зарегистрироваться.")
        await callback_query.answer()
        return

    await callback_query.message.answer("🔄 Генерирую рацион на сегодня...")

    # Получаем цель по калориям и макронутриентам
    goal_calories = user['goal_calories']
    goal_protein = user['protein']
    goal_fat = user['fat']
    goal_carbs = user['carbs']

    # Текущая дата
    today = datetime.now().strftime("%Y-%m-%d")

    # Очищаем текущий план на сегодня
    clear_meal_plan(user_id, today)

    # Получаем сохраненные рецепты пользователя
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов для генерации рациона. "
            "Сначала добавьте рецепты в разделе 'Рецепты'."
        )
        await callback_query.answer()
        return

    # Распределяем калории по приемам пищи
    meal_distribution = {
        "Завтрак": 0.25,
        "Обед": 0.35,
        "Ужин": 0.30,
        "Перекус": 0.10
    }

    generated_plan = []

    for meal_type, percentage in meal_distribution.items():
        target_calories = goal_calories * percentage

        # Находим подходящие рецепты
        suitable_recipes = [
            r for r in recipes
            if target_calories * 0.8 <= r['calories'] <= target_calories * 1.2
        ]

        if not suitable_recipes:
            # Если нет подходящих, берем ближайший по калориям
            suitable_recipes = sorted(recipes, key=lambda r: abs(r['calories'] - target_calories))[:1]

        if suitable_recipes:
            selected_recipe = random.choice(suitable_recipes)
            add_to_meal_plan(user_id, selected_recipe['id'], meal_type, today)
            generated_plan.append({
                'meal_type': meal_type,
                'recipe': selected_recipe
            })

    # Показываем сгенерированный план
    await show_generated_daily_plan(callback_query, state, generated_plan, today)


async def show_generated_daily_plan(callback_query: CallbackQuery, state: FSMContext, plan, date):
    """Показывает сгенерированный план на день."""

    message_text = f"🍽 <b>Рацион на {format_date(date)}</b>\n\n"

    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    for item in plan:
        recipe = item['recipe']
        meal_type = item['meal_type']

        message_text += f"<b>{meal_type}:</b>\n"
        message_text += f"  • {recipe['name']} – {recipe['calories']:.0f} ккал\n"
        message_text += f"    БЖУ: {recipe['protein']:.1f}г / {recipe['fat']:.1f}г / {recipe['carbs']:.1f}г\n\n"

        total_calories += recipe['calories']
        total_protein += recipe['protein']
        total_fat += recipe['fat']
        total_carbs += recipe['carbs']

    message_text += f"<b>Итого за день:</b>\n"
    message_text += f"Калории: {total_calories:.0f} ккал\n"
    message_text += f"БЖУ: {total_protein:.1f}г / {total_fat:.1f}г / {total_carbs:.1f}г"

    # Создаем клавиатуру с возможностью замены блюд и сохранения
    keyboard = []

    for item in plan:
        recipe = item['recipe']
        meal_type = item['meal_type']
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"🔄 Заменить {recipe['name'][:20]}...",
                callback_data=f"replace_dish:{recipe['id']}:{meal_type}:{date}"
            )
        ])

    keyboard.append([
        types.InlineKeyboardButton(
            text="💾 Сохранить рацион в дневник",
            callback_data=f"save_plan_to_diary:{date}"
        )
    ])

    keyboard.append([
        types.InlineKeyboardButton(text="🔄 Сгенерировать заново", callback_data="meal_plan:today"),
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="meal_plan:back")
    ])

    await callback_query.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def generate_weekly_meal_plan(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует рацион на неделю."""
    await callback_query.message.answer(
        "📅 <b>Генерация недельного рациона</b>\n\n"
        "🔧 Функция генерации рациона на неделю находится в разработке.\n"
        "Пока что вы можете генерировать рацион на каждый день отдельно.",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="meal_plan:back")]
        ])
    )
    await callback_query.answer()


async def handle_replace_dish(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает замену блюда в рационе."""
    data = callback_query.data.split(':')
    recipe_id = int(data[1])
    meal_type = data[2]
    date = data[3]

    user_id = callback_query.from_user.id

    # Получаем текущий рецепт для определения целевых калорий
    current_recipe = get_recipe_details(recipe_id)
    if not current_recipe:
        await callback_query.answer("Ошибка: рецепт не найден")
        return

    target_calories = current_recipe['calories']

    # Получаем все рецепты пользователя кроме текущего
    all_recipes = get_saved_recipes(user_id)
    available_recipes = [r for r in all_recipes if r['id'] != recipe_id]

    if not available_recipes:
        await callback_query.answer("Нет других рецептов для замены")
        return

    # Находим похожие по калориям рецепты
    similar_recipes = [
        r for r in available_recipes
        if target_calories * 0.8 <= r['calories'] <= target_calories * 1.2
    ]

    if not similar_recipes:
        # Если нет похожих, берем 3 ближайших по калориям
        similar_recipes = sorted(
            available_recipes, 
            key=lambda r: abs(r['calories'] - target_calories)
        )[:3]

    # Показываем варианты замены
    message_text = f"🔄 <b>Замена блюда для {meal_type}</b>\n\n"
    message_text += f"Текущее: {current_recipe['name']} ({current_recipe['calories']} ккал)\n\n"
    message_text += "Выберите замену:"

    keyboard = []
    for recipe in similar_recipes[:5]:  # Показываем максимум 5 вариантов
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{recipe['name']} ({recipe['calories']} ккал)",
                callback_data=f"confirm_replace:{recipe_id}:{recipe['id']}:{meal_type}:{date}"
            )
        ])

    keyboard.append([
        types.InlineKeyboardButton(text="◀️ Отмена", callback_data=f"show_plan:{date}")
    ])

    await callback_query.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback_query.answer()


async def confirm_replace_dish(callback_query: CallbackQuery, state: FSMContext):
    """Подтверждает замену блюда."""
    data = callback_query.data.split(':')
    old_recipe_id = int(data[1])
    new_recipe_id = int(data[2])
    meal_type = data[3]
    date = data[4]

    user_id = callback_query.from_user.id

    # Получаем ID записи в плане питания для замены
    plan_entries = get_meal_plan_for_type(user_id, meal_type, date)
    plan_entry_to_replace = None

    for entry in plan_entries:
        if entry['recipe_id'] == old_recipe_id:
            plan_entry_to_replace = entry
            break

    if plan_entry_to_replace:
        # Удаляем старую запись
        remove_from_meal_plan(plan_entry_to_replace['id'])

        # Добавляем новую
        add_to_meal_plan(user_id, new_recipe_id, meal_type, date)

        new_recipe = get_recipe_details(new_recipe_id)
        await callback_query.message.answer(
            f"✅ Блюдо заменено на {new_recipe['name']}!"
        )

        # Показываем обновленный план
        await show_daily_plan(callback_query.message, state, date)
    else:
        await callback_query.message.answer("❌ Ошибка при замене блюда")

    await callback_query.answer()


async def save_plan_to_diary(callback_query: CallbackQuery, state: FSMContext):
    """Сохраняет весь рацион в дневник."""
    date = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id

    # Получаем план питания на выбранный день
    daily_plan = get_daily_meal_plan(user_id, date)

    if not daily_plan:
        await callback_query.message.answer("План питания на этот день пуст.")
        await callback_query.answer()
        return

    # Переносим каждое блюдо в дневник
    for entry in daily_plan:
        # Получаем детали рецепта
        recipe = get_recipe_details(entry['recipe_id'])

        if recipe:
            # Добавляем запись в дневник питания
            add_food_entry(
                user_id,
                date,
                entry['meal_type'],
                recipe['name'],
                recipe['calories'],
                recipe['protein'],
                recipe['fat'],
                recipe['carbs']
            )

    await callback_query.message.answer(
        f"✅ Рацион на {format_date(date)} сохранен в дневник питания!"
    )
    await callback_query.answer()