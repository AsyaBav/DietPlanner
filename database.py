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


def init_nutritionists_table():
    """Создает таблицу диетологов и заполняет её тестовыми данными."""
    conn = get_db_connection()

    try:
        # Создаем таблицу диетологов
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nutritionists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                education TEXT NOT NULL,
                experience TEXT NOT NULL,
                specialization TEXT NOT NULL,
                approach TEXT NOT NULL,
                telegram_username TEXT,
                email TEXT,
                phone TEXT,
                work_hours TEXT DEFAULT 'Пн-Пт 9:00-18:00',
                price TEXT DEFAULT 'По договоренности',
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Проверяем, есть ли уже данные
        cursor = conn.execute("SELECT COUNT(*) FROM nutritionists")
        count = cursor.fetchone()[0]

        if count == 0:
            # Добавляем тестовых диетологов
            sample_nutritionists = [
                (
                    "Анна Петровна Смирнова",
                    "Московский медицинский университет им. И.М. Сеченова, диетология и нутрициология. Повышение квалификации в области спортивного питания.",
                    "8 лет",
                    "Снижение веса, спортивное питание, коррекция обмена веществ",
                    "Индивидуальный подход к каждому клиенту. Сбалансированное питание без строгих ограничений. Формирование здоровых пищевых привычек.",
                    "anna_nutritionist",
                    "anna.smirnova@dietconsult.ru",
                    "+7 (495) 123-45-67"
                ),
                (
                    "Дмитрий Александрович Козлов",
                    "СПбГМУ им. акад. И.П. Павлова, лечебное дело. Специализация по диетологии в РМАПО. Сертификат по функциональному питанию.",
                    "12 лет",
                    "Лечебное питание, работа с пищевыми расстройствами, детская диетология",
                    "Научно-обоснованный подход. Коррекция питания при заболеваниях ЖКТ. Психологическая работа с пищевым поведением.",
                    "dmitry_diet_doc",
                    "d.kozlov@healthnutrition.ru",
                    "+7 (812) 987-65-43"
                ),
                (
                    "Елена Викторовна Иванова",
                    "РГМУ им. Н.И. Пирогова, педиатрия. Ординатура по диетологии. Курсы по нутригенетике и превентивной медицине.",
                    "6 лет",
                    "Здоровое питание семьи, профилактическая диетология, anti-age питание",
                    "Комплексный подход к здоровью. Питание как основа долголетия. Учет генетических особенностей и образа жизни.",
                    "elena_family_nutrition",
                    "elena.ivanova@familyhealth.ru",
                    "+7 (903) 456-78-90"
                ),
                (
                    "Михаил Сергеевич Волков",
                    "Российский университет дружбы народов, лечебное дело. Интернатура по эндокринологии, переподготовка по диетологии.",
                    "10 лет",
                    "Диабетология, эндокринная диетология, метаболический синдром",
                    "Медикаментозная и немедикаментозная коррекция. Особое внимание к пациентам с диабетом и нарушениями обмена веществ.",
                    "mikhail_endo_diet",
                    "m.volkov@endohealth.ru",
                    "+7 (926) 123-89-67"
                )
            ]

            for nutritionist in sample_nutritionists:
                conn.execute('''
                    INSERT INTO nutritionists 
                    (full_name, education, experience, specialization, approach, telegram_username, email, phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', nutritionist)

            conn.commit()
            logger.info("Добавлены тестовые данные диетологов")

    except Exception as e:
        logger.error(f"Ошибка при создании таблицы диетологов: {e}")
    finally:
        conn.close()

def get_nutritionists():
    """Получает список всех активных диетологов."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM nutritionists 
            WHERE is_active = 1 
            ORDER BY full_name
        ''')
        nutritionists = [dict(row) for row in cursor.fetchall()]
        return nutritionists
    except Exception as e:
        logger.error(f"Ошибка при получении списка диетологов: {e}")
        return []
    finally:
        conn.close()


