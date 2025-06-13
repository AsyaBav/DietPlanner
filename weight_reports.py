"""
weight_reports.py

Модуль для работы с разделом "Отчет".
Реализует ввод веса, отслеживание прогресса и построение графиков.
"""

import logging
import io
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import matplotlib

matplotlib.use('Agg')  # Использование Agg бэкенда (не требует GUI)

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from database import (
    get_user, add_weight_record, get_weight_history,
    get_latest_weight_record, update_user_weight
)
from utils import format_date

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeightReportStates(StatesGroup):
    entering_weight = State()
    viewing_reports = State()


async def show_weight_reports_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню отчетов веса."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user or not user.get('registration_complete'):
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Поехали!")
        return

    # Получаем последнюю запись веса
    latest_record = get_latest_weight_record(user_id)
    current_weight = user.get('weight', 0)

    # Формируем информационный текст
    info_text = (
        "📈 <b>Отчет по весу</b>\n\n"
        "📊 Отслеживайте свой прогресс, регулярно вводя данные о весе. "
        "Это поможет вам видеть динамику изменений и корректировать план питания.\n\n"
    )

    if latest_record:
        days_since = (datetime.now() - datetime.strptime(latest_record['date'], '%Y-%m-%d')).days
        info_text += f"⚖️ <b>Текущий вес:</b> {current_weight} кг\n"
        info_text += f"📅 <b>Последний ввод:</b> {format_date(latest_record['date'])}"
        if days_since > 0:
            info_text += f" ({days_since} дн. назад)"
        info_text += f"\n📊 <b>Записано измерений:</b> {len(get_weight_history(user_id, 365))}\n\n"

        if days_since >= 1:
            info_text += "💡 <b>Рекомендация:</b> Для точного отслеживания взвешивайтесь каждый день в одно и то же время."
    else:
        info_text += f"⚖️ <b>Начальный вес:</b> {current_weight} кг\n"
        info_text += "📝 <b>Записей веса:</b> пока нет\n\n"
        info_text += "💡 <b>Совет:</b> Начните вести дневник веса уже сегодня!"

    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton(text="⚖️ Ввести вес", callback_data="weight:enter")],
        [InlineKeyboardButton(text="📊 Посмотреть график", callback_data="weight:show_chart")],
        [InlineKeyboardButton(text="📋 История измерений", callback_data="weight:show_history")],
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="weight:back_to_main")]
    ]

    await message.answer(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def request_weight_input(callback_query: CallbackQuery, state: FSMContext):
    """Запрашивает ввод веса от пользователя."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    # Получаем последнюю запись
    latest_record = get_latest_weight_record(user_id)

    input_text = (
        "⚖️ <b>Ввод веса</b>\n\n"
        "📝 Введите ваш текущий вес в килограммах.\n"
        "Например: <code>70.5</code> или <code>68</code>\n\n"
    )

    if latest_record:
        input_text += f"📊 <b>Предыдущий вес:</b> {latest_record['weight']} кг "
        input_text += f"({format_date(latest_record['date'])})\n\n"

    input_text += "💡 <b>Совет:</b> Взвешивайтесь утром натощак для более точных результатов."

    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="weight:cancel")]
    ]

    await callback_query.message.edit_text(
        input_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(WeightReportStates.entering_weight)


async def process_weight_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод веса пользователем."""
    user_id = message.from_user.id

    try:
        # Парсим вес
        weight_text = message.text.replace(',', '.')
        weight = float(weight_text)

        # Валидация
        if weight < 20 or weight > 300:
            await message.answer(
                "❌ <b>Некорректный вес</b>\n\n"
                "Пожалуйста, введите вес от 20 до 300 кг.",
                parse_mode="HTML"
            )
            return

        # Проверяем, есть ли уже запись на сегодня
        today = datetime.now().strftime("%Y-%m-%d")
        existing_records = get_weight_history(user_id, days=1)

        if existing_records and existing_records[0]['date'] == today:
            # Обновляем существующую запись
            update_weight_record(user_id, today, weight)
            action_text = "обновлен"
        else:
            # Добавляем новую запись
            add_weight_record(user_id, weight)
            action_text = "записан"

        # Обновляем вес в профиле пользователя
        update_user_weight(user_id, weight)

        # Получаем предыдущую запись для сравнения
        previous_records = get_weight_history(user_id, days=7)
        change_text = ""

        if len(previous_records) > 1:
            previous_weight = previous_records[1]['weight']
            change = weight - previous_weight

            if abs(change) > 0.1:  # Показываем изменение если больше 100г
                change_sign = "+" if change > 0 else ""
                change_text = f"\n📈 <b>Изменение:</b> {change_sign}{change:.1f} кг с предыдущего измерения"

        success_text = (
            f"✅ <b>Вес успешно {action_text}!</b>\n\n"
            f"⚖️ <b>Ваш вес:</b> {weight} кг\n"
            f"📅 <b>Дата:</b> {format_date(today)}"
            f"{change_text}\n\n"
            "💡 Продолжайте отслеживать свой прогресс!"
        )

        keyboard = [
            [InlineKeyboardButton(text="📊 Посмотреть график", callback_data="weight:show_chart")],
            [InlineKeyboardButton(text="📋 История", callback_data="weight:show_history")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="weight:back_to_main")]
        ]

        await message.answer(
            success_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

        await state.clear()

    except ValueError:
        await message.answer(
            "❌ <b>Некорректный формат</b>\n\n"
            "Пожалуйста, введите число. Например: <code>70.5</code> или <code>68</code>",
            parse_mode="HTML"
        )


async def show_weight_chart(callback_query: CallbackQuery, state: FSMContext):
    """Показывает график изменения веса."""
    user_id = callback_query.from_user.id

    # Получаем историю веса за последние 90 дней
    weight_history = get_weight_history(user_id, days=90)

    if len(weight_history) < 2:
        await callback_query.message.edit_text(
            "📊 <b>График веса</b>\n\n"
            "❌ Недостаточно данных для построения графика.\n"
            "Для создания графика нужно минимум 2 измерения.\n\n"
            "💡 Продолжайте вводить вес ежедневно!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚖️ Ввести вес", callback_data="weight:enter")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="weight:back_to_menu")]
            ])
        )
        return

    await callback_query.message.edit_text(
        "📊 Построение графика... Пожалуйста, подождите.",
        reply_markup=None
    )

    try:
        # Создаем график
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 8))

        # Подготавливаем данные
        dates = [datetime.strptime(record['date'], '%Y-%m-%d') for record in weight_history]
        weights = [record['weight'] for record in weight_history]

        # Строим график
        ax.plot(dates, weights, marker='o', linewidth=2, markersize=6, color='#2E86AB')
        ax.fill_between(dates, weights, alpha=0.3, color='#2E86AB')

        # Настройка осей
        ax.set_xlabel('Дата', fontsize=12)
        ax.set_ylabel('Вес (кг)', fontsize=12)
        ax.set_title('📊 График изменения веса', fontsize=16, fontweight='bold', pad=20)

        # Форматирование дат на оси X
        if len(dates) > 30:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            ax.xaxis.set_major_formatter(DateFormatter('%d.%m'))
        else:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            ax.xaxis.set_major_formatter(DateFormatter('%d.%m'))

        plt.xticks(rotation=45)

        # Добавляем сетку
        ax.grid(True, alpha=0.3)

        # Добавляем аннотации для первой и последней точки
        if len(weights) > 1:
            ax.annotate(f'{weights[0]:.1f} кг',
                        (dates[0], weights[0]),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

            ax.annotate(f'{weights[-1]:.1f} кг',
                        (dates[-1], weights[-1]),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7))

        # Подгоняем макет
        plt.tight_layout()

        # Сохраняем график в буфер
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        # Отправляем график
        photo = BufferedInputFile(buffer.read(), filename="weight_chart.png")

        # Подготавливаем статистику
        total_change = weights[-1] - weights[0]
        total_days = (dates[-1] - dates[0]).days
        avg_change_per_week = (total_change / max(total_days, 1)) * 7 if total_days > 0 else 0

        change_sign = "+" if total_change > 0 else ""
        trend_emoji = "📈" if total_change > 0 else "📉" if total_change < 0 else "➡️"

        stats_text = (
            f"📊 <b>Статистика за {total_days} дней:</b>\n\n"
            f"🎯 <b>Начальный вес:</b> {weights[0]:.1f} кг\n"
            f"⚖️ <b>Текущий вес:</b> {weights[-1]:.1f} кг\n"
            f"{trend_emoji} <b>Общее изменение:</b> {change_sign}{total_change:.1f} кг\n"
            f"📈 <b>Средний темп:</b> {change_sign}{avg_change_per_week:.1f} кг/неделю\n"
            f"📋 <b>Количество измерений:</b> {len(weights)}"
        )

        keyboard = [
            [InlineKeyboardButton(text="📋 История измерений", callback_data="weight:show_history")],
            [InlineKeyboardButton(text="⚖️ Ввести вес", callback_data="weight:enter")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="weight:back_to_menu")]
        ]

        await callback_query.message.answer_photo(
            photo=photo,
            caption=stats_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    except Exception as e:
        logger.error(f"Ошибка при создании графика: {e}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при создании графика. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="weight:back_to_menu")]
            ])
        )


