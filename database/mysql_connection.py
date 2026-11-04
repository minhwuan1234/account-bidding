"""Railway MySQL connectivity only; application data is not migrated yet."""

from __future__ import annotations

import os
from urllib.parse import unquote, urlparse


def connection_options() -> dict[str, object] | None:
    """Read Railway's MYSQL_URL or its individual MYSQL* variables."""
    url = os.environ.get("MYSQL_URL", "").strip()
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise ValueError("MYSQL_URL must use the mysql scheme")
        if not all((parsed.hostname, parsed.username, parsed.path.strip("/"))):
            raise ValueError("MYSQL_URL is missing a host, user, or database")
        options = {
            "host": parsed.hostname,
            "port": parsed.port or 3306,
            "user": unquote(parsed.username),
            "password": unquote(parsed.password or ""),
            "database": unquote(parsed.path.lstrip("/")),
        }
    else:
        host = os.environ.get("MYSQLHOST", "").strip()
        user = os.environ.get("MYSQLUSER", "").strip()
        database = os.environ.get("MYSQLDATABASE", "").strip()
        if not all((host, user, database)):
            return None
        options = {
            "host": host,
            "port": int(os.environ.get("MYSQLPORT", "3306")),
            "user": user,
            "password": os.environ.get("MYSQLPASSWORD", ""),
            "database": database,
        }
    return {**options, "charset": "utf8mb4", "connect_timeout": 3, "read_timeout": 3, "write_timeout": 3}


def connect():
    """Open a MySQL connection; caller owns and closes it."""
    options = connection_options()
    if options is None:
        raise RuntimeError("MySQL is not configured for this application service")
    import pymysql

    return pymysql.connect(**options)


def check_connection() -> dict[str, bool | str]:
    """Probe SELECT 1 without returning server details or credentials."""
    try:
        if connection_options() is None:
            return {"configured": False, "connected": False}
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return {"configured": True, "connected": True}
    except Exception:
        return {"configured": True, "connected": False}
