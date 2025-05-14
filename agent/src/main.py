import json

import faust
from faust.web import Request, Response, View
from confluent_kafka.schema_registry.avro import \
    AvroSerializer, AvroDeserializer, \
    SerializationContext, SchemaRegistryClient
from loguru import logger

from src.schemas import Message, CensoredWord, BlockedUser
from src.config import KafkaConfig


config = KafkaConfig()


# Инициализация приложения
app = faust.App(
    "censorship-app",
    broker=config.KAFKA_BROKERS,
    store=config.FAUST_STORE,
    value_serializer="raw"
)

# Таблицы
censored_words = app.Table('censored_words', default=list)
blocked_users = app.Table('blocked_users', default=list)

# Входной и выходной топики
msg_input_topic = app.topic(config.INPUT_TOPIC, key_type=str, value_type=bytes)
msg_output_topic = app.topic(config.OUTPUT_TOPIC, key_type=str, value_type=bytes)
blocked_topic = app.topic(config.BLOCKED_TOPIC, key_type=str, value_type=bytes)
censor_topic = app.topic(config.CENSOR_TOPIC, key_type=str, value_type=bytes)

# (Де)сериализаторы и подключение к Schema Registry
schema_client = SchemaRegistryClient(dict(url=config.SCHEMA_REGISTRY_SERVER))

msg_serializer = AvroSerializer(schema_client, json.dumps(Message.avro_schema()))
msg_deserializer = AvroDeserializer(schema_client, json.dumps(Message.avro_schema()))
msg_input_context = SerializationContext(config.INPUT_TOPIC, "message")
msg_output_context = SerializationContext(config.OUTPUT_TOPIC, "message")

blocked_deserializer = AvroDeserializer(schema_client, json.dumps(BlockedUser.avro_schema()))
blocked_context = SerializationContext(config.BLOCKED_TOPIC, "blockedusers")

censored_deserializer = AvroDeserializer(schema_client, json.dumps(CensoredWord.avro_schema()))
censored_context = SerializationContext(config.CENSOR_TOPIC, "censoredwords")


# обработка сообщений
@app.agent(msg_input_topic)
async def process_messages(stream):
    async for message in stream:
        message = msg_deserializer(message, msg_input_context)
        logger.info(f'Got message {message}')

        if message['username'] in blocked_users[message['to_user']]:
            logger.info(f'User {message["to_user"]} blocked {message["username"]}, ignoring message')
            continue
        
        for word in censored_words['words']:
            message['text'] = message['text'].replace(f'{word}', f'{"*" * len(word)}')

        await msg_output_topic.send(value=msg_serializer(message, msg_output_context))


# обработка запросов на блокировку пользователей
@app.agent(blocked_topic)
async def process_blocked_users(stream):
    async for message in stream:
        message = blocked_deserializer(message, blocked_context)
        logger.info(f'Got new block request {message}')

        # чехарда с получением значения - требование Faust
        blocked_users_for_user = blocked_users[message['blocking_user']]
        blocked_users_for_user.append(message['blocked_user'])
        blocked_users[message['blocking_user']] = blocked_users_for_user


# обработка запросов на добавление цензурируемых слов
@app.agent(censor_topic)
async def process_censored_words(stream):
    async for message in stream:
        message = censored_deserializer(message, censored_context)
        logger.info(f'Got new censored word {message}')

        # чехарда с получением значения - требование Faust
        words = censored_words['words']
        words.append(message['word'])
        censored_words['words'] = words


# возможность получить список текущих цензурируемых слов
@app.page('/config/censored_words')
@app.table_route(table=censored_words, exact_key='words')
async def get_censored_words(web, request) -> Response:
    return web.json({'censored_words': censored_words['words']})
    

# возможность получить список текущих заблокированных пользователей для пользователя
@app.page('/config/blocked_users/{user}')
@app.table_route(table=blocked_users, match_info='user')
async def get_blocked_users(web, request, user) -> Response:
    return web.json({'blocked_users': blocked_users[user]})
