# RPG To-Do Telegram Bot

A Telegram bot that turns real-life tasks into an RPG game with PvP duels, following modern software architecture patterns.

## Architecture

This project uses a **layered architecture** inspired by the se-toolkit-lab-8 backend:

```
rpg_todo_bot/
├── bot.py                 # Main entry point (like backend/main.py)
├── config.py              # Settings via pydantic-settings (like backend/settings.py)
├── database.py            # DB connection & session (like backend/database.py)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
│
├── models/                # SQLModel data models (like backend/models/)
│   └── __init__.py
│
├── db/                    # Data access layer (like backend/db/)
│   ├── __init__.py
│   ├── players.py
│   └── tasks.py
│
├── handlers/              # Aiogram routers (like backend/routers/)
│   ├── start.py           # /start, /help
│   ├── profile.py         # /profile
│   ├── tasks.py           # /add_task, /tasks, /complete
│   └── fight.py           # /fight, PvP duels
│
├── states/                # FSM states
│   └── __init__.py
│
└── keyboards/             # Keyboard builders
    └── __init__.py
```

## Features

### Core Features
- ✅ **Player Registration** - Automatic registration via `/start`
- ✅ **Profile System** - View stats with `/profile`
- ✅ **Task Management** - Add, view, and complete tasks with FSM
- ✅ **XP & Leveling** - Earn XP, level up, increase HP
- ✅ **Daily Action Points (OD)** - Earn OD by completing tasks
- ✅ **PvP Duels** - Challenge other players to turn-based battles
- ✅ **Daily Reset** - Automatic OD reset at midnight UTC

### Tech Stack
- **Python 3.9+**
- **aiogram 3.x** - Async Telegram Bot API
- **SQLModel** - Async ORM (SQLAlchemy + Pydantic)
- **aiosqlite** - Async SQLite driver
- **pydantic-settings** - Configuration management
- **asyncio** - Async task execution

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Bot

1. Get a bot token from [@BotFather](https://t.me/BotFather)
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and add your bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   DB_NAME=rpg_bot.db
   ```

### 3. Run the Bot

```bash
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Register and start playing |
| `/help` | Show available commands |
| `/profile` | View your player stats |
| `/add_task` | Add a new task (FSM dialog) |
| `/tasks` | View your tasks |
| `/complete` | Complete a task and earn XP |
| `/fight @username` | Challenge a player to PvP |
| `/accept` | Accept a fight challenge |
| `/surrender` | Surrender a fight |

## Game Mechanics

### Task System
1. Add tasks with `/add_task` (name + OD cost 1-8)
2. Complete tasks with `/complete`
3. Earn XP = OD × 10
4. Gain OD (Action Points) for the day

### Leveling
- XP needed for next level = Current Level × 100
- On level up: HP increases by 5, full HP restore

### PvP Duels
- Cost: 3 OD minimum to challenge/accept
- Actions:
  - **атака** (Attack): 5 damage, 1 OD
  - **защита** (Defense): Block 3 damage, 1 OD
  - **сильный удар** (Strong Hit): 10 damage, 3 OD
  - **пропустить** (Skip): Skip turn, 0 OD

### Daily Reset
- OD resets to 0 at midnight UTC automatically
- Background task handles this without manual intervention

## Architecture Patterns

This project follows patterns from the se-toolkit-lab-8 backend:

1. **Layered Architecture**: Models → DB Layer → Routers/Handlers
2. **Dependency Injection**: Async sessions via context managers
3. **Async-First Design**: All DB operations are async
4. **Configuration Management**: Pydantic-settings for env vars
5. **Router Pattern**: Separate handler modules for each feature
6. **Data Access Layer**: Clean separation of DB operations

## Development

### Project Structure Principles

- **models/**: SQLModel definitions (like backend/models/)
- **db/**: CRUD operations (like backend/db/)
- **handlers/**: Aiogram routers (like backend/routers/)
- **config.py**: Settings management (like backend/settings.py)

### Adding New Features

1. Add models to `models/`
2. Create DB operations in `db/`
3. Add handlers in `handlers/`
4. Register router in `bot.py`

## License

MIT

## Author

Built following modern async/await patterns and layered architecture best practices.
