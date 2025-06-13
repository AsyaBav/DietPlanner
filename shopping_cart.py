"""
shopping_cart.py

Модуль для работы с разделом "Продуктовая корзина".
Автоматически формирует список продуктов из рациона и рецептов.
"""

import logging
import re
from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    get_user, get_shopping_cart_items, add_shopping_cart_item,
    remove_shopping_cart_item, update_shopping_cart_item,
    clear_shopping_cart, toggle_item_purchased,
    get_daily_meal_plan, get_recipe_details,
    get_daily_entries
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShoppingCartStates(StatesGroup):
    selecting_period = State()
    adding_manual_item = State()
    viewing_cart = State()


async def show_shopping_cart_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню продуктовой корзины."""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user or not user.get('registration_complete'):
        await message.answer("Сначала нужно зарегистрироваться. Нажмите 🚀 Поехали!")
        return

    # Получаем текущую корзину
    cart_items = get_shopping_cart_items(user_id)

    # Формируем основной текст
    info_text = (
        "🛒 <b>Продуктовая корзина</b>\n\n"
        "📋 Автоматически формируется список продуктов на основе:\n"
        "• 📆 Вашего рациона питания\n"
        "• 🍳 Выбранных рецептов\n"
        "• 📘 Продуктов из дневника\n\n"
    )

    if cart_items:
        purchased_count = len([item for item in cart_items if item.get('is_purchased')])
        total_count = len(cart_items)

        info_text += f"📊 <b>В корзине:</b> {total_count} позиций\n"
        if purchased_count > 0:
            info_text += f"✅ <b>Куплено:</b> {purchased_count} из {total_count}\n"

        info_text += f"📅 <b>Период:</b> {cart_items[0].get('period', 'не указан')}\n\n"

        # Показываем первые несколько продуктов
        info_text += "🛍️ <b>Основные продукты:</b>\n"
        for item in cart_items[:5]:
            status = "✅" if item.get('is_purchased') else "🔘"
            name = item['product_name']
            quantity = item['quantity']
            unit = item.get('unit', 'г')
            info_text += f"{status} {name} — {quantity} {unit}\n"

        if len(cart_items) > 5:
            info_text += f"... и еще {len(cart_items) - 5} продуктов\n"
    else:
        info_text += "📝 <b>Корзина пуста</b>\n"
        info_text += "💡 Сформируйте рацион или выберите рецепты для автоматического создания списка покупок!"

    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton(text="🛒 Просмотреть корзину", callback_data="cart:view")],
        [
            InlineKeyboardButton(text="📝 Сформировать корзину", callback_data="cart:generate"),
            InlineKeyboardButton(text="🔄 Обновить корзину", callback_data="cart:refresh")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить продукт", callback_data="cart:add_manual"),
            InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart:clear")
        ],
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="cart:back_to_main")]
    ]

    await message.answer(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_cart_items(callback_query: CallbackQuery, state: FSMContext):
    """Показывает детальный список продуктов в корзине."""
    user_id = callback_query.from_user.id
    cart_items = get_shopping_cart_items(user_id)

    if not cart_items:
        await callback_query.message.edit_text(
            "🛒 <b>Продуктовая корзина</b>\n\n"
            "📝 Корзина пуста.\n\n"
            "💡 Сформируйте рацион или добавьте продукты вручную!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Сформировать корзину", callback_data="cart:generate")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="cart:back_to_menu")]
            ])
        )
        return

    # Разделяем на купленные и не купленные
    not_purchased = [item for item in cart_items if not item.get('is_purchased')]
    purchased = [item for item in cart_items if item.get('is_purchased')]

    cart_text = "🛒 <b>Ваша корзина продуктов</b>\n\n"

    if cart_items:
        period = cart_items[0].get('period', 'не указан')
        cart_text += f"📅 <b>Период:</b> {period}\n"
        cart_text += f"📊 <b>Всего позиций:</b> {len(cart_items)}\n\n"

    # Показываем не купленные продукты
    if not_purchased:
        cart_text += "🔘 <b>К покупке:</b>\n"
        for item in not_purchased:
            name = item['product_name']
            quantity = item['quantity']
            unit = item.get('unit', 'г')
            cart_text += f"• {name} — {quantity} {unit}\n"
        cart_text += "\n"

    # Показываем купленные продукты
    if purchased:
        cart_text += "✅ <b>Куплено:</b>\n"
        for item in purchased:
            name = item['product_name']
            quantity = item['quantity']
            unit = item.get('unit', 'г')
            cart_text += f"• <s>{name} — {quantity} {unit}</s>\n"

    if len(cart_text) > 4000:  # Ограничение Telegram
        cart_text = cart_text[:3900] + "...\n\n📝 Список слишком длинный, показана часть."

    # Создаем клавиатуру действий
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Отметить купленное", callback_data="cart:mark_purchased"),
            InlineKeyboardButton(text="🗑 Удалить продукт", callback_data="cart:remove_item")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить продукт", callback_data="cart:add_manual"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="cart:refresh")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cart:back_to_menu")]
    ]

    await callback_query.message.edit_text(
        cart_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def request_generation_period(callback_query: CallbackQuery, state: FSMContext):
    """Запрашивает период для формирования корзины."""
    period_text = (
        "📅 <b>Сформировать корзину</b>\n\n"
        "За какой период сформировать список продуктов?\n\n"
        "💡 Корзина будет создана на основе:\n"
        "• Вашего плана питания\n"
        "• Записей в дневнике\n"
        "• Сохраненных рецептов"
    )

    keyboard = [
        [
            InlineKeyboardButton(text="📅 На сегодня", callback_data="cart:generate:1"),
            InlineKeyboardButton(text="🗓 На 3 дня", callback_data="cart:generate:3")
        ],
        [
            InlineKeyboardButton(text="📊 На неделю", callback_data="cart:generate:7")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cart:back_to_menu")]
    ]

    await callback_query.message.edit_text(
        period_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(ShoppingCartStates.selecting_period)


async def generate_shopping_cart(callback_query: CallbackQuery, state: FSMContext, days: int):
    """Генерирует корзину продуктов на указанный период."""
    user_id = callback_query.from_user.id

    await callback_query.message.edit_text(
        "🔄 Формирую список продуктов...\nПожалуйста, подождите.",
        reply_markup=None
    )

    try:
        # Очищаем старую корзину
        clear_shopping_cart(user_id)

        # Собираем продукты из разных источников
        all_products = {}
        period_text = f"на {days} дн." if days > 1 else "на сегодня"

        # Получаем продукты из дневника питания и плана питания
        for day_offset in range(days):
            current_date = (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")

            # Из плана питания (если есть рецепты)
            try:
                meal_plan = get_daily_meal_plan(user_id, current_date)
                for meal in meal_plan:
                    if 'recipe_id' in meal and meal['recipe_id']:
                        recipe = get_recipe_details(meal['recipe_id'])
                        if recipe and recipe.get('ingredients'):
                            products = parse_ingredients(recipe['ingredients'])
                            merge_products(all_products, products)
            except Exception as e:
                logger.warning(f"Ошибка при получении плана питания для {current_date}: {e}")

            # Из дневника питания - берем названия продуктов
            try:
                diary_entries = get_daily_entries(user_id, current_date)
                for entry in diary_entries:
                    product_name = entry['food_name']

                    # Примерное количество на основе калорий (упрощенная формула)
                    # Средняя калорийность продуктов ~2-4 ккал/г
                    estimated_grams = max(50, int(entry['calories'] / 3))

                    # Нормализуем название продукта
                    product_name = product_name.strip().capitalize()

                    if product_name in all_products:
                        all_products[product_name]['quantity'] += estimated_grams
                    else:
                        all_products[product_name] = {
                            'quantity': estimated_grams,
                            'unit': 'г'
                        }
            except Exception as e:
                logger.warning(f"Ошибка при получении записей дневника для {current_date}: {e}")

        # Добавляем продукты в корзину
        items_added = 0
        for product_name, details in all_products.items():
            try:
                if add_shopping_cart_item(
                        user_id,
                        product_name,
                        details['quantity'],
                        details['unit'],
                        period_text
                ):
                    items_added += 1
            except Exception as e:
                logger.error(f"Ошибка при добавлении продукта {product_name}: {e}")

        if items_added > 0:
            success_text = (
                f"✅ <b>Корзина сформирована!</b>\n\n"
                f"📊 Добавлено продуктов: {items_added}\n"
                f"📅 Период: {period_text}\n\n"
                f"💡 Корзина создана на основе записей в вашем дневнике питания"
            )

            # Показываем первые несколько продуктов для примера
            if items_added <= 5:
                success_text += " и содержит:\n"
                for product_name, details in list(all_products.items())[:5]:
                    success_text += f"• {product_name} — {details['quantity']} {details['unit']}\n"
        else:
            success_text = (
                "😔 <b>Корзина пуста</b>\n\n"
                "Не удалось найти продукты для создания списка покупок.\n\n"
                "💡 Попробуйте:\n"
                "• Добавить записи в дневник питания за выбранный период\n"
                "• Создать план питания с рецептами\n"
                "• Добавить продукты в корзину вручную"
            )

        keyboard = [
            [InlineKeyboardButton(text="🛒 Просмотреть корзину", callback_data="cart:view")],
            [InlineKeyboardButton(text="➕ Добавить продукт", callback_data="cart:add_manual")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="cart:back_to_menu")]
        ]

        await callback_query.message.edit_text(
            success_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    except Exception as e:
        logger.error(f"Ошибка при генерации корзины: {e}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при формировании корзины.\n\n"
            f"Детали ошибки: {str(e)}\n\n"
            "Попробуйте добавить продукты вручную.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить вручную", callback_data="cart:add_manual")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="cart:back_to_menu")]
            ])
        )

    await state.clear()

def parse_ingredients(ingredients_text):
    """Парсит текст ингредиентов и извлекает продукты с количеством."""
    products = {}

    # Разбиваем по строкам
    lines = ingredients_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('•') and len(line) <= 2:
            continue

        # Убираем маркеры списка
        line = re.sub(r'^[•\-*]\s*', '', line)

        # Ищем паттерны типа "Продукт - количество единица"
        patterns = [
            r'(.+?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*(г|кг|мл|л|шт|ст\.л\.|ч\.л\.)',
            r'(.+?)\s*(\d+(?:\.\d+)?)\s*(г|кг|мл|л|шт|ст\.л\.|ч\.л\.)',
            r'(\d+(?:\.\d+)?)\s*(г|кг|мл|л|шт|ст\.л\.|ч\.л\.)\s*(.+)',
        ]

        parsed = False
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if pattern.startswith('(\\d'):  # количество в начале
                    quantity_str, unit, product_name = match.groups()
                else:  # продукт в начале
                    product_name, quantity_str, unit = match.groups()

                try:
                    quantity = float(quantity_str)

                    # Конвертируем в граммы
                    if unit.lower() in ['кг']:
                        quantity *= 1000
                        unit = 'г'
                    elif unit.lower() in ['л']:
                        quantity *= 1000
                        unit = 'мл'
                    elif unit.lower() in ['ст.л.', 'ст.л']:
                        quantity *= 15  # примерно 15 мл/г в столовой ложке
                        unit = 'г'
                    elif unit.lower() in ['ч.л.', 'ч.л']:
                        quantity *= 5  # примерно 5 мл/г в чайной ложке
                        unit = 'г'

                    product_name = product_name.strip().capitalize()

                    if product_name in products:
                        products[product_name]['quantity'] += quantity
                    else:
                        products[product_name] = {
                            'quantity': quantity,
                            'unit': unit
                        }

                    parsed = True
                    break

                except ValueError:
                    continue

        # Если не удалось распарсить, добавляем как есть с примерным количеством
        if not parsed and len(line) > 2:
            product_name = line.strip().capitalize()
            products[product_name] = {
                'quantity': 100,  # примерное количество
                'unit': 'г'
            }

    return products


def merge_products(target_dict, source_dict):
    """Объединяет списки продуктов, суммируя количества."""
    for product_name, details in source_dict.items():
        if product_name in target_dict:
            # Проверяем совместимость единиц измерения
            if target_dict[product_name]['unit'] == details['unit']:
                target_dict[product_name]['quantity'] += details['quantity']
            else:
                # Если единицы разные, создаем новую запись
                new_name = f"{product_name} ({details['unit']})"
                target_dict[new_name] = details
        else:
            target_dict[product_name] = details


async def request_manual_item(callback_query: CallbackQuery, state: FSMContext):
    """Запрашивает ручной ввод продукта."""
    input_text = (
        "➕ <b>Добавить продукт вручную</b>\n\n"
        "📝 Введите название и количество продукта.\n\n"
        "<b>Примеры:</b>\n"
        "• <code>Хлеб — 300 г</code>\n"
        "• <code>Молоко 1 л</code>\n"
        "• <code>Яйца - 10 шт</code>\n"
        "• <code>Рис 500г</code>\n\n"
        "💡 Поддерживаемые единицы: г, кг, мл, л, шт"
    )

    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cart:back_to_menu")]
    ]

    await callback_query.message.edit_text(
        input_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(ShoppingCartStates.adding_manual_item)


async def process_manual_item(message: types.Message, state: FSMContext):
    """Обрабатывает ручной ввод продукта."""
    user_id = message.from_user.id
    input_text = message.text.strip()

    # Парсим ввод пользователя
    products = parse_ingredients(input_text)

    if not products:
        await message.answer(
            "❌ <b>Не удалось распознать продукт</b>\n\n"
            "Попробуйте ввести в формате:\n"
            "<code>Название продукта - количество единица</code>\n\n"
            "Например: <code>Хлеб - 300 г</code>",
            parse_mode="HTML"
        )
        return

    # Добавляем продукты в корзину
    added_count = 0
    for product_name, details in products.items():
        if add_shopping_cart_item(
                user_id,
                product_name,
                details['quantity'],
                details['unit'],
                "добавлено вручную"
        ):
            added_count += 1

    if added_count > 0:
        if added_count == 1:
            product_name = list(products.keys())[0]
            details = products[product_name]
            success_text = (
                f"✅ <b>Продукт добавлен!</b>\n\n"
                f"🛒 {product_name} — {details['quantity']} {details['unit']}"
            )
        else:
            success_text = f"✅ <b>Добавлено продуктов:</b> {added_count}"
    else:
        success_text = "❌ Не удалось добавить продукт. Попробуйте еще раз."

    keyboard = [
        [InlineKeyboardButton(text="🛒 Просмотреть корзину", callback_data="cart:view")],
        [InlineKeyboardButton(text="➕ Добавить еще", callback_data="cart:add_manual")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="cart:back_to_main")]
    ]

    await message.answer(
        success_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.clear()


async def show_items_for_action(callback_query: CallbackQuery, action: str):
    """Показывает список продуктов для выполнения действия (отметить/удалить)."""
    user_id = callback_query.from_user.id
    cart_items = get_shopping_cart_items(user_id)

    if not cart_items:
        await callback_query.message.edit_text(
            "🛒 Корзина пуста",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="cart:view")]
            ])
        )
        return

    if action == "mark":
        title = "✅ Отметить как купленное"
        items_to_show = [item for item in cart_items if not item.get('is_purchased')]
        action_prefix = "cart:mark:"
    else:  # remove
        title = "🗑 Удалить продукт"
        items_to_show = cart_items
        action_prefix = "cart:delete:"

    if not items_to_show:
        message_text = f"{title}\n\nНет доступных продуктов для этого действия."
        keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="cart:view")]]
    else:
        message_text = f"{title}\n\nВыберите продукт:"
        keyboard = []

        for item in items_to_show[:10]:  # Показываем максимум 10 продуктов
            product_name = item['product_name']
            quantity = item['quantity']
            unit = item.get('unit', 'г')
            button_text = f"{product_name} ({quantity} {unit})"

            # Ограничиваем длину текста кнопки
            if len(button_text) > 30:
                button_text = button_text[:27] + "..."

            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"{action_prefix}{item['id']}"
                )
            ])

        if len(items_to_show) > 10:
            message_text += f"\n\nПоказано 10 из {len(items_to_show)} продуктов."

        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="cart:view")])

    await callback_query.message.edit_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def handle_shopping_cart_callback(callback_query: CallbackQuery, state: FSMContext):
    """Основной обработчик callback-запросов для продуктовой корзины."""
    data = callback_query.data
    logger.info(f"Получен cart callback: {data}")

    try:
        if data == "cart:view":
            await show_cart_items(callback_query, state)

        elif data == "cart:generate":
            await request_generation_period(callback_query, state)

        elif data.startswith("cart:generate:"):
            days = int(data.split(':')[2])
            await generate_shopping_cart(callback_query, state, days)

        elif data == "cart:refresh":
            # Обновляем корзину (регенерируем на тот же период)
            cart_items = get_shopping_cart_items(callback_query.from_user.id)
            if cart_items:
                # Определяем период по существующим данным
                period = cart_items[0].get('period', 'на сегодня')
                if 'сегодня' in period:
                    days = 1
                elif '3' in period:
                    days = 3
                elif 'неделю' in period:
                    days = 7
                else:
                    days = 1
                await generate_shopping_cart(callback_query, state, days)
            else:
                await request_generation_period(callback_query, state)

        elif data == "cart:add_manual":
            await request_manual_item(callback_query, state)

        elif data == "cart:mark_purchased":
            await show_items_for_action(callback_query, "mark")

        elif data == "cart:remove_item":
            await show_items_for_action(callback_query, "remove")

        elif data.startswith("cart:mark:"):
            item_id = int(data.split(':')[2])
            if toggle_item_purchased(callback_query.from_user.id, item_id):
                await callback_query.answer("✅ Отмечено как купленное!")
                await show_cart_items(callback_query, state)
            else:
                await callback_query.answer("❌ Ошибка при отметке")

        elif data.startswith("cart:delete:"):
            item_id = int(data.split(':')[2])
            if remove_shopping_cart_item(callback_query.from_user.id, item_id):
                await callback_query.answer("🗑 Продукт удален!")
                await show_cart_items(callback_query, state)
            else:
                await callback_query.answer("❌ Ошибка при удалении")

        elif data == "cart:clear":
            if clear_shopping_cart(callback_query.from_user.id):
                await callback_query.answer("🗑 Корзина очищена!")
                await show_shopping_cart_menu_callback(callback_query, state)
            else:
                await callback_query.answer("❌ Ошибка при очистке")

        elif data == "cart:back_to_menu":
            await show_shopping_cart_menu_callback(callback_query, state)

        elif data == "cart:back_to_main":
            await return_to_main_menu(callback_query, state)

        else:
            logger.warning(f"Неизвестная команда cart: {data}")
            await callback_query.answer("❌ Неизвестная команда")

    except Exception as e:
        logger.error(f"Ошибка в handle_shopping_cart_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка")

    await callback_query.answer()


async def show_shopping_cart_menu_callback(callback_query: CallbackQuery, state: FSMContext):
    """Показывает меню корзины через callback (для возврата)."""
    user_id = callback_query.from_user.id
    cart_items = get_shopping_cart_items(user_id)

    # Формируем основной текст
    info_text = (
        "🛒 <b>Продуктовая корзина</b>\n\n"
        "📋 Автоматически формируется список продуктов на основе:\n"
        "• 📆 Вашего рациона питания\n"
        "• 🍳 Выбранных рецептов\n"
        "• 📘 Продуктов из дневника\n\n"
    )

    if cart_items:
        purchased_count = len([item for item in cart_items if item.get('is_purchased')])
        total_count = len(cart_items)

        info_text += f"📊 <b>В корзине:</b> {total_count} позиций\n"
        if purchased_count > 0:
            info_text += f"✅ <b>Куплено:</b> {purchased_count} из {total_count}\n"

        info_text += f"📅 <b>Период:</b> {cart_items[0].get('period', 'не указан')}\n\n"

        # Показываем первые несколько продуктов
        info_text += "🛍️ <b>Основные продукты:</b>\n"
        for item in cart_items[:5]:
            status = "✅" if item.get('is_purchased') else "🔘"
            name = item['product_name']
            quantity = item['quantity']
            unit = item.get('unit', 'г')
            info_text += f"{status} {name} — {quantity} {unit}\n"

        if len(cart_items) > 5:
            info_text += f"... и еще {len(cart_items) - 5} продуктов\n"
    else:
        info_text += "📝 <b>Корзина пуста</b>\n"
        info_text += "💡 Сформируйте рацион или выберите рецепты для автоматического создания списка покупок!"

    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton(text="🛒 Просмотреть корзину", callback_data="cart:view")],
        [
            InlineKeyboardButton(text="📝 Сформировать корзину", callback_data="cart:generate"),
            InlineKeyboardButton(text="🔄 Обновить корзину", callback_data="cart:refresh")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить продукт", callback_data="cart:add_manual"),
            InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart:clear")
        ],
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="cart:back_to_main")]
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