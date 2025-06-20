import logging
from datetime import datetime
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup

from config import ACTIVITY_LEVELS
from utils import calculate_bmi, get_bmi_category, calculate_tdee, get_goal_calories, calculate_macronutrients
from database import create_user, get_user, update_user

from keyboards import (
    start_keyboard, gender_keyboard, activity_keyboard,
    goal_keyboard, after_calories_keyboard, create_recipes_keyboard
)
from diary import (
    show_diary, handle_diary_callback, process_food_entry,
    handle_food_selection, process_food_amount, confirm_food_entry,
    cancel_food_entry, confirm_clear_diary, cancel_clear_diary,
    handle_recent_food_selection, return_to_meal_selection,
    DiaryStates, WaterStates
)
from water_tracker import (
    water_tracker, add_water_amount, custom_water_amount,
    process_water_amount, set_water_goal_handler,
    process_water_goal, show_water_statistics, return_to_main_menu
)
from meal_planner import (
    show_meal_planner, handle_plan_date_selection, start_add_to_plan,
    handle_meal_type_selection, handle_recipe_selection, view_meal_type_plan,
    delete_plan_entry, clear_plan, confirm_clear_plan, cancel_clear_plan,
    transfer_plan_to_diary, generate_meal_plan, return_to_plan_view,
    handle_meal_plan_menu, handle_replace_dish, confirm_replace_dish,
    generate_daily_meal_plan, generate_weekly_meal_plan
)
from recipe_generator import (
    show_recipes_menu, handle_recipes_callback, view_recipe_details,
    toggle_recipe_favorite_status, delete_recipe_handler,
    return_to_recipes_menu, start_recipe_creation, process_recipe_name,
    process_recipe_ingredients, process_recipe_instructions,
    process_recipe_calories, process_recipe_protein,
    process_recipe_fat, process_recipe_carbs, save_recipe_handler,
    cancel_recipe_creation, generate_recipe, recipe_to_diary, process_search_query, show_search_results,
    handle_search_page,
    toggle_favorite_handler, add_to_menu_handler, show_favorites,
    show_favorites_page,
    view_favorite_recipe, RecipeStates
)
from visualizer import (
    show_statistics, handle_statistics_callback,
    VisualizationStates
)

from consultation import (
    show_consultation_menu, handle_consultation_callback,
    ConsultationStates
)

from articles import (
    show_articles_menu, handle_articles_callback,
    ArticlesStates
)

from weight_reports import (
    show_weight_reports_menu, handle_weight_reports_callback,
    process_weight_input, WeightReportStates
)