def get_nutritionist_by_id(nutritionist_id):
    """Получает данные диетолога по ID."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM nutritionists 
            WHERE id = ? AND is_active = 1
        ''', (nutritionist_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении диетолога по ID {nutritionist_id}: {e}")
        return None
    finally:
        conn.close()


def init_articles_tables():
    """Создает таблицы для статей и заполняет их тестовыми данными."""
    conn = get_db_connection()

    try:
        # Создаем таблицу тем статей
        conn.execute('''
            CREATE TABLE IF NOT EXISTS article_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '📖',
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем таблицу статей
        conn.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT,
                sources TEXT,
                publication_date TEXT,
                views_count INTEGER DEFAULT 0,
                is_published BOOLEAN DEFAULT 1,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES article_topics (id)
            )
        ''')

        # Проверяем, есть ли уже данные в темах
        cursor = conn.execute("SELECT COUNT(*) FROM article_topics")
        count = cursor.fetchone()[0]

        if count == 0:
            # Добавляем темы статей
            topics = [
                ("Витамины и БАДы", "💊", "Информация о витаминах, минералах и биологически активных добавках", 1),
                ("Основы питания", "🍎", "Базовые принципы здорового и сбалансированного питания", 2),
                ("Советы по похудению", "⚖️", "Эффективные и безопасные методы снижения веса", 3),
                ("Психология питания", "🧠", "Влияние психологических факторов на пищевое поведение", 4),
                ("Интервальное голодание", "⏰", "Методы и принципы интервального голодания", 5),
                ("Другое", "📝", "Разнообразные материалы о здоровье и питании", 6)
            ]

            for topic in topics:
                conn.execute('''
                    INSERT INTO article_topics (name, emoji, description, sort_order)
                    VALUES (?, ?, ?, ?)
                ''', topic)

            conn.commit()

            # Добавляем тестовые статьи
            sample_articles = [
                # Витамины и БАДы
                (1, "Витамин D: солнечный витамин для здоровья", """
<b>Витамин D</b> — один из важнейших витаминов для нашего организма, который часто называют "солнечным витамином".

🌟 <b>Почему витамин D так важен?</b>

• <b>Здоровье костей:</b> Витамин D помогает организму усваивать кальций и фосфор
• <b>Иммунная система:</b> Поддерживает защитные функции организма
• <b>Мышечная функция:</b> Необходим для нормальной работы мышц
• <b>Настроение:</b> Недостаток связан с депрессией и плохим настроением

☀️ <b>Источники витамина D:</b>

1. <b>Солнечный свет</b> — основной источник (15-20 минут на солнце ежедневно)
2. <b>Жирная рыба:</b> лосось, скумбрия, сардины
3. <b>Яичные желтки</b> от кур свободного выгула
4. <b>Обогащенные продукты:</b> молоко, каши
5. <b>Грибы</b> (особенно выращенные под УФ-лампами)

⚠️ <b>Признаки дефицита:</b>
• Усталость и слабость
• Боли в костях и мышцах
• Частые простуды
• Медленное заживление ран
• Депрессия

💊 <b>Нормы потребления:</b>
• Взрослые: 600-800 МЕ в день
• Пожилые люди (70+): 800-1000 МЕ в день
• При дефиците: по назначению врача до 4000 МЕ

🔬 <b>Важно знать:</b>
Перед приемом добавок обязательно сдайте анализ на 25(OH)D3 и проконсультируйтесь с врачом. Передозировка витамина D может быть опасной.
                """, "Команда NutriBot", "Mayo Clinic, Harvard Health Publishing", "2024-01-15"),

                (1, "Омега-3: незаменимые жирные кислоты", """
<b>Омега-3 жирные кислоты</b> — это незаменимые питательные вещества, которые наш организм не может производить самостоятельно.

🐟 <b>Основные типы Омега-3:</b>

• <b>EPA (эйкозапентаеновая кислота)</b> — противовоспалительное действие
• <b>DHA (докозагексаеновая кислота)</b> — важна для мозга и глаз
• <b>ALA (альфа-линоленовая кислота)</b> — растительная форма

💪 <b>Польза для здоровья:</b>

• <b>Сердце:</b> Снижают риск сердечно-сосудистых заболеваний
• <b>Мозг:</b> Улучшают память и когнитивные функции
• <b>Воспаление:</b> Обладают противовоспалительным эффектом
• <b>Глаза:</b> Поддерживают здоровье сетчатки
• <b>Настроение:</b> Могут помочь при депрессии

🍽️ <b>Лучшие источники:</b>

<b>Животные источники (EPA + DHA):</b>
• Жирная морская рыба: лосось, скумбрия, сардины, анчоусы
• Рыбий жир
• Морепродукты

<b>Растительные источники (ALA):</b>
• Льняное семя и масло
• Чиа семена
• Грецкие орехи
• Конопляные семена

📊 <b>Рекомендуемые дозы:</b>
• Здоровые взрослые: 250-500 мг EPA+DHA в день
• При заболеваниях: 1-4 г в день (по назначению врача)
• Рыба: 2-3 порции в неделю

⚖️ <b>Выбор добавок:</b>
Если не едите рыбу регулярно, рассмотрите качественные добавки Омега-3. Ищите продукты с высоким содержанием EPA и DHA, прошедшие очистку от тяжелых металлов.
                """, "Команда NutriBot", "American Heart Association, NIH", "2024-01-10"),

                # Основы питания
                (2, "Баланс макронутриентов: белки, жиры, углеводы", """
<b>Макронутриенты</b> — это основные питательные вещества, которые нужны нашему организму в больших количествах для получения энергии и нормального функционирования.

