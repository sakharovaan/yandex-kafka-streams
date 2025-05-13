import asyncio
import json

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from aiokafka import AIOKafkaProducer
from confluent_kafka.schema_registry.avro import AvroSerializer, SerializationContext
from loguru import logger

from src.producer.schemas import Message, BlockedUser, CensoredWord
from src.main import config

event_loop = asyncio.get_event_loop()

router = APIRouter()

@router.post(
    "/send",
    description="Send message to kafka",
)
async def send_kafka(message: Message, request: Request) -> None:
    
    serializer = AvroSerializer(request.app.schema_client, json.dumps(message.avro_schema()))
    logger.info(json.dumps(message.model_dump_json()))

    await request.app.kafka_producer.send(value=serializer(message.model_dump(),
                                                           SerializationContext(config.KAFKA_TOPIC, "message")), 
                                                           topic=config.KAFKA_TOPIC)
    

@router.post(
    "/censor",
    description="Censor word in messages"
)
async def censor_word(word: CensoredWord, request: Request) -> None:
    serializer = AvroSerializer(request.app.schema_client, json.dumps(word.avro_schema()))
    logger.info(json.dumps(word.model_dump_json()))

    await request.app.kafka_producer.send(value=serializer(word.model_dump(),
                                                        SerializationContext(config.KAFKA_CENSOR_TOPIC, "censoredwords")), 
                                                        topic=config.KAFKA_CENSOR_TOPIC)


@router.post(
    "/block_user",
    description="Block user for another user"
)
async def block_user(user: BlockedUser, request: Request) -> None:
    serializer = AvroSerializer(request.app.schema_client, json.dumps(user.avro_schema()))
    logger.info(json.dumps(user.model_dump_json()))

    await request.app.kafka_producer.send(value=serializer(user.model_dump(),
                                                        SerializationContext(config.KAFKA_BLOCKED_TOPIC, "blockedusers")), 
                                                        topic=config.KAFKA_BLOCKED_TOPIC)