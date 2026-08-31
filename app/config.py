from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_url: str
    redis_url: str
    openai_api_key: str | None = None
    openai_text_model: str = "gpt-4.1-mini"
    openai_image_model: str = "gpt-image-1"
    openai_transcribe_model: str = "gpt-4o-mini-transcribe"
    public_base_url: str = ""
    webhook_path: str = "/telegram/webhook"
    app_env: str = "production"
    log_level: str = "INFO"
    max_message_chars: int = 12000
    free_daily_ai: int = 20
    free_daily_voice: int = 3
    free_daily_file: int = 3
    free_daily_image: int = 1
    default_max_file_mb: int = 15
    default_referral_reward: int = 1
    broadcast_pause_ms: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_id_set(self) -> set[int]:
        result: set[int] = set()
        for item in self.admin_ids.split(","):
            if item.strip().isdigit():
                result.add(int(item.strip()))
        return result

@lru_cache
def get_settings() -> Settings:
    return Settings()