🥩 <b>БЕЛКИ (Протеины)</b>

<b>Функции:</b>
• Строительный материал для мышц, костей, кожи
• Синтез ферментов и гормонов
• Поддержание иммунитета
• Источник энергии (4 ккал/г)

<b>Норма:</b> 0.8-2.2 г на кг веса тела
<b>Источники:</b> мясо, рыба, яйца, молочные продукты, бобовые, орехи

🥑 <b>ЖИРЫ (Липиды)</b>

<b>Функции:</b>
• Источник энергии (9 ккал/г)
• Усвоение жирорастворимых витаминов (A, D, E, K)
• Строительство клеточных мембран
• Синтез гормонов

<b>Норма:</b> 20-35% от общей калорийности
<b>Источники:</b> растительные масла, орехи, авокадо, рыба, семена

🍞 <b>УГЛЕВОДЫ (Карбогидраты)</b>

<b>Функции:</b>
• Основной источник энергии (4 ккал/г)
• Питание мозга и нервной системы
• Поддержание уровня глюкозы в крови

<b>Норма:</b> 45-65% от общей калорийности
<b>Источники:</b> крупы, овощи, фрукты, хлеб, макароны

⚖️ <b>Оптимальное соотношение макронутриентов:</b>

<b>Для среднестатистического человека:</b>
• Белки: 15-25%
• Жиры: 20-35% 
• Углеводы: 45-65%

<b>Для похудения:</b>
• Белки: 25-30%
• Жиры: 25-30%
• Углеводы: 40-50%

<b>Для набора мышечной массы:</b>
• Белки: 25-35%
• Жиры: 20-25%
• Углеводы: 45-55%

💡 <b>Практические советы:</b>

1. <b>Включайте все три макронутриента в каждый прием пищи</b>
2. <b>Выбирайте качественные источники:</b> цельные продукты вместо переработанных
3. <b>Адаптируйте под свои цели:</b> больше белка для мышц, больше углеводов для энергии
4. <b>Слушайте свой организм</b> и корректируйте рацион при необходимости

Помните: идеальное соотношение индивидуально и может меняться в зависимости от ваших целей, активности и особенностей организма.
                """, "Команда NutriBot", "Academy of Nutrition and Dietetics", "2024-01-08"),

                # Советы по похудению
                (3, "Эффективные стратегии снижения веса", """
<b>Похудение</b> — это не только изменение внешнего вида, но и забота о здоровье. Рассмотрим научно обоснованные методы безопасного снижения веса.

⚖️ <b>Основные принципы похудения:</b>

1. <b>Дефицит калорий</b> — тратить больше, чем потребляете
2. <b>Постепенность</b> — 0.5-1 кг в неделю
3. <b>Сбалансированность</b> — не исключать целые группы продуктов
4. <b>Устойчивость</b> — изменения должны стать образом жизни

🍽️ <b>Питание для похудения:</b>

<b>Что ДЕЛАТЬ:</b>
• Увеличить потребление белка (до 30% калорий)
• Есть больше овощей и клетчатки
• Контролировать размер порций
• Пить достаточно воды (30-35 мл на кг веса)
• Планировать приемы пищи заранее

<b>Что НЕ делать:</b>
• Голодать или кардинально ограничивать калории
• Исключать жиры полностью
• Злоупотреблять "диетическими" продуктами
• Переедать даже здоровой пищи

🏃 <b>Физическая активность:</b>

<b>Кардио-тренировки:</b>
• 150-300 минут умеренной активности в неделю
• Ходьба, бег, плавание, велосипед
• Помогают создать дефицит калорий

<b>Силовые тренировки:</b>
• 2-3 раза в неделю
• Сохраняют мышечную массу
• Ускоряют метаболизм

🧠 <b>Психологические аспекты:</b>

• <b>Мотивация:</b> Определите четкие, реалистичные цели
• <b>Привычки:</b> Меняйте постепенно, по одной привычке
• <b>Поддержка:</b> Найдите единомышленников или специалиста
• <b>Терпение:</b> Результаты приходят не сразу

📊 <b>Практические советы:</b>

1. <b>Ведите дневник питания</b> — записывайте всё, что едите
2. <b>Готовьте дома</b> — контролируйте состав и калорийность
3. <b>Ешьте медленно</b> — мозг получает сигнал о насыщении через 20 минут
4. <b>Высыпайтесь</b> — недосып влияет на гормоны голода
5. <b>Управляйте стрессом</b> — кортизол способствует накоплению жира

⚠️ <b>Когда обратиться к специалисту:</b>
• ИМТ > 30 или серьезные проблемы со здоровьем
• Неудачные попытки похудения в прошлом
• Расстройства пищевого поведения
• Необходимость сбросить более 20% веса

