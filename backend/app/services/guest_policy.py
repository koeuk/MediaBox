"""Guest quality policy stored as one atomic setting; no database migration needed."""

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AppSetting
from app.schemas.public import GuestQualitySettings

SETTING_KEY = "guest_quality_settings"


def load(db: Session) -> GuestQualitySettings:
    row = db.get(AppSetting, SETTING_KEY)
    return GuestQualitySettings.model_validate_json(row.value) if row else GuestQualitySettings()


def save(db: Session, policy: GuestQualitySettings) -> GuestQualitySettings:
    row = db.get(AppSetting, SETTING_KEY)
    if row is None:
        row = AppSetting(key=SETTING_KEY)
        db.add(row)
    row.value = policy.model_dump_json()
    db.commit()
    return policy


def current() -> GuestQualitySettings:
    # Resolve a plain settings snapshot and release the DB connection before
    # the guest's synchronous download holds the request open.
    with SessionLocal() as db:
        return load(db)
