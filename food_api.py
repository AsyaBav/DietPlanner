import requests
import logging
import os
from config import NUTRITIONIX_APP_ID, NUTRITIONIX_API_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовый URL для API Nutritionix
BASE_URL = 'https://trackapi.nutritionix.com/v2'


def get_headers():
    """Возвращает заголовки для запросов к API."""
    return {
        'x-app-id': NUTRITIONIX_APP_ID,
        'x-app-key': NUTRITIONIX_API_KEY,
        'x-remote-user-id': '0'  # 0 для разработки
    }


def search_food(query, limit=5):
    """
    Поиск продуктов по запросу пользователя.

    Args:
        query (str): Строка поиска
        limit (int): Максимальное количество результатов

    Returns:
        list: Список найденных продуктов
    """
    if not query:
        return []

    logger.info(f"Searching Nutritionix for: {query}")

    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY:
        logger.error("API ключи Nutritionix не настроены")
        return []

    try:
        # Формируем URL для запроса
        url = f"{BASE_URL}/search/instant"

        # Параметры запроса
        params = {
            'query': query,
            'detailed': True,
            'common': True,
            'branded': True
        }

        # Выполняем запрос
        response = requests.get(url, params=params, headers=get_headers())
        response.raise_for_status()  # Проверка на ошибки

        data = response.json()

        # Комбинируем обычные и брендовые продукты
        common_foods = data.get('common', [])[:limit // 2]
        branded_foods = data.get('branded', [])[:limit // 2]

        results = []

        # Добавляем обычные продукты
        for food in common_foods:
            results.append({
                'food_name': food.get('food_name', ''),
                'serving_unit': food.get('serving_unit', 'г'),
                'serving_qty': food.get('serving_qty', 100),
                'photo': food.get('photo', {}).get('thumb', ''),
                'food_type': 'common',
                'tag_id': food.get('tag_id', None)
            })

        # Добавляем брендовые продукты
        for food in branded_foods:
            results.append({
                'food_name': food.get('food_name', ''),
                'brand_name': food.get('brand_name', ''),
                'serving_unit': food.get('serving_unit', 'г'),
                'serving_qty': food.get('serving_qty', 100),
                'photo': food.get('photo', {}).get('thumb', ''),
                'food_type': 'branded',
                'nix_item_id': food.get('nix_item_id', None)
            })

        return results[:limit]

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса к API Nutritionix: {e}")
        return []
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при поиске продуктов: {e}")
        return [{
            'food_name': query, 'serving_unit': 'г',
            'serving_qty': 100,
            'calories': 0,
            'protein': 0,
            'fat': 0,
            'carbs': 0,
            'food_type': 'common'  # Добавлено поле по умолчанию
        }]


def get_food_nutrients(food_name, tag_id=None):
    """
    Получает информацию о пищевой ценности продукта по имени для обычных продуктов.

    Args:
        food_name (str): Название продукта
        tag_id (str): ID тега продукта (опционально)

    Returns:
        dict: Информация о пищевой ценности
    """
    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY:
        logger.warning("API ключи Nutritionix не настроены")
        return None

    try:
        # Формируем URL для запроса
        url = f"{BASE_URL}/natural/nutrients"

        # Данные для запроса
        data = {
            'query': food_name
        }

        # Выполняем запрос
        response = requests.post(url, json=data, headers=get_headers())
        response.raise_for_status()

        data = response.json()

        if 'foods' in data and len(data['foods']) > 0:
            food_data = data['foods'][0]

            return {
                'food_name': food_data.get('food_name', food_name),
                'serving_qty': food_data.get('serving_qty', 1),
                'serving_unit': food_data.get('serving_unit', 'г'),
                'serving_weight_grams': food_data.get('serving_weight_grams', 100),
                'calories': food_data.get('nf_calories', 0),
                'protein': food_data.get('nf_protein', 0),
                'fat': food_data.get('nf_total_fat', 0),
                'carbs': food_data.get('nf_total_carbohydrate', 0)
            }

        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса к API Nutritionix: {e}")
        return None
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении информации о продукте: {e}")
        return None


def get_branded_food_info(nix_item_id):
    """
    Получает информацию о пищевой ценности брендового продукта по ID.

    Args:
        nix_item_id (str): ID продукта

    Returns:
        dict: Информация о пищевой ценности
    """
    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY:
        logger.warning("API ключи Nutritionix не настроены")
        return None

    try:
        # Формируем URL для запроса
        url = f"{BASE_URL}/search/item?nix_item_id={nix_item_id}"

        # Выполняем запрос
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()

        data = response.json()

        if 'foods' in data and len(data['foods']) > 0:
            food_data = data['foods'][0]

            return {
                'food_name': food_data.get('food_name', ''),
                'brand_name': food_data.get('brand_name', ''),
                'serving_qty': food_data.get('serving_qty', 1),
                'serving_unit': food_data.get('serving_unit', 'г'),
                'serving_weight_grams': food_data.get('serving_weight_grams', 100),
                'calories': food_data.get('nf_calories', 0),
                'protein': food_data.get('nf_protein', 0),
                'fat': food_data.get('nf_total_fat', 0),
                'carbs': food_data.get('nf_total_carbohydrate', 0)
            }

        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса к API Nutritionix: {e}")
        return None
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении информации о продукте: {e}")
        return None


def get_nutrients_from_text(text):
    """
    Извлекает информацию о питательной ценности из текстового описания.
    Например: "100г курицы с 200г риса"

    Args:
        text (str): Текстовое описание продуктов

    Returns:
        dict: Суммарная информация о пищевой ценности
    """
    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY:
        logger.warning("API ключи Nutritionix не настроены")
        return None

    try:
        # Формируем URL для запроса
        url = f"{BASE_URL}/natural/nutrients"

        # Данные для запроса
        data = {
            'query': text
        }

        # Выполняем запрос
        response = requests.post(url, json=data, headers=get_headers())
        response.raise_for_status()

        data = response.json()

        if 'foods' in data and len(data['foods']) > 0:
            # Суммируем питательную ценность всех продуктов
            total_calories = sum(food.get('nf_calories', 0) for food in data['foods'])
            total_protein = sum(food.get('nf_protein', 0) for food in data['foods'])
            total_fat = sum(food.get('nf_total_fat', 0) for food in data['foods'])
            total_carbs = sum(food.get('nf_total_carbohydrate', 0) for food in data['foods'])

            # Формируем полное название
            food_names = [food.get('food_name', '') for food in data['foods']]
            full_name = ", ".join(food_names)

            return {
                'food_name': full_name,
                'calories': total_calories,
                'protein': total_protein,
                'fat': total_fat,
                'carbs': total_carbs
            }

        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса к API Nutritionix: {e}")
        return None
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при анализе текста: {e}")
        return None
def search_food(query, limit=5):
    mock_data = {
        "яйцо": [{"food_name": "Яйцо куриное", "calories": 143, "protein": 12.6, "fat": 9.5, "carbs": 0.7}],
        "омлет": [{"food_name": "Омлет", "calories": 154, "protein": 10.6, "fat": 11.2, "carbs": 2.2}]
    }
    return mock_data.get(query.lower(), [])