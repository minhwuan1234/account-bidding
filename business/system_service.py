"""Operational checks exposed to the presentation layer."""

from database.mysql_connection import check_connection


def database_status() -> dict[str, bool | str]:
    return check_connection()
