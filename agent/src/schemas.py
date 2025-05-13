from pydantic_avro.base import AvroBase

# Схемы сообщений
class Message(AvroBase):
    username: str
    to_user: str
    text: str


class CensoredWord(AvroBase):
    word: str


class BlockedUser(AvroBase):
    blocking_user: str
    blocked_user: str
