from pathlib import Path

from pydantic import AnyHttpUrl, EmailStr, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
    )

    app_name: str = "MediaBox"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    frontend_url: AnyHttpUrl = "http://localhost:3005"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_email: EmailStr | None = None
    smtp_use_ssl: bool = False
    password_reset_expire_minutes: int = Field(default=30, ge=5, le=1440)

    @field_validator("smtp_from_email", mode="before")
    @classmethod
    def empty_sender(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    database_url: str = "sqlite:///./mediabox.db"
    # Optional separate password avoids URL-escaping credentials in containers.
    database_password: SecretStr | None = None
    # where downloaded/converted files are stored. Point this at any folder on
    # your computer, e.g. MEDIA_DIR=~/Videos/MediaBox — "~" and relative paths
    # are expanded to an absolute path so serving works regardless of CWD.
    media_dir: Path = Path("./media")

    @field_validator("media_dir")
    @classmethod
    def _resolve_media_dir(cls, value: Path) -> Path:
        return value.expanduser().resolve()
    cors_origins: str = "http://localhost:3000"
    max_download_size_mb: int = 2048
    do_spaces_key: SecretStr = SecretStr("")
    do_spaces_secret: SecretStr = SecretStr("")
    do_spaces_region: str = "sgp1"
    do_spaces_bucket: str = "droplinks-uploads"
    do_spaces_endpoint: AnyHttpUrl = "https://sgp1.digitaloceanspaces.com"
    max_concurrent_downloads: int = 3
    # hosts routed through yt-dlp instead of a direct stream (comma-separated,
    # subdomains included automatically); empty string disables extraction
    ytdlp_hosts: str = "tiktok.com,facebook.com,fb.watch,youtube.com,youtu.be,pornhub.com,instagram.com"
    # optional Netscape cookies.txt for login-gated videos (age-restricted etc.)
    ytdlp_cookies_file: str = ""
    # YouTube JS-challenge solver components (comma-separated, e.g. "ejs:github").
    # Without this, YouTube throttles downloads to a crawl and may 500. The
    # solver script is fetched once from GitHub and cached. Empty disables it.
    ytdlp_remote_components: str = "ejs:github"
    # SSRF guard: set true only in local development to download from
    # localhost / private-network URLs
    allow_private_urls: bool = False


settings = Settings()
settings.media_dir.mkdir(parents=True, exist_ok=True)
