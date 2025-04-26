import sqlite3
import logging
from datetime import datetime, timedelta
import json
import os
from config import DB_PATH, DEFAULT_WATER_GOAL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Создает соединение с базой данных."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализирует базу данных, создавая необходимые таблицы."""
    conn = get_db_connection()

    try:
        # Таблица пользователей
        conn.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            activity_level TEXT,
            goal TEXT,
            goal_calories REAL,
            protein INTEGER,
            fat INTEGER,
            carbs INTEGER,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
            water_goal INTEGER DEFAULT {DEFAULT_WATER_GOAL},
            registration_complete BOOLEAN DEFAULT FALSE
        )
        ''')

        # Таблица записей о еде
        conn.execute('''
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            meal_type TEXT,
            food_name TEXT,
            calories REAL,
            protein REAL,
            fat REAL,
            carbs REAL,
            entry_time TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Таблица для сохранения истории потребления воды
        conn.execute('''
        CREATE TABLE IF NOT EXISTS water_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            amount INTEGER,
            entry_time TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Таблица для хранения рецептов
        conn.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            ingredients TEXT,
            instructions TEXT,
            calories REAL,
            protein REAL,
            fat REAL,
            carbs REAL,
            is_favorite BOOLEAN DEFAULT 0,
            creation_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Таблица для плана питания
        conn.execute('''
        CREATE TABLE IF NOT EXISTS meal_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            meal_type TEXT,
            recipe_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (recipe_id) REFERENCES recipes (id)
        )
        ''')


        # Создаем индексы для оптимизации запросов
        conn.execute('CREATE INDEX IF NOT EXISTS idx_food_entries_user_date ON food_entries (user_id, date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_water_entries_user_date ON water_entries (user_id, date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_user ON recipes (user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_meal_plan_user_date ON meal_plan (user_id, date)')

        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]  # Теперь правильно
        logger.info(f"Структура таблицы users: {columns}")


        conn.commit()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
    finally:
        conn.close()


# Инициализируем базу данных при импорте
if not os.path.exists(DB_PATH):
    init_db()
else:
    # Проверим структуру базы данных и добавим недостающие таблицы
    init_db()


# Функции для работы с пользователями

def create_user(user_id, name=None):
    """Создает нового пользователя."""
    conn = get_db_connection()
    try:
        # Проверяем, существует ли пользователь
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            conn.execute(
                'INSERT INTO users (id, name, water_goal) VALUES (?, ?, ?)',
                (user_id, name, DEFAULT_WATER_GOAL)
            )
            conn.commit()
            logger.info(f"Создан новый пользователь с ID: {user_id}")
            return True
        else:
            logger.info(f"Пользователь с ID {user_id} уже существует")
            return False
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        return False
    finally:
        conn.close()


def get_user(user_id):
    """Получает данные пользователя."""
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if user:
            return dict(user)
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении данных пользователя: {e}")
        return None
    finally:
        conn.close()


def update_user(user_id, **kwargs):
    """Обновляет данные пользователя."""
    conn = get_db_connection()
    try:
        if 'goal_calories' in kwargs:
            kwargs['registration_complete'] = True

        # Формируем строку запроса и список значений
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)

        # Добавляем ID пользователя
        values.append(user_id)

        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        conn.execute(query, values)
        conn.commit()

        logger.info(f"Обновлены данные пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных пользователя: {e}")
        return False
    finally:
        conn.close()


# Функции для работы с записями о еде

def add_food_entry(user_id, date, meal_type, food_name, calories, protein, fat, carbs):
    """Добавляет запись о еде в дневник."""
    conn = get_db_connection()
    try:
        conn.execute(
            '''INSERT INTO food_entries 
            (user_id, date, meal_type, food_name, calories, protein, fat, carbs) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, date, meal_type, food_name, calories, protein, fat, carbs)
        )
        conn.commit()
        logger.info(f"Добавлена запись о еде для пользователя {user_id}")
        return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка при добавлении записи о еде: {e}")
        return None
    finally:
        conn.close()


def get_daily_entries(user_id, date):
    """Получает все записи о еде за день."""
    conn = get_db_connection()
    try:
        entries = conn.execute(
            'SELECT * FROM food_entries WHERE user_id = ? AND date = ? ORDER BY entry_time',
            (user_id, date)
        ).fetchall()
        return [dict(entry) for entry in entries]
    except Exception as e:
        logger.error(f"Ошибка при получении дневных записей: {e}")
        return []
    finally:
        conn.close()


def get_entries_by_meal(user_id, date, meal_type):
    #Получает записи о еде за день для конкретного приема пищи
    conn = get_db_connection()
    try:
        entries = conn.execute(
            'SELECT * FROM food_entries WHERE user_id = ? AND date = ? AND meal_type = ? ORDER BY entry_time',
            (user_id, date, meal_type)
        ).fetchall()
        return [dict(entry) for entry in entries]
    except Exception as e:
        logger.error(f"Ошибка при получении записей для приема пищи: {e}")
        return []
    finally:
        conn.close()


