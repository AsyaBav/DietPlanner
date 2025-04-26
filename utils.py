def calculate_bmi(weight, height):
    """
    Рассчитывает Индекс Массы Тела (ИМТ).

    Args:
        weight (float): Вес в килограммах
        height (float): Рост в сантиметрах

    Returns:
        float: Значение ИМТ
    """
    # Переводим рост из см в метры
    height_m = height / 100
    # Формула ИМТ: вес (кг) / (рост (м))²
    bmi = weight / (height_m ** 2)
    return bmi


def get_bmi_category(bmi):
    """
    Определяет категорию ИМТ.

    Args:
        bmi (float): Значение ИМТ

    Returns:
        str: Категория ИМТ
    """
    if bmi < 16:
        return "🚨 Выраженный дефицит массы тела"
    elif bmi < 18.5:
        return "⚠️ Недостаточная масса тела"
    elif bmi < 25:
        return "✅ Нормальная масса тела"
    elif bmi < 30:
        return "⚠️ Избыточная масса тела (предожирение)"
    elif bmi < 35:
        return "🚨 Ожирение I степени"
    elif bmi < 40:
        return "🚨 Ожирение II степени"
    else:
        return "🚨 Ожирение III степени"


def calculate_tdee(weight, height, age, activity_level, sex):
    """
    Рассчитывает общий расход энергии (TDEE).

    Args:
        weight (float): Вес в килограммах
        height (float): Рост в сантиметрах
        age (int): Возраст в годах
        activity_level (str): Уровень активности
        sex (str): Пол

    Returns:
        float: Значение TDEE в калориях
    """
    from config import ACTIVITY_LEVELS

    # Расчет базового обмена по формуле Миффлина-Сан Жеора
    if sex == "Мужчина":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # Женщина
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # Учитываем уровень активности
    activity_multiplier = ACTIVITY_LEVELS.get(activity_level, 1.2)

    # Итоговый расход энергии
    tdee = bmr * activity_multiplier

    return tdee


def get_goal_calories(tdee, goal):
    """
    Определяет целевое количество калорий в зависимости от цели.

    Args:
        tdee (float): Общий расход энергии
        goal (str): Цель пользователя

    Returns:
        float: Целевое количество калорий
    """
    from config import USER_GOALS

    # Получаем множитель для цели
    goal_multiplier = USER_GOALS.get(goal, 1.0)

    # Рассчитываем целевые калории
    goal_calories = tdee * goal_multiplier

    return goal_calories


def calculate_macronutrients(calories, weight, goal):
    """
    Рассчитывает распределение макронутриентов.

    Args:
        calories (float): Целевое количество калорий
        weight (float): Вес в килограммах
        goal (str): Цель пользователя

    Returns:
        dict: Словарь с распределением макронутриентов
    """
    # Корректируем белок в зависимости от цели
    if goal == "🔻 Похудение":
        protein_per_kg = 2.2  # Больше белка при похудении
    elif goal == "🔺 Набор веса":
        protein_per_kg = 1.8  # Средний уровень белка при наборе
    else:  # Поддержание
        protein_per_kg = 2.0  # Стандартный уровень

    # Рассчитываем количество белка
    protein = round(weight * protein_per_kg)
    protein_cal = protein * 4  # 1г белка = 4 ккал

    # Рассчитываем количество жиров (около 25% от общих калорий)
    fat_cal = calories * 0.25
    fat = round(fat_cal / 9)  # 1г жира = 9 ккал

    # Оставшиеся калории идут на углеводы
    carbs_cal = calories - protein_cal - fat_cal
    carbs = round(carbs_cal / 4)  # 1г углеводов = 4 ккал

    # Возвращаем результаты в словаре
    return {
        "protein": protein,
        "protein_cal": protein_cal,
        "fat": fat,
        "fat_cal": fat_cal,
        "carbs": carbs,
        "carbs_cal": carbs_cal
    }


def get_progress_percentage(current, goal):
    """
    Вычисляет процент выполнения цели.

    Args:
        current (float): Текущее значение
        goal (float): Целевое значение

    Returns:
        int: Процент выполнения (0-100)
    """
    if goal <= 0:
        return 0
    percentage = (current / goal) * 100
    return min(100, int(percentage))  # Ограничиваем максимальное значение 100%

def format_date(date_str):
    """
    Форматирует дату из ISO формата в читаемый вид.

    Args:
        date_str (str): Дата в формате ISO (YYYY-MM-DD)

    Returns:
        str: Отформатированная дата (DD.MM.YYYY)
    """
    try:
        year, month, day = date_str.split('-')
        return f"{day}.{month}.{year}"
    except:
        return date_str