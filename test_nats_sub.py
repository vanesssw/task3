#!/usr/bin/env python3
"""Тестовый скрипт для подписки на NATS сообщения"""
import asyncio
import json
import sys

try:
    import nats
except ImportError:
    print("Установи nats-py: pip install nats-py")
    sys.exit(1)


async def subscribe_to_nats():
    nc = await nats.connect("nats://localhost:4222")
    
    async def message_handler(msg):
        try:
            payload = json.loads(msg.data.decode())
            print(f"\n Получено сообщение из NATS:")
            print(f"   Subject: {msg.subject}")
            print(f"   Data: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
    
    await nc.subscribe("items.updates", cb=message_handler)
    print("Подписан на subject: items.updates")
    print("Ожидание сообщений... (Ctrl+C для выхода)\n")
    
    try:
        await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n\nОтключение от NATS...")
    finally:
        await nc.close()


if __name__ == "__main__":
    asyncio.run(subscribe_to_nats())