from shopping_cart import (
    show_shopping_cart_menu, handle_shopping_cart_callback,
    process_manual_item, ShoppingCartStates
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProfileStates(StatesGroup):
    editing_weight = State()
    editing_goal = State()
    editing_activity = State()


# Состояния для регистрации пользователя
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_activity = State()
    waiting_for_goal = State()


def register_handlers(dp):
    """Регистрирует все обработчики."""
    router = Router()

    # обработчик для поиска и добавления блюд
    @router.callback_query(F.data == "back_to_favorites")
    async def back_to_favorites_handler(callback_query: CallbackQuery, state: FSMContext):
        """Возвращает к списку избранных рецептов."""
        await show_favorites_page(callback_query, state)

    router.callback_query.register(save_recipe_handler, F.data == "recipe:save")
    router.callback_query.register(cancel_recipe_creation, F.data == "recipe:cancel")

    router.callback_query.register(handle_recipes_callback, F.data.startswith("recipe:"))
    router.message.register(process_search_query, StateFilter(RecipeStates.searching))
    router.callback_query.register(handle_search_page, F.data.startswith("search_page:"))
    router.callback_query.register(view_recipe_details, F.data.startswith("view_recipe:"))
    router.callback_query.register(toggle_favorite_handler, F.data.startswith("toggle_fav:"))
    router.callback_query.register(add_to_menu_handler, F.data.startswith("add_to_menu:"))
    router.callback_query.register(show_favorites_page, F.data.startswith("fav_page:"))
    router.callback_query.register(view_favorite_recipe, F.data.startswith("view_fav_recipe:"))
    router.callback_query.register(back_to_favorites_handler, F.data == "back_to_favorites")
    router.message.register(process_recipe_name, StateFilter(RecipeStates.entering_name))
    router.message.register(process_recipe_ingredients, StateFilter(RecipeStates.entering_ingredients))
    router.message.register(process_recipe_instructions, StateFilter(RecipeStates.entering_instructions))
    router.message.register(process_recipe_calories, StateFilter(RecipeStates.entering_calories))
    router.message.register(process_recipe_protein, StateFilter(RecipeStates.entering_protein))
    router.message.register(process_recipe_fat, StateFilter(RecipeStates.entering_fat))
    router.message.register(process_recipe_carbs, StateFilter(RecipeStates.entering_carbs))
    # Обработчики состояний рецептов уже зарегистрированы ниже

    # Обработчики для консультации с диетологом
    router.message.register(
        show_consultation_menu,
        F.text == "🩺 Консультация с диетологом"
    )
    router.callback_query.register(
        handle_consultation_callback,
        F.data.startswith("consultation:")
    )
    # Обработчики для статей
    router.message.register(
        show_articles_menu,
        F.text == "📚 Статьи"
    )
    router.callback_query.register(
        handle_articles_callback,
        F.data.startswith("articles:")
    )

    # Обработчики для отчетов веса
    router.message.register(
        show_weight_reports_menu,
        F.text == "📈 Отчет"
    )
    router.callback_query.register(
        handle_weight_reports_callback,
        F.data.startswith("weight:")
    )
    router.message.register(
        process_weight_input,
        StateFilter(WeightReportStates.entering_weight)
    )

    # Обработчики для продуктовой корзины
    router.message.register(
        show_shopping_cart_menu,
        F.text == "🛒 Продуктовая корзина"
    )
    router.callback_query.register(
        handle_shopping_cart_callback,
        F.data.startswith("cart:")
    )
    router.message.register(
        process_manual_item,
        StateFilter(ShoppingCartStates.adding_manual_item)
    )

    @router.callback_query(F.data == "back_to_search")
    async def back_to_search_handler(callback_query: CallbackQuery, state: FSMContext):
        """Возвращает к результатам поиска"""
        try:
            data = await state.get_data()
            if 'search_results' in data:
                from recipe_generator import show_search_results  # Добавляем импорт
                await show_search_results(callback_query, state, data.get('current_page', 0))
            else:
                from recipe_generator import show_recipes_menu  # Добавляем импорт
                await show_recipes_menu(callback_query.message, state)
            await callback_query.answer()
        except Exception as e:
            logger.error(f"Ошибка в back_to_search_handler: {e}")
            await callback_query.answer("❌ Ошибка возврата к поиску")

    # Обработчики профиля
    router.callback_query.register(edit_weight_handler, F.data == "edit_weight")
    router.callback_query.register(edit_goal_handler, F.data == "edit_goal")
    router.callback_query.register(edit_activity_handler, F.data == "edit_activity")
    router.callback_query.register(recalculate_handler, F.data == "recalculate")
    router.callback_query.register(profile_back_handler, F.data == "profile_back")

    # Обработчики состояний профиля определены отдельно ниже

    # Обработчик для трекера воды
    router.callback_query.register(add_water_amount, F.data.startswith("water_add:"))
    router.callback_query.register(custom_water_amount, F.data == "water_custom")
    router.callback_query.register(set_water_goal_handler, F.data == "water_goal")
    router.callback_query.register(show_water_statistics, F.data == "water_stats")
    router.callback_query.register(return_to_main_menu, F.data == "main_menu")
    router.callback_query.register(set_water_goal, F.data.startswith("water_goal_set:"))
    router.callback_query.register(water_tracker, F.data == "water_tracker")  # Для кнопки "Назад"
    router.message.register(process_water_amount, StateFilter(WaterStates.entering_amount))
    router.message.register(process_water_goal, StateFilter(WaterStates.setting_goal))

    # Команды
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_help, Command("help"))
    router.message.register(cmd_about, Command("about"))

    # Обработчики inline-кнопок стартового меню
    router.callback_query.register(about_bot_callback, F.data == "about_bot")
    #router.callback_query.register(start_registration_callback, F.data == "register")
    router.callback_query.register(back_to_start, F.data == "back_to_start")

    # Обработчик кнопки "О боте" (оставляем для совместимости)
    router.message.register(about_bot, F.text == "ℹ️ О боте")

    # Обработчик кнопки "🚀 Зарегистрироваться" (оставляем для совместимости)
    router.message.register(start_registration, F.text == "🚀 Зарегистрироваться")

    # Обработка стартовых действий
    router.message.register(show_about, F.text == "ℹ️ О боте")

    # Регистрация пользователя
    router.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
    router.message.register(process_gender, StateFilter(RegistrationStates.waiting_for_gender))
    router.message.register(process_age, StateFilter(RegistrationStates.waiting_for_age))
    router.message.register(process_height, StateFilter(RegistrationStates.waiting_for_height))
    router.message.register(process_weight, StateFilter(RegistrationStates.waiting_for_weight))
    router.message.register(process_activity, StateFilter(RegistrationStates.waiting_for_activity))
    router.message.register(process_goal, StateFilter(RegistrationStates.waiting_for_goal))

    # Обработчики основного меню
    router.message.register(show_profile, F.text == "👤 Профиль")
    router.message.register(show_diary, F.text == "📖 Мой дневник")
    router.message.register(show_meal_planner, F.text == "🍽 Рацион")
    router.message.register(show_recipes_menu, F.text == "🍳 Рецепты")
    router.message.register(water_tracker, F.text == "💧 Трекер воды")
    router.message.register(show_statistics, F.text == "📊 Статистика")
    router.message.register(show_consultation, F.text == "🩺 Консультация с диетологом")
    router.message.register(show_shopping_cart, F.text == "🛒 Продуктовая корзина")
    router.message.register(show_articles, F.text == "📚 Статьи")
    router.message.register(show_reports, F.text == "📈 Отчет")

    # Обработчики callback для рациона - ВАЖНО: должны быть ПЕРЕД другими обработчиками
    router.callback_query.register(handle_meal_plan_menu, F.data.startswith("meal_plan:"))

    # Колбэки
    router.callback_query.register(handle_diary_callback)
    router.callback_query.register(handle_food_selection, F.data.startswith("select_food:"))
    # router.callback_query.register(handle_food_selection, F.data.startswith("food:"))  # если используешь где-то ещё
    router.callback_query.register(confirm_food_entry, F.data == "confirm_food")
    router.callback_query.register(cancel_food_entry, F.data == "cancel_food")
    router.callback_query.register(confirm_clear_diary, F.data == "confirm_clear")
    router.callback_query.register(cancel_clear_diary, F.data == "cancel_clear")
    router.callback_query.register(handle_recent_food_selection, F.data.startswith("recent_food:"))
    router.callback_query.register(return_to_meal_selection, F.data == "return_to_meal_selection")

    # Обработчик возврата к дневнику из meal_planner
    @router.callback_query(F.data == "return_to_diary")
    async def return_to_diary_handler(callback_query: CallbackQuery, state: FSMContext):
        """Возвращает к дневнику из рациона."""
        try:
            await callback_query.message.delete()
        except:
            pass
        await show_diary(callback_query.message, state)
        await callback_query.answer()

    router.callback_query.register(handle_plan_date_selection, F.data.startswith("plan_date:"))
    router.callback_query.register(start_add_to_plan, F.data == "plan:add")
    router.callback_query.register(handle_meal_type_selection,
                                   F.data.startswith("meal_type:") & ~StateFilter(DiaryStates))
    router.callback_query.register(handle_recipe_selection, F.data.startswith("plan_recipe:"))
    router.callback_query.register(view_meal_type_plan, F.data.startswith("plan:") & F.data.contains(":") & ~F.data.in_(
        ["plan:add", "plan:generate", "plan:to_diary", "plan:clear", "plan:back"]))
    router.callback_query.register(delete_plan_entry, F.data.startswith("delete_plan_entry:"))
    router.callback_query.register(clear_plan, F.data == "plan:clear")
    router.callback_query.register(confirm_clear_plan, F.data.startswith("confirm_clear_plan:"))
    router.callback_query.register(cancel_clear_plan, F.data == "cancel_clear_plan")
    router.callback_query.register(transfer_plan_to_diary, F.data == "plan:to_diary")
    router.callback_query.register(generate_meal_plan, F.data == "plan:generate")
    router.callback_query.register(return_to_plan_view, F.data == "return_to_plan_view")

    # Обработчики для рациона - дополнительные
    router.callback_query.register(handle_replace_dish, F.data.startswith("replace_dish:"))
    router.callback_query.register(confirm_replace_dish, F.data.startswith("confirm_replace:"))

    # Импортируем новые функции
    from meal_planner import save_whole_plan_to_diary, show_plan_for_date, handle_save_plan_to_diary
    router.callback_query.register(save_whole_plan_to_diary, F.data.startswith("save_plan_to_diary:"))
    router.callback_query.register(handle_save_plan_to_diary, F.data.startswith("save_plan_to_diary:"))
    router.callback_query.register(show_plan_for_date, F.data.startswith("show_plan:"))
    router.callback_query.register(transfer_plan_to_diary, F.data == "plan:to_diary")

    router.callback_query.register(toggle_recipe_favorite_status, F.data.startswith("toggle_favorite:"))
    router.callback_query.register(delete_recipe_handler, F.data.startswith("delete_recipe:"))
    router.callback_query.register(return_to_recipes_menu, F.data == "return_to_recipes")
    router.callback_query.register(recipe_to_diary, F.data.startswith("recipe_to_diary:"))

    router.callback_query.register(handle_statistics_callback, F.data.startswith("stats:"))

    from diary import (
        add_product_handler,
        enter_weight_handler,
        back_to_list_handler
    )

    router.callback_query.register(add_product_handler, F.data.startswith("add_product:"))
    router.callback_query.register(enter_weight_handler, F.data.startswith("enter_weight:"))
    router.callback_query.register(back_to_list_handler, F.data == "back_to_list")

    # Обработка состояний
    router.message.register(process_food_entry, StateFilter(DiaryStates.entering_food))
    router.message.register(process_food_amount, StateFilter(DiaryStates.entering_amount))

    router.message.register(process_water_amount, StateFilter(WaterStates.entering_amount))
    router.message.register(process_water_goal, StateFilter(WaterStates.setting_goal))



    # Обработчики состояний профиля
    router.message.register(process_new_weight, StateFilter(ProfileStates.editing_weight))
    router.message.register(process_new_goal, StateFilter(ProfileStates.editing_goal))
    router.message.register(process_new_activity, StateFilter(ProfileStates.editing_activity))

    # Добавляем роутер в диспетчер
    dp.include_router(router)