Помните: лучшая диета — та, которой вы можете придерживаться всю жизнь!
                """, "Команда NutriBot", "CDC, Mayo Clinic", "2024-01-05"),

                # Психология питания
                (4, "Эмоциональное переедание: как с ним справиться", """
<b>Эмоциональное переедание</b> — это употребление пищи не из-за физического голода, а для управления эмоциями или стрессом.

😔 <b>Что такое эмоциональное переедание?</b>

Это когда мы едим в ответ на:
• Стресс и тревогу
• Скуку или одиночество
• Грусть или депрессию
• Гнев или фрустрацию
• Усталость
• Социальное давление

🔍 <b>Как распознать эмоциональный голод?</b>

<b>Физический голод:</b>
• Развивается постепенно
• Можно подождать
• Удовлетворяется любой едой
• Останавливается при насыщении
• Не вызывает чувства вины

<b>Эмоциональный голод:</b>
• Возникает внезапно
• Требует немедленного удовлетворения
• Хочется определенной "комфортной" еды
• Трудно остановиться
• Вызывает чувство вины и стыда

🧠 <b>Причины эмоционального переедания:</b>

1. <b>Стресс</b> — повышает уровень кортизола, который стимулирует аппетит
2. <b>Детские привычки</b> — еда как утешение или награда
3. <b>Социальные факторы</b> — еда как способ общения
4. <b>Скука</b> — еда как развлечение
5. <b>Привычка</b> — автоматическое поведение

💪 <b>Стратегии преодоления:</b>

<b>1. Осознанность:</b>
• Ведите дневник эмоций и еды
• Задавайтесь вопросом: "Я действительно голоден?"
• Оценивайте голод по шкале от 1 до 10

<b>2. Альтернативные способы:</b>
• При стрессе: медитация, глубокое дыхание
• При скуке: хобби, прогулка, чтение
• При грусти: общение с друзьями, творчество
• При усталости: отдых, сон

<b>3. Изменение среды:</b>
• Уберите триггерные продукты из поля зрения
• Держите здоровые закуски под рукой
• Создайте "зоны без еды" (кровать, рабочий стол)

<b>4. Техники самопомощи:</b>
• <b>Пауза:</b> Подождите 10 минут перед едой
• <b>HALT:</b> Проверьте — не голодны ли вы, не злы, не одиноки, не устали
• <b>Дыхательные упражнения</b> для снижения стресса
• <b>Прогрессивная мышечная релаксация</b>

🍎 <b>Практические советы:</b>

• <b>Регулярное питание</b> — не пропускайте приемы пищи
• <b>Достаточный сон</b> — 7-9 часов в сутки
• <b>Физическая активность</b> — природный антидепрессант
• <b>Социальная поддержка</b> — делитесь переживаниями с близкими

🆘 <b>Когда обратиться за помощью:</b>
• Переедание происходит несколько раз в неделю
• Чувство потери контроля над едой
• Значительное влияние на вес и здоровье
• Депрессия или тревожные расстройства

Помните: изменение пищевого поведения — это процесс. Будьте терпеливы к себе и не стесняйтесь обращаться за профессиональной помощью.
                """, "Команда NutriBot", "American Psychological Association", "2024-01-03"),

                # Интервальное голодание
                (5, "Интервальное голодание: руководство для начинающих", """
<b>Интервальное голодание (ИГ)</b> — это режим питания, при котором чередуются периоды приема пищи и голодания.

⏰ <b>Популярные методы ИГ:</b>

<b>16:8 (метод Леангейнза):</b>
• 16 часов голодания, 8 часов для еды
• Например: ужин в 20:00, следующий прием пищи в 12:00
• Самый популярный и легкий для начинающих

<b>5:2 (диета Фаста):</b>
• 5 дней обычного питания, 2 дня ограничения (500-600 ккал)
• Дни голодания не должны идти подряд

<b>24-часовое голодание:</b>
• Полный день без еды 1-2 раза в неделю
• Например: от ужина до ужина следующего дня

<b>Альтернативное голодание:</b>
• Чередование дней обычного питания и голодания
• Самый сложный метод

🔬 <b>Потенциальная польза ИГ:</b>

• <b>Снижение веса</b> — за счет ограничения калорий
• <b>Улучшение метаболизма</b> — повышение чувствительности к инсулину
• <b>Клеточное обновление</b> — активация аутофагии
• <b>Здоровье мозга</b> — улучшение когнитивных функций
• <b>Долголетие</b> — потенциальное увеличение продолжительности жизни

💧 <b>Что можно во время голодания:</b>

✅ <b>Разрешено:</b>
• Вода (главное!)
• Черный кофе без добавок
• Зеленый, черный, травяной чай
• Минеральная вода

❌ <b>Запрещено:</b>
• Любые напитки с калориями
• Жевательная резинка с сахаром
• Витамины в сиропе
• Искусственные подсластители (спорно)

