"""User role enumeration."""

from enum import Enum


class UserRole(str, Enum):
    """Enum representing user roles on Nyaa.si."""

    TRUSTED = "trusted"
    UPLOADER = "uploader"
