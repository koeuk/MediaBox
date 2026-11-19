from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, field_validator

from app.models import DownloadStatus
from app.permissions import PermissionName


class AdminStats(BaseModel):
    users: int
    downloads: int
    feedback: int = 0
    reviews: int = 0
    queued: int
    downloading: int
    completed: int
    failed: int
    favorites: int
    bytes_stored: int


class AdminMonthStats(BaseModel):
    month: date
    downloads: int
    new_users: int


class AdminAnalytics(BaseModel):
    start_date: date
    end_date: date
    months: list[AdminMonthStats]


class AdminUserOut(BaseModel):
    default_permissions: dict[PermissionName, bool] = Field(default_factory=dict)
    permissions: dict[PermissionName, bool] | None = None
    id: int
    email: EmailStr
    username: str
    is_admin: bool
    is_suspended: bool
    is_premium: bool
    premium_until: datetime | None
    created_at: datetime
    download_count: int
    bytes_stored: int


class AdminUserEdit(BaseModel):
    """Every field optional — the admin form sends only what it changed."""

    permissions: dict[PermissionName, StrictBool] | None = None
    username: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    is_admin: bool | None = None
    is_suspended: bool | None = None
    # grant a subscription: a plan code extends the account, "" ends it now
    plan: str | None = None
    # an admin reset: no current password, because the whole point is that the
    # account holder cannot supply one
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


class AdminDownloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    title: str | None
    filename: str | None
    url: str
    status: DownloadStatus
    total_bytes: int
    created_at: datetime


class AdminDownloadPageOut(BaseModel):
    items: list[AdminDownloadOut]
    total: int
    page: int
    limit: int
    total_pages: int


class SiteBrandingOut(BaseModel):
    site_title: str
    has_logo: bool


class SiteTitleEdit(BaseModel):
    site_title: str = Field(min_length=1, max_length=60)

    @field_validator("site_title")
    @classmethod
    def validate_site_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Site title cannot be empty or only whitespace.")
        return clean




class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    days: int
    price: float
    is_free: bool
    sort_order: int


class PlanEdit(BaseModel):
    price: float | None = Field(default=None, ge=0)
    is_free: bool | None = None


class AccessSettings(BaseModel):
    paid_mode: bool


class AccessSettings(BaseModel):
    paid_mode: bool


class PaymentRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    plan_code: str
    plan_label: str
    method: str
    amount: float
    status: str
    created_at: datetime


class PaymentSubmit(BaseModel):
    plan_code: str
    method: str
    # no amount: the server charges what the plan costs


class PaymentSettingsOut(BaseModel):
    cash_enabled: bool


class PaymentSettingsEdit(BaseModel):
    cash_enabled: bool


class DefaultPermissions(BaseModel):
    permissions: dict[PermissionName, StrictBool]


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    is_admin: StrictBool = False

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value):
        return value.strip() if isinstance(value, str) else value


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,15}$")
    label: str = Field(min_length=1, max_length=40)
    days: int = Field(ge=1, le=3650, strict=True)
    price: float = Field(default=0, ge=0, le=99999999.99)
    is_free: StrictBool = False

    @field_validator("code", "label", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value