🚀 <b>Как начать ИГ:</b>

<b>Неделя 1-2:</b> 12-часовое голодание
<b>Неделя 3-4:</b> 14-часовое голодание  
<b>Неделя 5+:</b> 16-часовое голодание

<b>Советы для начинающих:</b>
• Начинайте постепенно
• Пейте много воды
• Занимайтесь в периоды голодания легкой активностью
• Не переедайте в окна приема пищи

⚠️ <b>Противопоказания и предосторожности:</b>

<b>ИГ НЕ подходит при:</b>
• Диабете 1 типа
• Расстройствах пищевого поведения
• Беременности и кормлении
• Детском и подростковом возрасте
• Серьезных хронических заболеваниях

<b>Возможные побочные эффекты:</b>
• Голод и раздражительность (первые недели)
• Головные боли
• Усталость
• Проблемы с концентрацией

📊 <b>Практические рекомендации:</b>

• <b>Качество пищи важнее:</b> ИГ не оправдывает нездоровую еду
• <b>Слушайте организм:</b> если плохо себя чувствуете — остановитесь
• <b>Социальная жизнь:</b> адаптируйте окна приема пищи под свой график
• <b>Тренировки:</b> можно заниматься натощак, но осторожно

🏥 <b>Когда обратиться к врачу:</b>
Обязательно проконсультируйтесь с врачом перед началом ИГ, особенно если у вас есть хронические заболевания или вы принимаете лекарства.

Помните: ИГ — это инструмент, а не панацея. Главное — общее качество питания и образ жизни!
                """, "Команда NutriBot", "New England Journal of Medicine, Harvard Health", "2024-01-01"),

                # Другое
                (6, "Гидратация: сколько воды нужно пить в день", """
<b>Вода</b> — основа жизни. Наш организм на 60% состоит из воды, и правильная гидратация критически важна для здоровья.

💧 <b>Функции воды в организме:</b>

• <b>Транспорт:</b> Доставка питательных веществ к клеткам
• <b>Детоксикация:</b> Выведение токсинов через почки
• <b>Терморегуляция:</b> Поддержание температуры тела
• <b>Смазка:</b> Смазывание суставов и органов
• <b>Пищеварение:</b> Помощь в расщеплении пищи
• <b>Кровообращение:</b> Поддержание объема крови

📊 <b>Сколько воды нужно пить?</b>

<b>Общие рекомендации:</b>
• Мужчины: 3.7 л (15 стаканов) всех жидкостей в день
• Женщины: 2.7 л (11 стаканов) всех жидкостей в день
• Из них чистой воды: 8-10 стаканов (2-2.5 л)

<b>Индивидуальная формула:</b>
30-35 мл на 1 кг массы тела

<b>Пример:</b> Вес 70 кг = 70 × 30 = 2100 мл (2.1 л)

💪 <b>Когда нужно пить больше:</b>

• <b>Физическая активность:</b> +500-750 мл на час тренировки
• <b>Жаркая погода:</b> +500-1000 мл в день
• <b>Болезнь:</b> при лихорадке, рвоте, диарее
• <b>Беременность и кормление:</b> +300-700 мл в день
• <b>Большая высота:</b> над 2500 м
• <b>Алкоголь и кофеин:</b> дополнительный стакан воды на каждую порцию

🚰 <b>Источники жидкости:</b>

<b>Лучшие источники:</b>
• Чистая вода (основной источник)
• Травяные чаи без сахара
• Вода с лимоном или огурцом

<b>Хорошие источники:</b>
• Зеленый и черный чай
• Кофе (в умеренных количествах)
• Молоко и растительные аналоги

<b>Дополнительные источники:</b>
• Супы и бульоны
• Фрукты (арбуз, апельсины, виноград)
• Овощи (огурцы, помидоры, салат)

⚠️ <b>Признаки обезвоживания:</b>

<b>Легкое обезвоживание:</b>
• Жажда
• Темная моча
• Усталость
• Головная боль

<b>Умеренное обезвоживание:</b>
• Сухость во рту и на языке
• Снижение мочеиспускания
• Мышечные спазмы
• Тошнота

<b>Серьезное обезвоживание:</b>
• Крайняя жажда
• Отсутствие мочеиспускания
• Обморок
• Учащенное сердцебиение

💡 <b>Практические советы:</b>

1. <b>Начинайте день со стакана воды</b>
2. <b>Носите бутылку воды с собой</b>
3. <b>Пейте перед каждым приемом пищи</b>
4. <b>Установите напоминания на телефоне</b>
5. <b>Ароматизируйте воду естественными добавками</b>
6. <b>Следите за цветом мочи</b> — должна быть светло-желтой

⚖️ <b>Можно ли пить слишком много воды?</b>

