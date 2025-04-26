import requests
import logging
from config import NUTRITIONIX_APP_ID, NUTRITIONIX_API_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовый URL для Nutritionix API
BASE_URL = 'https://trackapi.nutritionix.com/v2'


def get_headers():
    """Возвращает заголовки для запросов к Nutritionix API."""
    return {
        'x-app-id': NUTRITIONIX_APP_ID,
        'x-app-key': NUTRITIONIX_API_KEY,
        'x-remote-user-id': '0'
    }


def make_request(method, endpoint, **kwargs):
    """Упрощенная функция для выполнения GET или POST запроса."""
    url = f"{BASE_URL}{endpoint}"

    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY:
        logger.error("API ключи Nutritionix не настроены.")
        return None

    try:
        if method == 'GET':
            response = requests.get(url, headers=get_headers(), **kwargs)
        elif method == 'POST':
            response = requests.post(url, headers=get_headers(), **kwargs)
        else:
            logger.error(f"Неподдерживаемый метод запроса: {method}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к Nutritionix: {e}")
        return None


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

    logger.info(f"Поиск продуктов по запросу: {query}")

    data = make_request('GET', '/search/instant', params={'query': query})

    if not data:
        return []

    common_foods = data.get('common', [])[:limit]
    branded_foods = data.get('branded', [])[:limit]
    results = []

    for food in common_foods:
        results.append({
            'food_name': food.get('food_name', ''),
            'serving_unit': food.get('serving_unit', 'г'),
            'serving_qty': food.get('serving_qty', 100),
            'photo': food.get('photo', {}).get('thumb', ''),
            'food_type': 'common',
            'tag_id': food.get('tag_id', None)
        })

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


def get_food_nutrients(food_name):
    """
    Получает информацию о пищевой ценности обычного продукта.

    Args:
        food_name (str): Название продукта

    Returns:
        dict: Информация о пищевой ценности
    """
    logger.info(f"Получение информации о пищевой ценности продукта: {food_name}")

    data = make_request('POST', '/natural/nutrients', json={'query': food_name})

    if not data or 'foods' not in data or len(data['foods']) == 0:
        return None

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


def get_branded_food_info(nix_item_id):
    """
    Получает информацию о пищевой ценности брендированного продукта по ID.

    Args:
        nix_item_id (str): ID брендированного продукта

    Returns:
        dict: Информация о пищевой ценности
    """
    logger.info(f"Получение информации о брендированном продукте: {nix_item_id}")

    data = make_request('GET', f'/search/item?nix_item_id={nix_item_id}')

    if not data or 'foods' not in data or len(data['foods']) == 0:
        return None

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


def get_nutrients_from_text(text):
    """
    Извлекает информацию о питательной ценности из текстового описания.

    Args:
        text (str): Описание продуктов (например, "100г курицы и 200г риса")

    Returns:
        dict: Суммарная информация о пищевой ценности
    """
    logger.info(f"Анализ текста для расчета питательности: {text}")

    data = make_request('POST', '/natural/nutrients', json={'query': text})

    if not data or 'foods' not in data or len(data['foods']) == 0:
        return None

    total_calories = sum(food.get('nf_calories', 0) for food in data['foods'])
    total_protein = sum(food.get('nf_protein', 0) for food in data['foods'])
    total_fat = sum(food.get('nf_total_fat', 0) for food in data['foods'])
    total_carbs = sum(food.get('nf_total_carbohydrate', 0) for food in data['foods'])
    food_names = [food.get('food_name', '') for food in data['foods']]
    full_name = ", ".join(food_names)

    return {
        'food_name': full_name,
        'calories': total_calories,
        'protein': total_protein,
        'fat': total_fat,
        'carbs': total_carbs
    }