async def show_weight_history(callback_query: CallbackQuery, state: FSMContext):
    """Показывает историю измерений веса."""
    user_id = callback_query.from_user.id

    # Получаем историю за последние 30 дней
    weight_history = get_weight_history(user_id, days=30)

    if not weight_history:
        await callback_query.message.edit_text(
            "📋 <b>История измерений</b>\n\n"
            "❌ У вас пока нет записей о весе.\n\n"
            "💡 Начните вести дневник веса уже сегодня!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚖️ Ввести вес", callback_data="weight:enter")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="weight:back_to_menu")]
            ])
        )
        return

    # Формируем текст истории
    history_text = "📋 <b>История измерений</b>\n\n"

    for i, record in enumerate(weight_history[:15]):  # Показываем последние 15 записей
        date_formatted = format_date(record['date'])
        weight = record['weight']

        # Добавляем изменение по сравнению с предыдущим днем
        change_text = ""
        if i < len(weight_history) - 1:
            prev_weight = weight_history[i + 1]['weight']
            change = weight - prev_weight
            if abs(change) > 0.1:
                change_sign = "+" if change > 0 else ""
                change_emoji = "📈" if change > 0 else "📉"
                change_text = f" ({change_sign}{change:.1f} кг {change_emoji})"

        history_text += f"📅 {date_formatted}: <b>{weight} кг</b>{change_text}\n"

    if len(weight_history) > 15:
        history_text += f"\n... и еще {len(weight_history) - 15} записей"

    # Добавляем краткую статистику
    if len(weight_history) > 1:
        total_change = weight_history[0]['weight'] - weight_history[-1]['weight']
        change_sign = "+" if total_change > 0 else ""
        trend_emoji = "📈" if total_change > 0 else "📉" if total_change < 0 else "➡️"

        history_text += f"\n\n{trend_emoji} <b>За период:</b> {change_sign}{total_change:.1f} кг"

    keyboard = [
        [InlineKeyboardButton(text="📊 Посмотреть график", callback_data="weight:show_chart")],
        [InlineKeyboardButton(text="⚖️ Ввести вес", callback_data="weight:enter")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="weight:back_to_menu")]
    ]

    await callback_query.message.edit_text(
        history_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def handle_weight_reports_callback(callback_query: CallbackQuery, state: FSMContext):
    """Основной обработчик callback-запросов для раздела отчетов веса."""
    data = callback_query.data
    logger.info(f"Получен weight callback: {data}")

    try:
        if data == "weight:enter":
            await request_weight_input(callback_query, state)

        elif data == "weight:show_chart":
            await show_weight_chart(callback_query, state)

        elif data == "weight:show_history":
            await show_weight_history(callback_query, state)

        elif data == "weight:back_to_menu":
            await show_weight_menu_callback(callback_query, state)

        elif data == "weight:back_to_main":
            await return_to_main_menu(callback_query, state)

        elif data == "weight:cancel":
            await state.clear()
            await show_weight_menu_callback(callback_query, state)

        else:
            logger.warning(f"Неизвестная команда weight: {data}")
            await callback_query.answer("❌ Неизвестная команда")

    except Exception as e:
        logger.error(f"Ошибка в handle_weight_reports_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка")

    await callback_query.answer()


async def show_weight_menu_callback(callback_query: CallbackQuery, state: FSMContext):
    """Показывает меню отчетов через callback (для возврата)."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    # Получаем последнюю запись веса
    latest_record = get_latest_weight_record(user_id)
    current_weight = user.get('weight', 0)

    # Формируем информационный текст
    info_text = (
        "📈 <b>Отчет по весу</b>\n\n"
        "📊 Отслеживайте свой прогресс, регулярно вводя данные о весе. "
        "Это поможет вам видеть динамику изменений и корректировать план питания.\n\n"
    )

    if latest_record:
        days_since = (datetime.now() - datetime.strptime(latest_record['date'], '%Y-%m-%d')).days
        info_text += f"⚖️ <b>Текущий вес:</b> {current_weight} кг\n"
        info_text += f"📅 <b>Последний ввод:</b> {format_date(latest_record['date'])}"
        if days_since > 0:
            info_text += f" ({days_since} дн. назад)"
        info_text += f"\n📊 <b>Записано измерений:</b> {len(get_weight_history(user_id, 365))}\n\n"

        if days_since >= 1:
            info_text += "💡 <b>Рекомендация:</b> Для точного отслеживания взвешивайтесь каждый день в одно и то же время."
    else:
        info_text += f"⚖️ <b>Начальный вес:</b> {current_weight} кг\n"
        info_text += "📝 <b>Записей веса:</b> пока нет\n\n"
        info_text += "💡 <b>Совет:</b> Начните вести дневник веса уже сегодня!"

    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton(text="⚖️ Ввести вес", callback_data="weight:enter")],
        [InlineKeyboardButton(text="📊 Посмотреть график", callback_data="weight:show_chart")],
        [InlineKeyboardButton(text="📋 История измерений", callback_data="weight:show_history")],
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="weight:back_to_main")]
    ]

    await callback_query.message.edit_text(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def return_to_main_menu(callback_query: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в главное меню."""
    await state.clear()

    from keyboards import after_calories_keyboard

    await callback_query.message.answer(
        "🏠 Вы вернулись в главное меню.",
        reply_markup=after_calories_keyboard
    )