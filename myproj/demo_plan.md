📁 Этап 1: Структура проекта и установка

Начните с создания правильной архитектуры проекта. Это обеспечит его масштабируемость и простоту поддержки.

1.1. Создайте следующую структуру каталогов и файлов:

text
rpg_todo_bot/
│
├── bot.py                 # Точка входа в приложение
├── config.py              # Файл для хранения конфигураций (токен и т.д.)
├── database.py            # Модуль для всех операций с базой данных SQLite
├── requirements.txt      # Список зависимостей Python
├── .env                   # Файл для переменных окружения (не загружается в Git)
│
├── handlers/              # Пакет с обработчиками команд
│   ├── __init__.py
│   ├── start.py           # Обработчики команд /start и /help
│   ├── profile.py         # Обработчики команд /profile
│   ├── tasks.py           # Обработчики для работы с задачами (FSM)
│   └── fight.py           # Обработчики для вызовов на дуэль и управления боем
│
├── keyboards/             # Пакет с клавиатурами
│   ├── __init__.py
│   ├── inline_keyboards.py  # Функции для создания inline-клавиатур (для боев)
│   └── reply_keyboards.py   # Функции для reply-клавиатур (опционально)
│
└── states/                # Пакет с классами состояний (FSM)
    ├── __init__.py
    └── task_states.py     # Классы состояний для процесса добавления задачи
1.2. Установите необходимые библиотеки:
Откройте терминал в корневой папке проекта и активируйте виртуальное окружение. Затем выполните команду для установки зависимостей, которые вы пропишете в файле requirements.txt:

bash
pip install aiogram python-dotenv aiosqlite
После этого создайте файл requirements.txt со следующим содержимым, чтобы в будущем можно было легко воссоздать окружение:

text
aiogram
python-dotenv
aiosqlite
Сохранить список зависимостей в файл можно командой:

bash
pip freeze > requirements.txt
1.3. Настройте конфигурацию:

В файле .env пропишите ваш токен, полученный от @BotFather:

text
BOT_TOKEN=ваш_токен_здесь
В файле config.py напишите код для загрузки токена из переменных окружения:

python
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
🗄️ Этап 2: База данных (SQLite)

В демо-версии уже должна быть база данных, чтобы прогресс игроков сохранялся при перезапуске бота. Для этого используется aiosqlite для асинхронной работы с SQLite.

2.1. Создайте файл database.py и определите в нем асинхронные функции для работы с БД:

python
import aiosqlite

DB_NAME = 'rpg_bot.db'

# --- Функции для инициализации таблиц ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица игроков
        await db.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 25,
                od_today INTEGER DEFAULT 0
            )
        ''')
        # Таблица задач
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                od INTEGER,
                date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY(user_id) REFERENCES players(user_id)
            )
        ''')
        await db.commit()

