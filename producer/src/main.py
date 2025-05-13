import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from aiokafka import AIOKafkaProducer
from confluent_kafka.schema_registry import SchemaRegistryClient

from src.producer import routers as kafka_routers
from src.config import KafkaConfig

config = KafkaConfig()

async def start_producer():
    """Запуск Kafka Producer"""
    kafka_producer = AIOKafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True
    )
    await kafka_producer.start()
    return kafka_producer


async def shutdown_producer(kafka_producer: AIOKafkaProducer):
    """Остановка Kafka Producer"""
    await kafka_producer.stop()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Добавление kafka producer в объект FastApi, чтобы не запускать producer при каждом запросе"""
    app.kafka_producer = await start_producer()
    app.schema_client = SchemaRegistryClient(dict(url=config.SCHEMA_REGISTRY_SERVER))
    app.include_router(kafka_routers.all_routers)
    yield
    await shutdown_producer(app.kafka_producer)

app = FastAPI(
    title="Kafka producer",
    description="""
            Отправляет сообщения в Kafka
            """,
    version="1.0.0",
    lifespan=lifespan
)

async def start_fastapi():
    """Запуск FastAPI сервера"""
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=9000,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Основная точка входа - запуск веб-сервера Uvicorn
    """
    await asyncio.create_task(
        start_fastapi(),
    )


if __name__ == "__main__":
    asyncio.run(main())
