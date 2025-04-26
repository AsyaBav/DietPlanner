import asyncio
import logging
import random
from aiogram import types, F, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from datetime import datetime

from database import (
    save_recipe, get_saved_recipes, get_recipe_details, toggle_favorite_recipe,
    delete_recipe, add_food_entry, get_user
)
from keyboards import create_recipes_keyboard, create_recipe_confirmation_keyboard
from food_api import search_food, get_food_nutrients, get_branded_food_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовые шаблоны рецептов для разных целей
BASE_RECIPES = {
    "🔻 Похудение": [
        {
            "name": "Салат с куриной грудкой",
            "ingredients": "Куриная грудка - 150 г\nЛистья салата - 80 г\nОгурец - 1 шт\nПомидор - 1 шт\nОливковое масло - 1 ч.л.\nЛимонный сок - 1 ст.л.\nСоль, перец - по вкусу",
            "instructions": "1. Куриную грудку отварить и нарезать кубиками\n2. Овощи нарезать и смешать с курицей\n3. Заправить оливковым маслом и лимонным соком\n4. Посолить, поперчить по вкусу",
            "calories": 220,
            "protein": 30,
            "fat": 8,
            "carbs": 10
        },
        {
            "name": "Овощной омлет",
            "ingredients": "Яйца - 3 шт\nМолоко 1% - 30 мл\nШпинат - 50 г\nПомидор - 1 шт\nСладкий перец - 1/2 шт\nСоль, перец - по вкусу",
            "instructions": "1. Яйца взбить с молоком, посолить и поперчить\n2. Овощи мелко нарезать\n3. Смешать овощи с яичной смесью\n4. Вылить на разогретую сковороду\n5. Готовить под крышкой на среднем огне 5-7 минут",
            "calories": 250,
            "protein": 20,
            "fat": 15,
            "carbs": 8
        }
    ],
    "🔺 Набор веса": [
        {
            "name": "Протеиновый коктейль с бананом",
            "ingredients": "Молоко 3.2% - 250 мл\nПротеин - 30 г (1 мерная ложка)\nБанан - 1 шт\nМед - 1 ст.л.\nОвсяные хлопья - 30 г",
            "instructions": "1. Добавить все ингредиенты в блендер\n2. Взбить до однородной массы\n3. Подавать охлажденным",
            "calories": 450,
            "protein": 35,
            "fat": 10,
            "carbs": 55
        },
        {
            "name": "Паста с куриным филе",
            "ingredients": "Макароны - 100 г\nКуриное филе - 200 г\nСливки 20% - 100 мл\nСыр пармезан - 30 г\nЧеснок - 2 зубчика\nОливковое масло - 2 ст.л.\nСоль, перец, специи - по вкусу",
            "instructions": "1. Макароны отварить согласно инструкции\n2. Куриное филе нарезать, обжарить на оливковом масле\n3. Добавить измельченный чеснок и сливки\n4. Тушить 5-7 минут\n5. Добавить макароны, перемешать\n6. Посыпать тертым сыром",
            "calories": 650,
            "protein": 50,
            "fat": 25,
            "carbs": 60
        }
    ],
    "🔄 Поддержание текущего веса": [
        {
            "name": "Киноа с овощами",
            "ingredients": "Киноа - 70 г\nБрокколи - 100 г\nМорковь - 1 шт\nСладкий перец - 1 шт\nОливковое масло - 1 ст.л.\nЛимонный сок - 1 ч.л.\nСоль, перец, зелень - по вкусу",
            "instructions": "1. Киноа промыть и отварить\n2. Овощи нарезать и обжарить на оливковом масле\n3. Смешать киноа с овощами\n4. Добавить лимонный сок, соль, перец и зелень",
            "calories": 350,
            "protein": 12,
            "fat": 10,
            "carbs": 55
        },
        {
            "name": "Творожная запеканка",
            "ingredients": "Творог 5% - 250 г\nЯйца - 2 шт\nМед - 2 ст.л.\nВанилин - на кончике ножа\nЯблоко - 1 шт\nОвсяные хлопья - 30 г",
            "instructions": "1. Творог смешать с яйцами и медом\n2. Яблоко натереть на терке\n3. Добавить яблоко, овсяные хлопья и ванилин к творожной массе\n4. Выложить в форму и выпекать при 180°C 30-35 минут",
            "calories": 400,
            "protein": 30,
            "fat": 15,
            "carbs": 35
        }
    ]
}


