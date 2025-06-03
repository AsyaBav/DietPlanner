import asyncio
import logging
import random
from aiogram import types, F, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram import Router
from aiogram.types import Message
from typing import Union
from database import (
    save_recipe, get_saved_recipes, get_recipe_details, toggle_favorite_recipe,
    delete_recipe, add_food_entry, get_user, get_db_connection, search_recipes
)
from keyboards import create_recipes_keyboard, create_recipe_confirmation_keyboard
from food_api import search_food, get_food_nutrients, get_branded_food_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Состояния для создания и выбора рецептов
class RecipeStates(StatesGroup):
    selecting_type = State()
    entering_name = State()
    entering_ingredients = State()
    entering_instructions = State()
    entering_photo = State()
    entering_calories = State()
    entering_protein = State()
    entering_fat = State()
    entering_carbs = State()
    confirming = State()
    generating = State()
    searching = State()

    waiting_for_name = State()
    waiting_for_ingredients = State()
    waiting_for_instructions = State()


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
        await search_recipes(callback_query, state)
    elif action == "favorites":
        await show_favorites(callback_query, state)
    elif action == "create":
        await start_recipe_creation(callback_query, state)
    elif action == "generate":
        await generate_recipe(callback_query)
    elif action == "back":
        await return_to_main_menu(callback_query)
    await callback_query.answer()


'''async def search_recipes(callback_query: CallbackQuery, state: FSMContext):
    """Запрашиваем текст для поиска"""
    await callback_query.message.edit_text(
        "🔍 Введите название или ингредиенты для поиска:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="recipe:back")]
        ]))
    await state.set_state(RecipeStates.searching)
    await callback_query.answer()'''


async def search_recipes(callback_query: CallbackQuery, state: FSMContext):
    """Запрашиваем текст для поиска"""
    await callback_query.message.edit_text(
        "🔍 Введите название или ингредиенты для поиска:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="recipe:back")]
        ]))
    await state.set_state(RecipeStates.searching)
    await callback_query.answer()


# @router.message(RecipeStates.searching)
async def process_search_query(message: Message, state: FSMContext):
    """Обрабатываем поисковый запрос"""
    search_query = message.text.strip()
    if not search_query:
        await message.answer("Пожалуйста, введите поисковый запрос")
        return

    search_query = ' '.join(search_query.split())

    user_id = message.from_user.id
    from database import search_recipes
    recipes = search_recipes(user_id, search_query)

    if not recipes:
        await message.answer("😕 Ничего не найдено. Попробуйте другой запрос.")
        await state.clear()
        return

    # Сохраняем результаты поиска в состоянии
    await state.update_data(
        search_results=recipes,
        current_page=0,
        search_query=search_query
    )

    # Показываем первую страницу результатов
    await show_search_results(message, state)


async def show_search_results(message: Union[Message, CallbackQuery], state: FSMContext, page=0):
    """Показываем страницу с результатами поиска"""
    data = await state.get_data()
    recipes = data.get('search_results', [])
    search_query = data.get('search_query', '')

    # Пагинация - разбиваем на страницы по 5 рецептов
    page_size = 5
    total_pages = (len(recipes) // page_size + (1 if len(recipes) % page_size else 0))

    if page >= total_pages:
        page = total_pages - 1

    start_idx = page * page_size
    page_recipes = recipes[start_idx:start_idx + page_size]

    # Формируем текст сообщения
    text = f"🔍 Результаты поиска по запросу '{search_query}':\n\n"
    for i, recipe in enumerate(page_recipes, 1):
        text += f"{i}. {recipe['name']} ({recipe['calories']} ккал)\n"

    # Создаем клавиатуру
    keyboard = []

    # Кнопки для рецептов
    for recipe in page_recipes:
        keyboard.append([
            InlineKeyboardButton(
                text=recipe['name'],
                callback_data=f"view_recipe:{recipe['id']}"
            )
        ])

        # Кнопки пагинации
    pagination_row = []
    if total_pages > 1:
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"search_page:{page - 1}"
                )
            )

        pagination_row.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                callback_data="noop"
            )
        )

        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=f"search_page:{page + 1}"
                )
            )

        keyboard.append(pagination_row)

    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад к поиску",
            callback_data="recipe:search"
        )
    ])

    if isinstance(message, CallbackQuery):
        await message.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await message.answer()
    else:
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