async def cmd_start(message: Message, state: FSMContext):
    """Обрабатывает команду /start."""
    # Очищаем текущее состояние
    await state.clear()

    # Получаем пользователя из БД
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        # Создаем базовую запись для пользователя
        create_user(user_id, message.from_user.first_name)

        # Отправляем приветственное сообщение
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n\n"
            "🍏 Я твой персональный помощник по диетологии и правильному питанию.\n\n"
            "Я помогу тебе:\n"
            "✅ Рассчитать идеальную норму калорий для твоей цели\n"
            "✅ Составить вкусный и сбалансированный рацион\n"
            "✅ Вести дневник питания\n"
            "✅ Следить за водным балансом\n"
            "✅ Дать рекомендации по питанию, учитывая твой образ жизни и активность 🚴‍♂️🏋️\n"
            "✅ Поддерживать мотивацию на пути к лучшей версии себя! 🔥\n\n"
            "Готов начать? Тогда жми на кнопки ниже и поехали! 🚀",
            reply_markup=start_keyboard
        )
    else:
        # Проверяем, завершил ли пользователь регистрацию (указал ли цель по калориям)
        if not user.get('goal_calories'):
            await message.answer(
                f"👋 С возвращением, {message.from_user.first_name}!\n\n"
                "Похоже, ты не завершил регистрацию. Давай продолжим?",
                reply_markup=start_keyboard
            )
        else:
            # Показываем основное меню
            await message.answer(
                f"👋 С возвращением, {message.from_user.first_name}!\n\n"
                "Выбери, что ты хочешь сделать:",
                reply_markup=after_calories_keyboard
            )