Да, гипонатриемия (водное отравление) возможна, но редка:
• Более 1 литра в час в течение нескольких часов
• Симптомы: тошнота, головная боль, confusion

<b>Золотое правило:</b> Пейте, когда хочется, и немного больше во время активности или жары.

Помните: жажда — уже признак начального обезвоживания. Не ждите, пока захочется пить!
                """, "Команда NutriBot", "Mayo Clinic, National Academies", "2023-12-28")
            ]

            for article in sample_articles:
                conn.execute('''
                    INSERT INTO articles (topic_id, title, content, author, sources, publication_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', article)

            conn.commit()
            logger.info("Добавлены тестовые статьи")

    except Exception as e:
        logger.error(f"Ошибка при создании таблиц статей: {e}")
    finally:
        conn.close()

def get_article_topics():
    """Получает список всех активных тем статей."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM article_topics 
            WHERE is_active = 1 
            ORDER BY sort_order, name
        ''')
        topics = [dict(row) for row in cursor.fetchall()]
        return topics
    except Exception as e:
        logger.error(f"Ошибка при получении тем статей: {e}")
        return []
    finally:
        conn.close()

def get_articles_by_topic(topic_id):
    """Получает список статей по теме."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM articles 
            WHERE topic_id = ? AND is_published = 1 
            ORDER BY publication_date DESC, title
        ''', (topic_id,))
        articles = [dict(row) for row in cursor.fetchall()]
        return articles
    except Exception as e:
        logger.error(f"Ошибка при получении статей по теме {topic_id}: {e}")
        return []
    finally:
        conn.close()

def get_article_by_id(article_id):
    """Получает статью по ID."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM articles 
            WHERE id = ? AND is_published = 1
        ''', (article_id,))
        row = cursor.fetchone()

        if row:
            # Увеличиваем счетчик просмотров
            conn.execute('''
                UPDATE articles 
                SET views_count = views_count + 1 
                WHERE id = ?
            ''', (article_id,))
            conn.commit()

        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении статьи по ID {article_id}: {e}")
        return None
    finally:
        conn.close()


def init_weight_reports_table():
    """Создает таблицу для записей веса."""
    conn = get_db_connection()

    try:
        # Создаем таблицу записей веса
        conn.execute('''
            CREATE TABLE IF NOT EXISTS weight_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                weight REAL NOT NULL,
                notes TEXT,
                entry_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, date)
            )
        ''')

        # Создаем индекс для оптимизации запросов
        conn.execute('CREATE INDEX IF NOT EXISTS idx_weight_records_user_date ON weight_records (user_id, date)')

        conn.commit()
        logger.info("Таблица записей веса создана")

    except Exception as e:
        logger.error(f"Ошибка при создании таблицы записей веса: {e}")
    finally:
        conn.close()

def add_weight_record(user_id, weight, notes=None):
    """Добавляет запись о весе."""
    conn = get_db_connection()
    try:
        today = datetime.now().strftime("%Y-%m-%d")

        conn.execute('''
            INSERT OR REPLACE INTO weight_records (user_id, date, weight, notes)
            VALUES (?, ?, ?, ?)
        ''', (user_id, today, weight, notes))

        conn.commit()
        logger.info(f"Добавлена запись веса для пользователя {user_id}: {weight} кг")
        return True

    except Exception as e:
        logger.error(f"Ошибка при добавлении записи веса: {e}")
        return False
    finally:
        conn.close()

def get_weight_history(user_id, days=30):
    """Получает историю записей веса за указанное количество дней."""
    conn = get_db_connection()
    try:
        # Вычисляем дату начала периода
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor = conn.execute('''
            SELECT date, weight, notes, entry_time
            FROM weight_records 
            WHERE user_id = ? AND date >= ?
            ORDER BY date DESC
        ''', (user_id, start_date))

        records = [dict(row) for row in cursor.fetchall()]
        return records

    except Exception as e:
        logger.error(f"Ошибка при получении истории веса: {e}")
        return []
    finally:
        conn.close()

def get_latest_weight_record(user_id):
    """Получает последнюю запись веса пользователя."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT date, weight, notes, entry_time
            FROM weight_records 
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (user_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    except Exception as e:
        logger.error(f"Ошибка при получении последней записи веса: {e}")
        return None
    finally:
        conn.close()

def update_weight_record(user_id, date, weight, notes=None):
    """Обновляет существующую запись веса."""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE weight_records 
            SET weight = ?, notes = ?, entry_time = CURRENT_TIMESTAMP
            WHERE user_id = ? AND date = ?
        ''', (weight, notes, user_id, date))

        conn.commit()
        logger.info(f"Обновлена запись веса для пользователя {user_id} на {date}: {weight} кг")
        return True

    except Exception as e:
        logger.error(f"Ошибка при обновлении записи веса: {e}")
        return False
    finally:
        conn.close()

def update_user_weight(user_id, new_weight):
    """Обновляет текущий вес в профиле пользователя."""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE users 
            SET weight = ?
            WHERE id = ?
        ''', (new_weight, user_id))

        conn.commit()
        logger.info(f"Обновлен вес в профиле пользователя {user_id}: {new_weight} кг")
        return True

    except Exception as e:
        logger.error(f"Ошибка при обновлении веса в профиле: {e}")
        return False
    finally:
        conn.close()


