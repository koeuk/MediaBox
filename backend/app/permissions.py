"""Member feature permissions and delegated administrative access."""
from typing import Literal, get_args

PermissionName = Literal[
    'media.view', 'media.create', 'media.edit', 'media.delete',
    'categories.view', 'categories.create', 'categories.edit', 'categories.delete',
    'public_feedback.view', 'public_feedback.create',
    'dashboard.view', 'downloads.view',
    'feedback.view', 'feedback.create', 'feedback.edit', 'feedback.delete',
    'users.view', 'users.edit', 'users.delete',
    'plans.view', 'plans.edit', 'payments.view', 'payments.edit',
]


STANDARD_PERMISSIONS = {
    name: True for name in get_args(PermissionName)
    if name.split('.')[0] in ('media', 'categories', 'public_feedback')
}
ADMIN_PERMISSIONS = tuple(name for name in get_args(PermissionName) if name not in STANDARD_PERMISSIONS)


def get_defaults(db) -> dict[str, bool]:
    if db is None:
        return dict(STANDARD_PERMISSIONS)
    from app.models import AppSetting
    prefix = 'default_perm:'
    known = set(get_args(PermissionName))
    return {
        **STANDARD_PERMISSIONS,
        **{
            row.key[len(prefix):]: row.value == '1'
            for row in db.query(AppSetting).filter(AppSetting.key.startswith(prefix)).all()
            if row.key[len(prefix):] in known
        },
    }


def set_defaults(db, permissions: dict[str, bool]) -> dict[str, bool]:
    from app.models import AppSetting
    for permission in get_args(PermissionName):
        key = f'default_perm:{permission}'
        row = db.get(AppSetting, key)
        value = '1' if permissions.get(permission, STANDARD_PERMISSIONS.get(permission, False)) else '0'
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_defaults(db)


def is_full_admin(user) -> bool:
    return user.is_admin and user.permissions is None


def can(user, permission: str, defaults: dict[str, bool] | None = None) -> bool:
    overrides = user.permissions or {}
    if defaults is None:
        defaults = user.default_permissions
    allowed = overrides.get(permission, defaults.get(permission, user.is_admin))
    section, action = permission.split('.')
    return bool(allowed and (action == 'view' or overrides.get(f'{section}.view', defaults.get(f'{section}.view', user.is_admin))))


def has_admin_access(user) -> bool:
    defaults = user.default_permissions
    return any(can(user, permission, defaults) for permission in ADMIN_PERMISSIONS)
