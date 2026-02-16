"""Application configuration using Pydantic Settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Company
    company_name: str = Field(default="<<YOUR COMPANY>>", alias="COMPANY_NAME")
    timezone: str = Field(default="Asia/Kolkata", alias="TIMEZONE")
    run_time_hhmm: str = Field(default="07:30", alias="RUN_TIME_HHMM")
    
    # Country profile
    country_profile: str = Field(default="IN", alias="COUNTRY_PROFILE")  # IN for India, US, etc.

    # Database
    database_url: str = Field(
        default="postgresql://director_monitor:director_monitor@localhost:5432/director_monitor",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Providers
    providers_enabled: str = Field(default="gdelt", alias="PROVIDERS_ENABLED")
    bing_news_key: str = Field(default="", alias="BING_NEWS_KEY")
    serpapi_key: str = Field(default="", alias="SERPAPI_KEY")
    # India-focused providers
    newsdata_api_key: str = Field(default="", alias="NEWSDATA_API_KEY")
    newsapi_ai_key: str = Field(default="", alias="NEWSAPI_AI_KEY")

    # Classification
    use_llm: bool = Field(default=False, alias="USE_LLM")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    confidence_threshold_alert: float = Field(default=0.75, alias="CONFIDENCE_THRESHOLD_ALERT")

    # Email
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_pass: str = Field(default="", alias="SMTP_PASS")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    from_email: str = Field(default="noreply@example.com", alias="FROM_EMAIL")
    recipients_md: str = Field(default="", alias="RECIPIENTS_MD")
    recipients_admin: str = Field(default="", alias="RECIPIENTS_ADMIN")

    # Storage
    storage_type: str = Field(default="local", alias="STORAGE_TYPE")
    local_storage_dir: str = Field(default="/app/storage", alias="LOCAL_STORAGE_DIR")
    s3_endpoint: str = Field(default="", alias="S3_ENDPOINT")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    # Security
    secret_key: str = Field(default="change-this-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Observability
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Performance
    max_articles_per_director_per_provider: int = Field(
        default=50, alias="MAX_ARTICLES_PER_DIRECTOR_PER_PROVIDER"
    )
    article_fetch_timeout: int = Field(default=30, alias="ARTICLE_FETCH_TIMEOUT")
    article_fetch_retries: int = Field(default=3, alias="ARTICLE_FETCH_RETRIES")

    # Data Retention
    data_retention_days: int = Field(default=365, alias="DATA_RETENTION_DAYS")

    @property
    def enabled_providers_list(self) -> List[str]:
        """Get list of enabled providers."""
        return [p.strip() for p in self.providers_enabled.split(",") if p.strip()]

    @property
    def recipients_md_list(self) -> List[str]:
        """Get list of MD recipients."""
        return [r.strip() for r in self.recipients_md.split(",") if r.strip()]

    @property
    def recipients_admin_list(self) -> List[str]:
        """Get list of admin recipients."""
        return [r.strip() for r in self.recipients_admin.split(",") if r.strip()]


settings = Settings()