def get_daily_totals(user_id, date):
    #Получает суммарные показатели за день.
    conn = get_db_connection()
    try:
        result = conn.execute(
            '''SELECT 
                COALESCE(SUM(calories), 0) as total_calories, 
                COALESCE(SUM(protein), 0) as total_protein, 
                COALESCE(SUM(fat), 0) as total_fat, 
                COALESCE(SUM(carbs), 0) as total_carbs 
            FROM food_entries 
            WHERE user_id = ? AND date = ?''',
            (user_id, date)
        ).fetchone()

        if result:
            return dict(result)
        return {"total_calories": 0, "total_protein": 0, "total_fat": 0, "total_carbs": 0}
    except Exception as e:
        logger.error(f"Ошибка при получении дневных тоталов: {e}")
        return {"total_calories": 0, "total_protein": 0, "total_fat": 0, "total_carbs": 0}
    finally:
        conn.close()


def clear_daily_entries(user_id, date):
    #Удаляет все записи о еде за указанный день
    conn = get_db_connection()
    try:
        conn.execute(
            'DELETE FROM food_entries WHERE user_id = ? AND date = ?',
            (user_id, date)
        )
        conn.commit()
        logger.info(f"Очищены записи о еде для пользователя {user_id} за {date}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при очистке дневных записей: {e}")
        return False
    finally:
        conn.close()


def get_recent_foods(user_id, limit=5):
    #Получает последние добавленные продукты пользователя.
    conn = get_db_connection()
    try:
        entries = conn.execute(
            '''SELECT DISTINCT food_name, AVG(calories) as calories, AVG(protein) as protein, 
            AVG(fat) as fat, AVG(carbs) as carbs, MAX(id) as id 
            FROM food_entries 
            WHERE user_id = ? 
            GROUP BY food_name 
            ORDER BY MAX(entry_time) DESC LIMIT ?''',
            (user_id, limit)
        ).fetchall()
        return [dict(entry) for entry in entries]
    except Exception as e:
        logger.error(f"Ошибка при получении последних продуктов: {e}")
        return []
    finally:
        conn.close()


# Функции для работы с водным балансом

def add_water_entry(user_id, amount):
    #Добавляет запись о потреблении воды
    date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO water_entries (user_id, date, amount) VALUES (?, ?, ?)',
            (user_id, date, amount)
        )
        conn.commit()
        logger.info(f"Добавлена запись о воде ({amount} мл) для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении записи о воде: {e}")
        return False
    finally:
        conn.close()


def get_daily_water(user_id, date=None):
    #Получает суммарное потребление воды за день
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    try:
        result = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as amount FROM water_entries WHERE user_id = ? AND date = ?',
            (user_id, date)
        ).fetchone()

        if result:
            return result['amount']
        return 0
    except Exception as e:
        logger.error(f"Ошибка при получении дневного потребления воды: {e}")
        return 0
    finally:
        conn.close()


def get_water_goal(user_id):
    #Получает целевое значение потребления воды
    conn = get_db_connection()
    try:
        result = conn.execute(
            'SELECT water_goal FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if result:
            return result['water_goal']
        return DEFAULT_WATER_GOAL
    except Exception as e:
        logger.error(f"Ошибка при получении цели по воде: {e}")
        return DEFAULT_WATER_GOAL
    finally:
        conn.close()


def set_water_goal(user_id, goal):
    #Устанавливает новую цель по потреблению воды
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE users SET water_goal = ? WHERE id = ?',
            (goal, user_id)
        )
        conn.commit()
        logger.info(f"Установлена новая цель по воде ({goal} мл) для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке цели по воде: {e}")
        return False
    finally:
        conn.close()


def get_weekly_water(user_id, end_date=None):
    #Получает данные о потреблении воды за неделю
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Вычисляем начальную дату (неделю назад)
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    start_date_obj = end_date_obj - timedelta(days=6)

    result = []
    current_date = start_date_obj

    # Заполняем данные по каждому дню
    while current_date <= end_date_obj:
        date_str = current_date.strftime("%Y-%m-%d")
        amount = get_daily_water(user_id, date_str)

        result.append({
            "date": date_str,
            "amount": amount
        })

        current_date += timedelta(days=1)

    return result


# Функции для работы с рецептами

