"""Request/response models, grouped by the router that uses them.

Everything is re-exported here, so `from app.schemas import DownloadOut` keeps
working regardless of which module a model actually lives in.
"""

from app.schemas.admin import AdminDownloadOut, AdminStats, AdminUserOut
from app.schemas.auth import (
    MediaTokenOut,
    ProfileUpdate,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.schemas.category import HEX_COLOR_PATTERN, CategoryCreate, CategoryEdit, CategoryOut
from app.schemas.download import (
    CONVERT_TARGET_PATTERN,
    CUTOUT_QUALITY_PATTERN,
    QUALITY_PATTERN,
    BatchDownloadCreate,
    ConvertRequest,
    DownloadCategoryUpdate,
    DownloadCreate,
    DownloadOut,
    RemoveBackgroundRequest,
)

__all__ = [
    # auth
    "UserCreate",
    "UserLogin",
    "ProfileUpdate",
    "UserOut",
    "TokenOut",
    "MediaTokenOut",
    # downloads
    "DownloadCreate",
    "BatchDownloadCreate",
    "DownloadCategoryUpdate",
    "ConvertRequest",
    "RemoveBackgroundRequest",
    "DownloadOut",
    "QUALITY_PATTERN",
    "CONVERT_TARGET_PATTERN",
    "CUTOUT_QUALITY_PATTERN",
    # categories
    "CategoryCreate",
    "CategoryEdit",
    "CategoryOut",
    "HEX_COLOR_PATTERN",
    # admin
    "AdminStats",
    "AdminUserOut",
    "AdminDownloadOut",
]