# @router.callback_query(F.data.startswith("search_page:"))
async def handle_search_page(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатываем переключение страниц поиска"""
    page = int(callback_query.data.split(":")[1])
    await state.update_data(current_page=page)
    await show_search_results(callback_query, state, page)


async def view_recipe_card(callback_query: CallbackQuery, recipe_id: int):
    """Показываем карточку рецепта"""
    recipe = get_recipe_details(recipe_id)
    if not recipe:
        await callback_query.answer("Рецепт не найден")
        return

    # Формируем текст карточки
    text = f"🍳 <b>{recipe['name']}</b>\n\n"
    text += "<b>Ингредиенты:</b>\n"
    text += recipe['ingredients'].replace(",", "\n") + "\n\n"
    text += "<b>Способ приготовления:</b>\n"
    text += recipe['instructions'] + "\n\n"
    text += "<b>Пищевая ценность (на 100г):</b>\n"
    text += f"• Калории: {recipe['calories']} ккал\n"
    text += f"• Белки: {recipe['protein']} г\n"
    text += f"• Жиры: {recipe['fat']} г\n"
    text += f"• Углеводы: {recipe['carbs']} г"

    # Клавиатура карточки
    keyboard = [
        [
            InlineKeyboardButton(text="❤️ В избранное", callback_data=f"toggle_fav:{recipe_id}"),
            InlineKeyboardButton(text="➕ В меню", callback_data=f"add_to_menu:{recipe_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_search")]
    ]

    # Если есть фото (добавьте поле photo_path в таблицу recipes)
    if recipe.get('photo_path'):
        await callback_query.message.answer_photo(
            photo=recipe['photo_path'],
            caption=text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await callback_query.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback_query.answer()


async def show_favorites(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    from database import get_saved_recipes
    favorites = get_saved_recipes(user_id, is_favorite=True)  # Функция из database.py

    '''if not favorites:
        text = "У вас пока нет избранных рецептов."
    else:
        text = "⭐ Ваши избранные рецепты:\n\n"
        for recipe in favorites:
            text += f"- {recipe['name']} ({recipe['calories']} ккал)\n"'''

    if not favorites:
        await callback_query.message.edit_text(
            "У вас пока нет избранных рецептов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="recipe:back")]
            ]))
        await callback_query.answer()
        return

        # Сохраняем список избранного в состоянии
    await state.update_data(favorites_list=favorites, current_fav_page=0)

    # Формируем сообщение с пагинацией
    await show_favorites_page(callback_query, state)

    '''await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="recipes:back")]
        ])
    )'''


async def show_favorites_page(callback_query: CallbackQuery, state: FSMContext, page=0):
    """Показывает страницу с избранными рецептами"""
    data = await state.get_data()
    favorites = data.get('favorites_list', [])

    # Пагинация
    page_size = 5
    total_pages = (len(favorites) // page_size + (1 if len(favorites) % page_size else 0))
    page = min(page, total_pages - 1) if total_pages > 0 else 0
    start_idx = page * page_size
    page_favorites = favorites[start_idx:start_idx + page_size]

    text = "⭐ Ваши избранные рецепты:\n\n"
    for i, recipe in enumerate(page_favorites, start_idx + 1):
        text += f"{i}. {recipe['name']} ({recipe['calories']} ккал)\n"

    # Клавиатура с рецептами и пагинацией
    keyboard = []
    for recipe in page_favorites:
        keyboard.append([InlineKeyboardButton(
            text=recipe['name'],
            callback_data=f"view_fav_recipe:{recipe['id']}"
        )])

    # Пагинация
    pagination_row = []
    if total_pages > 1:
        if page > 0:
            pagination_row.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"fav_page:{page - 1}"
            ))

        # Добавляем номер страницы в любом случае
        pagination_row.append(InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data="noop"
        ))

        if page < total_pages - 1:
            pagination_row.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"fav_page:{page + 1}"
            ))
    if pagination_row:
        keyboard.append(pagination_row)

    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад в меню рецептов",
        callback_data="recipe:back"
    )])

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback_query.answer()


'''async def start_recipe_creation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "Введите название рецепта:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="recipes:back")]
        ])
    )
    await state.set_state(RecipeStates.waiting_for_name)'''

async def start_recipe_creation(callback_query: CallbackQuery, state: FSMContext):
    """Начинает процесс создания рецепта."""
    await state.clear()

    await callback_query.message.answer(
        "Давайте создадим новый рецепт! Введите название рецепта:"
    )
    await state.set_state(RecipeStates.entering_name)



async def view_favorite_recipe(callback_query: CallbackQuery, state: FSMContext):
    """Показывает карточку избранного рецепта"""
    recipe_id = int(callback_query.data.split(':')[1])
    recipe = get_recipe_details(recipe_id)

    if not recipe:
        await callback_query.answer("Рецепт не найден")
        return

    # Формируем текст карточки
    text = f"⭐️🍳 <b>{recipe['name']}</b>\n\n"
    text += "<b>Ингредиенты:</b>\n"
    text += recipe['ingredients'].replace(",", "\n") + "\n\n"
    text += "<b>Способ приготовления:</b>\n"
    text += recipe['instructions'] + "\n\n"
    text += "<b>Пищевая ценность:</b>\n"
    text += f"• Калории: {recipe['calories']} ккал\n"
    text += f"• Белки: {recipe['protein']} г\n"
    text += f"• Жиры: {recipe['fat']} г\n"
    text += f"• Углеводы: {recipe['carbs']} г"

    # Клавиатура карточки
    keyboard = [
        [
            InlineKeyboardButton(text="💔 Удалить из избранного", callback_data=f"toggle_fav:{recipe_id}"),
            InlineKeyboardButton(text="➕ В меню", callback_data=f"add_to_menu:{recipe_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад к избранному", callback_data="back_to_favorites")]
    ]

    await callback_query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback_query.answer()


async def generate_recipe(callback_query: types.CallbackQuery):
    # Здесь будет код генерации рецепта
    await callback_query.message.edit_text(
        "🎲 Генерация рецепта...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="recipes:back")]
        ])
    )


async def return_to_main_menu(callback_query: types.CallbackQuery):
    from handlers import after_calories_keyboard
    await callback_query.message.delete()
    await callback_query.message.answer(
        "Вы вернулись в главное меню",
        reply_markup=after_calories_keyboard
    )


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
    try:
        recipe_id = int(callback_query.data.split(':')[1])
        from database import get_recipe_details  # Добавляем импорт
        recipe = get_recipe_details(recipe_id)

        if not recipe:
            await callback_query.answer("Рецепт не найден")
            return

        # Формируем текст карточки
        text = f"🍳 <b>{recipe['name']}</b>\n\n"
        text += "<b>Ингредиенты:</b>\n"
        text += recipe['ingredients'].replace(",", "\n") + "\n\n"
        text += "<b>Способ приготовления:</b>\n"
        text += recipe['instructions'] + "\n\n"
        text += "<b>Пищевая ценность:</b>\n"
        text += f"• Калории: {recipe['calories']} ккал\n"
        text += f"• Белки: {recipe['protein']} г\n"
        text += f"• Жиры: {recipe['fat']} г\n"
        text += f"• Углеводы: {recipe['carbs']} г"

        # Клавиатура карточки
        keyboard = [
            [
                InlineKeyboardButton(text="❤️ В избранное", callback_data=f"toggle_fav:{recipe_id}"),
                InlineKeyboardButton(text="➕ В меню", callback_data=f"add_to_menu:{recipe_id}")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_search")]
        ]

        # Удаляем предыдущее сообщение с результатами поиска
        await callback_query.message.delete()

        # Отправляем новое сообщение с карточкой рецепта
        await callback_query.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка при отображении рецепта: {e}")
        await callback_query.answer("Произошла ошибка при загрузке рецепта")


async def toggle_favorite_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает добавление/удаление из избранного"""
    recipe_id = int(callback_query.data.split(':')[1])
    from database import toggle_favorite_recipe

    new_status = toggle_favorite_recipe(recipe_id)
    status_text = "добавлен в избранное" if new_status else "удален из избранного"

    await callback_query.answer(f"Рецепт {status_text}!")
    # Обновляем сообщение с рецептом
    await view_recipe_details(callback_query, callback_query.message.bot.current_state(callback_query.from_user.id))
    await view_recipe_details(callback_query, state)


async def add_to_menu_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает добавление рецепта в меню на сегодня"""
    recipe_id = int(callback_query.data.split(':')[1])
    from database import get_recipe_details, add_food_entry

    recipe = get_recipe_details(recipe_id)
    if not recipe:
        await callback_query.answer("Рецепт не найден")
        return

    # Добавляем в дневник как отдельный прием пищи "Рецепт"
    today = datetime.now().strftime("%Y-%m-%d")
    add_food_entry(
        user_id=callback_query.from_user.id,
        date=today,
        meal_type="Рецепт",
        food_name=recipe['name'],
        calories=recipe['calories'],
        protein=recipe['protein'],
        fat=recipe['fat'],
        carbs=recipe['carbs']
    )

    await callback_query.answer(f"Рецепт '{recipe['name']}' добавлен в сегодняшнее меню!")


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
        "Отлично! Теперь введите список ингредиентов с граммовками:"
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
    await state.update_data(instructions=message.text)
    data = await state.get_data()

    from database import save_recipe

    # Сохраняем рецепт в базу данных
    recipe_id = save_recipe(
        user_id=message.from_user.id,
        name=data['name'],
        ingredients=data['ingredients'],
        instructions=message.text,
        calories=0,  # Можно указать 0 или запросить у пользователя
        protein=0,
        fat=0,
        carbs=0
    )

    if recipe_id:
        await message.answer("✅ Рецепт успешно сохранен!")
    else:
        await message.answer("❌ Ошибка при сохранении рецепта")

    await state.clear()
    await show_recipes_menu(message)


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
    await callback_query.message.answer("🔧 Генерация рецепта в разработке!")
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
