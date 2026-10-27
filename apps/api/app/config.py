from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: str = 'development'
    database_url: str = 'postgresql+asyncpg://auction:local_dev_only@localhost:5432/auction'
    redis_url: str = 'redis://localhost:6379/0'
    app_secret: str = Field(min_length=32)
    web_origin: str = 'http://localhost:3000'
    cookie_secure: bool = False
    metrics_token: str = Field(min_length=12)
    sentry_dsn: str | None = None

    @model_validator(mode='after')
    def production_guards(self):
        if self.app_env == 'production':
            if not self.cookie_secure or not self.web_origin.startswith('https://'):
                raise ValueError('Production requires HTTPS WEB_ORIGIN and COOKIE_SECURE=true')
            if 'replace_me' in self.app_secret or 'local_' in self.app_secret:
                raise ValueError('Configure a unique production APP_SECRET')
        return self

settings = Settings()