async def cmd_help(message: Message):
    """Обрабатывает команду /help."""
    help_text = (
        "🔍 <b>Справка по боту</b>\n\n"

        "<b>Основные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "/about - О боте\n\n"

        "<b>Основные функции:</b>\n"
        "• <b>Мой дневник</b> - ведение записей о питании\n"
        "• <b>Водный баланс</b> - отслеживание потребления воды\n"
        "• <b>Рацион на день</b> - составление плана питания\n"
        "• <b>Рецепты</b> - поиск и создание рецептов\n"
        "• <b>Профиль</b> - просмотр и редактирование ваших данных\n"
        "• <b>Моя статистика</b> - графики и анализ ваших показателей\n\n"

        "<b>Как пользоваться дневником:</b>\n"
        "1. Выберите прием пищи\n"
        "2. Введите название продукта\n"
        "3. Выберите продукт из списка\n"
        "4. Укажите количество в граммах\n"
        "5. Подтвердите добавление\n\n"

        "Если у вас возникли вопросы или проблемы - напишите разработчику."
    )

    await message.answer(help_text, parse_mode="HTML")


async def cmd_about(message: Message):
    """Обрабатывает команду /about."""
    await show_about(message)


async def show_about(message: Message):
    """Показывает информацию о боте."""
    about_text = (
        "ℹ️ <b>О боте</b>\n\n"

        "Этот бот создан для помощи в ведении здорового образа жизни и правильного питания.\n\n"

        "<b>Возможности:</b>\n"
        "• Расчет индекса массы тела (ИМТ)\n"
        "• Определение дневной нормы калорий\n"
        "• Ведение дневника питания\n"
        "• Отслеживание водного баланса\n"
        "• Составление плана питания\n"
        "• Поиск и сохранение рецептов\n"
        "• Анализ и визуализация прогресса\n\n"

        "<b>Технические детали:</b>\n"
        "• Бот использует API Nutritionix для данных о продуктах\n"
        "• Все данные пользователей хранятся локально и защищены\n"
        "• Рассчеты производятся по формуле Миффлина-Сан Жеора\n\n"

        "Версия: 1.0.0\n"
        "Разработчик: Diet Planner Team"
    )

    await message.answer(about_text, parse_mode="HTML")


async def start_registration(message: Message, state: FSMContext):
    """Начинает процесс регистрации пользователя."""
    # Очищаем текущее состояние
    await state.clear()

    await message.answer(
        "👶 <b>Начинаем регистрацию</b>\n\n"
        "Для составления персонального плана питания мне нужно собрать немного информации о тебе.\n\n"
        "Как я могу к тебе обращаться?",
        parse_mode="HTML"
    )

    # Устанавливаем состояние ожидания имени
    await state.set_state(RegistrationStates.waiting_for_name)


