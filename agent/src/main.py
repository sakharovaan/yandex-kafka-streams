import os
import json

import faust
from confluent_kafka.schema_registry.avro import \
    AvroSerializer, AvroDeserializer, \
    SerializationContext, SchemaRegistryClient
from loguru import logger
from pydantic_avro.base import AvroBase
from pydantic_settings import BaseSettings, SettingsConfigDict

# Конфигурация
class ConfigBase(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class KafkaConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="AGENT_") 

    KAFKA_BROKERS: str
    SCHEMA_REGISTRY_SERVER: str
    FAUST_STORE: str
    INPUT_TOPIC: str
    OUTPUT_TOPIC: str

config = KafkaConfig()

# Схема сообщения
class Message(AvroBase):
    text: str

# Инициализация приложения
app = faust.App(
    "censorship-app",
    broker=config.KAFKA_BROKERS,
    store=config.FAUST_STORE,
    value_serializer="raw"
)

# Входной и выходной топики
input_topic = app.topic(config.INPUT_TOPIC, key_type=str, value_type=bytes)
output_topic = app.topic(config.OUTPUT_TOPIC, key_type=str, value_type=bytes) 

# (Де)сериализаторы и подключение к Schema Registry
schema_client = SchemaRegistryClient(dict(url=config.SCHEMA_REGISTRY_SERVER))
serializer = AvroSerializer(schema_client, json.dumps(Message.avro_schema()))
deserializer = AvroDeserializer(schema_client, json.dumps(Message.avro_schema()))
input_context = SerializationContext(config.INPUT_TOPIC, "message")
output_context = SerializationContext(config.OUTPUT_TOPIC, "message")

@app.agent(input_topic)
async def process_messages(stream):
    async for message in stream:
        message = deserializer(message, input_context)
        logger.info(f'Got message {message}')

        await output_topic.send(value=serializer(message, output_context))
