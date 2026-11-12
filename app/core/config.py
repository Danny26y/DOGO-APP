from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DOGO Backend"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./dogo.db"
    jwt_secret: str = "development-only-change-this-secret-before-deploying"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 30
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    platform_admin_emails: str = ""
    customer_verification_terms_version: str = ""
    customer_verification_terms_url: str = ""
    privacy_policy_version: str = ""
    privacy_policy_url: str = ""
    # Provider credentials are optional until sandbox/live integrations are enabled.
    paystack_secret_key: str = ""
    paystack_public_key: str = ""
    paystack_base_url: str = "https://api.paystack.co"
    email_otp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    osrm_base_url: str = ""
    geocoding_base_url: str = ""
    email_otp_ttl_minutes: int = 10
    verification_upload_dir: str = "./private_uploads/verification"

    @property
    def platform_admin_email_set(self) -> set[str]:
        return {item.strip().lower() for item in self.platform_admin_emails.split(",") if item.strip()}

    @field_validator("jwt_secret")
    @classmethod
    def require_strong_production_secret(cls, value: str, info):
        environment = info.data.get("environment", "development")
        if environment.lower() == "production" and (len(value) < 32 or value.startswith("development-only")):
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