async def process_name(message: Message, state: FSMContext):
    """Обрабатывает ввод имени."""
    name = message.text.strip()

    if not name or len(name) > 50:
        await message.answer("Пожалуйста, введите корректное имя (не более 50 символов).")
        return

    # Сохраняем имя
    await state.update_data(name=name)

    # Обновляем имя в БД
    user_id = message.from_user.id
    update_user(user_id, name=name)

    # Запрашиваем пол
    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "Укажите свой пол:",
        reply_markup=gender_keyboard
    )

    # Устанавливаем состояние ожидания пола
    await state.set_state(RegistrationStates.waiting_for_gender)


async def process_gender(message: Message, state: FSMContext):
    """Обрабатывает выбор пола."""
    gender = message.text.strip()

    if gender not in ["Мужчина", "Женщина"]:
        await message.answer("Пожалуйста, выберите пол, используя кнопки.")
        return

    # Сохраняем пол
    await state.update_data(gender=gender)

    # Обновляем пол в БД
    user_id = message.from_user.id
    update_user(user_id, gender=gender)

    # Запрашиваем возраст
    await message.answer(
        "Укажите свой возраст (полных лет):"
    )

    # Устанавливаем состояние ожидания возраста
    await state.set_state(RegistrationStates.waiting_for_age)


async def process_age(message: Message, state: FSMContext):
    """Обрабатывает ввод возраста."""
    try:
        age = int(message.text.strip())

        if age < 12 or age > 120:
            raise ValueError("Возраст должен быть от 12 до 120 лет")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный возраст (целое число от 12 до 120).")
        return

    # Сохраняем возраст
    await state.update_data(age=age)

    # Обновляем возраст в БД
    user_id = message.from_user.id
    update_user(user_id, age=age)

    # Запрашиваем рост
    await message.answer(
        "Укажите свой рост в сантиметрах (например, 175):"
    )

    # Устанавливаем состояние ожидания роста
    await state.set_state(RegistrationStates.waiting_for_height)


async def process_height(message: Message, state: FSMContext):
    """Обрабатывает ввод роста."""
    try:
        height = float(message.text.strip().replace(',', '.'))

        if height < 100 or height > 250:
            raise ValueError("Рост должен быть от 100 до 250 см")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный рост (от 100 до 250 см).")
        return

    # Сохраняем рост
    await state.update_data(height=height)

    # Обновляем рост в БД
    user_id = message.from_user.id
    update_user(user_id, height=height)

    # Запрашиваем вес
    await message.answer(
        "Укажите свой текущий вес в килограммах (например, 70.5):"
    )

    # Устанавливаем состояние ожидания веса
    await state.set_state(RegistrationStates.waiting_for_weight)


async def process_weight(message: Message, state: FSMContext):
    """Обрабатывает ввод веса."""
    try:
        weight = float(message.text.strip().replace(',', '.'))

        if weight < 30 or weight > 300:
            raise ValueError("Вес должен быть от 30 до 300 кг")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный вес (от 30 до 300 кг).")
        return

    await state.update_data(weight=weight) # Сохраняем вес

    # Обновляем вес в БД
    user_id = message.from_user.id
    update_user(user_id, weight=weight)

    # Получаем данные для расчета ИМТ
    user_data = await state.get_data()
    height = user_data.get('height')

    # Рассчитываем ИМТ
    bmi = calculate_bmi(weight, height)
    bmi_category = get_bmi_category(bmi)

    # Выводим информацию об ИМТ
    await message.answer(
        f"📊 <b>Ваш индекс массы тела (ИМТ): {bmi:.1f}</b>\n\n"
        f"Категория: {bmi_category}\n\n"
        f"Теперь укажите уровень вашей физической активности:",
        parse_mode="HTML",
        reply_markup=activity_keyboard
    )

    # Устанавливаем состояние ожидания уровня активности
    await state.set_state(RegistrationStates.waiting_for_activity)


async def process_activity(message: Message, state: FSMContext):
    """Обрабатывает выбор уровня активности."""
    activity_level = message.text.strip()

    if activity_level not in ACTIVITY_LEVELS:
        await message.answer("Пожалуйста, выберите уровень активности, используя кнопки.")
        return

    # Сохраняем уровень активности
    await state.update_data(activity_level=activity_level)

    # Обновляем уровень активности в БД
    user_id = message.from_user.id
    update_user(user_id, activity_level=activity_level)

    # Запрашиваем цель
    await message.answer(
        "Выберите вашу основную цель:",
        reply_markup=goal_keyboard
    )

    # Устанавливаем состояние ожидания цели
    await state.set_state(RegistrationStates.waiting_for_goal)


