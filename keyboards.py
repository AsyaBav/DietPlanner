from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from config import MEAL_TYPES, WATER_INCREMENTS

# Основная клавиатура при старте
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Погнали!")],
        [KeyboardButton(text="ℹ️ О боте")]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора пола
gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора уровня активности
activity_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Сидячий образ жизни")],
        [KeyboardButton(text="Легкая активность (1-2 тренировки в неделю)")],
        [KeyboardButton(text="Средняя активность (3-5 тренировок)")],
        [KeyboardButton(text="Высокая активность (6-7 тренировок)")],
        [KeyboardButton(text="Атлет (ежедневные интенсивные тренировки)")]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора цели
goal_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔻 Похудение")],
        [KeyboardButton(text="🔺 Набор веса")],
        [KeyboardButton(text="🔄 Поддержание текущего веса")]
    ],
    resize_keyboard=True
)

# Клавиатура основного меню
after_calories_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📖 Мой дневник")],
        [KeyboardButton(text="🍽 Рацион"), KeyboardButton(text="💧 Трекер воды")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🍳 Рецепты")],
        [KeyboardButton(text="🩺 Консультация с диетологом"), KeyboardButton(text="🛒 Продуктовая корзина")],
        [KeyboardButton(text="📚 Статьи"), KeyboardButton(text="📈 Отчет")]
    ],
    resize_keyboard=True
)


def create_date_selection_keyboard(current_date_str):
    """Создает клавиатуру для выбора даты для дневника."""
    # Парсим текущую дату
    current_date = datetime.strptime(current_date_str, "%Y-%m-%d")

    # Создаем кнопки для 3 предыдущих дней, текущего и 3 будущих
    date_buttons = []

    for i in range(-3, 4):
        date = current_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        display_str = date.strftime("%d.%m") + (" (сегодня)" if i == 0 else "")
        date_buttons.append(InlineKeyboardButton(text=display_str, callback_data=f"date:{date_str}"))

    # Компонуем кнопки по 1 в ряд
    keyboard = [[button] for button in date_buttons]

    # Добавляем кнопки действий
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_food"),
        InlineKeyboardButton(text="🗑 Очистить день", callback_data="clear_diary")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_meal_types_keyboard():
    """Создает клавиатуру для выбора типа приема пищи."""
    keyboard = []

    # Создаем по 2 кнопки в ряд
    for i in range(0, len(MEAL_TYPES), 2):
        row = []
        row.append(InlineKeyboardButton(text=MEAL_TYPES[i], callback_data=f"meal_type:{MEAL_TYPES[i]}"))

        if i + 1 < len(MEAL_TYPES):
            row.append(InlineKeyboardButton(text=MEAL_TYPES[i + 1], callback_data=f"meal_type:{MEAL_TYPES[i + 1]}"))

        keyboard.append(row)

    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton(text="◀️ Назад к дневнику", callback_data="return_to_diary")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_food_entry_keyboard():
    """Создает клавиатуру для ввода продукта."""
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад к выбору приема пищи", callback_data="return_to_diary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


'''def create_water_keyboard():
    """Создает клавиатуру для трекера воды."""
    keyboard = [
        [
            InlineKeyboardButton(text="+200 мл", callback_data="water_add:200"),
            InlineKeyboardButton(text="+300 мл", callback_data="water_add:300"),
            InlineKeyboardButton(text="+500 мл", callback_data="water_add:500")
        ],
        [
            InlineKeyboardButton(text="🔧 Свое количество", callback_data="water_custom"),
            InlineKeyboardButton(text="⚙️ Изменить цель", callback_data="water_goal")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="water_stats"),
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="water_back")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)'''




def create_diary_keyboard():
    """Создает клавиатуру для дневника питания."""
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Вчера", callback_data="date:prev"),
            InlineKeyboardButton(text="Сегодня", callback_data="date:today"),
            InlineKeyboardButton(text="Завтра ▶️", callback_data="date:next")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_food"),
            InlineKeyboardButton(text="🗑 Очистить день", callback_data="clear_diary")
        ],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="return_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_recipes_keyboard():
    """Создает клавиатуру для меню рецептов."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔍 Найти рецепт", callback_data="recipe:search"),
            InlineKeyboardButton(text="🌟 Избранные", callback_data="recipe:favorites")
        ],
        [
            InlineKeyboardButton(text="➕ Создать свой", callback_data="recipe:create"),
            InlineKeyboardButton(text="✨ Сгенерировать", callback_data="recipe:generate")
        ],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="recipe:back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_recipe_confirmation_keyboard(recipe_id=None):
    """Создает клавиатуру для подтверждения рецепта."""
    keyboard = []

    if recipe_id:
        # Если это существующий рецепт
        keyboard.append([
            InlineKeyboardButton(text="❤️ В избранное", callback_data=f"toggle_favorite:{recipe_id}"),
            InlineKeyboardButton(text="📝 В дневник", callback_data=f"recipe_to_diary:{recipe_id}")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_recipe:{recipe_id}"),
            InlineKeyboardButton(text="◀️ Назад", callback_data="return_to_recipes")
        ])
    else:
        # Если это новый рецепт
        keyboard.append([
            InlineKeyboardButton(text="✅ Сохранить", callback_data="recipe:save"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="recipe:cancel")
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_meal_plan_keyboard():
    """Создает клавиатуру для плана питания."""
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Вчера", callback_data="plan_date:prev"),
            InlineKeyboardButton(text="Сегодня", callback_data="plan_date:today"),
            InlineKeyboardButton(text="Завтра ▶️", callback_data="plan_date:next")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="plan:add"),
            InlineKeyboardButton(text="🔄 Сгенерировать", callback_data="plan:generate")
        ],
        [
            InlineKeyboardButton(text="📝 Добавить в дневник", callback_data="plan:to_diary"),
            InlineKeyboardButton(text="🗑 Очистить", callback_data="plan:clear")
        ],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="plan:back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_recent_foods_keyboard(recent_foods):
    """Создает клавиатуру для выбора недавно добавленных продуктов."""
    keyboard = []

    for food in recent_foods:
        food_name = food['food_name']
        if len(food_name) > 25:
            food_name = food_name[:22] + "..."

        keyboard.append([
            InlineKeyboardButton(
                text=f"{food_name} ({food['calories']} ккал)",
                callback_data=f"recent_food:{food['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="✏️ Ввести другой продукт",
            callback_data="add_food"
        ),
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="return_to_diary"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)