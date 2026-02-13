import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    POSTGRES_USER: str = 'assessment'
    POSTGRES_PASSWORD: str = 'assessment123'
    POSTGRES_DB: str = 'assessment_db'
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ''
    LOG_LEVEL: str = 'INFO'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f'postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}'
            f'@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
        )


settings = Settings()