async def process_goal(message: Message, state: FSMContext):
    """Обрабатывает выбор цели."""
    goal = message.text.strip()

    valid_goals = ["🔻 Похудение", "🔺 Набор веса", "🔄 Поддержание текущего веса"]
    if goal not in valid_goals:
        await message.answer("Пожалуйста, выберите цель, используя кнопки.")
        return

    # Сохраняем цель
    await state.update_data(goal=goal)

    # Обновляем цель в БД
    user_id = message.from_user.id
    update_user(user_id, goal=goal)

    # Получаем данные для расчета калорий
    user_data = await state.get_data()
    weight = user_data.get('weight')
    height = user_data.get('height')
    age = user_data.get('age')
    activity_level = user_data.get('activity_level')
    gender = user_data.get('gender')

    # Рассчитываем TDEE (общий расход энергии)
    tdee = calculate_tdee(weight, height, age, activity_level, gender)

    # Рассчитываем целевое количество калорий
    goal_calories = get_goal_calories(tdee, goal)

    # Рассчитываем распределение макронутриентов
    macros = calculate_macronutrients(goal_calories, weight, goal)

    # Обновляем цели в БД
    update_user(
        user_id,
        goal_calories=goal_calories,
        protein=macros['protein'],
        fat=macros['fat'],
        carbs=macros['carbs'],
        registration_complete=True
    )

    # Формируем сообщение с результатами
    message_text = (
        "✅ <b>Регистрация завершена!</b>\n\n"

        f"<b>Ваша дневная норма калорий: {goal_calories:.0f} ккал</b>\n\n"

        "Распределение макронутриентов:\n"
        f"• Белки: {macros['protein']} г ({macros['protein_cal']:.0f} ккал)\n"
        f"• Жиры: {macros['fat']} г ({macros['fat_cal']:.0f} ккал)\n"
        f"• Углеводы: {macros['carbs']} г ({macros['carbs_cal']:.0f} ккал)\n\n"

        "Теперь вы можете начать вести дневник питания, отслеживать водный баланс и использовать другие функции бота!\n\n"

        "Выберите, что вы хотите сделать:"
    )

    # Отправляем сообщение с клавиатурой основного меню
    await message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=after_calories_keyboard
    )

    success = update_user(
        user_id,
        goal=goal,
        goal_calories=goal_calories,
        protein=macros['protein'],
        fat=macros['fat'],
        carbs=macros['carbs'],
        registration_complete=True  # Явный флаг завершения регистрации
    )

    if not success:
        await message.answer("❌ Ошибка сохранения данных. Попробуйте ещё раз.")
        return

    # Очищаем состояние только после успешного сохранения
    await state.clear()