def init_shopping_cart_table():
    """Создает таблицу для продуктовой корзины."""
    conn = get_db_connection()

    try:
        # Создаем таблицу корзины
        conn.execute('''
            CREATE TABLE IF NOT EXISTS shopping_cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT DEFAULT 'г',
                period TEXT,
                is_purchased BOOLEAN DEFAULT 0,
                source TEXT DEFAULT 'manual',
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Создаем индекс для оптимизации
        conn.execute('CREATE INDEX IF NOT EXISTS idx_shopping_cart_user ON shopping_cart (user_id)')

        conn.commit()
        logger.info("Таблица корзины создана")

    except Exception as e:
        logger.error(f"Ошибка при создании таблицы корзины: {e}")
    finally:
        conn.close()

def get_shopping_cart_items(user_id):
    """Получает все продукты из корзины пользователя."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT id, product_name, quantity, unit, period, is_purchased, source, created_date
            FROM shopping_cart 
            WHERE user_id = ?
            ORDER BY is_purchased ASC, product_name ASC
        ''', (user_id,))

        items = [dict(row) for row in cursor.fetchall()]
        return items

    except Exception as e:
        logger.error(f"Ошибка при получении корзины: {e}")
        return []
    finally:
        conn.close()

def add_shopping_cart_item(user_id, product_name, quantity, unit='г', period='manual', source='manual'):
    """Добавляет продукт в корзину."""
    conn = get_db_connection()
    try:
        # Проверяем, есть ли уже такой продукт
        cursor = conn.execute('''
            SELECT id, quantity FROM shopping_cart 
            WHERE user_id = ? AND product_name = ? AND unit = ?
        ''', (user_id, product_name, unit))

        existing = cursor.fetchone()

        if existing:
            # Обновляем количество
            new_quantity = existing['quantity'] + quantity
            conn.execute('''
                UPDATE shopping_cart 
                SET quantity = ?, period = ?, source = ?
                WHERE id = ?
            ''', (new_quantity, period, source, existing['id']))
        else:
            # Добавляем новый продукт
            conn.execute('''
                INSERT INTO shopping_cart (user_id, product_name, quantity, unit, period, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, product_name, quantity, unit, period, source))

        conn.commit()
        logger.info(f"Добавлен продукт в корзину: {product_name} - {quantity} {unit}")
        return True

    except Exception as e:
        logger.error(f"Ошибка при добавлении в корзину: {e}")
        return False
    finally:
        conn.close()

def remove_shopping_cart_item(user_id, item_id):
    """Удаляет продукт из корзины."""
    conn = get_db_connection()
    try:
        conn.execute('''
            DELETE FROM shopping_cart 
            WHERE user_id = ? AND id = ?
        ''', (user_id, item_id))

        conn.commit()
        return conn.total_changes > 0

    except Exception as e:
        logger.error(f"Ошибка при удалении из корзины: {e}")
        return False
    finally:
        conn.close()

def update_shopping_cart_item(user_id, item_id, quantity, unit):
    """Обновляет количество продукта в корзине."""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE shopping_cart 
            SET quantity = ?, unit = ?
            WHERE user_id = ? AND id = ?
        ''', (quantity, unit, user_id, item_id))

        conn.commit()
        return conn.total_changes > 0

    except Exception as e:
        logger.error(f"Ошибка при обновлении корзины: {e}")
        return False
    finally:
        conn.close()

def toggle_item_purchased(user_id, item_id):
    """Переключает статус покупки продукта."""
    conn = get_db_connection()
    try:
        # Получаем текущий статус
        cursor = conn.execute('''
            SELECT is_purchased FROM shopping_cart 
            WHERE user_id = ? AND id = ?
        ''', (user_id, item_id))

        row = cursor.fetchone()
        if not row:
            return False

        new_status = not row['is_purchased']

        conn.execute('''
            UPDATE shopping_cart 
            SET is_purchased = ?
            WHERE user_id = ? AND id = ?
        ''', (new_status, user_id, item_id))

        conn.commit()
        return conn.total_changes > 0

    except Exception as e:
        logger.error(f"Ошибка при изменении статуса покупки: {e}")
        return False
    finally:
        conn.close()

