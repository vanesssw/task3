# HLTV News Service

Асинхронный backend-сервис на FastAPI с REST API, WebSocket, фоновой задачей и интеграцией с NATS.

## Технологический стек

- **FastAPI** - веб-фреймворк
- **Playwright** - парсинг новостей с hltv.org
- **NATS.io** - брокер сообщений
- **SQLite** - база данных
- **SQLAlchemy** (async) - ORM
- **WebSockets** - real-time обновления
- **Docker** - контейнеризация

## Структура проекта

```
app/
    api/          # REST API endpoints
    ws/           # WebSocket manager
    services/     # Бизнес-логика
    tasks/        # Фоновые задачи
    db/           # База данных
    models/       # SQLAlchemy модели
    nats/         # NATS клиент
    main.py       # Точка входа
    config.py     # Конфигурация
```

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Запуск через Docker Compose (рекомендуется)

```bash
docker compose up --build
```

Сервис будет доступен на:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **NATS**: nats://localhost:4222
- **NATS Monitoring**: http://localhost:8222

### 3. Запуск локально (без Docker)

1. Запусти NATS сервер:
```bash
docker run -p 4222:4222 nats:2.10 -js
```

2. Установи переменные окружения (опционально):
```bash
export DATABASE_URL=sqlite+aiosqlite:///./news.db
export NATS_URL=nats://localhost:4222
export FETCH_INTERVAL_SECONDS=300
```

3. Запусти приложение:
```bash
uvicorn app.main:app --reload
```

## API Документация

### Swagger UI

Открой в браузере: **http://localhost:8000/docs**

Интерактивная документация со всеми эндпоинтами и возможностью тестирования.

### REST API Endpoints

#### Получить список новостей
```http
GET /items?limit=50&offset=0
```

#### Получить новость по ID
```http
GET /items/{id}
```

#### Создать новость
```http
POST /items
Content-Type: application/json

{
  "title": "News title",
  "url": "https://example.com/news",
  "country": "USA",
  "published_text": "2 hours ago",
  "comments": 5
}
```

#### Обновить новость
```http
PATCH /items/{id}
Content-Type: application/json

{
  "title": "Updated title",
  "comments": 10
}
```

#### Удалить новость
```http
DELETE /items/{id}
```

#### Принудительно запустить фоновую задачу
```http
POST /tasks/run
```

## WebSocket

### Подключение

Подключись к WebSocket endpoint:
```
ws://localhost:8000/ws/items
```

### События

Приложение отправляет следующие события:

- `item.created` - при создании новости
- `item.updated` - при обновлении новости
- `item.deleted` - при удалении новости
- `task.completed` - при завершении фоновой задачи
- `nats.forwarded` - при получении сообщения из NATS

### Пример использования в браузере

Открой консоль браузера (F12) и выполни:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/items');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onopen = () => {
    console.log('WebSocket connected');
};
```

### Использование с wscat

```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/items
```

### Использование с Postman

1. Открой Postman
2. Создай новый WebSocket запрос
3. Введи URL: `ws://localhost:8000/ws/items`
4. Нажми Connect
5. Создай/обнови/удали новость через REST API
6. Увидишь события в WebSocket

## NATS

### Конфигурация

- **Subject**: `items.updates`
- **URL**: `nats://localhost:4222` (по умолчанию)

### Публикация сообщений

При любых изменениях данных (create/update/delete) приложение автоматически публикует события в NATS.

### Подписка на события

Приложение автоматически подписывается на `items.updates` и:
- Логирует все входящие сообщения
- Обновляет локальную БД при получении событий `item.created`, `item.updated`, `item.deleted`
- Форвардит сообщения в WebSocket

### Пример публикации сообщения

Используй тестовый скрипт:

```bash
python test_nats_pub.py
```

Или через Python:

```python
import asyncio
import json
import nats

async def publish():
    nc = await nats.connect("nats://localhost:4222")
    message = {
        "event": "item.created",
        "data": {
            "title": "Test from NATS",
            "url": "https://example.com/test",
            "country": "Test",
            "published_text": "Just now",
            "comments": 0
        }
    }
    await nc.publish("items.updates", json.dumps(message).encode())
    await nc.close()

asyncio.run(publish())
```

### Пример подписки на события

```python
import asyncio
import json
import nats

async def subscribe():
    nc = await nats.connect("nats://localhost:4222")
    
    async def handler(msg):
        data = json.loads(msg.data.decode())
        print(f"Received: {data}")
    
    await nc.subscribe("items.updates", cb=handler)
    print("Subscribed to items.updates")
    
    # Держи соединение открытым
    await asyncio.sleep(3600)
    await nc.close()

asyncio.run(subscribe())
```

## Фоновая задача

### Автоматический запуск

Фоновая задача автоматически запускается каждые N секунд (по умолчанию 300 секунд = 5 минут).

Настрой интервал через переменную окружения:
```bash
export FETCH_INTERVAL_SECONDS=60  # каждую минуту
```

### Что делает задача

