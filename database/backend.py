"""Choose persistent storage for application documents."""

from __future__ import annotations

import os

from database.mysql_connection import connection_options


def use_mysql() -> bool:
    """Railway must use MySQL; local runs may keep their existing SQLite data."""
    if connection_options() is not None:
        return True
    if os.environ.get("RAILWAY_PROJECT_ID"):
        raise RuntimeError("Railway chưa cấu hình MYSQL_URL cho service ứng dụng")
    return False
