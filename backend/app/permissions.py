"""Permissions for delegated access to administrative sections."""
from typing import Literal

PermissionName = Literal[
    'dashboard.view', 'downloads.view',
    'feedback.view', 'feedback.create', 'feedback.edit', 'feedback.delete',
    'users.view', 'users.edit', 'users.delete',
    'plans.view', 'plans.edit', 'payments.view', 'payments.edit',
]


def is_full_admin(user) -> bool:
    return user.is_admin and user.permissions is None


def can(user, permission: str) -> bool:
    overrides = user.permissions or {}
    allowed = overrides.get(permission, user.is_admin)
    section, action = permission.split('.')
    return bool(allowed and (action == 'view' or overrides.get(f'{section}.view', user.is_admin)))