async def show_profile(message: Message):
    """Показывает профиль пользователя."""
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Зарегистрироваться!")
        return

    # Рассчитываем ИМТ
    bmi = calculate_bmi(user['weight'], user['height'])
    bmi_category = get_bmi_category(bmi)

    # Формируем сообщение с профилем
    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"

        f"<b>Личные данные:</b>\n"
        f"• Имя: {user['name']}\n"
        f"• Пол: {user['gender']}\n"
        f"• Возраст: {user['age']} лет\n"
        f"• Рост: {user['height']} см\n"
        f"• Вес: {user['weight']} кг\n"
        f"• ИМТ: {bmi:.1f} ({bmi_category})\n"
        f"• Уровень активности: {user['activity_level']}\n"
        f"• Цель: {user['goal']}\n\n"

        f"<b>Суточная норма:</b>\n"
        f"• Калории: {user['goal_calories']:.0f} ккал\n"
        f"• Белки: {user['protein']} г\n"
        f"• Жиры: {user['fat']} г\n"
        f"• Углеводы: {user['carbs']} г\n"
        f"• Вода: {user['water_goal']} мл\n\n"

        f"• Дата регистрации: {user['registration_date'][:10]}"
    )

    # Создаем клавиатуру для редактирования профиля
    keyboard = [
        [
            types.InlineKeyboardButton(text="✏️ Изменить вес", callback_data="edit_weight"),
            types.InlineKeyboardButton(text="🔄 Изменить цель", callback_data="edit_goal")
        ],
        [
            types.InlineKeyboardButton(text="📝 Изменить активность", callback_data="edit_activity"),
            types.InlineKeyboardButton(text="🔍 Пересчитать калории", callback_data="recalculate")
        ],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="profile_back")]
    ]

    await message.answer(
        profile_text,
        parse_mode="HTML",

        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def about_bot(message: Message):
    """Информация о боте."""
    help_text = (
        "🤖 <b>О боте Diet Planner</b>\n\n"
        "Я помогаю составлять персональный план питания на основе ваших целей.\n\n"
        "<b>Мои возможности:</b>\n"
        "• Расчет ИМТ и дневной нормы калорий\n"
        "• Ведение дневника питания\n"
        "• Трекер потребления воды\n"
        "• Планирование рациона\n"
        "• База рецептов\n"
        "• Статистика и прогресс\n\n"
        "Для начала работы нажмите 🚀 Погнали!"
    )

    await message.answer(help_text, parse_mode="HTML", reply_markup=start_keyboard)


async def about_bot_callback(callback_query: CallbackQuery):
    """Обработчик inline-кнопки 'О боте'."""
    text = (
        "Я — Fit&Food, твой персональный помощник по питанию и здоровому образу жизни! 🍏💪\n\n"
        "Я помогу тебе:\n"
        "✅ Рассчитать *идеальную норму калорий* для твоей цели.\n"
        "✅ Составить вкусный и сбалансированный рацион. 🍽\n"
        "✅ Дать рекомендации по питанию, учитывая твой образ жизни и активность. 🚴‍♂️🏋️\n"
        "✅ Поддерживать мотивацию на пути к лучшей версии себя! 🔥\n\n"
        "Моя миссия — сделать твое питание простым, понятным и эффективным. 💯"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
            [InlineKeyboardButton(text="Помощь", callback_data="help")]
        ]
    )

    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def start_registration_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик inline-кнопки 'Зарегистрироваться'."""
    await callback_query.message.edit_text(
        "👶 Начинаем регистрацию\n\n"
        "Для составления персонального плана питания мне нужно собрать немного информации о тебе."
    )

    await callback_query.message.answer("Для начала напишите свой возраст.")
    await state.set_state(RegistrationStates.age)


async def back_to_start(callback_query: CallbackQuery):
    """Возврат к стартовому сообщению."""
    text = (
        f"Привет, {callback_query.from_user.first_name}!\n\n"
        "🍏 Я твой персональный помощник по диетологии и правильному питанию.\n\n"
        "Я помогу тебе:\n"
        "✅ Рассчитать идеальную норму калорий для твоей цели\n"
        "✅ Составить вкусный и сбалансированный рацион\n"
        "✅ Вести дневник питания\n"
        "✅ Следить за водным балансом\n"
        "✅ Дать рекомендации по питанию, учитывая твой образ жизни и активность 🚴‍♂️🏋️\n"
        "✅ Поддерживать мотивацию на пути к лучшей версии себя! 🔥\n\n"
        "Готов начать? Тогда жми на кнопки ниже и поехали! 🚀"
    )

    await callback_query.message.edit_text(text, reply_markup=start_keyboard)


# Добавьте эти функции в handlers.py
async def edit_weight_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Введите новый вес (кг):")
    await state.set_state(ProfileStates.editing_weight)
    await callback_query.answer()


async def edit_goal_handler(callback_query: CallbackQuery, state: FSMContext):
    from keyboards import goal_keyboard
    await callback_query.message.answer("Выберите новую цель:", reply_markup=goal_keyboard)
    await state.set_state(ProfileStates.editing_goal)
    await callback_query.answer()


async def edit_activity_handler(callback_query: CallbackQuery, state: FSMContext):
    from keyboards import activity_keyboard
    await callback_query.message.answer("Выберите уровень активности:", reply_markup=activity_keyboard)
    await state.set_state(ProfileStates.editing_activity)
    await callback_query.answer()


async def recalculate_handler(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user:
        await callback_query.answer("❌ Пользователь не найден")
        return

    try:
        # Исправленный вызов функции
        macros = calculate_macronutrients(
            calories=user['goal_calories'],
            weight=user['weight'],
            goal=user['goal']
        )

        update_user(
            user_id,
            protein=macros['protein'],
            fat=macros['fat'],
            carbs=macros['carbs']
        )

        await callback_query.answer("✔️ Данные пересчитаны!")
        await show_profile(callback_query.message)
    except Exception as e:
        logger.error(f"Ошибка пересчета: {e}")
        await callback_query.answer("❌ Ошибка пересчета")


async def profile_back_handler(callback_query: CallbackQuery):
    """Обработчик кнопки 'Назад' в профиле"""
    try:
        from keyboards import after_calories_keyboard
        await callback_query.message.delete()

        await callback_query.message.answer(
            "Вы вернулись в главное меню",
            reply_markup=after_calories_keyboard
        )
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка в profile_back_handler: {e}")
        await callback_query.answer("❌ Ошибка возврата в меню", show_alert=True)


# Обработчики состояний профиля
async def process_new_weight(message: Message, state: FSMContext):
    try:
        new_weight = float(message.text)
        if new_weight < 30 or new_weight > 300:
            raise ValueError
        user_id = message.from_user.id

        user = get_user(user_id)
        tdee = calculate_tdee(
            weight=new_weight,
            height=user['height'],
            age=user['age'],
            activity_level=user['activity_level'],
            sex=user['gender']
        )
        new_calories = get_goal_calories(tdee, user['goal'])
        macros = calculate_macronutrients(new_calories, new_weight, user['goal'])

        update_user(
            user_id,
            weight=new_weight,
            goal_calories=new_calories,
            protein=macros['protein'],
            fat=macros['fat'],
            carbs=macros['carbs']
        )
        await message.answer("✔️ Вес успешно обновлен!")
        await show_profile(message)
    except ValueError:
        await message.answer("❌ Введите корректный вес (30-300 кг)")

    await state.clear()


async def process_new_goal(message: Message, state: FSMContext):
    valid_goals = ["🔻 Похудение", "🔺 Набор веса", "🔄 Поддержание текущего веса"]
    if message.text not in valid_goals:
        await message.answer("❌ Выберите цель из предложенных вариантов")
        return

    user_id = message.from_user.id
    user = get_user(user_id)

    # Пересчет калорий
    tdee = calculate_tdee(
        weight=user['weight'],
        height=user['height'],
        age=user['age'],
        activity_level=user['activity_level'],
        sex=user['gender']
    )
    new_calories = get_goal_calories(tdee, message.text)
    macros = calculate_macronutrients(new_calories, user['weight'], message.text)

    update_user(
        user_id,
        goal=message.text,
        goal_calories=new_calories,
        protein=macros['protein'],
        fat=macros['fat'],
        carbs=macros['carbs']
    )

    await message.answer("✔️ Цель успешно обновлена!")
    await show_profile(message)
    await state.clear()


async def process_new_activity(message: Message, state: FSMContext):
    valid_activities = list(ACTIVITY_LEVELS.keys())
    if message.text not in valid_activities:
        await message.answer("❌ Выберите уровень активности из предложенных")
        return

    user_id = message.from_user.id
    user = get_user(user_id)

    # Пересчет калорий с новой активностью
    tdee = calculate_tdee(
        weight=user['weight'],
        height=user['height'],
        age=user['age'],
        activity_level=message.text,
        sex=user['gender']
    )
    new_calories = get_goal_calories(tdee, user['goal'])
    macros = calculate_macronutrients(new_calories, user['weight'], user['goal'])

    update_user(
        user_id,
        activity_level=message.text,
        goal_calories=new_calories,
        protein=macros['protein'],
        fat=macros['fat'],
        carbs=macros['carbs']
    )

    await message.answer("✔️ Уровень активности обновлен!")
    await show_profile(message)
    await state.clear()


async def set_water_goal(callback_query: CallbackQuery, state: FSMContext):
    """Устанавливает новую цель по воде из готовых вариантов."""
    goal = int(callback_query.data.split(':')[1])
    user_id = callback_query.from_user.id

    # Обновляем цель по воде в БД
    from database import set_water_goal
    set_water_goal(user_id, goal)

    await callback_query.message.answer(f"✅ Новая цель по потреблению воды установлена: {goal} мл!")

    # Возвращаемся к трекеру воды
    await water_tracker(callback_query.message, state)
    await callback_query.answer()


async def show_recipes_menu(message: Message):
    await message.answer(
        "🍴 Меню рецептов\n\nЗдесь ты можешь найти, сохранить или создать новые рецепты.",
        reply_markup=create_recipes_keyboard()
    )


async def show_consultation(message: Message):
    """Показывает раздел консультации с диетологом."""
    text = (
        "🩺 <b>Консультация с диетологом</b>\n\n"
        "Персональные рекомендации от квалифицированных специалистов помогут вам "
        "достичь ваших целей в питании более эффективно и безопасно.\n\n"
        "💡 <b>Почему это важно:</b>\n"
        "• Индивидуальный подход к вашему здоровью\n"
        "• Учет особенностей организма и заболеваний\n"
        "• Профессиональная корректировка рациона\n"
        "• Поддержка на пути к цели\n\n"
        "🔧 <i>Раздел в разработке</i>"
    )
    await message.answer(text, parse_mode="HTML")


async def show_shopping_cart(message: Message):
    """Показывает продуктовую корзину."""
    text = (
        "🛒 <b>Продуктовая корзина</b>\n\n"
        "Автоматически формируйте список покупок на основе вашего рациона!\n\n"
        "📋 <b>Возможности:</b>\n"
        "• Автоматическое составление списка из рациона\n"
        "• Группировка продуктов по категориям\n"
        "• Отметка купленных товаров\n"
        "• Расчет количества на несколько дней\n\n"
        "🔧 <i>Раздел в разработке</i>"
    )
    await message.answer(text, parse_mode="HTML")


async def show_articles(message: Message):
    """Показывает раздел статей."""
    text = (
        "📚 <b>Образовательные статьи</b>\n\n"
        "Расширьте свои знания о правильном питании!\n\n"
        "📖 <b>Темы статей:</b>\n"
        "• Основы здорового питания\n"
        "• Витамины и микроэлементы\n"
        "• Психология пищевого поведения\n"
        "• Интервальное голодание\n"
        "• Спортивное питание\n"
        "• Питание при различных заболеваниях\n\n"
        "🔧 <i>Раздел в разработке</i>"
    )
    await message.answer(text, parse_mode="HTML")


async def show_reports(message: Message):
    """Показывает раздел отчетов."""
    text = (
        "📈 <b>Отчеты и прогресс</b>\n\n"
        "Отслеживайте свой прогресс в достижении целей!\n\n"
        "📊 <b>Доступные отчеты:</b>\n"
        "• Динамика веса\n"
        "• Соблюдение калорийности\n"
        "• Баланс БЖУ\n"
        "• Потребление воды\n"
        "• Ежедневные записи\n\n"
        "💡 <i>Регулярно вводите свой вес для точной статистики</i>\n\n"
        "🔧 <i>Раздел в разработке</i>"
    )
    await message.answer(text, parse_mode="HTML")