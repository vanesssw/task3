# Примеры использования API

## Swagger UI

Открой в браузере: **http://localhost:8000/docs**

Swagger UI предоставляет интерактивную документацию со всеми эндпоинтами и возможностью тестирования прямо в браузере.

## REST API Примеры

### 1. Получить список новостей

```bash
curl http://localhost:8000/items?limit=10&offset=0
```

**Ответ:**
```json
[
  {
    "id": 1,
    "title": "News title",
    "url": "https://example.com/news",
    "country": "USA",
    "published_text": "2 hours ago",
    "comments": 5,
    "created_at": "2025-12-10T14:00:00",
    "updated_at": "2025-12-10T14:00:00"
  }
]
```

### 2. Получить новость по ID

```bash
curl http://localhost:8000/items/1
```

### 3. Создать новость

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New News",
    "url": "https://example.com/new-news",
    "country": "USA",
    "published_text": "1 hour ago",
    "comments": 0
  }'
```

### 4. Обновить новость

```bash
curl -X PATCH http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "comments": 10
  }'
```

### 5. Удалить новость

```bash
curl -X DELETE http://localhost:8000/items/1
```

### 6. Принудительно запустить фоновую задачу

```bash
curl -X POST http://localhost:8000/tasks/run
```

**Ответ:**
```json
{
  "status": "scheduled",
  "timestamp": "2025-12-10T14:00:00",
  "count": 10
}
```

## WebSocket Примеры

### JavaScript (браузер)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/items');

ws.onopen = () => {
    console.log('Подключено к WebSocket');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Событие:', data.event);
    console.log('Данные:', data.data);
};

ws.onerror = (error) => {
    console.error('Ошибка WebSocket:', error);
};

ws.onclose = () => {
    console.log('Отключено от WebSocket');
};
```

### Python

```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8000/ws/items"
    async with websockets.connect(uri) as websocket:
        print("Подключено к WebSocket")
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Событие: {data['event']}")
            print(f"Данные: {data['data']}")

asyncio.run(websocket_client())
```

### wscat

```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/items
```

## NATS Примеры

### Publisher (отправка сообщений)

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
    print("Сообщение отправлено")
    await nc.close()

asyncio.run(publish())
```

### Subscriber (подписка на сообщения)

```python
import asyncio
import json
import nats

async def subscribe():
    nc = await nats.connect("nats://localhost:4222")
    
    async def handler(msg):
        data = json.loads(msg.data.decode())
        print(f"Получено: {data}")
    
    await nc.subscribe("items.updates", cb=handler)
    print("Подписан на items.updates")
    
    # Держим соединение открытым
    await asyncio.sleep(3600)
    await nc.close()

asyncio.run(subscribe())
```

### Использование тестовых скриптов

**Publisher:**
```bash
python test_nats_pub.py
```

**Subscriber:**
```bash
python test_nats_sub.py
```

## Формат событий WebSocket

### item.created
```json
{
  "event": "item.created",
  "data": {
    "id": 1,
    "title": "News title",
    "url": "https://example.com/news",
    "country": "USA",
    "published_text": "2 hours ago",
    "comments": 5,
    "created_at": "2025-12-10T14:00:00",
    "updated_at": "2025-12-10T14:00:00"
  }
}
```

### item.updated
```json
{
  "event": "item.updated",
  "data": {
    "id": 1,
    "title": "Updated title",
    "url": "https://example.com/news",
    "country": "USA",
    "published_text": "2 hours ago",
    "comments": 10,
    "created_at": "2025-12-10T14:00:00",
    "updated_at": "2025-12-10T15:00:00"
  }
}
```

### item.deleted
```json
{
  "event": "item.deleted",
  "data": {
    "id": 1
  }
}
```

### task.completed
```json
{
  "event": "task.completed",
  "data": {
    "timestamp": "2025-12-10T14:00:00",
    "count": 10
  }
}
```

### nats.forwarded
```json
{
  "event": "nats.forwarded",
  "data": {
    "event": "item.created",
    "data": {
      "title": "Test",
      "url": "https://example.com/test"
    }
  }
}
```

