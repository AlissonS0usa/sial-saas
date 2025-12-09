from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1000
    DATABASE_URL: str

    MQTT_BROKER_HOST: str = "broker.hivemq.com"
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC_ROOT: str = "alissondev007/umidificador"
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()