# Состояния для создания и выбора рецептов
class RecipeStates(StatesGroup):
    selecting_type = State()
    entering_name = State()
    entering_ingredients = State()
    entering_instructions = State()
    entering_calories = State()
    entering_protein = State()
    entering_fat = State()
    entering_carbs = State()
    confirming = State()
    generating = State()
    searching = State()


async def show_recipes_menu(message: types.Message, state: FSMContext):
    """Показывает меню рецептов."""
    await state.clear()
    keyboard = create_recipes_keyboard()
    await message.answer("🍴 <b>Меню рецептов</b>\n\nЗдесь ты можешь найти, сохранить или создать новые рецепты.",
                         parse_mode="HTML",
                         reply_markup=keyboard)


async def handle_recipes_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатия на кнопки меню рецептов."""
    action = callback_query.data.split(':')[1]

    if action == "search":
        await show_saved_recipes(callback_query, state)
    elif action == "favorites":
        await show_favorite_recipes(callback_query, state)
    elif action == "create":
        await start_recipe_creation(callback_query, state)
    elif action == "generate":
        await generate_recipe(callback_query, state)
    elif action == "back":
        await callback_query.message.answer("Вернулись в главное меню.")
        await callback_query.answer()


async def show_saved_recipes(callback_query: CallbackQuery, state: FSMContext):
    """Показывает сохраненные рецепты пользователя."""
    user_id = callback_query.from_user.id
    recipes = get_saved_recipes(user_id)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет сохраненных рецептов. Вы можете создать новый или сгенерировать рецепт.")
        await callback_query.answer()
        return

    text = "📝 <b>Ваши рецепты:</b>\n\n"

    # Создаем клавиатуру с рецептами
    keyboard = []
    for recipe in recipes:
        recipe_name = recipe['name']
        if len(recipe_name) > 30:
            recipe_name = recipe_name[:27] + "..."

        keyboard.append([types.InlineKeyboardButton(
            text=f"{'★' if recipe['is_favorite'] else '☆'} {recipe_name} ({recipe['calories']} ккал)",
            callback_data=f"view_recipe:{recipe['id']}"
        )])

    # Добавляем кнопку возврата
    keyboard.append([types.InlineKeyboardButton(
        text="◀️ Назад к меню рецептов",
        callback_data="return_to_recipes"
    )])

    await callback_query.message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback_query.answer()


async def show_favorite_recipes(callback_query: CallbackQuery, state: FSMContext):
    """Показывает избранные рецепты пользователя."""
    user_id = callback_query.from_user.id
    recipes = get_saved_recipes(user_id, is_favorite=True)

    if not recipes:
        await callback_query.message.answer(
            "У вас пока нет избранных рецептов. Вы можете добавить рецепты в избранное.")
        await callback_query.answer()
        return

    text = "⭐️ <b>Ваши избранные рецепты:</b>\n\n"

    # Создаем клавиатуру с рецептами
    keyboard = []
    for recipe in recipes:
        recipe_name = recipe['name']
        if len(recipe_name) > 30:
            recipe_name = recipe_name[:27] + "..."

        keyboard.append([types.InlineKeyboardButton(
            text=f"★ {recipe_name} ({recipe['calories']} ккал)",
            callback_data=f"view_recipe:{recipe['id']}"
        )])

    # Добавляем кнопку возврата
    keyboard.append([types.InlineKeyboardButton(
        text="◀️ Назад к меню рецептов",
        callback_data="return_to_recipes"
    )])

    await callback_query.message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback_query.answer()


async def view_recipe_details(callback_query: CallbackQuery, state: FSMContext):
    """Показывает детальную информацию о рецепте."""
    recipe_id = int(callback_query.data.split(':')[1])
    recipe = get_recipe_details(recipe_id)

    if not recipe:
        await callback_query.message.answer("Рецепт не найден.")
        await callback_query.answer()
        return

    await state.update_data(current_recipe_id=recipe_id)

    # Формируем текст рецепта
    text = f"🍳 <b>{recipe['name']}</b>\n\n"
    text += "<b>Ингредиенты:</b>\n"
    text += f"{recipe['ingredients']}\n\n"
    text += "<b>Способ приготовления:</b>\n"
    text += f"{recipe['instructions']}\n\n"
    text += "<b>Пищевая ценность:</b>\n"
    text += f"• Калории: {recipe['calories']} ккал\n"
    text += f"• Белки: {recipe['protein']} г\n"
    text += f"• Жиры: {recipe['fat']} г\n"
    text += f"• Углеводы: {recipe['carbs']} г\n"

    # Создаем клавиатуру для действий с рецептом
    keyboard = create_recipe_confirmation_keyboard(recipe_id)

    await callback_query.message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback_query.answer()


async def toggle_recipe_favorite_status(callback_query: CallbackQuery, state: FSMContext):
    """Меняет статус избранного рецепта."""
    recipe_id = int(callback_query.data.split(':')[1])
    new_status = toggle_favorite_recipe(recipe_id)

    status_text = "добавлен в избранное" if new_status else "удален из избранного"
    await callback_query.message.answer(f"Рецепт {status_text}!")

    # Показываем обновленные детали рецепта
    await view_recipe_details(callback_query, state)
    await callback_query.answer()


async def delete_recipe_handler(callback_query: CallbackQuery, state: FSMContext):
    """Удаляет рецепт."""
    recipe_id = int(callback_query.data.split(':')[1])
    delete_recipe(recipe_id)

    await callback_query.message.answer("Рецепт успешно удален!")
    await show_saved_recipes(callback_query, state)
    await callback_query.answer()


async def return_to_recipes_menu(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает к меню рецептов."""
    await show_recipes_menu(callback_query.message, state)
    await callback_query.answer()