def clear_shopping_cart(user_id):
    """Очищает всю корзину пользователя."""
    conn = get_db_connection()
    try:
        conn.execute('''
            DELETE FROM shopping_cart 
            WHERE user_id = ?
        ''', (user_id,))

        conn.commit()
        logger.info(f"Корзина пользователя {user_id} очищена")
        return True

    except Exception as e:
        logger.error(f"Ошибка при очистке корзины: {e}")
        return False
    finally:
        conn.close()

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

        # Таблица рецептов
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
                    photo_path TEXT,
                    creation_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_favorite BOOLEAN DEFAULT 0,
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



        # строки для создания индексов
        conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recipes_user_name 
                ON recipes(user_id, name COLLATE NOCASE)
                """)

        conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recipes_user_ingredients 
                ON recipes(user_id, ingredients COLLATE NOCASE)
                """)

        conn.execute('CREATE INDEX IF NOT EXISTS idx_food_entries_user_date ON food_entries (user_id, date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_water_entries_user_date ON water_entries (user_id, date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_user ON recipes (user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_meal_plan_user_date ON meal_plan (user_id, date)')



        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]  # Теперь правильно
        logger.info(f"Структура таблицы users: {columns}")

        cursor = conn.execute("PRAGMA table_info(recipes)")
        columns = [row[1] for row in cursor.fetchall()]

        if "photo_path" not in columns:
            conn.execute("ALTER TABLE recipes ADD COLUMN photo_path TEXT")
            conn.commit()
            logger.info("Столбец photo_path успешно добавлен в таблицу recipes.")

        conn.commit()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
    finally:
        conn.close()

    init_nutritionists_table()
    init_articles_tables()
    init_weight_reports_table()
    init_shopping_cart_table()

# Инициализируем базу данных при импорте
if not os.path.exists(DB_PATH):
    init_db()
else:
    # Проверим структуру базы данных и добавим недостающие таблицы
    init_db()


def execute_query(query, params=(), fetch_one=False, fetch_all=False):
    """
    Выполняет SQL-запрос и возвращает результаты (если требуется).

    Args:
        query (str): SQL-запрос.
        params (tuple): Параметры для подстановки.
        fetch_one (bool): Возвращать одну строку.
        fetch_all (bool): Возвращать все строки.

    Returns:
        list or dict or None: Результаты запроса или None при ошибке.
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

        if fetch_one:
            return cursor.fetchone()

        if fetch_all:
            return cursor.fetchall()

        return None  # Если не требуется вернуть данные

    except sqlite3.Error as e:
        logger.error(f"Ошибка выполнения запроса: {e}")
        return None

    finally:
        conn.close()
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

    logging.info(f"Вызов get_user с ID: {user_id}")
    query = "SELECT * FROM users WHERE id = ?"
    result = execute_query(query, (user_id,), fetchone=True)
    logging.info(f"Результат get_user: {result}")
    return result


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
#Сохраняет новый рецепт

def save_recipe(user_id, name, ingredients, instructions, calories, protein, fat, carbs, photo_path=None):
    conn = get_db_connection()
    try:
        conn.execute(
            '''INSERT INTO recipes 
            (user_id, name, ingredients, instructions, calories, protein, fat, carbs, photo_path) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, name, ingredients, instructions, calories, protein, fat, carbs, photo_path)
        )
        conn.commit()
        #return True
        recipe_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        logger.info(f"Сохранен новый рецепт {name} для пользователя {user_id}")
        return recipe_id
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
#Добавляет рецепт в план питания
def add_to_meal_plan(user_id, recipe_id, meal_type, date):
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

#Получает план питания на день
def get_daily_meal_plan(user_id, date):
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


def search_recipes(user_id, search_query):
    """Поиск рецептов по названию и ингредиентам"""
    conn = get_db_connection()
    try:
        # Подготавливаем поисковый запрос
        search_query = f"%{search_query.strip().lower()}%"

        query = """
        SELECT * FROM recipes 
        WHERE user_id = ? 
        AND (LOWER(name) LIKE ? OR LOWER(ingredients) LIKE ?)
        ORDER BY 
            CASE 
                WHEN LOWER(name) LIKE ? THEN 1  
                ELSE 2 
            END,
            is_favorite DESC,
            creation_date DESC
        LIMIT 20
        """

        recipes = conn.execute(query, (user_id, search_query, search_query, search_query)).fetchall()
        logger.info(f"Found {len(recipes)} recipes for query: {search_query}")
        return [dict(recipe) for recipe in recipes]
    except Exception as e:
        logger.error(f"Ошибка при поиске рецептов: {e}", exc_info=True)
        return []
    finally:
        conn.close()



def close_db():
    """Закрывает соединение с базой данных."""
    pass  # Здесь ничего не нужно делать, т.к. мы создаем и закрываем соединение в каждой функции