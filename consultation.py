"""
Модуль для работы с разделом "Консультация с диетологом".
Реализует просмотр карточек диетологов, навигацию между ними и возможность связи.
"""

import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user, get_nutritionists, get_nutritionist_by_id

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsultationStates(StatesGroup):
    viewing_nutritionists = State()
    viewing_nutritionist_card = State()
    contact_form = State()


async def show_consultation_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню консультации с диетологом."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user or not user.get('registration_complete'):
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Поехали!")
        return

    # Информационный текст о важности консультаций
    info_text = (
        "🩺 <b>Консультация с диетологом</b>\n\n"
        "💡 <b>Почему это важно?</b>\n"
        "• Персональный подход к вашему здоровью\n"
        "• Профессиональная оценка рациона питания\n"
        "• Коррекция питания с учетом ваших особенностей\n"
        "• Поддержка в достижении целей по весу\n"
        "• Рекомендации при наличии заболеваний\n\n"
        "👨‍⚕️ Наши специалисты имеют многолетний опыт работы и помогут вам "
        "составить оптимальный план питания для достижения ваших целей!\n\n"
        "Выберите диетолога для консультации:"
    )

    keyboard = [
        [InlineKeyboardButton(text="👨‍⚕️ Выбрать диетолога", callback_data="consultation:select_nutritionist")],
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="consultation:back_to_main")]
    ]

    await message.answer(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_nutritionists_list(callback_query: CallbackQuery, state: FSMContext):
    """Показывает список диетологов с возможностью навигации."""
    user_id = callback_query.from_user.id

    # Получаем список диетологов
    nutritionists = get_nutritionists()

    if not nutritionists:
        await callback_query.message.edit_text(
            "😔 К сожалению, в данный момент диетологи недоступны. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="consultation:back_to_main")]
            ])
        )
        return

    # Сохраняем данные в состояние
    await state.update_data(
        nutritionists=nutritionists,
        current_index=0
    )
    await state.set_state(ConsultationStates.viewing_nutritionists)

    # Показываем первого диетолога
    await show_nutritionist_card(callback_query, state, 0)


async def show_nutritionist_card(callback_query: CallbackQuery, state: FSMContext, index: int):
    """Показывает карточку конкретного диетолога."""
    data = await state.get_data()
    nutritionists = data.get('nutritionists', [])

    if not nutritionists or index < 0 or index >= len(nutritionists):
        await callback_query.answer("❌ Ошибка загрузки данных")
        return

    nutritionist = nutritionists[index]

    # Формируем текст карточки
    card_text = (
        f"👨‍⚕️ <b>{nutritionist['full_name']}</b>\n\n"
        f"🎓 <b>Образование:</b>\n{nutritionist['education']}\n\n"
        f"📊 <b>Стаж работы:</b> {nutritionist['experience']}\n\n"
        f"🔬 <b>Направление работы:</b>\n{nutritionist['specialization']}\n\n"
        f"💡 <b>Подход к питанию:</b>\n{nutritionist['approach']}\n\n"
        f"📋 Диетолог {index + 1} из {len(nutritionists)}"
    )

    # Создаем клавиатуру навигации
    keyboard = []

    # Кнопки навигации
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"consultation:prev:{index}"))
    if index < len(nutritionists) - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"consultation:next:{index}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка связи с диетологом
    keyboard.append([
        InlineKeyboardButton(
            text="💬 Связаться с диетологом",
            callback_data=f"consultation:contact:{nutritionist['id']}"
        )
    ])

    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="consultation:back_to_main")
    ])

    # Обновляем состояние
    await state.update_data(current_index=index)

    await callback_query.message.edit_text(
        card_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def handle_navigation(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает навигацию между карточками диетологов."""
    action = callback_query.data.split(':')[1]
    current_index = int(callback_query.data.split(':')[2])

    if action == "prev":
        new_index = current_index - 1
    elif action == "next":
        new_index = current_index + 1
    else:
        await callback_query.answer("❌ Неизвестная команда")
        return

    await show_nutritionist_card(callback_query, state, new_index)
    await callback_query.answer()


async def handle_contact_nutritionist(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает запрос на связь с диетологом."""
    nutritionist_id = int(callback_query.data.split(':')[2])

    # Получаем данные диетолога
    nutritionist = get_nutritionist_by_id(nutritionist_id)

    if not nutritionist:
        await callback_query.answer("❌ Диетолог не найден")
        return

    # Формируем сообщение с контактной информацией
    contact_text = (
        f"📞 <b>Связаться с {nutritionist['full_name']}</b>\n\n"
        f"Для записи на консультацию выберите удобный способ связи:\n\n"
        f"💬 <b>Telegram:</b> @{nutritionist.get('telegram_username', 'nutritionist_bot')}\n"
        f"📧 <b>Email:</b> {nutritionist.get('email', 'consultation@dietbot.ru')}\n"
        f"📱 <b>Телефон:</b> {nutritionist.get('phone', '+7 (xxx) xxx-xx-xx')}\n\n"
        f"⏰ <b>Время работы:</b> {nutritionist.get('work_hours', 'Пн-Пт 9:00-18:00')}\n\n"
        f"💰 <b>Стоимость консультации:</b> {nutritionist.get('price', 'По договоренности')}\n\n"
        f"📝 При обращении укажите, что вы пользователь Diet Planner Bot!"
    )

    keyboard = [
        [InlineKeyboardButton(
            text="💬 Написать в Telegram",
            url=f"https://t.me/{nutritionist.get('telegram_username', 'nutritionist_bot')}"
        )],
        [InlineKeyboardButton(text="◀️ Назад к карточке", callback_data="consultation:back_to_card")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="consultation:back_to_main")]
    ]

    await callback_query.message.edit_text(
        contact_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await callback_query.answer("💬 Контактная информация загружена!")


async def handle_consultation_callback(callback_query: CallbackQuery, state: FSMContext):
    """Основной обработчик callback-запросов для раздела консультации."""
    data = callback_query.data
    logger.info(f"Получен consultation callback: {data}")

    try:
        if data == "consultation:select_nutritionist":
            await show_nutritionists_list(callback_query, state)

        elif data.startswith("consultation:prev:") or data.startswith("consultation:next:"):
            await handle_navigation(callback_query, state)

        elif data.startswith("consultation:contact:"):
            await handle_contact_nutritionist(callback_query, state)

        elif data == "consultation:back_to_card":
            # Возврат к текущей карточке
            data = await state.get_data()
            current_index = data.get('current_index', 0)
            await show_nutritionist_card(callback_query, state, current_index)

        elif data == "consultation:back_to_main":
            await return_to_main_menu(callback_query, state)

        else:
            logger.warning(f"Неизвестная команда consultation: {data}")
            await callback_query.answer("❌ Неизвестная команда")

    except Exception as e:
        logger.error(f"Ошибка в handle_consultation_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка")

    await callback_query.answer()


async def return_to_main_menu(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в главное меню."""
    await state.clear()

    from keyboards import after_calories_keyboard

    await callback_query.message.answer(
        "🏠 Вы вернулись в главное меню.",
        reply_markup=after_calories_keyboard
    )