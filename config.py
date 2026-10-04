from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    cache_ttl: int = 60  # مدت زمان کش به ثانیه (پیش‌فرض ۱ دقیقه)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

config = Settings()