1. Открывает https://www.hltv.org через Playwright
2. Парсит новости с главной страницы
3. Сохраняет/обновляет новости в БД
4. Публикует событие `task.completed` в NATS и WebSocket

### Ручной запуск

```bash
curl -X POST http://localhost:8000/tasks/run
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `DATABASE_URL` | URL базы данных | `sqlite+aiosqlite:///./news.db` |
| `NATS_URL` | URL NATS сервера | `nats://localhost:4222` |
| `FETCH_INTERVAL_SECONDS` | Интервал фоновой задачи (секунды) | `300` |

## База данных

SQLite база данных создаётся автоматически при первом запуске.

Просмотр данных:
```bash
docker compose exec app sqlite3 /app/news.db 'SELECT * FROM news_items ORDER BY id DESC LIMIT 10;'
```

## Логи

Просмотр логов:
```bash
docker compose logs app -f
```

## Тестирование

### Проверка REST API
```bash
# Получить список
curl http://localhost:8000/items

# Создать новость
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","url":"https://example.com/test"}'

# Обновить новость
curl -X PATCH http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"comments":5}'

# Удалить новость
curl -X DELETE http://localhost:8000/items/1
```

### Проверка WebSocket
1. Подключись к `ws://localhost:8000/ws/items`
2. Выполни CRUD операции через REST API
3. Увидишь события в WebSocket

### Проверка NATS
1. Запусти `python test_nats_pub.py`
2. Проверь логи приложения
3. Проверь БД - должна появиться новая запись

## Troubleshooting

### Playwright не работает
Убедись, что браузер установлен:
```bash
python -m playwright install chromium
```

### NATS не подключается
Проверь, что NATS сервер запущен:
```bash
docker compose ps
```

### База данных не создаётся
Проверь права на запись в директории проекта.

## Статические ресурсы и размещение в Yandex Cloud Storage

Вы можете хранить `HTML` и `CSS` в Yandex Cloud Storage (S3-совместимый бакет) и указывать публичные ссылки в параметре `css_url`, чтобы страница загружала внешний стиль.

1. Подготовьте CSS-файл, например `news.css` (в проекте есть `static/news.css`).
2. Загрузите файл в бакет через веб-интерфейс или `yc`/`aws s3` команды.

Пример загрузки с помощью `aws-cli` (S3-совместимый endpoint Yandex Cloud):

```bash
# пример для yc S3-compatible endpoint, настройте профиль и endpoint заранее
aws --endpoint-url https://storage.yandexcloud.net s3 cp static/news.css s3://my-bucket/path/news.css
```

3. Сделайте объект публичным (в настройках бакета/объекта) или используйте временную ссылку.
4. На клиенте укажите ссылку как query-параметр `css_url` при запросе страницы `/news`:

Пример:
```
# локально
http://localhost:8000/news?css_url=https://storage.yandexcloud.net/my-bucket/path/news.css
```

Если `css_url` не указан или объект недоступен, шаблон использует встроенные стили (фолбек).

Для локной отладки можно просто открыть локальный файл стилей, если настроить отдачу статических файлов через FastAPI (могу помочь настроить `app.mount("/static", StaticFiles(directory="static"), name="static")`, если нужно).


### Использование внешнего хостинга HTML/CSS

По умолчанию endpoint `/news` теперь редиректит на внешний HTML-файл, если в конфигурации задана переменная `EXTERNAL_HTML_URL` (или если задана переменная окружения `EXTERNAL_HTML_URL`). В проекте по умолчанию эти значения установлены на:

- EXTERNAL_HTML_URL: https://storage.yandexcloud.net/prodproject/news.html
- EXTERNAL_CSS_URL: https://storage.yandexcloud.net/prodproject/news.css

Примеры:

- По умолчанию (редирект на внешний HTML):
```
http://localhost:8000/news
```
Ответ: 307 Temporary Redirect -> https://storage.yandexcloud.net/prodproject/news.html

- Принудительно рендерить локальный шаблон, но подключить внешний CSS:
```
http://localhost:8000/news?css_url=https://storage.yandexcloud.net/prodproject/news.css
```

- Перенаправить на другой внешний HTML, указав `html_url` в query:
```
http://localhost:8000/news?html_url=https://storage.yandexcloud.net/prodproject/other.html
```

Как переопределить поведение через переменные окружения:

```bash
# Задать другой внешний HTML
export EXTERNAL_HTML_URL="https://storage.yandexcloud.net/my-bucket/news.html"
# Задать внешний CSS
export EXTERNAL_CSS_URL="https://storage.yandexcloud.net/my-bucket/news.css"
# или unset, чтобы всегда рендерить локально
unset EXTERNAL_HTML_URL
```

Если хотите, чтобы приложение всегда рендерило локально и просто подставляло внешний CSS (без редиректа), скажите — я быстро поменяю логику `/news` (уберу redirect и всегда рендерю шаблон, подставляя EXTERNAL_CSS_URL по умолчанию).


## Лицензия

MIT

