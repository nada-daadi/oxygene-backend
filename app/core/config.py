from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str
    DATABASE_NAME: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    GOOGLE_WEB_CLIENT_ID: str
    GOOGLE_ANDROID_CLIENT_ID: str

    class Config:
        env_file = ".env"


settings = Settings()
