from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MediaBox"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = "sqlite:///./mediabox.db"
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
    max_concurrent_downloads: int = 3
    # hosts routed through yt-dlp instead of a direct stream (comma-separated,
    # subdomains included automatically); empty string disables extraction
    ytdlp_hosts: str = "tiktok.com,facebook.com,fb.watch,youtube.com,youtu.be"
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
