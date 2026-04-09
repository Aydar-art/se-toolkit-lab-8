# 🚀 Quick Start Guide - RPG To-Do Bot

## Get Started in 5 Minutes

### Step 1: Get Your Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions:
   - Choose a name for your bot (e.g., "My RPG Todo Bot")
   - Choose a username (must end in `bot`, e.g., `my_rpg_todo_bot`)
4. Copy the token BotFather gives you

### Step 2: Configure the Bot
```bash
# Navigate to the project
cd /root/se-toolkit-lab-8/myproj/rpg_todo_bot

# Edit the .env file
nano .env
```

Replace `your_bot_token_here` with your actual token:
```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
DB_NAME=rpg_bot.db
```

Save and exit (Ctrl+X, Y, Enter)

### Step 3: Install Dependencies (if not done)
```bash
cd /root/se-toolkit-lab-8/myproj/rpg_todo_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Verify Everything Works
```bash
python test_verify.py
```

You should see:
```
✅ ALL TESTS PASSED!
The bot is ready to run!
```

### Step 5: Start the Bot!
```bash
python bot.py
```

You'll see:
```
Starting RPG To-Do Bot...
Database initialized
Bot started and polling...
```

### Step 6: Test in Telegram
1. Open Telegram
2. Search for your bot by username
3. Send `/start`
4. You should get a welcome message!

## Available Commands

Once the bot is running, try these commands:

| Command | What it does |
|---------|-------------|
| `/start` | Register as a player |
| `/help` | Show all commands |
| `/profile` | View your stats |
| `/add_task` | Add a new task |
| `/tasks` | See your tasks |
| `/complete` | Mark a task as done |
| `/fight @username` | Challenge someone |

## Example Usage

### Adding Your First Task
```
You: /add_task
Bot: 📝 Введите название задачи:
You: Complete homework
Bot: ⚡ Введите количество ОД (1-8):
You: 3
Bot: ✅ Задача 'Complete homework' добавлена! (ОД: 3)
```

### Completing a Task
```
You: /complete
Bot: Выберите задачу для выполнения (введите номер):
     1. Complete homework (ОД: 3)
You: 1
Bot: ✅ Задача 'Complete homework' выполнена!
     +30 XP | +3 ОД сегодня
```

### Checking Your Profile
```
You: /profile
Bot: 🎭 Профиль игрока
     👤 Имя: YourName
     🏆 Уровень: 1
     ⭐ XP: 30/100
     ❤️ HP: 25/25
     ⚡ ОД сегодня: 3
```

## Stopping the Bot

Press `Ctrl+C` in the terminal

## Restarting the Bot

```bash
cd /root/se-toolkit-lab-8/myproj/rpg_todo_bot
source .venv/bin/activate
python bot.py
```

## Troubleshooting

### "BOT_TOKEN is not set"
- Make sure your `.env` file has the correct token
- No spaces around the `=` sign

### "Module not found"
- Make sure you activated the virtual environment:
  ```bash
  source .venv/bin/activate
  ```

### "Database error"
- Delete the database and restart:
  ```bash
  rm rpg_bot.db
  python bot.py
  ```

### Bot doesn't respond
- Check if it's running (you should see no errors in terminal)
- Make sure you're using the correct bot username
- Try sending `/start` again

## What's Next?

After testing:
1. Add real tasks from your daily life
2. Track your progress
3. Challenge friends to PvP duels!
4. Level up and become an RPG master!

## Running in Background (Optional)

To keep the bot running after closing terminal:

```bash
# Using nohup
nohup python bot.py > bot.log 2>&1 &

# Check if it's running
ps aux | grep bot.py

# View logs
tail -f bot.log

# Stop the bot
kill %1
```

---

**Need help?** Check `README.md` for full documentation or `IMPLEMENTATION_SUMMARY.md` for architecture details.
