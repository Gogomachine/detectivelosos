# 🐟🔎 Детектив Лосось — AML Journalist Agent

Автономный AI-агент, который ведёт Telegram-канал про борьбу с отмыванием денег (AML).

## Возможности

- **Мониторинг новостей** — парсит RSS-фиды и веб-страницы ведущих AML-ресурсов (FATF, OCCRP, FinCEN, Chainalysis и др.)
- **Генерация контента** — пишет посты через Claude API в стиле энергичного детектива
- **Утренние и вечерние дайджесты** — автоматические сводки новостей
- **Минимум 5 постов в день** — автоматически добирает контент интересными фактами
- **База данных статей** — все статьи и посты сохраняются в SQLite
- **Админ-бот** — управление через Telegram-команды

## Архитектура

```
src/
├── agent.py              # Главный оркестратор
├── parsers/
│   ├── rss_parser.py     # Парсер RSS-лент
│   ├── web_scraper.py    # Скрапер веб-страниц
│   └── news_filter.py    # Фильтрация по AML-релевантности
├── content/
│   └── generator.py      # Генерация контента через Claude API
├── database/
│   └── db.py             # SQLite база данных
├── telegram_bot/
│   └── bot.py            # Telegram публикация + админ-бот
└── scheduler/
    └── scheduler.py      # Планировщик задач
config/
├── __init__.py           # Переменные окружения
├── sources.py            # Источники новостей и ключевые слова
└── prompts.py            # Промпты для Claude API
```

## Установка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd detectivelosos

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -e .

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env — добавить токены
```

## Настройка

В файле `.env` указать:
- `TELEGRAM_BOT_TOKEN` — токен бота из @BotFather
- `TELEGRAM_CHANNEL_ID` — ID канала (например `@detectivelosos`)
- `ANTHROPIC_API_KEY` — API ключ Anthropic

## Запуск

```bash
# Полный запуск агента (24/7)
python main.py

# Одиночные действия
python main.py --parse          # Спарсить новости
python main.py --post           # Опубликовать пост
python main.py --digest         # Утренний дайджест
python main.py --digest-evening # Вечерний дайджест
python main.py --status         # Статус агента
```

## Расписание (UTC)

| Время | Действие |
|-------|----------|
| Каждые 30 мин | Парсинг новостей |
| 07:00 | Утренний дайджест |
| 10:00 | Пост из новостей |
| 13:00 | Пост из новостей |
| 16:00 | Пост из новостей |
| 18:00 | Проверка квоты + fun facts |
| 19:00 | Вечерний дайджест |

## Стек

- **Python 3.11+** + asyncio
- **Claude API** (Anthropic) — генерация контента
- **python-telegram-bot** — публикация в канал
- **feedparser + BeautifulSoup** — парсинг источников
- **APScheduler** — планировщик
- **aiosqlite** — асинхронная SQLite база