async def start_recipe_creation(callback_query: CallbackQuery, state: FSMContext):
    """Начинает процесс создания рецепта."""
    await state.clear()

    await callback_query.message.answer(
        "Давайте создадим новый рецепт! Введите название рецепта:"
    )

    await state.set_state(RecipeStates.entering_name)
    await callback_query.answer()


async def process_recipe_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия рецепта."""
    name = message.text.strip()

    if not name or len(name) > 100:
        await message.answer("Пожалуйста, введите корректное название (не более 100 символов).")
        return

    await state.update_data(name=name)

    await message.answer(
        "Отлично! Теперь введите список ингредиентов (каждый ингредиент с новой строки):"
    )

    await state.set_state(RecipeStates.entering_ingredients)


async def process_recipe_ingredients(message: types.Message, state: FSMContext):
    """Обрабатывает ввод ингредиентов рецепта."""
    ingredients = message.text.strip()

    if not ingredients:
        await message.answer("Пожалуйста, введите список ингредиентов.")
        return

    await state.update_data(ingredients=ingredients)

    await message.answer(
        "Хорошо! Теперь введите инструкции по приготовлению:"
    )

    await state.set_state(RecipeStates.entering_instructions)


async def process_recipe_instructions(message: types.Message, state: FSMContext):
    """Обрабатывает ввод инструкций рецепта."""
    instructions = message.text.strip()

    if not instructions:
        await message.answer("Пожалуйста, введите инструкции по приготовлению.")
        return

    await state.update_data(instructions=instructions)

    await message.answer(
        "Отлично! Теперь введите калорийность блюда (ккал):"
    )

    await state.set_state(RecipeStates.entering_calories)


async def process_recipe_calories(message: types.Message, state: FSMContext):
    """Обрабатывает ввод калорийности рецепта."""
    try:
        calories = float(message.text.strip().replace(',', '.'))
        if calories <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число для калорий.")
        return

    await state.update_data(calories=calories)

    await message.answer(
        "Теперь введите количество белков (г):"
    )

    await state.set_state(RecipeStates.entering_protein)


async def process_recipe_protein(message: types.Message, state: FSMContext):
    """Обрабатывает ввод количества белка."""
    try:
        protein = float(message.text.strip().replace(',', '.'))
        if protein < 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное неотрицательное число для белков.")
        return

    await state.update_data(protein=protein)

    await message.answer(
        "Теперь введите количество жиров (г):"
    )

    await state.set_state(RecipeStates.entering_fat)


async def process_recipe_fat(message: types.Message, state: FSMContext):
    """Обрабатывает ввод количества жиров."""
    try:
        fat = float(message.text.strip().replace(',', '.'))
        if fat < 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное неотрицательное число для жиров.")
        return

    await state.update_data(fat=fat)

    await message.answer(
        "И наконец, введите количество углеводов (г):"
    )

    await state.set_state(RecipeStates.entering_carbs)


async def process_recipe_carbs(message: types.Message, state: FSMContext):
    """Обрабатывает ввод количества углеводов."""
    try:
        carbs = float(message.text.strip().replace(',', '.'))
        if carbs < 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное неотрицательное число для углеводов.")
        return

    await state.update_data(carbs=carbs)

    # Получаем все данные рецепта
    recipe_data = await state.get_data()

    # Показываем итоговую информацию для подтверждения
    confirmation_text = (
        f"<b>Проверьте данные рецепта:</b>\n\n"
        f"<b>Название:</b> {recipe_data['name']}\n\n"
        f"<b>Ингредиенты:</b>\n{recipe_data['ingredients']}\n\n"
        f"<b>Способ приготовления:</b>\n{recipe_data['instructions']}\n\n"
        f"<b>Пищевая ценность:</b>\n"
        f"• Калории: {recipe_data['calories']} ккал\n"
        f"• Белки: {recipe_data['protein']} г\n"
        f"• Жиры: {recipe_data['fat']} г\n"
        f"• Углеводы: {recipe_data['carbs']} г\n\n"
        f"Всё правильно?"
    )

    # Создаем клавиатуру для подтверждения
    keyboard = create_recipe_confirmation_keyboard()

    await message.answer(
        confirmation_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await state.set_state(RecipeStates.confirming)


async def save_recipe_handler(callback_query: CallbackQuery, state: FSMContext):
    """Сохраняет созданный рецепт."""
    user_id = callback_query.from_user.id
    recipe_data = await state.get_data()

    # Сохраняем рецепт в базу данных
    recipe_id = save_recipe(
        user_id,
        recipe_data['name'],
        recipe_data['ingredients'],
        recipe_data['instructions'],
        recipe_data['calories'],
        recipe_data['protein'],
        recipe_data['fat'],
        recipe_data['carbs']
    )

    if recipe_id:
        await callback_query.message.answer(f"✅ Рецепт '{recipe_data['name']}' успешно сохранен!")

        # Возвращаемся к меню рецептов
        await show_recipes_menu(callback_query.message, state)
    else:
        await callback_query.message.answer("❌ Ошибка при сохранении рецепта. Пожалуйста, попробуйте еще раз.")

    await state.clear()
    await callback_query.answer()


async def cancel_recipe_creation(callback_query: CallbackQuery, state: FSMContext):
    """Отменяет создание рецепта."""
    await callback_query.message.answer("Создание рецепта отменено.")

    # Возвращаемся к меню рецептов
    await show_recipes_menu(callback_query.message, state)
    await state.clear()
    await callback_query.answer()


async def generate_recipe(callback_query: CallbackQuery, state: FSMContext):
    """Генерирует рецепт на основе цели пользователя."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user or not user.get('goal'):
        await callback_query.message.answer(
            "Сначала нужно завершить регистрацию и указать цель."
        )
        await callback_query.answer()
        return

    goal = user['goal']

    # Выбираем случайный рецепт из базовых шаблонов в соответствии с целью
    base_recipes = BASE_RECIPES.get(goal)

    if not base_recipes:
        # Если для цели нет специальных рецептов, берем из поддержания веса
        base_recipes = BASE_RECIPES["🔄 Поддержание текущего веса"]

    # Выбираем случайный рецепт
    recipe = random.choice(base_recipes)

    # Сохраняем данные в состояние
    await state.update_data(
        name=recipe['name'],
        ingredients=recipe['ingredients'],
        instructions=recipe['instructions'],
        calories=recipe['calories'],
        protein=recipe['protein'],
        fat=recipe['fat'],
        carbs=recipe['carbs']
    )

    # Показываем информацию о рецепте для подтверждения
    confirmation_text = (
        f"<b>Сгенерирован рецепт для {goal}:</b>\n\n"
        f"<b>Название:</b> {recipe['name']}\n\n"
        f"<b>Ингредиенты:</b>\n{recipe['ingredients']}\n\n"
        f"<b>Способ приготовления:</b>\n{recipe['instructions']}\n\n"
        f"<b>Пищевая ценность:</b>\n"
        f"• Калории: {recipe['calories']} ккал\n"
        f"• Белки: {recipe['protein']} г\n"
        f"• Жиры: {recipe['fat']} г\n"
        f"• Углеводы: {recipe['carbs']} г\n\n"
        f"Хотите сохранить этот рецепт?"
    )

    # Создаем клавиатуру для подтверждения
    keyboard = create_recipe_confirmation_keyboard()

    await callback_query.message.answer(
        confirmation_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await state.set_state(RecipeStates.confirming)
    await callback_query.answer()


async def recipe_to_diary(callback_query: CallbackQuery, state: FSMContext):
    """Добавляет рецепт в дневник питания."""
    recipe_id = int(callback_query.data.split(':')[1])
    recipe = get_recipe_details(recipe_id)

    if not recipe:
        await callback_query.message.answer("Рецепт не найден.")
        await callback_query.answer()
        return

    # Создаем клавиатуру для выбора приема пищи
    keyboard = []
    for meal_type in ["Завтрак", "Обед", "Ужин", "Перекус"]:
        keyboard.append([
            types.InlineKeyboardButton(
                text=meal_type,
                callback_data=f"add_recipe_to_meal:{recipe_id}:{meal_type}"
            )
        ])

    keyboard.append([
        types.InlineKeyboardButton(
            text="◀️ Отмена",
            callback_data=f"view_recipe:{recipe_id}"
        )
    ])

    await callback_query.message.answer(
        f"Выберите прием пищи для добавления рецепта '{recipe['name']}':",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await callback_query.answer()


async def add_recipe_to_meal(callback_query: CallbackQuery, state: FSMContext):
    """Добавляет рецепт в конкретный прием пищи в дневнике."""
    data = callback_query.data.split(':')
    recipe_id = int(data[1])
    meal_type = data[2]

    user_id = callback_query.from_user.id
    recipe = get_recipe_details(recipe_id)

    if not recipe:
        await callback_query.message.answer("Рецепт не найден.")
        await callback_query.answer()
        return

    # Текущая дата
    today = datetime.now().strftime("%Y-%m-%d")

    # Добавляем рецепт в дневник
    entry_id = add_food_entry(
        user_id,
        today,
        meal_type,
        recipe['name'],
        recipe['calories'],
        recipe['protein'],
        recipe['fat'],
        recipe['carbs']
    )

    if entry_id:
        await callback_query.message.answer(
            f"✅ Рецепт '{recipe['name']}' добавлен в {meal_type.lower()}!"
        )
    else:
        await callback_query.message.answer(
            "❌ Ошибка при добавлении рецепта в дневник. Пожалуйста, попробуйте еще раз."
        )

    # Возвращаемся к деталям рецепта
    await view_recipe_details(callback_query, state)
    await callback_query.answer()
