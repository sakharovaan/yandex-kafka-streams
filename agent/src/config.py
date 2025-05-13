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
    BLOCKED_TOPIC: str
    CENSOR_TOPIC: str