# --- Функции для работы с игроками ---
async def register_player(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute('INSERT INTO players (user_id) VALUES (?)', (user_id,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # Игрок уже существует

async def get_player(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT level, xp, hp, od_today FROM players WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return {"level": result[0], "xp": result[1], "hp": result[2], "od_today": result[3]}
            return None

# --- Функции для работы с задачами ---
async def add_task(user_id: int, name: str, od: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO tasks (user_id, name, od) VALUES (?, ?, ?)', (user_id, name, od))
        await db.commit()

async def get_tasks(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT id, name, od FROM tasks WHERE user_id = ? AND date = DATE("now")', (user_id,)) as cursor:
            return await cursor.fetchall()
2.2. Инициализация базы данных при старте бота:
В файле bot.py перед запуском поллинга вызовите функцию init_db():

python
from database import init_db
import asyncio

async def main():
    await init_db()
    # ... остальной код ...
🎮 Этап 3: Регистрация и профиль игрока

3.1. Создайте обработчики в handlers/start.py:

Импортируйте необходимые модули: from aiogram import Router, types, F, а также функции из database.py.
Создайте роутер: router = Router().
Напишите хендлер для команды /start, который будет проверять наличие пользователя в БД и при необходимости регистрировать его, вызывая register_player().
Напишите хендлер для команды /help, который будет выводить список доступных команд.
3.2. Создайте обработчики в handlers/profile.py:

Напишите хендлер для команды /profile, который будет получать данные игрока через get_player() и выводить их в красивом форматированном виде.
3.3. Подключите роутеры в bot.py:
В главном файле после создания диспетчера (dp = Dispatcher()) подключите роутеры:

python
from handlers import start, profile

dp.include_router(start.router)
dp.include_router(profile.router)
✍️ Этап 4: Управление задачами (FSM)

Для пошагового создания задачи используйте FSM (Finite State Machine).

4.1. Создайте класс состояний в states/task_states.py:

python
from aiogram.fsm.state import State, StatesGroup

class AddTaskStates(StatesGroup):
    waiting_for_name = State()  # Ожидание названия задачи
    waiting_for_od = State()    # Ожидание количества ОД
4.2. Создайте обработчики в handlers/tasks.py:

Импортируйте AddTaskStates, функции из database.py и FSMContext.
Напишите хендлер для команды /add_task, который переведет пользователя в состояние waiting_for_name и спросит название.
Напишите хендлер для состояния waiting_for_name, который сохранит название в FSMContext и переведет пользователя в состояние waiting_for_od, задав вопрос о количестве ОД.
Напишите хендлер для состояния waiting_for_od, который проверит корректность введенного числа (1-8), вызовет add_task() для сохранения в БД и завершит FSM, вызвав await state.clear().
Напишите хендлер для команды /tasks, который получит список задач через get_tasks() и выведет их пользователю.
Напишите хендлер для команды /complete, который позволит отметить задачу как выполненную, начислить XP и ОД, обновить уровень и HP игрока.
4.3. Не забудьте подключить роутер tasks.router в bot.py.

⚔️ Этап 5: Система PvP-дуэлей (Сердце проекта)

Это самый интересный, но и самый сложный этап.

5.1. Создайте inline-клавиатуры для боя в keyboards/inline_keyboards.py:
Вам понадобятся функции для создания клавиатур с действиями во время боя (Атака, Защита и т.д.), использующие InlineKeyboardBuilder. Callback-данные должны быть уникальными для каждого действия и хода.

5.2. Создайте класс состояний для боя в states/fight_states.py:

python
from aiogram.fsm.state import State, StatesGroup

class FightStates(StatesGroup):
    waiting_for_opponent = State()  # Ожидание согласия соперника
    in_fight = State()              # Активный бой
5.3. Реализуйте логику боя в handlers/fight.py:
Этот файл будет самым большим. Вот основные шаги:

Вызов на дуэль (/fight @username): Найдите ID соперника, проверьте, зарегистрирован ли он и есть ли у него ОД. Создайте временную "сессию боя" (можно хранить в словаре в памяти, т.к. она нужна только на время одного боя) и отправьте сопернику сообщение с inline-кнопками "Принять" и "Отказаться". Переведите себя и соперника в состояние waiting_for_opponent.
Принятие боя (callback_query): При нажатии на "Принять" инициализируйте бой. Определите очередность ходов (например, по количеству ОД или случайно). Создайте объекты "бойцов" с их HP и доступными ОД. Отправьте обоим игрокам сообщение о начале боя и первому игроку — inline-клавиатуру с действиями. Переведите обоих в состояние in_fight.
Ход боя (callback_query): Обрабатывайте нажатия на кнопки действий. Учитывайте потраченные ОД, наносите урон (например, 5 урона за атаку, 10 за "Сильный удар" за 3 ОД), применяйте защиту. Отправляйте обновленный статус боя обоим игрокам. Если у игрока кончились ОД, у него не должно быть выбора действий, кроме как пропустить ход.
Завершение боя: Когда HP одного из игроков достигнет 0 или ниже, объявите победителя. Начислите бонусный XP (например, +50 XP победителю, +10 XP проигравшему) и обновите данные в БД. Сбросьте сессию боя и состояние FSM.
🔄 Этап 6: Ежедневный сброс ОД

6.1. Реализуйте простую фоновую задачу:
Так как в демо-версии не требуется сложных планировщиков, можно создать асинхронную функцию, которая будет бесконечно проверять время и при наступлении полуночи (по UTC) сбрасывать od_today = 0 для всех игроков в базе данных. Запустите эту функцию одновременно с поллингом бота.

python
# В файле bot.py
async def daily_reset():
    while True:
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        await asyncio.sleep((midnight - now).seconds)
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE players SET od_today = 0")
            await db.commit()

async def main():
    asyncio.create_task(daily_reset())
    # ... остальной код ...
🚀 Этап 7: Запуск и тестирование

7.1. Запустите бота:
Убедитесь, что вы находитесь в виртуальном окружении и в корневой папке проекта. Выполните команду:

bash
python bot.py
7.2. Проведите тщательное тестирование всех функций:

Регистрация и профиль.
Добавление, просмотр и выполнение задач.
Вызов и проведение дуэли (с разными исходами и сценариями).
Проверка сброса ОД в полночь.
✅ Чек-лист для успешного запуска MVP

Пройдитесь по этому списку, чтобы убедиться, что ничего не упущено:

Архитектура: Создана структура проекта с папками handlers, states, keyboards.
База Данных: SQLite инициализирован с таблицами players и tasks.
Регистрация: Бот корректно регистрирует новых пользователей при /start.
Задачи (FSM): Работает пошаговое добавление задач, они сохраняются в БД. Команды /tasks и /complete работают.
Профиль: Команда /profile отображает актуальную статистику игрока.
Дуэли (PvP):

Бот обрабатывает команду /fight.
Соперник получает запрос на бой и может его принять/отклонить.
Во время боя работают inline-кнопки с действиями.
Система корректно отслеживает HP и ОД, объявляет победителя.
После боя победитель и проигравший получают бонусный XP.
Цикличность: Фоновая задача сбрасывает ОД в полночь.
Когда все пункты чек-листа будут выполнены и протестированы, у вас в руках будет полностью рабочая демо-версия вашего RPG To-Do бота. Это станет прочным фундаментом для дальнейшего добавления более сложных функций, таких как система навыков, полноценная автоматизация боев с inline-клавиатурами и многое другое. Удачи в реализации!
