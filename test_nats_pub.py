#!/usr/bin/env python3
"""Тестовый скрипт для отправки сообщений в NATS"""
import asyncio
import json
import sys

try:
    import nats
except ImportError:
    print("Установи nats-py: pip install nats-py")
    sys.exit(1)


async def publish_message():
    """Публикует тестовое сообщение в NATS"""
    nc = await nats.connect("nats://localhost:4222")
    
    from datetime import datetime

    messages = [
        {
            "event": "item.created",
            "data": {
                "title": f"Test News from NATS - {datetime.now().strftime('%H:%M:%S')}",
                "url": f"https://example.com/test-nats-{datetime.now().timestamp()}",
                "country": "Test",
                "published_text": "Just now",
                "comments": 0
            }
        },
    ]
    
    for message in messages:
        await nc.publish("items.updates", json.dumps(message).encode())
        print(f"   Отправлено сообщение в NATS:")
        print(f"   Subject: items.updates")
        print(f"   Event: {message['event']}")
        print(f"   Data: {json.dumps(message['data'], indent=2, ensure_ascii=False)}\n")
    
    await nc.close()
    print(" Проверь логи приложения и WebSocket для подтверждения получения сообщения")


if __name__ == "__main__":
    asyncio.run(publish_message())