def save_recipe(user_id, name, ingredients, instructions, calories, protein, fat, carbs):
    #Сохраняет новый рецепт
    conn = get_db_connection()
    try:
        conn.execute(
            '''INSERT INTO recipes 
            (user_id, name, ingredients, instructions, calories, protein, fat, carbs) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, name, ingredients, instructions, calories, protein, fat, carbs)
        )
        conn.commit()
        logger.info(f"Сохранен новый рецепт {name} для пользователя {user_id}")
        return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка при сохранении рецепта: {e}")
        return None
    finally:
        conn.close()


def get_saved_recipes(user_id, is_favorite=None):
    #Получает список сохраненных рецептов
    conn = get_db_connection()
    try:
        query = 'SELECT * FROM recipes WHERE user_id = ?'
        params = [user_id]

        if is_favorite is not None:
            query += ' AND is_favorite = ?'
            params.append(int(is_favorite))

        query += ' ORDER BY is_favorite DESC, creation_date DESC'

        recipes = conn.execute(query, params).fetchall()
        return [dict(recipe) for recipe in recipes]
    except Exception as e:
        logger.error(f"Ошибка при получении списка рецептов: {e}")
        return []
    finally:
        conn.close()


def get_recipe_details(recipe_id):
    #Получает подробную информацию о рецепте
    conn = get_db_connection()
    try:
        recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()

        if recipe:
            return dict(recipe)
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении информации о рецепте: {e}")
        return None
    finally:
        conn.close()


def toggle_favorite_recipe(recipe_id):
    #Изменяет статус избранного для рецепта
    conn = get_db_connection()
    try:
        # Получаем текущий статус
        current = conn.execute(
            'SELECT is_favorite FROM recipes WHERE id = ?',
            (recipe_id,)
        ).fetchone()

        if current:
            new_status = 1 - current['is_favorite']  # Инвертируем статус

            conn.execute(
                'UPDATE recipes SET is_favorite = ? WHERE id = ?',
                (new_status, recipe_id)
            )
            conn.commit()
            logger.info(f"Изменен статус избранного для рецепта {recipe_id} на {new_status}")

            return bool(new_status)
        return False
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса избранного: {e}")
        return False
    finally:
        conn.close()


def delete_recipe(recipe_id):
    #Удаляет рецепт
    conn = get_db_connection()
    try:
        # Сначала удаляем все ссылки на этот рецепт из плана питания
        conn.execute('DELETE FROM meal_plan WHERE recipe_id = ?', (recipe_id,))

        # Затем удаляем сам рецепт
        conn.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))

        conn.commit()
        logger.info(f"Удален рецепт {recipe_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении рецепта: {e}")
        return False
    finally:
        conn.close()


# Функции для работы с планом питания

def add_to_meal_plan(user_id, recipe_id, meal_type, date):
    #Добавляет рецепт в план питания
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO meal_plan (user_id, recipe_id, meal_type, date) VALUES (?, ?, ?, ?)',
            (user_id, recipe_id, meal_type, date)
        )
        conn.commit()
        logger.info(f"Добавлен рецепт {recipe_id} в план питания пользователя {user_id}")
        return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка при добавлении в план питания: {e}")
        return None
    finally:
        conn.close()


def get_daily_meal_plan(user_id, date):
    #Получает план питания на день
    conn = get_db_connection()
    try:
        result = conn.execute(
            '''SELECT mp.id, mp.meal_type, r.name, r.calories, r.protein, r.fat, r.carbs 
            FROM meal_plan mp 
            JOIN recipes r ON mp.recipe_id = r.id 
            WHERE mp.user_id = ? AND mp.date = ? 
            ORDER BY 
                CASE mp.meal_type 
                    WHEN 'Завтрак' THEN 1 
                    WHEN 'Обед' THEN 2 
                    WHEN 'Ужин' THEN 3 
                    WHEN 'Перекус' THEN 4 
                    ELSE 5 
                END''',
            (user_id, date)
        ).fetchall()

        return [dict(entry) for entry in result]
    except Exception as e:
        logger.error(f"Ошибка при получении плана питания: {e}")
        return []
    finally:
        conn.close()


def get_meal_plan_for_type(user_id, meal_type, date):
    """Получает план питания для конкретного приема пищи."""
    conn = get_db_connection()
    try:
        result = conn.execute(
            '''SELECT mp.id, mp.meal_type, r.id as recipe_id, r.name, r.calories, r.protein, r.fat, r.carbs 
            FROM meal_plan mp 
            JOIN recipes r ON mp.recipe_id = r.id 
            WHERE mp.user_id = ? AND mp.date = ? AND mp.meal_type = ?''',
            (user_id, date, meal_type)
        ).fetchall()

        return [dict(entry) for entry in result]
    except Exception as e:
        logger.error(f"Ошибка при получении плана для приема пищи: {e}")
        return []
    finally:
        conn.close()


def remove_from_meal_plan(plan_id):
    """Удаляет запись из плана питания."""
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM meal_plan WHERE id = ?', (plan_id,))
        conn.commit()
        logger.info(f"Удалена запись {plan_id} из плана питания")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении из плана питания: {e}")
        return False
    finally:
        conn.close()


def clear_meal_plan(user_id, date):
    """Очищает план питания на день."""
    conn = get_db_connection()
    try:
        conn.execute(
            'DELETE FROM meal_plan WHERE user_id = ? AND date = ?',
            (user_id, date)
        )
        conn.commit()
        logger.info(f"Очищен план питания для пользователя {user_id} за {date}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при очистке плана питания: {e}")
        return False
    finally:
        conn.close()

def check_db_structure():
    conn = get_db_connection()
    try:
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Структура таблицы users: {columns}")
    finally:
        conn.close()

def close_db():
    """Закрывает соединение с базой данных."""
    pass  # Здесь ничего не нужно делать, т.к. мы создаем и закрываем соединение в каждой функции
