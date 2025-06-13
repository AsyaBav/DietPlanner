"""
Модуль для работы с разделом "Статьи".
Реализует просмотр статей по темам, навигацию и образовательный контент.
"""

import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user, get_article_topics, get_articles_by_topic, get_article_by_id

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticlesStates(StatesGroup):
    viewing_topics = State()
    viewing_articles_list = State()
    reading_article = State()


async def show_articles_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню статей с темами."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user or not user.get('registration_complete'):
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Поехали!")
        return

    # Получаем список тем
    topics = get_article_topics()

    if not topics:
        await message.answer(
            "📚 <b>Образовательные статьи</b>\n\n"
            "К сожалению, статьи временно недоступны. Попробуйте позже.",
            parse_mode="HTML"
        )
        return

    # Информационный текст
    info_text = (
        "📚 <b>Образовательные статьи</b>\n\n"
        "💡 Здесь вы найдете полезную информацию о правильном питании, "
        "здоровом образе жизни и достижении ваших целей.\n\n"
        "📖 Выберите интересующую вас тему:"
    )

    # Создаем клавиатуру с темами
    keyboard = []
    for topic in topics:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{topic['emoji']} {topic['name']}",
                callback_data=f"articles:topic:{topic['id']}"
            )
        ])

    # Добавляем кнопку возврата
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="articles:back_to_main")
    ])

    await message.answer(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(ArticlesStates.viewing_topics)


async def show_articles_by_topic(callback_query: CallbackQuery, state: FSMContext):
    """Показывает список статей по выбранной теме."""
    topic_id = int(callback_query.data.split(':')[2])

    # Получаем статьи по теме
    articles = get_articles_by_topic(topic_id)
    topics = get_article_topics()

    # Находим название темы
    topic_name = "Неизвестная тема"
    topic_emoji = "📖"
    for topic in topics:
        if topic['id'] == topic_id:
            topic_name = topic['name']
            topic_emoji = topic['emoji']
            break

    if not articles:
        await callback_query.message.edit_text(
            f"{topic_emoji} <b>{topic_name}</b>\n\n"
            "📄 В этой теме пока нет статей.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к темам", callback_data="articles:back_to_topics")]
            ])
        )
        return

    # Формируем текст со списком статей
    articles_text = f"{topic_emoji} <b>{topic_name}</b>\n\n"
    articles_text += "📋 Доступные статьи:\n\n"

    # Создаем клавиатуру со статьями
    keyboard = []
    for i, article in enumerate(articles, 1):
        articles_text += f"{i}. {article['title']}\n"
        keyboard.append([
            InlineKeyboardButton(
                text=f"📖 {article['title']}",
                callback_data=f"articles:read:{article['id']}"
            )
        ])

    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад к темам", callback_data="articles:back_to_topics")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="articles:back_to_main")
    ])

    # Сохраняем данные в состояние
    await state.update_data(current_topic_id=topic_id, topic_name=topic_name, topic_emoji=topic_emoji)
    await state.set_state(ArticlesStates.viewing_articles_list)

    await callback_query.message.edit_text(
        articles_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_article(callback_query: CallbackQuery, state: FSMContext):
    """Показывает содержимое выбранной статьи."""
    article_id = int(callback_query.data.split(':')[2])

    # Получаем статью
    article = get_article_by_id(article_id)

    if not article:
        await callback_query.answer("❌ Статья не найдена")
        return

    # Формируем текст статьи
    article_text = f"📖 <b>{article['title']}</b>\n\n"
    article_text += f"{article['content']}\n\n"

    # Если есть источники
    if article.get('sources'):
        article_text += f"🔗 <b>Источники:</b>\n{article['sources']}\n\n"

    # Добавляем информацию об авторе и дате
    if article.get('author'):
        article_text += f"✍️ <b>Автор:</b> {article['author']}\n"

    if article.get('publication_date'):
        article_text += f"📅 <b>Дата публикации:</b> {article['publication_date']}"

    # Создаем клавиатуру навигации
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад к списку статей", callback_data="articles:back_to_list")],
        [InlineKeyboardButton(text="📚 К темам", callback_data="articles:back_to_topics")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="articles:back_to_main")]
    ]

    await state.set_state(ArticlesStates.reading_article)

    # Проверяем длину сообщения (лимит Telegram - 4096 символов)
    if len(article_text) > 4000:
        # Разбиваем длинную статью на части
        parts = []
        current_part = ""

        for paragraph in article_text.split('\n\n'):
            if len(current_part + paragraph + '\n\n') > 4000:
                if current_part:
                    parts.append(current_part.strip())
                current_part = paragraph + '\n\n'
            else:
                current_part += paragraph + '\n\n'

        if current_part:
            parts.append(current_part.strip())

        # Отправляем первую часть с измененным сообщением
        await callback_query.message.edit_text(
            parts[0],
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

        # Отправляем остальные части как новые сообщения
        for part in parts[1:]:
            await callback_query.message.answer(
                part,
                parse_mode="HTML"
            )
    else:
        await callback_query.message.edit_text(
            article_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


async def handle_articles_callback(callback_query: CallbackQuery, state: FSMContext):
    """Основной обработчик callback-запросов для раздела статей."""
    data = callback_query.data
    logger.info(f"Получен articles callback: {data}")

    try:
        if data.startswith("articles:topic:"):
            await show_articles_by_topic(callback_query, state)

        elif data.startswith("articles:read:"):
            await show_article(callback_query, state)

        elif data == "articles:back_to_topics":
            await show_topics_menu(callback_query, state)

        elif data == "articles:back_to_list":
            # Возврат к списку статей текущей темы
            data = await state.get_data()
            topic_id = data.get('current_topic_id')
            if topic_id:
                callback_query.data = f"articles:topic:{topic_id}"
                await show_articles_by_topic(callback_query, state)
            else:
                await show_topics_menu(callback_query, state)

        elif data == "articles:back_to_main":
            await return_to_main_menu(callback_query, state)

        else:
            logger.warning(f"Неизвестная команда articles: {data}")
            await callback_query.answer("❌ Неизвестная команда")

    except Exception as e:
        logger.error(f"Ошибка в handle_articles_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка")

    await callback_query.answer()


async def show_topics_menu(callback_query: CallbackQuery, state: FSMContext):
    """Показывает меню тем (используется для возврата)."""
    topics = get_article_topics()

    info_text = (
        "📚 <b>Образовательные статьи</b>\n\n"
        "💡 Здесь вы найдете полезную информацию о правильном питании, "
        "здоровом образе жизни и достижении ваших целей.\n\n"
        "📖 Выберите интересующую вас тему:"
    )

    # Создаем клавиатуру с темами
    keyboard = []
    for topic in topics:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{topic['emoji']} {topic['name']}",
                callback_data=f"articles:topic:{topic['id']}"
            )
        ])

    # Добавляем кнопку возврата
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="articles:back_to_main")
    ])

    await callback_query.message.edit_text(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(ArticlesStates.viewing_topics)


async def return_to_main_menu(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в главное меню."""
    await state.clear()

    from keyboards import after_calories_keyboard

    await callback_query.message.answer(
        "🏠 Вы вернулись в главное меню.",
        reply_markup=after_calories_keyboard
    )